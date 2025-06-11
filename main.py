from machine import Timer, Pin, reset
import _thread, gc, log, time
print(time.ticks_ms())
from sensors import *
from config import *
print(time.ticks_ms())
from tcp4client import TCP4client
from enc28j60 import Ntw
from uDnsClient import DnsClientNtw
print(time.ticks_ms()) 
#from uDnsClient import DnsClientNtw, DNS_RCODE_NOERROR

###################################################################################
measure = True  #callback timer

def init_modules():   #tries to init all functions in list sensors which have False in the last index (tries to restart broken ones)
    global l
    #print(type(l))
    #print(sensors)
    for s in sensors:
        #print(sensors[i], len(sensors[i]))
        if not s.use:
            try:
                if callable(s.init):
                    s.use = True
                    s.init()
                    print("successfully initialised", str(s.init), "\n")
                    l.write("successfully initialised", str(s.init), "\n")
                else:
                    print(f"function {s.init} is not callable")
            except Exception as e:
                s.use = False
                print("failed initialising", str(s.init), ":", str(e), "\n")
                l.write("failed initialising", str(s.init), ":", str(e), "\n")   

def process():  #takes num_of_samples measurements from each sensor, makes average and sends them to the server, if there is an issue with reading, sets last index to False
    global measure
    measure = False
    
    for s in sensors:        
        if s.use and not len(s.paths) == 0:
            output = []
            for x in range(num_of_samples):
                try:
                    if not callable(s.read):
                        print(f"function {s.read} is not callable")
                        break
                    v = s.read()
                    print(v)
                    if v == None:
                        print("failed reading ", str(s.read))
                        l.write("failed reading (timeout)", str(s.read))
                    elif not type(v)==tuple:
                        output.append((v,))
                    else:
                        output.append(v)
                        
                    
                except:
                    print("failed reading ", str(s.read))
                    l.write("failed reading ", str(s.read))

                    s.use = False
                    continue

            for j, path in enumerate(s.paths):
                avg = []
                for o in output:
                    if j < len(o):
                        avg.append(o[j])
                avg = average(avg)
                if not avg == None:
                    send_data(avg, path)



def average(*args: list):   #calculates average of all values in list
    try:
        if args == []:
            return None
        else:
            return sum(args[0]) / len(args[0])
    except Exception as e:
        print("Error calculating average:", e)
        return None


def send_data(value:float, sensor_type:str):    #sends data to server
    print(value, sensor_type)
    if not ethernet:
        print("ethernet disabled")
        return
    data = '{"type":"' + sensor_type + '","value":' + str(value) + '}'  #constructing json

    s = tcp.new_connection(tgt_port=port, domain=server)  #creating new connection
    while not type(s) == TCP4client.Session:
        print("Err starting connection, ", s)
        s = tcp.new_connection(domain=server, tgt_port=port)
        time.sleep(0.5)

    s.send("POST {} HTTP/1.1" "\r\n"          #constructing http header
        "Host: {}" "\r\n"
        "Content-Length: {}" "\r\n"
        #"Content-Type: application/json" "\r\n" 
        "Connection-Type: closed""\r\n""\r\n"
        "{}".format(path, server, len(data), data))

def second_core():     #automaticly sends data when available, runs on second core. To use spi0, set ethernet to False
    print("ethernet thread started")
    while True:
        if ethernet:
            try:
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

                tcp.loop()
                gc.collect()
                
            except Exception as e:
                import sys
                sys.print_exception(e)
                try:
                    l.write("Exception in ethernet: ", e)
                except:
                    print("unable to write to log")
        gc.collect()  #collects garbage
        if alive + 60 < time.time():
            print("Mateo got stuck, restarting...")
            l.write("Mateo got stuck, restarting...")
            reset()  #restarts if not alive for more than 60 seconds
        
        time.sleep(1)  #sleep to prevent high cpu usage

def callback(timer):    #callback function for timer
    global measure
    measure = True

alive = 0
def still_alive():
    global alive
    alive = time.time()

print("Mateo started")


l = log.log("mateo-log.txt")    #setups logging

if ethernet:    #inits ethernet
    ntw = Ntw.Ntw(spi0, Pin(17))
    ntw.setIPv4(ip, mask, gw_ip)
    dns_client = DnsClientNtw(ntw, 567)
    dns_client.set_serv_addr(bytes([8,8,8,8]))
    tcp = TCP4client(ntw, dns_client, max_sessions=5, max_messages=20)

led = Pin("LED", Pin.OUT)
led.on()    #turns led on on startup
main_timer = Timer(-1, mode=Timer.PERIODIC, period=INTERVAL, callback=callback)
still_alive()
try:
    _thread.stack_size(1<<13)
    _thread.start_new_thread(second_core, ())  #starts loop on second core for ethernet
except Exception as e:
    print("Error starting ethernet thread:", e)
    l.write("Error starting ethernet thread:", str(e), "\n")
    
while True:
    try:
        

        init_modules()  #runs all init functions in list sensors
        
        gc.collect()  #collects garbage
        print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())

        while True:
            if measure:
                print('processing')
                process()
                gc.collect()
                still_alive()
                init_modules()
                gc.collect()
                print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())
            time.sleep(1)
            still_alive()
    except KeyboardInterrupt:
        break
    except Exception as e:
        gc.collect()
        print("global Error:", e)
        try:
            l.write("global Error: ", str(e), "\n")
        except:
            print("failed to write into log")