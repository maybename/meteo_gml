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


ip = "192.168.68.129"
mask = "255.255.255.0"
gw_ip = "192.168.68.1"

sntp_server = "pool.ntp.org"  # NTP server for time synchronization

ethernet = True     #False to disable ethernet

INTERVAL = 3*60*1000 #the interval between measuring cycles
TIMEOUT = 60000  #timeout for cores to prevent hanging in milliseconds
num_of_samples = 5  # number of samples to take for each sensor
data_file = "measurements.log"

#########################################################################









ip, mask, gw_ip = bytes([int(i) for i in ip.split('.')]), bytes([int(i) for i in mask.split('.')]), bytes([int(i) for i in gw_ip.split('.')]),   
server = "student.gml.cz" #target server, use domain name

port = 80   #target port
path = "/meteo/measurements.php" #target path