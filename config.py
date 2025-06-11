'''
ip = "172.20.2.190"
mask = "255.255.255.0"
gw_ip = "172.20.2.254"
#'''
'''#for inf3
ip = "172.20.13.112"
mask = "255.255.255.0"
gw_ip = "172.20.13.254"
#'''

#############################  config  ###################################

ip = "192.168.68.129"
mask = "255.255.255.0"
gw_ip = "192.168.68.1"

ethernet = True     #False to disable ethernet

num_of_samples = 5  #number of samples to be taken from each sensor

INTERVAL = 3*60*1000 #the interval between measuring cycles

#########################################################################









ip, mask, gw_ip = bytes([int(i) for i in ip.split('.')]), bytes([int(i) for i in mask.split('.')]), bytes([int(i) for i in gw_ip.split('.')]),   
server = "student.gml.cz" #target server, use domain name

port = 80   #target port
path = "/skriptsql.php" #target path