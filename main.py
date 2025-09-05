from machine import Pin, reset
import _thread, gc, log, time, json
print(time.ticks_ms())
from measuring_sensors import *
from core1 import *

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

file_lock = _thread.allocate_lock()  #lock for file access


def second_core():     #automaticly sends data when available, runs on second core. To use spi0, set ethernet to False
    global core1_wants_restart
    print("Starting ethernet thread")
    try:
        if ethernet:    
            ether = EthernetThread() #inits ethernet
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
            gc.collect()  #collects garbage
            if not core0_WDT.is_alive():
                print("core0 got stuck, restarting...")
                l.write("core0 got stuck, restarting...")
                input()
                reset()  #restarts if not alive for more than 60 seconds
            
            time.sleep(1)  #sleep to prevent high cpu usage
    except Exception as e:
        core1_wants_restart = True  #sets flag to restart core1

def main_loop():
    global measured_timer, core1_wants_restart
    while True:
        if run_init_modules:    #if not done in last minute, runs init_modules
            init_modules()
        
        print("main loop", measured_timer + INTERVAL - time.time()*1000)
        if measured_timer + INTERVAL <= time.time()*1000:  #if last measurement was less than INTERVAL ago, waits
            measured_timer = time.time()*1000
            print('processing')
            data = process()   #measuring sensors, viz measuring data
            print(data)
            file_lock.acquire()
            print("lock acquired")
            try:
                with open(data_file, "a") as f:
                    f.write(json.dumps(data) + "\n")
                    f.flush()
            except Exception as e:
                print("Error writing to data file:", e)
                try:
                    l.write("Error writing to data file:", str(e), "\n")
                except:
                    print("failed to write into log")
            finally:
                file_lock.release()

                gc.collect()
                init_modules()
                gc.collect()
                print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())
        
        
        #WDTs
        core0_WDT.feed()  #feeds watchdog timer for core0
        #print(core1_WDT.is_alive(), core1_wants_restart)
        if not core1_WDT.is_alive() or core1_wants_restart:
            core1_wants_restart = False
            print("core1 got stuck, restarting...")
            l.write("core1 got stuck, restarting...")
            gc.collect()
            try:
                _thread.start_new_thread(second_core, ())  #restarts thread
            except Exception as e:
                print("Error restarting second_core, restarting:", e)
                l.write("Error restarting second_core, restarting:", str(e), "\n")
                input()
                reset()  #restarts the whole pico
        time.sleep(1)

def read_last_line(filename):
    with open(filename, "rb") as f:
        f.seek(0, 2)  # go to end
        pos = f.tell()
        line = b""
        while pos > 0:
            pos -= 1
            f.seek(pos)
            char = f.read(1)
            if char == b"\n" and line:
                break
            line = char + line
        return line.decode()
    


def startup():
    global measured_timer, l
    l = log.log("mateo-log.txt")    #setups logging
    try:
        measured_timer = json.loads(read_last_line(data_file))["time"]

    except (OSError, ValueError):
        print("Data file not found, creating new one.")
        with open(data_file, "w"):
            pass  #creates new file
        
    except Exception as e:
        print("Error reading data file:", e)
        l.write("Error reading data file:", str(e), "\n")
        
    _thread.stack_size(1<<13)
    try:
        #pass
        _thread.start_new_thread(second_core, ())  #starts loop on second core for ethernet
    except Exception as e:
        print("Error starting ethernet thread:", e)
        l.write("Error starting ethernet thread:", str(e), "\n")
        input()
        reset()  #restarts the whole pico if error occurs

    gc.collect()


if __name__ == "__main__":
    # Sync time with NTP server

    if time.time() < 1672441200:  #if time is not set, syncs with NTP server
        print("syncing time...")
        from sntp import actual_time
        from machine import RTC
        RTC().datetime(actual_time)  #syncs time with NTP server
        print(time.time())

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
            input()
            reset()  #restarts on error