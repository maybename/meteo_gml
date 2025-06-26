from machine import Pin, SPI
from enc28j60 import Ntw
import time, urandom, struct
from uDnsClient import DnsClientNtw, DNS_RCODE_NOERROR

MAX_UINT32 = (1<<32)-1

SHOW_PRINTS = False

class TCP4client:
    class Session:
        def __init__(self, port, tgt_ip, tgt_port, domain='', timeout = 10, window_size = 512, keep = False):
            self.port = port
            self.tgt_ip = tgt_ip
            self.tgt_port = tgt_port
            self.domain = domain

            self.keep = keep
            self.timeout = timeout
            self.window_size = window_size #curently work in process

            self.to_send = []
            self.sended = []
            self.messages = []
            self.reset()

        def __call__(self, pkt):
            if (pkt.tcp_seq_num >= self.last_seq_num or pkt.tcp_seq_num == 0) and not pkt.tcp_flags == self.last_flags and pkt.tcp_dstPort == self.port and len(self._received) < 10:
                if SHOW_PRINTS: 
                   print('\t[TCPclient] Recived: Port {0} -> {1}, seq: {2}, ack: {3}, flags: {4}'.format(pkt.tcp_srcPort, pkt.tcp_dstPort, pkt.tcp_seq_num, pkt.tcp_ack_num, pkt.tcp_flags))
                self.last_seq_num, self.last_flags = pkt.tcp_seq_num, pkt.tcp_flags
                self._received.append(pkt)

        def reset(self):
            self.to_send = []
            self.sended = []

            self.responses = []

            self.seq_num = 0 & MAX_UINT32
            self.seq_num = urandom.getrandbits(32)  #randomize seq_num
            self.ack_num = 0 & MAX_UINT32

            self._received = []
            self.state = -1     #-1 - offline,0 - available 1 - starting, 2 - stoping, 3 - half closed, 4 - server closing, 5 - restart_timeout
            self.timer = 0

            self.last_ack_num = 0 & MAX_UINT32
            self.last_seq_num = 0 & MAX_UINT32
            self.last_flags = 0

        def send(self, message:str | list):
            if type(message) == str:
                messages = [message]
            elif type(message) == list:
                messages = message

            self.messages += messages

    def __init__(self, ntw:Ntw.Ntw, dns_client = None, port_min = 1000, port_max = 2000, max_sessions = None, max_messages = None):

        self.ntw = ntw
        self.dns_client = dns_client
        self.known_domains = {}
        self.module = True #true, module connected; false, something wrong with module

        self.available_ports = [i for i in range(port_min, port_max)]

        self.sessions:list[TCP4client.Session] = []

        self.max_sessions = max_sessions
        self.max_messages = max_messages

        if self.check_module() == -1:
            self.module = False
            return -1

    def dnsCallback(self, hostname, status, addr, ttl):
        if DNS_RCODE_NOERROR != status or addr is None:
            if SHOW_PRINTS:
                print(f'[DNS] Cannot resolve {hostname} name')
            return

        if SHOW_PRINTS:
            print(f'[DNS] {hostname} at {addr[0]}.{addr[1]}.{addr[2]}.{addr[3]}')
        self.known_domains[hostname] = addr

    def sendTCP(self, session:Session, message, flags):
            if session.tgt_ip == []:
                if session.domain in self.known_domains:
                    session.tgt_ip = self.known_domains[session.domain]
                else:
                    if SHOW_PRINTS: 
                       print("Unknown target IP")

            elif self.ntw.getArpEntry(self.ntw.gwIp4Addr) == None and self.ntw.getArpEntry(session.tgt_ip) == None:
                if SHOW_PRINTS: 
                    print("Unknown MAC, sending request")
                if self.ntw.isLocalIp4(session.tgt_ip):
                    self.ntw.sendArpRequest(session.tgt_ip)
                else:
                    self.ntw.sendArpRequest(self.ntw.gwIp4Addr)
            else:
                self.ntw.sendTcp4(session.tgt_ip, session.tgt_port, session.port, message, session.seq_num, session.ack_num, flags, session.window_size)
                if SHOW_PRINTS:
                    print('\t[TCPclient] Sended: Port {0} -> {1}, seq: {2}, ack: {3}, flags: {4}, data: {5}'.format(session.port, session.tgt_port, session.seq_num, session.ack_num, flags, message))

            session.sended = [message, flags, session.seq_num]
            if not flags == 0b10000:
                session.timer = time.time()



    def new_connection(self, domain = '', tgt_port = 80, tgt_ip = [], timeout = 10, window_size = 512, keep = False):
        if not self.module or len(self.available_ports) == 0:
           return -1

        if domain in self.known_domains.keys():
            if SHOW_PRINTS:
                print(self.known_domains)
            tgt_ip = self.known_domains[domain]

        if tgt_ip == [] and not domain == '' and not self.dns_client == None:
                if SHOW_PRINTS:
                    print("Unknown domain, resolving with DNS...")
                self.dns_client.resolve_host_name(domain, self.dnsCallback)
        elif tgt_ip == []:
            return -3

        if not self.max_sessions == None and len(self.sessions) >= self.max_sessions:
            if not self.max_messages == None:
                m = 0
                for s in self.sessions:
                    m += len(s.messages)
                if m >= self.max_messages:
                    if SHOW_PRINTS:
                        print("Too much messages, ", m)
                    return -4
            
            minim = None
            out = None
                
            for i, s in enumerate(self.sessions):
                if ((not domain == '' and s.domain == domain) or (not tgt_ip == [] and s.tgt_ip == tgt_ip)) and s.tgt_port == tgt_port:
                    if minim == None or s.messages < minim:
                        minim = s.messages
                        out = i
            
            if not out == None:
                return self.sessions[out]
                
            return -2
        else:
            port = self.available_ports.pop(0)

            session = self.Session(port, tgt_ip, tgt_port, domain, timeout, window_size, keep)

            if domain != '' and not self.dns_client == None:
                self.dns_client.resolve_host_name(domain, self.dnsCallback)

            self.sessions.append(session)

            self.ntw.registerTcp4Callback(port, self.sessions[-1])
            return session

    def terminate_connection(self, session:Session):
        if SHOW_PRINTS:
            print("terminating session")
        if session in self.sessions:
            messages = session.messages
            self.available_ports.append(session.port)
            if session.keep or len(session.messages) >= 0:
                tgt_port, tgt_ip, domain, timeout, window_size, keep = session.tgt_port, session.tgt_ip, session.domain, session.timeout, session.window_size, session.keep
                
                
                self.sessions.remove(session)
                s = None
                while not type(s) == TCP4client.Session:
                    s = self.new_connection(domain=domain, tgt_port=tgt_port, tgt_ip=tgt_ip, timeout=timeout, window_size=window_size, keep=keep)
                s.messages = messages
            else:
                self.sessions.remove(session)

            session.reset()
            self.ntw.registerTcp4Callback(session.port, None)
            
        else:
            return -1

    def check_module(self):
        revID = self.ntw.nic.GetRevId()
        if revID == 0x00:
            if SHOW_PRINTS:
                print("ethernet module is not working")
            return -1
        else:
            #print("ethernet module OK")
            return 0

    def procResponses(self, session:Session):
        for pkt in session._received:
            if pkt.tcp_flags & 0b100 == 0b100: #RST packet
                session.seq_num = 0
                session.ack_num = pkt.tcp_seq_num + 1
                self.sendTCP(session, '',0b10000)    #acknowleging packet
                session.state = 5

            elif pkt.tcp_seq_num >= session.last_seq_num:
                session.last_seq_num = pkt.tcp_seq_num

                if pkt.tcp_flags & 0b10000 == 0b10000:
                    session.seq_num = pkt.tcp_ack_num
                    session.ack_num = pkt.tcp_seq_num + len(pkt.tcp_data) + (len(pkt.tcp_data) == 0 and not pkt.tcp_flags == 0b10000)

                    session.ack_num = session.ack_num & MAX_UINT32 #ack_num must be 32bit

                    if session.state == 4: #When server starts closing and aknowleged clients fin flag
                        session.state = 5      #closed connection

                    if session.state == 2:     #when stoping connection and fin flag was aknowleged
                        session.state = 3      #connection half-closed

                if pkt.tcp_flags & 0b1000 == 0b1000:
                    session.responses.append(pkt.tcp_data)

                if pkt.tcp_flags & 0b10 == 0b10:
                    #print("syn flag")
                    session.state = 0

                if pkt.tcp_flags & 0b1 == 0b1:
                    #print('fin flag')
                    if session.state == 0:
                        session.to_send.append([session.seq_num, '', 0b10001])
                        session.state = 4
                    elif session.state == 3 or session.state == 2:
                        session.state = 5

                #######################################################################################
                if session.state == 0 and session.sended[1] == 0b10:
                    self.sendTCP(session, '',0b10000)
                    self.insert_message(session, session.seq_num)
                if session.seq_num in [i for i,j,k in session.to_send] and not session.state == 4:
                    for i, j, k in session.to_send:
                        if i == session.seq_num:
                            self.sendTCP(session, j, k)
                            break
                elif session.state == 0:
                    self.sendTCP(session, '', 0b10001)
                    session.state = 2

                #########################################
            pkt = None
        session._received = []

    def insert_message(self, session, seq_num):
        message = session.messages.pop(0)
        session.to_send.append([seq_num, message, 0b11000])
        #seq_num = session.to_send[-1][0] + len(session.to_send[-1][1]) + (len(session.to_send[-1][1]) == 0)

    def loop(self):
        for session in self.sessions:
            self.procResponses(session)
            if len(session.messages) > 0 and session.state == -1:
                self.sendTCP(session, '', 0b10)
                session.state = 1

            if session.timer + session.timeout <= time.time() and not session.state == -1:
                if not session.state == 5 and not session.sended == []:
                        if SHOW_PRINTS:
                            print('timeout!!!', time.time())
                        session.seq_num = session.sended[2]
                        self.sendTCP(session, session.sended[0], session.sended[1])

                else:
                    self.terminate_connection(session)
        return [s.state for s in self.sessions]  #returning sessions states for debugging purposes

