from lib.tcp4clientX import TCP4client
import buffer, time

from enc28j60.Ntw import Ntw
from enc28j60.uDnsClient import DnsClientNtw


last_send = time.time()  #last time data was sent

class Sender:
    def __init__(self, ntw: Ntw, dns: DnsClientNtw, port_range: tuple[int,int], tgt_server, tgt_port:int = 80, tgt_path = "/", prints: bool = False) -> None:
        self.payload = ""
        self.ntw = ntw
        self.dns_client = dns
        
        self.enable_prints = prints
        
        self.server = tgt_server
        self.tgt_port = tgt_port
        self.port_range = port_range
        self.tgt_path = tgt_path
        
        self.reset()  #inits tcp4client and session


    def reset(self):    #resets tcp client and session
        print("resetting")
        for port in self.ntw.tcp4UniBind.keys():
            if port >= self.port_range[0] and port <= self.port_range[1]:
                self.ntw.registerTcp4Callback(port, None)
        self.tcp = TCP4client(self.ntw, self.dns_client, max_messages=20, port_min=self.port_range[0], port_max=self.port_range[1])
        s = self.tcp.new_connection(domain=self.server, tgt_port=self.tgt_port, keep=True)
        while type(s) is not TCP4client.Session:
            if self.enable_prints:
                print("Waiting for TCP session to be created... Error: ", s)
            s = self.tcp.new_connection(domain=self.server, tgt_port=port, keep=True)
        self.session = s

    def run(self):
        self.tcp.loop()

        if self.session.state == -1:    #if tcp offline check if data was sent successfuly and than send new data
            for s in self.session.responses:
                s = bytes(s)
                if self.enable_prints:
                    print("response: ", s)
                if b'OK' in s and self.payload in buffer.buffer:
                    buffer.remove(self.payload)
                    if self.enable_prints:
                        print("successfuly sended")
            self.session.responses = []
            status = self.send()
            global last_send
            last_send = time.time()
            if self.enable_prints:
                print(status)
                
        elif last_send + 60 <= time.time():
            self.reset()

    def send(self):
        if self.enable_prints:
            print("sending...", last_send, time.time())
        line = buffer.read_first()  #tries to get data from buffer
        if line == None:    #if buffer empty, return
            return -1
        
        self.payload = line
        if self.enable_prints:
            print("payload:", self.payload)
        try:
            data = self.payload.strip()
            # construct and send HTTP request
            self.session.send(
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Length: {}\r\n"
                "Connection-Type: closed\r\n\r\n"
                "{}".format(self.tgt_path, self.server, len(data), data)
            )
        except Exception as e:
            if self.enable_prints:
                print("network send failed:", e)
            return