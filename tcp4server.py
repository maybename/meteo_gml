from machine import Pin, SPI
from enc28j60 import Ntw
import time, urandom, gc

MAX_UINT32 = (1<<32)-1
SHOW_PRINTS = True
RETRANSMITION = 1

def generate_response(http_version = "HTTP/1.1", status = "200 OK", content_type = "text/html", data = "", headers:dict = {}):
    r = http_version + " " + status + "\r\n"
    for k in headers.keys():
        r += k + ": " + headers[k] + "\r\n"
    
    r += "Content-Type: " + content_type + "\r\n"
    r += "Content-Length: " + str(len(data)) + "\r\n"
    
    r += "\r\n" + data
    
    return r

class TCPpacket:
    def __init__(self, srcIP:bytes, destIP:bytes, srcPort:int, destPort:int, seq_num: int, ack_num:int, flags:int, data:memoryview) -> None:
        self.srcPort = srcPort
        self.dstPort = destPort
        
        self.srcIP = srcIP
        self.dstIP = destIP
        
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.data = bytes(data)
    
class TCP4server:
    class HTTPpage:
        def __init__(self, path:str, content, method: str = "GET"):
            #content function must take 5 args, content(http_version, headers, http_data, pkt.srcIP, pkt.srcPort)
            if not type(content) == str and not callable(content):
                return
            self.path = path
            self.method = method.upper()
            self.content = content
        

    class Session:
        def __init__(self, tcp, port, tgt_ip, tgt_port, ack_num = 0, timeout = 10, window_size = 10000, keep = False, max_messages = 20):
            self.port = port
            self.tgt_ip = tgt_ip
            self.tgt_port = tgt_port
            self.tcp = tcp
            
            self.num_of_timeouts = 0
            
            self.keep = keep
            self.max_messages = max_messages
            
            self.timeout = timeout
            self.window_size = window_size #curently work in process

            self.to_send = []
            self.sended = []
            self.reset()
            self.ack_num = ack_num

        def process(self, pkt:TCPpacket):
                try:
                    data:list[str] = bytes(pkt.data).decode().split("\r\n")
                except:
                    if SHOW_PRINTS:
                        print("failed to decode data", pkt.data)
                        #input()
                    return -1
                for d in data:
                    d.strip()
                
                request = data[0].split(" ")
                if len(request) < 3 and len(request[2]) > 4  and not request[2][:4].upper() == "HTTP":
                    if SHOW_PRINTS:
                        print('\t[HTTP]\tInvalid request line')
                    return -1

                method, path, http_version = request[:3]
                headers:list[str] = []
                http_data:str = ""
                c = 0
                for d in data[1:]:
                    if d == "" and c == 0:
                        c = 1
                    if c == 0:
                        headers.append(d)
                    else:
                        http_data += d
                
                print("success")
                
                method = method.upper()
                content = None
                for p in self.tcp.HTTPpages:
                    if p.method == method and p.path == path:
                        content = p.content
                        
                if callable(content):
                    content = content(http_version, headers, http_data, pkt.srcIP, pkt.srcPort)
                
                if content == None:
                    return (0, generate_response(http_version=http_version, status="404 ERROR", data="<h1>404 Error</h1><span>page not found</span>"))

                return (0, generate_response(http_version=http_version, data=str(content)))
                                

        def reset(self):
            self.to_send = []
            self.sended = []

            self.mac_dict = {}
            
            self.responses = []

            self.seq_num = 0 & MAX_UINT32
            self.seq_num = urandom.getrandbits(32)  #randomize seq_num
            self.ack_num = 0 & MAX_UINT32

            self.state = 0     #-1 - offline,0 - available 1 - starting, 2 - stoping, 3 - half closed, 4 - server closing, 5 - restart_timeout
            self.timer = 0

            self.last_ack_num = 0 & MAX_UINT32
            self.last_seq_num = 0 & MAX_UINT32
            self.last_flags = 0
        
    def __init__(self, ntw:Ntw.Ntw, port = 80, max_connections = 50):
        self.ntw = ntw
        self.ntw.registerTcp4Callback(port, self)
        self.module = True #true, module connected; false, something wrong with module

        self.sessions = []
        self.max_connections = max_connections
        self.port = port

        self.HTTPpages:list[TCP4server.HTTPpage] = []
        self._received:list[TCPpacket] = []

        if self.check_module() == -1:
            self.module = False
            return -1        

    def __call__(self, pkt):
            # --- ARP pre-learning ---
        try:
            # Learn MAC address of sender directly from Ethernet header
            self.ntw.addArpEntry(pkt.ip_src_addr, pkt.eth_src)
            print("ARP added")
                
        except Exception as e:
            if SHOW_PRINTS:
                print("Failed to add ARP entry:", e)
            
        if SHOW_PRINTS: 
            print('\t[TCPclient] Recived: Port {0} -> {1}, seq: {2}, ack: {3}, flags: {4}, data:{5}'.format(pkt.tcp_srcPort, pkt.tcp_dstPort, pkt.tcp_seq_num, pkt.tcp_ack_num, pkt.tcp_flags, bytes(pkt.tcp_data)))
        self._received.append(TCPpacket(pkt.ip_src_addr, pkt.ip_dst_addr, pkt.tcp_srcPort, pkt.tcp_dstPort, pkt.tcp_seq_num, pkt.tcp_ack_num, pkt.tcp_flags, pkt.tcp_data))

    def page(self, path:str, content:str | function, method: str = "GET"):
        page = self.HTTPpage(path, content, method)
        for p in self.HTTPpages:    #if there is page with same method and path replace content
            if p.path == path and p.method == method:
                p = page
                return
            
        self.HTTPpages.append(page)
        
    def sendTCP(self, session:Session, message, flags):
            if self.ntw.getArpEntry(self.ntw.gwIp4Addr) == None and self.ntw.getArpEntry(session.tgt_ip) == None:
                if SHOW_PRINTS: 
                    print("Unknown MAC, sending request")
                if self.ntw.isLocalIp4(session.tgt_ip):
                    self.ntw.sendArpRequest(session.tgt_ip)
                else:
                    self.ntw.sendArpRequest(self.ntw.gwIp4Addr)
            else:
                for i in range(RETRANSMITION):
                    print(self.ntw.arpTable)
                    self.ntw.sendTcp4(session.tgt_ip, session.tgt_port, session.port, message, session.seq_num, session.ack_num, flags, session.window_size)
                if SHOW_PRINTS:
                    print('\t[TCPclient] Sended: Port {0} -> {1}, seq: {2}, ack: {3}, flags: {4}, data: {5}'.format(session.port, session.tgt_port, session.seq_num, session.ack_num, flags, message))

            session.sended = [message, flags, session.seq_num]
            if not flags == 0b10000:
                session.timer = time.time()

    def sendlastTCP(self, session):
        session.seq_num = session.sended[2]
        self.sendTCP(session, session.sended[0], session.sended[1])

    def check_module(self):
        revID = self.ntw.nic.GetRevId()
        if revID == 0x00:
            if SHOW_PRINTS:
                print("ethernet module is not working")
            return -1
        else:
            #print("ethernet module OK")
            return 0

    def procResponses(self):
        if SHOW_PRINTS:
            print("processing packets")
        for pkt in self._received:
            if pkt.flags & 0b00010: #SYN
                i = None
                if len(self.sessions) < self.max_connections:
                    self.sessions.append(self.Session(self, self.port, pkt.srcIP, pkt.srcPort, ack_num = pkt.seq_num+1))
                    i = -1
                else:
                    for c, s in enumerate(self.sessions):
                        if s == None or s.state == -1:
                            self.sessions[c] = self.Session(self, self.port, pkt.srcIP, pkt.srcPort, ack_num = pkt.seq_num+1)
                            i = c
                            break
                if i == None:
                    if SHOW_PRINTS:
                        print("No free sessions")
                    continue
                else:
                    self.sendTCP(self.sessions[i], '', 0b10010) #SYN+ACK
                    continue
                
            for i, session in enumerate(self.sessions):
                if session == None or session.state == -1:
                    continue

                if pkt.dstPort == session.port and pkt.srcPort == session.tgt_port and pkt.srcIP == session.tgt_ip and pkt.seq_num == session.ack_num:    
                    #if correct session and new packet
                    session.seq_num = pkt.ack_num
                    session.ack_num = pkt.seq_num + len(pkt.data) + (len(pkt.data) == 0 and not pkt.flags == 0b10000)
                    self.last_seq_num, self.last_flags = pkt.seq_num, pkt.flags
                    if pkt.flags & 0b100 == 0b100:  #if reset flag, discard session
                        self.sessions[i] = None
                        if SHOW_PRINTS:
                            print("discarding session")
                        continue
                    if pkt.flags == 0b10000:        #if only ACK, skip
                        session.timer = 0
                        if session.state == 2:
                            self.sendTCP(session, '', 0b10001)
                            self.state = 4
                        continue
                    
                    if pkt.flags & 0b1 == 0b1:
                        if session.state == 0:
                            self.sendTCP(session, '', 0b10000)
                            self.sendTCP(session, '', 0b10001)
                            self.state = 5
                        
                        elif session.state == 4:
                            self.sendTCP(session, '', 0b10000)
                            self.state = 5
                        continue
                    
                    self.sendTCP(session, '', 0b10000)
                    s = session.process(pkt)
                    if type(s) == tuple and len(s) == 2 :
                        fin, data = s
                    else:
                        continue

                    self.sendTCP(session, data, 0b11000)
                    if fin == 0:
                        session.state = 2
                    
        
        self._received = []

    def loop(self):
        self.procResponses()
        for i, session in enumerate(self.sessions):
            if session == None or session.state == -1:
                continue
            
            if not session.timer == 0 and session.timer + session.timeout <= time.time() and not session.state == -1:
                if not session.state == 5 and not session.sended == [] and not session.sended[1] == 0b10000:
                        if SHOW_PRINTS:
                            print('timeout!!!', time.time())
                        session.num_of_timeouts += 1
                        if session.num_of_timeouts >= 3:
                            print("discarding session, too much timeouts")
                            self.sessions[i] = None
                            continue
                        print("resending")
                        self.sendlastTCP(session)
                else:
                    session = None
        print(len(self.sessions), self.sessions.count(None))
        return self.max_connections - self.sessions.count(None)


def web_callback_example(vesion:str, headers:str, data:str, ip:bytes, port:int):
    return f"<h1>Picos time is: {time.time()}</h1>"

if __name__ == '__main__':
    nicSpi = SPI(0, baudrate=10000000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
    nicCsPin = 17

    ntw = Ntw.Ntw(nicSpi, Pin(nicCsPin))

# Set static IP address
    ntw.setIPv4([192,168,68,129], [255,255,255,0], [192,168,68,1]) #doma
    #ntw.setIPv4([172,20,13,112], [255,255,255,0], [172,20,13,254]) #škola

    tcp = TCP4server(ntw, 80, max_connections=5)

    tcp.page("/", "<h1>Hello World</h1>")
    tcp.page("/time/", web_callback_example)
    print("Web server on ip: ", [192,168,68,129])
    while True:
        ntw.rxAllPkt()
        tcp.loop()
        gc.collect()
        print(gc.mem_free())
        time.sleep(0.5)
