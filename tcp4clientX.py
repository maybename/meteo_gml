from machine import Pin, SPI
from enc28j60 import Ntw 
import time, random

class TCP4client:
    def __init__(self, ntw):
        self.ntw = ntw
        
        self.module = True #true, module connected; false, something wrong with module
        
        self.seassion = None
        
        if self.check_module() == -1:
            self.module = False
        return -1
    class Seassion:
        def __init__(self, port, tgt_ip, tgt_port, timeout = 30, window_size = 512):
            self.port = port    
            self.tgt_ip = tgt_ip
            self.tgt_port = tgt_port

            self.timeout = timeout
            self.window_size = window_size #curently work in process

            self.messages = []
            
            self.reset() #sets default for rest variables, which would need reset 
            
        def __call__(self, pkt):
            if pkt.tcp_seq_num >= self.last_seq_num or pkt.tcp_seq_num == 0:
                data = bytes(pkt.tcp_data).decode('utf-8')
                print('\t[TCPclient] Recived: Port {0} -> {1}, seq: {2}, ack: {3}, flags: {4}, data: {5}'.format(pkt.tcp_srcPort, pkt.tcp_dstPort, pkt.tcp_seq_num, pkt.tcp_ack_num, pkt.tcp_flags, data))
                self.last_seq_num = pkt.tcp_seq_num
                self._recived.append(pkt)
        
        def reset(self):
            self.to_send = []
            self.sended = None
            
            self.responses = []

            self.seq_num = random.randint(0,0xFFFFFFF)
            self.ack_num = 0 & 0xFFFFFFFF
            
            self._recived = []
            self.state = -1     #-1 - offline,0 - available 1 - starting, 2 - stoping, 3 - half closed, 4 - server closing, 5 - restart_timeout
            self.timer = 0
                    
            self.last_ack_num = 0 & 0xFFFFFFFF
            self.last_seq_num = 0 & 0xFFFFFFFF
        
    def send(self, message: str):
        if self.seassion == None:
            return -1    
        self.seassion.messages.append(message)

    def sendTCP(self, seassion, message, flags):
            if self.ntw.getArpEntry(self.ntw.gwIp4Addr) == None and self.ntw.getArpEntry(seassion.tgt_ip) == None:
                print("Unknown MAC, sending request")
                if self.ntw.isLocalIp4(seassion.tgt_ip):
                    self.ntw.sendArpRequest(seassion.tgt_ip)
                else:
                    self.ntw.sendArpRequest(self.ntw.gwIp4Addr)
            else:
                print('\t[TCPclient] Sended: Port {0} -> {1}, seq: {2}, ack: {3}, flags: {4}, data: {5}'.format(seassion.port, seassion.tgt_port, seassion.seq_num, seassion.ack_num, flags, message))
                self.ntw.sendTcp4(seassion.tgt_ip, seassion.tgt_port, seassion.port, message, seassion.seq_num, seassion.ack_num, flags, seassion.window_size)
            
            seassion.sended = [message, flags, seassion.seq_num]
            if not flags == 0b10000:
                seassion.timer = time.time()
    
    def new_connection(self, tgt_port = 80, tgt_ip = bytes([]), timeout:int = 30):
        if type(self.seassion) == TCP4client.Seassion and (tgt_ip == self.seassion.tgt_ip or tgt_ip == []) and (tgt_port == self.seassion.tgt_port or tgt_port == []):
            return self.seassion
        
        if not self.seassion == None:

            while len(self.seassion.messages) > 0 or not self.seassion.state == 5:
                pass


            self.ntw.registerTcp4Callback(self.seassion.port, None)
            
            port = self.seassion.port + 1
            if port > 1100:
                port = 1000
                
        else:
            port = 1000
            
        seassion = self.Seassion(port, tgt_ip, tgt_port, timeout=timeout)        
        self.ntw.registerTcp4Callback(port, seassion)
        
        self.seassion = seassion

        #self.mk_path(tgt_ip)

        return seassion

    
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
            #print("ethernet module OK")
            return 0
    

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
                    seassion.ack_num = pkt.tcp_seq_num + len(pkt.tcp_data) + (len(pkt.tcp_data) == 0 and not pkt.tcp_flags == 0b10000)
                    
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

    def loop(self):
        if not self.seassion == None:
            self.procResponses(self.seassion)
            if len(self.seassion.messages) > 0 and self.seassion.state == -1:
                self.sendTCP(self.seassion, '', 0b10)
                self.seassion.state = 1
                
            if self.seassion.timer + self.seassion.timeout <= time.time() and not self.seassion.state == -1:
                if not self.seassion.state == 5 and not self.seassion.sended == None:
                        print('timeout!!!', time.time())
                        self.seassion.seq_num = self.seassion.sended[2]
                        self.sendTCP(self.seassion, self.seassion.sended[0], self.seassion.sended[1])
                        
                else:
                    self.seassion.reset()
                    self.ntw.registerTcp4Callback(self.seassion.port, None)
                    self.seassion.port += 1
                    if self.seassion.port > 1100:
                        self.seassion.port = 1000
                    self.ntw.registerTcp4Callback(self.seassion.port, self.seassion)
                

if __name__ == '__main__':
    nicSpi = SPI(0, baudrate=10000000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    
    nicCsPin = 17

    server_ip = "195.113.164.188" #enter ip there
    
    server = bytes([int(i) for i in server_ip.split('.')])            
    target_port = 80 #usualy a http port    
    
    ntw = Ntw.Ntw(nicSpi, Pin(nicCsPin))

# Set static IP address
    ip = [172,20,2,190]
    mask = [255,255,255,0]
    gw_ip = [172,20,2,254]
    ntw.setIPv4(ip,mask,gw_ip)
    #ntw.setIPv4([192,168,68,135], [255,255,255,0], [192,168,68,1]) #doma
    #ntw.setIPv4([172,20,13,112], [255,255,255,0], [172,20,13,254]) #škola

        
    
    
    tcp = TCP4client(ntw)
    
    seassion1 = tcp.new_connection(tgt_ip=server)
    sensor_type = "hum"
    value = 100
    path = "/skriptsql.php"
    data = '{"type":"' + sensor_type + '","value":' + str(value) + '}'  #constructing json
    tcp.send("POST {} HTTP/1.1" "\r\n"          #constructing http header
        "Host: student.gml.cz" "\r\n"
        "Content-Length: {}" "\r\n"
        #"Content-Type: application/json" "\r\n"
        "Connection-Type: closed""\r\n""\r\n"
        "{}".format(path, len(data), data))
    
    print("looping")
    while True:
        ntw.rxAllPkt()
        
        if ntw.configIp4Done:
            tcp.loop()