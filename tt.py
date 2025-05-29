from tcp4clientX import TCP4client
from enc28j60 import Ntw 
from sensors import *

ip, mask, gw_ip = [192,168,68,135], [255,255,255,0], [192,168,68,1]

server = bytes([195,113,164,188]) #target ip, currently student.gml.cz
port = 80   #target port
path = "/skriptsql.php" #target path

ntw = Ntw.Ntw(spi0, Pin(17))
ntw.setIPv4(ip, mask, gw_ip)
tcp = TCP4client(ntw)
seassion1 = tcp.new_connection(tgt_ip=server, timeout=10, tgt_port=port)

def function():
    ntw.rxAllPkt()
    if ntw.configIp4Done:
        tcp.loop()
    if not tcp.seassion == None:
        for response in tcp.seassion.responses:
            print(response)
            
def send_data(value:float, sensor_type:str):    #sends data to server
    print(value, sensor_type)
    data = '{"type":"' + sensor_type + '","value":' + str(value) + '}'  #constructing json
    tcp.send("POST {} HTTP/1.1" "\r\n"          #constructing http header
        "Host: student.gml.cz" "\r\n"
        "Content-Length: {}" "\r\n"
        #"Content-Type: application/json" "\r\n"
        "Connection-Type: closed""\r\n""\r\n"
        "{}".format(path, len(data), data))
    
send_data(1.23, "temp")
while True:
    function()
    