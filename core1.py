from config import *

from machine import Pin
from sensors import spi0
import _thread, time, buffer, json

from enc28j60 import Ntw
from enc28j60.uDnsClient import DnsClientNtw
from tcp4clientX import TCP4client
from tcp4server import TCP4server

last_send = time.time()  #last time data was sent
ethernet_lock = _thread.allocate_lock()  #lock for ethernet access

def tail(filename, n=1, block_size=128): 
    """Read the last n lines of a text file efficiently on MicroPython.""" 
    with open(filename, 'rb') as f: 
        f.seek(0, 2) # go to end of file 
        file_size = f.tell() 
        data = b'' 
        lines = [] 
        pos = file_size # read backwards in small blocks until we get enough lines
        while pos > 0 and len(lines) <= n: 
            read_size = min(block_size, pos) 
            pos -= read_size 
            f.seek(pos) 
            data = f.read(read_size) + data 
        lines = data.split(b'\n') # convert bytes to strings and strip 
        result = [line.decode().strip() for line in lines if line] 
        return result[-n:]

def ethernet_disable():
    ethernet_lock.acquire()

def ethernet_enable():
    ethernet_lock.release()

class Server:
    def __init__(self, port, ntw, ether) -> None:
        self.ntw = ntw
        self.ether = ether
        self.server = TCP4server(ntw, port, 10)
        self.server.page("/", "<h1>This is the webserver of GML weatherstation</h1>")
        self.server.page("/time",self.time)
        self.server.page("/data",self.data)
        self.server.page("/log",self.log)
        
    def run(self,):
        self.server.loop()
        
    def time(self, *args):
        return f"Current time on Pico is {time.time()} - {time.gmtime()}"
    
    def data(self, *args):
        count = len(buffer.buffer)
        out = '''<h1>measured data</h1>
        <pre style="text-align: left;">
        '''
    
        out += f"datapackets waits to send: {count}\r\n"
        out += f"last sended measurement: \r\n"
        for k in json.loads(self.ether.payload)["sensordatavalues"]:
            out += f"\t- {k["value_type"]} : {k["value"]}\r\n"
        out += "</pre>"
        return out
    
    def log(self, *args):
        out = "<h1>logs</h1>"
        with meteo_l.lock:
            o = tail(meteo_l.file, 5)
            for i in o:
                if type(i) == str:
                    out += i
        return out

class EthernetThread:
    def __init__(self, server, port):
        print("init")
        self.ethernet = _thread.allocate_lock()
        self.server, self.port = server, port
        self.online = False
        self.ntw = Ntw.Ntw(spi0, Pin(17))
        self.ntw.setIPv4(ip, mask, gw_ip)
        self.dns_client = DnsClientNtw(self.ntw, 567)
        self.dns_client.set_serv_addr(bytes([8,8,8,8]))
        self.payload = ""
        self.enable_prints = True  #enable prints for debugging
        self.port_range = (1000, 2000)
        self.reset()  #inits tcp4client and session

        self.my_server = Server(80, self.ntw, self)


    def reset(self):    #resets tcp client and session
        print("resetting")
        for port in self.ntw.tcp4UniBind.keys():
            if port >= self.port_range[0] and port <= self.port_range[1]:
                self.ntw.registerTcp4Callback(port, None)
        self.tcp = TCP4client(self.ntw, self.dns_client, max_messages=20, port_min=self.port_range[0], port_max=self.port_range[1])
        s = self.tcp.new_connection(domain=self.server, tgt_port=self.port, keep=True)
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

            if self.session.state == -1:    #if tcp offline check if data was sent successfuly and than send new data
                for s in self.session.responses:
                    s = bytes(s)
                    print("response: ", s)
                    if b'OK' in s and self.payload in buffer.buffer:
                        buffer.remove(self.payload)
                        print("successfuly sended")
                self.session.responses = []
                status = self.send()
                global last_send
                last_send = time.time()
                print(status)
                '''if status == -1:    #buffer empty, reset tcp4client
                    self.reset()'''
            elif last_send + 60 <= time.time():
                self.reset()
        
        self.my_server.run()
        
        ethernet_lock.release()

    def send(self):
        if self.enable_prints:
            print("sending...", last_send, time.time())
        line = buffer.read_first()  #tries to get data from buffer
        if line == None:    #if buffer empty, return
            return -1
        
        self.payload = line
        
        print("payload:", self.payload)
        try:
            data = self.payload.strip()
            # construct and send HTTP request
            self.session.send(
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Length: {}\r\n"
                "Connection-Type: closed\r\n\r\n"
                "{}".format(path, server, len(data), data)
            )
        except Exception as e:
            print("network send failed:", e)
            # do not advance offset; retry later
            return
        
if __name__ == "__main__":
    ether = EthernetThread(server, port) #inits ethernet
    while True:
        try:
            ether.run()
            time.sleep(1)
        except Exception as e:
                import sys
                sys.print_exception(e)
                print("Exception in ethernet: ", e)
                
                core1_wants_restart = True  #sets flag to restart core1
                _thread.exit()  #exits thread on error