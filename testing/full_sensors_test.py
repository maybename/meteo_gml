from measuring_sensors import *
import json, gc, _thread
from config import *

file_lock = _thread.allocate_lock()  #lock for file access
init_modules()
data={}  #dictionary for measured data, reserving space for json data
process(data)   #measuring sensors, viz measuring data