import time
from machine import UART, Pin

TIMEOUT = 20000

class PMS5003:
    variable_description = ["PM1.0", "PM2.5", "PM10", 
                    "the number of particles beyond 0.3 um in 0.1 L of air",
                    "the number of particles beyond 0.5 um in 0.1 L of air",
                    "the number of particles beyond 1.0 um in 0.1 L of air",
                    "the number of particles beyond 2.5 um in 0.1 L of air",
                    "the number of particles beyond 5.0 um in 0.1 L of air",
                    "the number of particles beyond 10 um in 0.1 L of air"]
    def __init__(self, UART, timeout = TIMEOUT):
        self.UART = UART
        self.timeout = timeout

    def read(self):
        start_time = time.ticks_ms()
        self.UART.read()    #clear the buffer
        data_raw = bytes()
        while start_time + self.timeout > time.ticks_ms():
            #print(time.ticks_ms(), " ", start_time + self.timeout)
            d = self.UART.read()
                
            if not d == None:
                data_raw += d

            #print("data_raw: ", data_raw)
            while not data_raw[0:2] == b'\x42\x4d' and len(data_raw) > 1:
                data_raw = data_raw[1:]
                
            if len(data_raw) > 4:
                if data_raw[0:2] == b'\x42\x4d':
                    length = data_raw[2]*256 + data_raw[3]
                    if len(data_raw) < 4 + length:
                        continue
                    
                    data = data_raw[4:4+length-2]
                    checksum = data_raw[4+length-2]*256+data_raw[4+length-1]
                    suma = sum(data_raw[:4+length-2])
                    #print(length, data, checksum, suma)

                    if suma == checksum and length == 28:
                        PM1_0, PM2_5, PM10, pm0_3, pm0_5, pm1_0, pm2_5, pm5_0, pm10_0 = [data[i] * 256 + data[i + 1] for i in range(6, 24, 2)]
                        #print("PM1.0: ", PM1_0, " PM2.5: ", PM2_5, " PM10: ", PM10,
                        #      " PM0.3: ", pm0_3, " PM0.5: ", pm0_5, 
                        #      " PM1.0: ", pm1_0, " PM2.5: ", pm2_5, 
                        #      " PM5.0: ", pm5_0, " PM10.0: ", pm10_0)
                        return (PM1_0, PM2_5, PM10, pm0_3, pm0_5, pm1_0, pm2_5, pm5_0, pm10_0)
                    else:
                        print("Checksum error")
                        data_raw = data_raw[1:]
                        continue
            else:
                time.sleep(0.01)
        return None
                
if __name__ == "__main__":
    PMS=PMS5003(UART(0, baudrate=9600, tx=Pin(12), rx=Pin(13), timeout=20))
    while True:
        print(time.ticks_ms())
        data = PMS.read()
        print(data)
        print(time.ticks_ms())