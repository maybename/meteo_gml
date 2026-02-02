from config import *

from machine import Pin
from lib.sensors import spi0
import _thread, time

from enc28j60 import Ntw
from enc28j60.uDnsClient import DnsClientNtw

from sender import Sender
from server import Server


ethernet_lock = _thread.allocate_lock()  #lock for ethernet access

def ethernet_disable():
    ethernet_lock.acquire()

def ethernet_enable():
    ethernet_lock.release()


class EthernetThread:
    def __init__(self, server, port, lock: _thread.LockType = ethernet_lock):
        print("init")
        self.ethernet = lock
        self.ethernet.acquire()
        self.server, self.port = server, port
        self.ntw = Ntw.Ntw(spi0, Pin(17))
        self.ntw.setIPv4(ip, mask, gw_ip)
        self.enable_prints = True  #enable prints for debugging
        
        self.my_server = Server(80, self.ntw, self)
        self.dns_client = DnsClientNtw(self.ntw, 567)
        self.dns_client.set_serv_addr(bytes([8,8,8,8]))
        self.sender = Sender(self.ntw, self.dns_client, (1000, 2000), server, tgt_path=path, prints=self.enable_prints)
        
        self.ethernet.release()

    def run(self):
        self.ethernet.acquire()

        self.ntw.rxAllPkt()
        if not self.ntw.configIp4Done or not self.ntw.nic.IsLinkUp():
            if self.enable_prints:
                print("Waiting for link/IP...")
            time.sleep(1)
            # Skip DNS/TCP until Ethernet is ready


        else:
            try:
                self.dns_client.loop()
            except Exception as e:
                if self.enable_prints:
                    print("dns_client error: ", e)
                
                self.dns_client = DnsClientNtw(self.ntw, 567)
                self.dns_client.set_serv_addr(bytes([8,8,8,8]))
        
            if not self.dns_client.is_serv_addr_set():
                self.dns_client.set_serv_addr(self.ntw.getDnsSrvIpv4())

            try:
                self.my_server.run()
            except Exception as e:
                if self.enable_prints:
                    print("local server error: ", e)
            self.my_server = Server(80, self.ntw, self)


            try:
                self.sender.run()
            except Exception as e:
                if self.enable_prints:
                    print("sender error: ", e)
                self.sender = Sender(self.ntw, self.dns_client, (1000, 2000), server, tgt_path=path, prints=self.enable_prints)

        self.ethernet.release()
        
    
        
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