if __name__ == '__main__':
    nicSpi = SPI(0, baudrate=10000000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    nicCsPin = 17

    server_ip = "195.113.164.188" #enter ip there

    server = bytes([int(i) for i in server_ip.split('.')])
    target_port = 80 #usualy a http port

    ntw = Ntw.Ntw(nicSpi, Pin(nicCsPin))
    dns_client = DnsClientNtw(ntw, 567)

    # Set static IP address
    ntw.setIPv4([192,168,68,129], [255,255,255,0], [192,168,68,1]) #doma
    #ntw.setIPv4([172,20,13,112], [255,255,255,0], [172,20,13,254]) #škola

    dns_client.set_serv_addr(bytes([8,8,8,8]))

    tcp = TCP4client(ntw, dns_client=dns_client, max_sessions=2, max_messages=10)

    session1 = tcp.new_connection(tgt_port=target_port, domain="google.com")
    if not type(session1) == TCP4client.Session:
        print("Failed to create TCP session", session1)
        exit(1)

    session1.send("GET / HTTP/1.1\r\n"
                  "Host: google.com\r\n"
                  "Content-Length: 0\r\n"
                  "Connection: close\r\n"
                  "\r\n")

    print(session1.messages)
    print("looping")
    while True:
        ntw.rxAllPkt()
        dns_client.loop()

        if not dns_client.is_serv_addr_set() and ntw.isIPv4Configured():
            dns_client.set_serv_addr(ntw.getDnsSrvIpv4())

        if ntw.configIp4Done:
            tcp.loop()