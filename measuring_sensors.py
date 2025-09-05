from machine import Timer
from sensors import *
import log
from config import *

l = log.log("sensors.log")
measured_data = {"sensors": [], "time": 0}  # dictionary to store sensor data
output = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] for _ in range(num_of_samples)]  # list to store temp output from sensors
run_init_modules = True  # flag to indicate if init modules should be run
init_Timer = Timer(-1, period=60000, mode=Timer.ONE_SHOT, callback=lambda t: init_callback())  # timer to run init modules every second

def init_callback():
    global run_init_modules
    run_init_modules = True



def init_modules():   #tries to init all functions in list sensors which have False in the last index (tries to restart broken ones)
    global run_init_modules
    run_init_modules = False  # resets flag
    init_Timer.init()   #resets timer
    for s in sensors:
        #print(sensors[i], len(sensors[i]))
        if not s.use:
            try:
                if callable(s.init):
                    s.use = True
                    s.init()
                    print(f"sensor {s.name} successfully initialised ")
                    l.write(f"sensor {s.name} successfully initialised ")
                else:
                    print(f"function {s.init} is not callable")
            except Exception as e:
                s.use = False
                print(f"sensor {s.name}: failed initialising:", str(e))
                l.write(f"sensor {s.name}: failed initialising:", str(e))

def process():  #takes num_of_samples measurements from each sensor, makes average and sends them to the server, if there is an issue with reading, sets last index to False
    global measured_data, output
    measured_data = {"sensors": [], "time": 0}  # dictionary to store sensor data
    for s in sensors:        
        if s.use and not len(s.paths) == 0:
            for x in range(num_of_samples):
                try:
                    if not callable(s.read):
                        print(f"sensor {s.name}: function {s.read} is not callable")
                        break
                    v = s.read()
                    print(v)
                    if v == None:
                        print(f"sensor {s.name}: failed reading (timeout)")
                        l.write(f"sensor {s.name}: failed reading (timeout)")
                    elif isinstance(v, (tuple, list)):
                        for i in range(len(v)):
                            output[x][i] = v[i]
                    elif isinstance(v, (int, float)) and v >= 0:
                        output[x][0] = v

                except Exception as e:
                    print(f"sensor {s.name}: failed reading:", str(e))
                    l.write(f"sensor {s.name}: failed reading:", str(e))

                    s.use = False
                    continue

            for j, path in enumerate(s.paths):
                avg = []
                for o in output:
                    if j < len(o):
                        avg.append(o[j])
                avg = average(avg)
                if not avg == None:
                    measured_data["sensors"].append({"type": path, "value": avg})
    
    measured_data["time"] = time.time()
    return measured_data

def average(*args: list[int | float]):   #calculates average of all values in list
    try:
        if args == []:
            return None
        else:
            return sum(args[0]) / len(args[0])
    except Exception as e:
        print("Error calculating average:", e)
        return None