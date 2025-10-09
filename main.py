from machine import Pin, reset
import _thread, gc, log, time, json
print(time.ticks_ms())
from measuring_sensors import *
from core1 import *
from buffer import *
from keep_alive import WDT
from config import *
print(time.ticks_ms())

print(time.ticks_ms()) 
#from uDnsClient import DnsClientNtw, DNS_RCODE_NOERROR

################################global variables###################################
measured_timer = 0  #last_time measured
core0_WDT = WDT(TIMEOUT)  #watchdog timer for core0
core1_WDT = WDT(TIMEOUT)  #watchdog timer for core1
core1_wants_restart = False  #flag if core1 crashed

data = {}  #dictionary for measured data, reserving space for json data
#####################################################################################

def second_core():     #automaticly sends data when available, runs on second core. To use spi0, set ethernet to False
    global core1_wants_restart
    if SHOW_PRINTS & 0b10:
        print("Starting ethernet thread")

    try:
        if ethernet:    
            ether = EthernetThread() #inits ethernet
            if not SHOW_PRINTS & 0b10:
                ether.enable_prints = False
        if SHOW_PRINTS & 0b10:
            print("Ethernet thread initialized")
        
        while True:
            if ethernet:
                try:
                    ether.run()
                except Exception as e:
                        import sys
                        sys.print_exception(e)
                        try:
                            print("Exception in ethernet: ", e)
                            l.write("Exception in ethernet: ", e)
                        except:
                            print("unable to write to log")
                        core1_wants_restart = True  #sets flag to restart core1
                        _thread.exit()  #exits thread on error
                        
            core1_WDT.feed()  #feeds watchdog timer for core1
            print(core0_WDT.is_alive())
            if not core0_WDT.is_alive():
                if SHOW_PRINTS & 0b10:
                    print("core0 got stuck, restarting...")
                l.write("core0 got stuck, restarting...")
                #input()
                reset()  #restarts if not alive for more than 60 seconds
            
            time.sleep(1)  #sleep to prevent high cpu usage
    except Exception as e:
        core1_wants_restart = True  #sets flag to restart core1

def main_loop():
    global measured_timer, core1_wants_restart, data, last_send
    while True:
        led.toggle()  #toggles led to show the pico is alive
        print("toggled led")
        if run_init_modules():    #if not done in last minute, runs init_modules
            print("reinitializing sensors...")
            init_modules()

        if SHOW_PRINTS & 0b01:
            print("main loop", measured_timer + INTERVAL - time.time()*1000)
        if measured_timer + INTERVAL <= time.time()*1000:  #if last measurement was less than INTERVAL ago, waits
            measured_timer = time.time()*1000
            if SHOW_PRINTS & 0b01:
                print('processing')
            process(data)   #measuring sensors, viz measuring data
            if SHOW_PRINTS & 0b01:
                print(data)
            print(last_send, time.time())
            log_measurement(data)
            gc.collect()
            init_modules()
            gc.collect()
            if SHOW_PRINTS & 0b01:
                print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())


        #WDTs
        core0_WDT.feed()  #feeds watchdog timer for core0
        #print(core1_WDT.is_alive(), core1_wants_restart)
        if not core1_WDT.is_alive() or core1_wants_restart:
            core1_wants_restart = False
            if SHOW_PRINTS & 0b10:
                print("core1 got stuck, restarting...")
            l.write("core1 got stuck, restarting...")
            gc.collect()
            try:
                #pass
                _thread.start_new_thread(second_core, ())  #restarts thread
            except Exception as e:
                print("Error restarting second_core, restarting:", e)
                l.write("Error restarting second_core, restarting:", str(e), "\n")
                #input()
                reset()  #restarts the whole pico
        time.sleep(1)

def startup():
    global measured_timer, l
    l = log.log("mateo-log.txt")    #setups logging    
    if not SHOW_PRINTS & 0b01:
        global sensors_prints
        sensors_prints = False
    
    _thread.stack_size(1<<13)
    try:
        #pass
        _thread.start_new_thread(second_core, ())  #starts loop on second core for ethernet
    except Exception as e:
        print("Error starting ethernet thread:", e)
        l.write("Error starting ethernet thread:", str(e), "\n")
        #input()
        reset()  #restarts the whole pico if error occurs
        
    time.sleep(5)  #waits for core1 to start
    gc.collect()


if __name__ == "__main__":
    # Sync time with NTP server

    if time.time() < 1672441200:  #if time is not set, syncs with NTP server
        print("syncing time...")
        import sntp #imports sntp module, which sets the time acording to sntp_server in config.py

    print("Mateo started")
    led = Pin("LED", Pin.OUT)
    led.on()    #turns led on on startup



    startup()  #calls startup function

    while True:
        try:
            print("looping")
            main_loop()
    
        except KeyboardInterrupt:
            break  #breaks on keyboard interrupt
        except Exception as e:
            gc.collect()
            led.off()
            print("global Error on main:", e)
            try:
                l.write("global Error on main: ", str(e), "\n")
            except:
                print("failed to write into log")
            #input()
            reset()  #restarts on error