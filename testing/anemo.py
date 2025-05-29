#this will be the main code, which will use the other files


#multithreading???

import math
import time
from sensors import Sensors
from ssd1306 import SSD1306_I2C
from machine import Pin

r = 10 #cm
num_of_mesuring_per_second = 2





WIDTH =128 
HEIGHT= 64
if __name__ == "__main__":
    mateo = Sensors()
    oled = SSD1306_I2C(WIDTH,HEIGHT,mateo.i2c)
    
    while True:
        mateo.wind_start()
        time.sleep(1)
        frequency = mateo.wind_values()["wind"]
        RPM = frequency * 60
        wind_speed = frequency * r * 2 * math.pi /100
        oled.fill(0)
        oled.text(str(RPM), 64, 5)
        oled.text("RPM:", 10, 5)
        oled.text("speed:", 10, 30)
        oled.text(f"{wind_speed:.2f} m/s", 30, 40)
        oled.text(f"{wind_speed*3.6:.2f} km/h", 30, 50)
        oled.show()