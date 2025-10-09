from config import *
import buffer

from machine import Pin
from sensors import spi0
import _thread, time

from enc28j60 import Ntw
from enc28j60.uDnsClient import DnsClientNtw
from tcp4clientX import TCP4client

last_send = time.time()  #last time data was sent

ethernet_lock = _thread.allocate_lock()  #lock for ethernet access

def ethernet_disable():
    ethernet_lock.acquire()

def ethernet_enable():
    ethernet_lock.release()
    
class EthernetThread:
    def __init__(self):
        self.ethernet = _thread.allocate_lock()
        self.online = False
        self.ntw = Ntw.Ntw(spi0, Pin(17))
        self.ntw.setIPv4(ip, mask, gw_ip)
        self.dns_client = DnsClientNtw(self.ntw, 567)
        self.dns_client.set_serv_addr(bytes([8,8,8,8]))
        self.payload = ""
        self.enable_prints = True  #enable prints for debugging
        self.port_range = (1000, 2000)
        self.reset()  #inits tcp4client and session

    def reset(self):    #resets tcp client and session
        for port in self.ntw.tcp4UniBind.keys():
            if port >= self.port_range[0] and port <= self.port_range[1]:
                self.ntw.registerTcp4Callback(port, None)
        self.tcp = TCP4client(self.ntw, self.dns_client, max_messages=20, port_min=self.port_range[0], port_max=self.port_range[1])
        s = self.tcp.new_connection(domain=server, tgt_port=port, keep=True)
        while type(s) is not TCP4client.Session:
            print("Waiting for TCP session to be created... Error: ", s)
            s = self.tcp.new_connection(domain=server, tgt_port=port, keep=True)
        self.session = s

    def run(self):
        ethernet_lock.acquire()
        self.ntw.rxAllPkt()
        if not self.ntw.configIp4Done or not self.ntw.nic.IsLinkUp():
            print("Waiting for link/IP...")
            time.sleep(1)
            # Skip DNS/TCP until Ethernet is ready
        else:
            try:
                self.dns_client.loop()
            except Exception as e:
                print("dns_client error: ", e)

            if not self.dns_client.is_serv_addr_set():
                self.dns_client.set_serv_addr(self.ntw.getDnsSrvIpv4())

            self.tcp.loop()

            if self.session.state == -1:    #if tcp offline send data
                status = self.send()
                global last_send
                last_send = time.time()
                print(status)
                if status == -1:    #buffer empty, reset tcp4client
                    self.reset()
            elif last_send >= time.time() - 60:
                self.reset()
                        
        ethernet_lock.release()

    def send(self):
        if self.enable_prints:
            print("sending...", last_send, time.time())
        line = buffer.get_entry()  #tries to get data from buffer
        if line == None:    #if buffer empty, return
            return -1
        
        try:
            self.payload = line.strip("\n")
        except Exception:
            # fallback, keep as ascii-ish
            self.payload = str(line)
        print("payload:", self.payload)
        try:
            # construct and send HTTP request
            self.session.send(
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Length: {}\r\n"
                "Connection-Type: closed\r\n\r\n"
                "{}".format(path, server, len(self.payload), self.payload)
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