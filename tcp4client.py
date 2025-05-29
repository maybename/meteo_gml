from machine import Pin, SPI
from enc28j60 import Ntw 
import time, random
from uDnsClient import DnsClientNtw, DNS_RCODE_NOERROR

class TCP4client:
    def __init__(self, ntw, dns_client = None, port_min = 1000, port_max = 10000):
        self.ntw = ntw
        self.dns_client = dns_client
        
        self.module = True #true, module connected; false, something wrong with module
        
        self.available_ports = [i for i in range(port_min, port_max)]
        
        self.seassions = []
        
        if self.check_module() == -1:
            self.module = False
            return -1
        
    class Seassion:
        def __init__(self, port, tgt_ip, tgt_port, timeout = 10, window_size = 512, keep = False):
            self.port = port    
            self.tgt_ip = tgt_ip
            self.tgt_port = tgt_port

            self.timeout = timeout
            self.window_size = window_size #curently work in process

            self.to_send = []


            self.messages = []
            self.responses = []

            self.seq_num = random.randint(0,0xFFFFFFF)
            self.ack_num = 0 & 0xFFFFFFFF
            
            self._recived = []
            self.state = -1     #-1 - offline,0 - sending data 1 - starting, 2 - stoping, 3 - half closed, 4 - server closing, 5 - restart_timeout
            self.timer = 0
                    
            self.last_ack_num = 0 & 0xFFFFFFFF
            self.last_seq_num = 0 & 0xFFFFFFFF
        
        def __call__(self, pkt):
            if pkt.tcp_seq_num >= self.last_seq_num or pkt.tcp_seq_num == 0:
                data = bytes(pkt.tcp_data).decode('utf-8')
                print('\t[TCPclient] Recived: Port {0} -> {1}, seq: {2}, ack: {3}, flags: {4}, data: {5}'.format(pkt.tcp_srcPort, pkt.tcp_dstPort, pkt.tcp_seq_num, pkt.tcp_ack_num, pkt.tcp_flags, data))
                self._recived.append(pkt)
        
        def dnsCallback(self, hostname, status, addr, ttl):
            if DNS_RCODE_NOERROR != status or addr is None:
                print(f'[DNS] Cannot resolve {hostname} name')
                return

            self.tgt_ip = addr
            print(f'[DNS] {hostname} at {addr[0]}.{addr[1]}.{addr[2]}.{addr[3]}')
                
        def send(self, message):
            if not type(message) == list:
                messages = [message]
            else:
                messages = message
                
            for m in messages:
                self.messages.append(m)

    def sendTCP(self, seassion, message, flags):
            if self.ntw.getArpEntry(self.ntw.gwIp4Addr) == None and self.ntw.getArpEntry(seassion.tgt_ip) == None:
                print("Unknown MAC, sending request")
                if self.ntw.isLocalIp4(seassion.tgt_ip):
                    self.ntw.sendArpRequest(seassion.tgt_ip)
                else:
                    self.ntw.sendArpRequest(self.ntw.gwIp4Addr)
            else:
                self.ntw.sendTcp4(seassion.tgt_ip, seassion.tgt_port, seassion.port, message, seassion.seq_num, seassion.ack_num, flags, seassion.window_size)
                print('\t[TCPclient] Sended: Port {0} -> {1}, seq: {2}, ack: {3}, flags: {4}, data: {5}'.format(seassion.port, seassion.tgt_port, seassion.seq_num, seassion.ack_num, flags, message))
            
            seassion.sended = [message, flags, seassion.seq_num]
            if not flags == 0b10000:
                seassion.timer = time.time()
    
    
    
    def new_connection(self, domain = '', tgt_port = 80, tgt_ip = []):
        if not self.module:
            return -1
        
        port = self.available_ports.pop(random.randint(0, len(self.available_ports)))
        
        seassion = self.Seassion(port, tgt_ip, tgt_port)    
        
        if domain != '' and not dns_client == None:
            dns_client.resolve_host_name(domain, callback=seassion.dnsCallback)

        elif tgt_ip == []:           
            return -1
        
        self.seassions.append(seassion)            

        #self.mk_path(tgt_ip)

        self.ntw.registerTcp4Callback(port, self.seassions[-1])
        return seassion
    
    def terminate_connection(self, seassion):
        if seassion in self.seassions:
            self.available_ports.append(seassion.port)
            self.seassions.remove(seassion)
        else:    
            return -1

    def mk_path(self, tgt_ip):
        tgtMac = None
        while tgtMac == None:
            if self.ntw.isLocalIp4(tgt_ip):
                tgtMac = self.ntw.getArpEntry(tgt_ip)
            else:
                tgtMac = self.ntw.getArpEntry(self.ntw.gwIp4Addr)
            if tgtMac == None:
                print("Unknown MAC, sending request")
                if self.ntw.isLocalIp4(tgt_ip):
                    self.ntw.sendArpRequest(tgt_ip)
                else:
                    self.ntw.sendArpRequest(self.ntw.gwIp4Addr)
            timer = time.time()
            
            while True:
                self.ntw.rxAllPkt()
                if self.ntw.isLocalIp4(tgt_ip):
                    tgtMac = self.ntw.getArpEntry(tgt_ip)
                else:
                    tgtMac = self.ntw.getArpEntry(self.ntw.gwIp4Addr)
                if not tgtMac == None:
                    return
                if timer + 10 <= time.time():                        
                    print('timeout!!! ', time.time())
                    break

    
    def check_module(self):
        revID = self.ntw.nic.GetRevId()
        if revID == 0x00:
            print("ethernet module is not working")
            return -1
        else:
            print("ethernet module OK")
        
    

    def procResponses(self, seassion):
        for pkt in seassion._recived:
            if pkt.tcp_flags & 0b100 == 0b100: #RST packet
                seassion.seq_num = 0
                seassion.ack_num = pkt.tcp_seq_num + 1
                self.sendTCP(seassion, '',0b10000)    #acknowleging packet
                seassion.state = 5
                        
            elif pkt.tcp_seq_num >= seassion.last_seq_num:
                seassion.last_seq_num = pkt.tcp_seq_num
                
                if pkt.tcp_flags & 0b10000 == 0b10000:
                    seassion.seq_num = pkt.tcp_ack_num
                    seassion.ack_num = pkt.tcp_seq_num + len(pkt.tcp_data) + (len(pkt.tcp_data) == 0)
                    
                    seassion.ack_num = seassion.ack_num & 0xFFFFFFFF
                        
                    if seassion.state == 4: #When server starts closing and aknowleged clients fin flag
                        seassion.state = 5      #closed connection
                    
                    if seassion.state == 2:     #when stoping connection and fin flag was aknowleged
                        seassion.state = 3      #connection half-closed
                
                if pkt.tcp_flags & 0b1000 == 0b1000:
                    seassion.responses.append(pkt.tcp_data)
                
                if pkt.tcp_flags & 0b10 == 0b10:
                    print("syn flag")
                    seassion.state = 0
                
                if pkt.tcp_flags & 0b1 == 0b1:
                    print('fin flag')
                    if seassion.state == 0:
                        seassion.to_send.append([seassion.seq_num, '', 0b10001])
                        seassion.state = 4
                    elif seassion.state == 3 or seassion.state == 2:
                        seassion.state = 5
                
                #######################################################################################
                if seassion.state == 0 and seassion.sended[1] == 0b10:
                    self.sendTCP(seassion, '',0b10000)
                    self.insert_message(seassion, seassion.seq_num)
                if seassion.seq_num in [i for i,j,k in seassion.to_send] and not seassion.state == 4:
                    for i, j, k in seassion.to_send:
                        if i == seassion.seq_num:
                            self.sendTCP(seassion, j, k)
                            break
                elif seassion.state == 0:
                    self.sendTCP(seassion, '', 0b10001)
                    seassion.state = 2

                #########################################
            
            seassion._recived.remove(pkt)
                          
    def generate_seq_num(self):
        return(random.randint(0,0xFFFFFFF))
    
    def insert_message(self, seassion, seq_num):
        message = seassion.messages.pop(0)
        seassion.to_send.append([seq_num, message, 0b11000])
        seq_num = seassion.to_send[-1][0] + len(seassion.to_send[-1][1]) + (len(seassion.to_send[-1][1]) == 0)

    def loop(self):
        for seassion in self.seassions:
            self.procResponses(seassion)
            if len(seassion.messages) > 0 and seassion.state == -1:
                self.sendTCP(seassion, '', 0b10)
                seassion.state = 1
                
            if seassion.timer + seassion.timeout <= time.time() and not seassion.state == -1:
                if not seassion.state == 5:
                        print('timeout!!!', time.time())
                        seassion.seq_num = seassion.sended[2]
                        self.sendTCP(seassion, seassion.sended[0], seassion.sended[1])
                        
                elif not seassion.keep and len(seassion.messages) == 0:
                    self.terminate_connection(seassion)

