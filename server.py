from lib.tcp4server import TCP4server
import json
import buffer
import time
import config
from lib.sensors import sensors
from lib.text_colors import *
from core1 import EthernetThread

class Server:
    def __init__(self, port, ntw, ether: EthernetThread) -> None:
        self.ntw = ntw
        self.ether = ether
        self.server = TCP4server(ntw, port, 10)
        
        self.server.page("/", "<h1>This is the webserver of GML weatherstation</h1>")
        self.server.page("/time", self.get_time)
        self.server.page("/data", self.data)
        self.server.page("/testing", self.page_test, "PUT")
    
    def add_page(self, path, function, method):
        self.server.page(path, function, method)
    
    def get_last_data(self):
        return self.ether.sender.payload
    
    def run(self):
        self.server.loop()
        
    def get_time(*args):
            return f"Current time on Pico is {time.time()} - {time.gmtime()}"
        
    def data(self, *args):
            count = len(buffer.buffer)
            out = '''<h1>measured data</h1>
            <pre style="text-align: left;">
            '''
        
            out += f"datapackets waits to send: {count}\r\n"
            out += f"last sended measurement: \r\n"
            for k in json.loads(self.get_last_data())["sensordatavalues"]:
                out += f"\t- {k["value_type"]} : {k["value"]}\r\n"
            out += f"\n\n Connected sensors: \n"
            for s in sensors:
                out += f"\t{s.name}: {GREEN + "online" + RESET if s.use else RED + "offline" + RESET + "\n"}"
            out += "</pre>"
            return out
        
    def log(self, *args):
        out = f'''<h1>last events in log</h1>
        <span>main loop: </span><br>
        <pre style="text-align: left;">
        {config.meteo_l.last_writes()}
        </pre>
        <span>sensors: </span><br>
        <pre style="text-align: left;">
        {config.measurements_l.last_writes()}
        </pre>
        '''
        return(0, "200 OK", out)
        
        
        
    def page_test(self, http_version, headers, http_data, srcIP, srcPort):
        if "API" in headers.keys() and "filename" in headers and headers["API"] == "testing_stupid_ideas":
            self.server.page(f"/testing/{headers["filename"]}", http_data)
            
            return(0, "200 OK", "OK")
        return(0, "401 Error", "missing header or wrong api"+str(headers))
            
        