from enc28j60.SntpClient import SntpClient
from enc28j60.uDnsClient import DnsClientNtw
from enc28j60 import Ntw
from sensors import spi0
from machine import Pin
from config import *
import time, gc


sntp_ip = []

def callback(*args):
    global sntp_ip
    sntp_ip = args[2]
    print(args)

def main():
    
    ntw = Ntw.Ntw(spi0, Pin(17))

    # Set static IP address
    ntw.setIPv4(ip, mask, gw_ip)

    # Create DNS client
    dns_client = DnsClientNtw(ntw, 567)
    dns_client.set_serv_addr(bytes([8,8,8,8]))
    dns_client.resolve_host_name(sntp_server, callback=callback)
    
    # Create SNTP client
    sntp_cli = SntpClient(ntw, 51000, [162,159,200,1])

    while sntp_ip == []:
        ntw.rxAllPkt()
        gc.collect()
        if not ntw.configIp4Done or not ntw.nic.IsLinkUp():
            print("Waiting for link/IP...")
            time.sleep(1)
            continue  # Skip DNS/TCP until Ethernet is ready
        
        try:
            dns_client.loop()
        except Exception as e:
            print("dns_client error: ", e)
        gc.collect()
        
        if not dns_client.is_serv_addr_set():
            dns_client.set_serv_addr(ntw.getDnsSrvIpv4())
        
    while sntp_cli.datetimetuple == None:
        ntw.rxAllPkt()
        gc.collect()
        sntp_cli.loop()
    return sntp_cli.datetimetuple  # Return the synchronized time as a tuple

actual_time = main()  # Get the actual time from SNTP client
#actual_time = time.mktime(actual_time)  # Convert to seconds since epoch
print(actual_time)
