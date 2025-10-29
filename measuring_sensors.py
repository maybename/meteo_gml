from machine import Timer
from sensors import *
import log, time
from config import *

output = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] for _ in range(num_of_samples)]  # list to store temp output from sensors
last_init = 0

sensors_prints = True  #enable prints for debugging


def run_init_modules():
    return time.time() > last_init + 60



def init_modules():   #tries to init all functions in list sensors which have False in the last index (tries to restart broken ones)
    if sensors_prints:
        print("initializing sensors...")
    global last_init
    last_init = time.time()
    for s in sensors:
        #print(sensors[i], len(sensors[i]))
        if not s.use:
            try:
                if callable(s.init):
                    s.use = True
                    s.init()
                    if sensors_prints:
                        print(f"sensor {s.name} successfully initialised ")
                    measurements_l.write(f"sensor {s.name} successfully initialised ")
                else:
                    if sensors_prints:
                        print(f"function {s.init} is not callable")
            except Exception as e:
                s.use = False
                print(f"sensor {s.name}: failed initialising:", str(e))
                measurements_l.write(f"sensor {s.name}: failed initialising:", str(e))

def process(measured_data):  #takes num_of_samples measurements from each sensor, makes average and sends them to the server, if there is an issue with reading, sets last index to False
    global output
    measured_data["sensordatavalues"] = []
    for s in sensors:        
        if s.use and not len(s.paths) == 0:
            for x in range(num_of_samples):
                try:
                    if not callable(s.read):
                        if sensors_prints:
                            print(f"sensor {s.name}: function {s.read} is not callable")
                        break
                    v = s.read()
                    if sensors_prints:
                        print(v)
                    if v == None:
                        print(f"sensor {s.name}: failed reading (timeout)")
                        measurements_l.write(f"sensor {s.name}: failed reading (timeout)")
                    elif isinstance(v, (tuple, list)):
                        for i in range(len(v)):
                            output[x][i] = v[i]
                    elif isinstance(v, (int, float)) and v >= 0:
                        output[x][0] = v

                except Exception as e:
                    print(f"sensor {s.name}: failed reading:", str(e))
                    measurements_l.write(f"sensor {s.name}: failed reading:", str(e))

                    s.use = False
                    continue

            for j, path in enumerate(s.paths):
                avg = []
                for o in output:
                    if j < len(o):
                        avg.append(o[j])
                avg = average(avg)
                if not avg == None:
                    if measured_data.get("sensordatavalues") is None:
                        measured_data["sensordatavalues"] = []
                    measured_data["sensordatavalues"].append({"value_type": path, "value": avg})
    
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