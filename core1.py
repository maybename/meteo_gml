from config import *
from machine import Pin
from sensors import spi0
import _thread
import time, gc

from enc28j60 import Ntw
from enc28j60.uDnsClient import DnsClientNtw
from tcp4clientX import TCP4client

def read_line(filename, start_pos=0): #reads one line from start_pos and returns the end pos and line
    """Resume reading from file at start_pos, return new pos after last read"""
    with open(filename, "r") as f:
        f.seek(start_pos)  # jump to saved position
        for line in f:
            line = line.strip()

            # Save current position for next time
            pos = f.tell()
            return pos, line   # stop after one line
    return start_pos, None  # EOF reached



class EthernetThread:
    def __init__(self, fileq=_thread.allocate_lock()):
        self.ethernet = _thread.allocate_lock()
        self.online = False
        self.ntw = Ntw.Ntw(spi0, Pin(17))
        self.ntw.setIPv4(ip, mask, gw_ip)
        self.dns_client = DnsClientNtw(self.ntw, 567)
        self.dns_client.set_serv_addr(bytes([8,8,8,8]))
        self.fileq = fileq
        self.pointer = 0
        self.pointer_file = "eth.pointer"
        try:
            with open(self.pointer_file, "r") as f:
                self.pointer = int(f.readline())
        
        except OSError:
            self.save_pointer()  # if there is no pointer file create one
        
        self.tcp = TCP4client(self.ntw, self.dns_client, max_messages=20)
        s = self.tcp.new_connection(domain=server, tgt_port=port, keep=True)
        while type(s) is not TCP4client.Session:
            print("Waiting for TCP session to be created... Error: ", s)
            s = self.tcp.new_connection(domain=server, tgt_port=port, keep=True)
        self.session = s

    def disable(self):
        self.ethernet.acquire()
    
    def enable(self):
        self.ethernet.release()

    def save_pointer(self):
        with open(self.pointer_file, "w") as f:
            f.write(str(self.pointer))

    def run(self):
        self.ethernet.acquire()
        self.ntw.rxAllPkt()
        gc.collect()
        if not self.ntw.configIp4Done or not self.ntw.nic.IsLinkUp():
            print("Waiting for link/IP...")
            time.sleep(1)
            # Skip DNS/TCP until Ethernet is ready
        else:
            try:
                self.dns_client.loop()
            except Exception as e:
                print("dns_client error: ", e)
            gc.collect()

            if not self.dns_client.is_serv_addr_set():
                self.dns_client.set_serv_addr(self.ntw.getDnsSrvIpv4())

            self.tcp.loop()
            if self.session.state == -1:    #if tcp offline send data
                if self.send() == -1:
                    time.sleep(5)  #wait a second to give core0 time to write new data

            gc.collect()
        self.ethernet.release()
        
    def send(self):
        print("sending...")
        self.fileq.acquire()
        try:
            self.pointer, line = read_line(data_file, self.pointer)
            if line == None:
                with open(data_file, "w") as f:
                    pass  # truncate file if EOF reached
                self.pointer = 0
                self.save_pointer()
                return -1  # nothing to send
            
        except OSError as e:
                print("send: file read error", e)
                return -2
        finally:
            # release quickly so core0 can append while we perform network I/O
            self.fileq.release()

        try:
            payload = line.strip("\n")
        except Exception:
            # fallback, keep as ascii-ish
            payload = str(line)
        print("payload:", payload)
        try:
            # construct and send HTTP request
            body = payload
            self.session.send(
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Length: {}\r\n"
                "Connection-Type: closed\r\n\r\n"
                "{}".format(path, server, len(body), body)
            )
        except Exception as e:
            print("network send failed:", e)
            # do not advance offset; retry later
            return
        
if __name__ == "__main__":
    ether = EthernetThread() #inits ethernet
    while True:
        try:
            ether.run()
        except Exception as e:
                import sys
                sys.print_exception(e)
                print("Exception in ethernet: ", e)
                
                core1_wants_restart = True  #sets flag to restart core1
                _thread.exit()  #exits thread on error