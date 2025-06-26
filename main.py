from machine import Timer, Pin, reset
import _thread, gc, log, time, ujson
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
second_core_lock = False  #lock for second core

to_send = {"sensors":[]}    #dict with data to send

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

def sec_core_f(f, arg = ()):
    global second_core_lock
    second_core_lock = True
    f(*arg)
    second_core_lock = False

def run_on_second_core(func, arg=()):  #runs function on second core
    try:
        _thread.start_new_thread(sec_core_f, (func, arg))
    except Exception as e:
        print("Error running function on second core:", e)
        l.write("Error running function on second core:", str(e), "\n")
    

def read_sensor(sensor:Sensor):  #reads sensor data
    global to_send
    output = []
    for x in range(num_of_samples):
        try:
            if not callable(sensor.read):
                print(f"function {sensor.read} is not callable")
                break
            v = sensor.read()
            print(v)
            if v == None:
                print("failed reading ", str(sensor.read))
                l.write("failed reading (timeout)", str(sensor.read))
            elif not type(v)==tuple:
                output.append((v,))
            else:
                output.append(v)
                
            
        except:
            print("failed reading ", str(sensor.read))
            l.write("failed reading ", str(sensor.read))

            sensor.use = False
            continue

    for j, path in enumerate(sensor.paths):
        avg = []
        for o in output:
            if j < len(o):
                avg.append(o[j])
        avg = average(avg)
    
        if not avg == None:
            to_send["sensors"].append({"type": path, "value": avg})  #appends data to dict to_send


def process():  #takes num_of_samples measurements from each sensor, makes average and sends them to the server, if there is an issue with reading, sets last index to False
    global measure, second_core_lock
    measure = False
    to_send["sensors"].clear()  #clears dict to_send
    for s in sensors:        
        if s.use and not len(s.paths) == 0:
            if s.second_core and second_core_lock == False:
                run_on_second_core(read_sensor, (s,))  #runs reading on second core
            else:
                read_sensor(s)  #runs reading on main core
    print(second_core_lock)
    while second_core_lock:  #waits for second core to finish
        pass
    
    send_data(to_send)

def restart():  #resets the device
    print("Resetting device...")
    l.write("Resetting device...")
    led.off()  #turns led off
    reset()  #resets the device

def average(*args: list):   #calculates average of all values in list
    try:
        if args == []:
            return None
        else:
            return sum(args[0]) / len(args[0])
    except Exception as e:
        print("Error calculating average:", e)
        return None


def send_data(json:dict):    #sends data to server
    print(json)
    if not ethernet:
        print("ethernet disabled")
        return
    data = ujson.dumps(json)  #converts dict to json

    s = tcp.new_connection(tgt_port=port, domain=server)  #creating new connection
    
    if s == -2 or s == -4:
        tcp.terminate_connection(tcp.sessions[0])
        s = tcp.new_connection(tgt_port=port, domain=server)  #creating new connection
    
    if not type(s) == TCP4client.Session:
        print("failed creating connection, Err: ", s)
        l.write("failed creating connection, Err: ", s)        
        return

    s.send("POST {} HTTP/1.1" "\r\n"          #constructing http header
        "Host: {}" "\r\n"
        "Content-Length: {}" "\r\n"
        #"Content-Type: application/json" "\r\n" 
        "Connection-Type: closed""\r\n""\r\n"
        "{}".format(path, server, len(data), data))

def ethernet_loop():  #ethernet communication
    if ethernet:
        try:
            ntw.rxAllPkt()
            gc.collect()
            if not ntw.configIp4Done or not ntw.nic.IsLinkUp():
                print("Waiting for link/IP...")
                return  # Skip DNS/TCP until Ethernet is ready
            try:
                dns_client.loop()
            except Exception as e:
                print("dns_client error: ", e)
            gc.collect()
            
            if not dns_client.is_serv_addr_set():
                dns_client.set_serv_addr(ntw.getDnsSrvIpv4())

            if len(tcp.sessions) == 0:
                print("All data sent")
            else:   
                tcp.loop()
    
            gc.collect()
            
        except Exception as e:
            import sys
            sys.print_exception(e)
            try:
                l.write("Exception in ethernet: ", e)
            except:
                print("unable to write to log")
        

def restart_ethernet():  #restarts ethernet connection
    global ntw, dns_client, tcp
    if ethernet:    #inits ethernet
        ntw = Ntw.Ntw(spi0, Pin(17))
        ntw.setIPv4(ip, mask, gw_ip)
        dns_client = DnsClientNtw(ntw, 567)
        dns_client.set_serv_addr(bytes([8,8,8,8]))
        tcp = TCP4client(ntw, dns_client, max_sessions=5, max_messages=20)


def callback(timer):    #callback function for timer
    global measure
    measure = True









print("Mateo started")
l = log.log("mateo-log.txt")    #setups logging

led = Pin("LED", Pin.OUT)
led.on()    #turns led on on startup
restart_enabled = True

main_timer = Timer(-1, mode=Timer.PERIODIC, period=INTERVAL, callback=callback)
_thread.stack_size(1<<13)

while True:
    try:
        restart_ethernet() #init ethernet module
        print("Ethernet started")

        init_modules()  #runs all init functions in list sensors
        
        gc.collect()  #collects garbage
        print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())
        t = 0
        while True:
            if measure:
                print('processing')
                process()
                gc.collect()
                run_on_second_core(init_modules)
                print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())
            
            gc.collect()  #collects garbage            
            ethernet_loop()
            if t + 20 > time.time():  #if more than 20 seconds passed since last measurement
                print("memory: ", gc.mem_alloc(), " free: ", gc.mem_free())
                t = time.time()  #sets t to current time
                
                if gc.mem_alloc()/gc.mem_free() > 9:
                    l.write("High memory usage: ", gc.mem_alloc() ,", free: ", gc.mem_free())
                
                elif gc.mem_alloc()/gc.mem_free() > 10:
                    l.write("Too high memory usage: ", gc.mem_alloc() ,", free: ", gc.mem_free())
                    restart()
                    
    except KeyboardInterrupt:
        restart_enabled = False
        break
    
    except Exception as e:
        gc.collect()
        print("global Error:", e)
        try:
            l.write("global Error: ", str(e), "\n")
        except:
            print("failed to write into log")

if restart_enabled:  #if restart is True, resets the device      
    restart()