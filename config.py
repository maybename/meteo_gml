import _thread, log

#roof
ip = "172.20.2.190"
mask = "255.255.255.0"
gw_ip = "172.20.2.254"

#home
ip = "192.168.68.129"
mask = "255.255.255.0"
gw_ip = "192.168.68.1"

#inf3
ip = "172.20.13.112"
mask = "255.255.255.0"
gw_ip = "172.20.13.254"


#############################  config  ###################################
#home
ip = "192.168.68.129"
mask = "255.255.255.0"
gw_ip = "192.168.68.1"

sntp_server = "pool.ntp.org"  # NTP server for time synchronization

ethernet = True     #False to disable ethernet

INTERVAL = 3*60*1000 #the interval between measuring cycles
TIMEOUT = 60000  #timeout for cores to prevent hanging in milliseconds
SEND_INTERVAL = 10*60  #maximum interval between sending data in seconds, after it data saved into file not in RAM
MAX_DATA_FILE_SIZE = 1000000  #maximum size of data file in bytes, after it is cleared



port = 80   #target port
path = "/meteo/data.php" #target path
sensor_id = 1225515600
    
    
num_of_samples = 5  # number of samples to take for each sensor

#########################################################################
SHOW_PRINTS = 0b11  #bitmask for prints, 1st bit for main, 2nd for ethernet
meteo_l = log.log("mateo-log.txt")    #setups logging
measurements_l = log.log("sensors.log")



ip, mask, gw_ip = bytes([int(i) for i in ip.split('.')]), bytes([int(i) for i in mask.split('.')]), bytes([int(i) for i in gw_ip.split('.')]),   
server = "student.gml.cz" #target server, use domain name