from machine import Timer, Pin
import _thread, gc, log, time
print(time.ticks_ms())
from sensors import *
print(time.ticks_ms())
from tcp4client import TCP4client
from enc28j60 import Ntw
print(time.ticks_ms()) 
#from uDnsClient import DnsClientNtw, DNS_RCODE_NOERROR

###################################################################################
measure = True  #callback timer
num_of_samples = 5  #number of samples to be taken from each sensor

######ethernet config######
'''
ip = [172,20,13,112]
mask = [255,255,255,0]
gw_ip = [172,20,13,254]
#'''
'''#for inf3
ip = [172,20,13,112]
mask = [255,255,255,0]
gw_ip = [172,20,13,254]
#'''
ip, mask, gw_ip = [192,168,68,135], [255,255,255,0], [192,168,68,1]
server = bytes([195,113,164,188]) #target ip, currently student.gml.cz
port = 80   #target port
path = "/skriptsql.php" #target path

ethernet = True #False to disable ethernet
###########################




def init_modules():   #tries to init all functions in list sensors which have False in the last index (tries to restart broken ones)
    global l
    print(type(l))
    #print(sensors)
    for i in range(len(sensors)):
        #print(sensors[i], len(sensors[i]))
        if not sensors[i][3]:
            try:
                sensors[i][0]()
                sensors[i][3] = True
                print("successfully initialised ", str(sensors[i][0]), "\n")    
                l.write("successfully initialised ", str(sensors[i][0]), "\n")
            except Exception as e:
                sensors[i][3] = False
                print("failed initialising ", str(sensors[i][0]), ": ", str(e), "\n")    
                l.write("failed initialising ", str(sensors[i][0]), ": ", str(e), "\n")    

def process():  #takes num_of_samples measurements from each sensor, makes average and sends them to the server, if there is an issue with reading, sets last index to False
    global measure
    measure = False
    
    for s in sensors:        
        if s[3] and not len(s[2]) == 0:
            output = []
            for x in range(num_of_samples):
                try:
                    v = s[1]()
                    #print(v)
                    if v == None:
                        print("failed reading ", str(s[1]))
                        l.write("failed reading (timeout)", str(s[1]))
                    elif not type(v)==tuple:
                        output.append((v,))
                    else:
                        output.append(v)
                        
                    
                except:
                    print("failed reading ", str(s[1]))
                    l.write("failed reading ", str(s[1]))

                    s[3] = False
                    continue

            for j, path in enumerate(s[2]):
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

    s = tcp.new_connection(tgt_ip=server, tgt_port=port)  #creating new connection
    while s == -1:  #waiting for connection to be established
        s = tcp.new_connection(tgt_ip=server, tgt_port=port)
    s.send("POST {} HTTP/1.1" "\r\n"          #constructing http header
        "Host: student.gml.cz" "\r\n"
        "Content-Length: {}" "\r\n"
        #"Content-Type: application/json" "\r\n" 
        "Connection-Type: closed""\r\n""\r\n"
        "{}".format(path, len(data), data))
    # There might be a memory leak here, because the connection is not terminated
    # tcp.terminate_connection(s)
    
def ether_on_second_core():     #automaticly sends data when available, runs on second core. To use spi0, set ethernet to False
    while True:
        if ethernet:
            try:
                ntw.rxAllPkt()
                if ntw.configIp4Done:
                    tcp.loop()

                for s in tcp.seassions:
                    if s == None:
                        continue
                    #print("\t[TCP] Session: ", s.state, s.messages)
                    if not s.responses == []:
                        for response in s.responses:
                            if "ERR" in response:
                                print(str(response))
                                l.write("\n", "Error from server", "\n-----------------\n", response, "\n------------------")
                        s.responses.clear()
                gc.collect()  #collects garbage
            except Exception as e:
                print("Exception on second core: ", e)
                l.write("Exception on second core: ", e)
        time.sleep(0.1)  #sleep to prevent high cpu usage            

def callback(timer):    #callback function for timer
    global measure
    measure = True




print("Mateo started")


l = log.log("mateo-log.txt")    #setups logging

if ethernet:    #inits ethernet
    ntw = Ntw.Ntw(spi0, Pin(17))
    ntw.setIPv4(ip, mask, gw_ip)
    tcp = TCP4client(ntw)
    
while True:
    try:
        led = Pin("LED", Pin.OUT)
        led.on()    #turns led on on startup
        main_timer = Timer(-1, mode=Timer.PERIODIC, period=3*60*1000, callback=callback)

        try:
            # https://stackoverflow.com/questions/75257342/micropython-runtimeerror-maximum-recursion-depth-exceeded
            # _thread.stack_size(5*1024)
            # _thread.start_new_thread(recursionTest,())
            _thread.start_new_thread(ether_on_second_core, ())  #starts loop on second core for ethernet
        except Exception as e:
            print("Error starting ethernet thread:", e)
            l.write("Error starting ethernet thread:", str(e), "\n")

        #checks if all functions from file sensors.py in list sensors are valid, if not they will be removed
        k = 0
        while k < (len(sensors)):
            print(sensors[k])
            if not len(sensors[k]) == 3:
                sensors.pop(k)
            else:
                sensors[k].append(False)    
                k += 1
        init_modules()  #runs all init functions in list sensors
        
        gc.collect()  #collects garbage
        print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())

        while True:
            if measure:
                print('processing')
                process()
                gc.collect()
                init_modules()
                gc.collect()
                print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())
            time.sleep(1)

    except Exception as e:
        if e == KeyboardInterrupt:
            break
        print("global Error:", e)
        l.write("global Error: ", str(e), "\n")