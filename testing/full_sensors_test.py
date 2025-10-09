from measuring_sensors import *
import json, gc, _thread
from config import *

file_lock = _thread.allocate_lock()  #lock for file access
init_modules()
data={}  #dictionary for measured data, reserving space for json data
process(data)   #measuring sensors, viz measuring data

file_lock.acquire()
try:
    with open(data_file, "a") as f:
        f.write(json.dumps(data) + "\n")
        f.flush()
finally:
    file_lock.release()

    gc.collect()
    init_modules()
    gc.collect()
    print('free: ', gc.mem_free(), '  used: ', gc.mem_alloc())