if __name__ == '__main__':
    nicSpi = SPI(0, baudrate=10000000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    nicCsPin = 17

    server_ip = "195.113.164.188" #enter ip there
    
    server = bytes([int(i) for i in server_ip.split('.')])            
    target_port = 80 #usualy a http port    
    
    ntw = Ntw.Ntw(nicSpi, Pin(nicCsPin))
    dns_client = DnsClientNtw(ntw, 567)

# Set static IP address
    ntw.setIPv4([192,168,68,131], [255,255,255,0], [192,168,68,1]) #doma
    #ntw.setIPv4([172,20,13,112], [255,255,255,0], [172,20,13,254]) #škola

    dns_client.set_serv_addr(bytes([8,8,8,8]))
        
    
    
    tcp = TCP4client(ntw, dns_client=dns_client)
    
    seassion1 = tcp.new_connection(tgt_ip=server, tgt_port=target_port)
    if seassion1 == -1:
        print("Failed to create TCP session")
        exit(1)
        
    seassion1.send("POST /humidity/post/ HTTP/1.1\r\n"
                    "Host: student.gml.cz\r\n"
                    "Content-Type: application/x-www-form-urlencoded\r\n"
                    "Content-Length: 13\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    "value=100")
    
    print("looping")
    while True:
        ntw.rxAllPkt()
        dns_client.loop()
        
        if not dns_client.is_serv_addr_set() and ntw.isIPv4Configured():
            dns_client.set_serv_addr(ntw.getDnsSrvIpv4())

        if ntw.configIp4Done:
            tcp.loop()