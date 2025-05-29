#libraries
from machine import Pin, I2C, UART, SPI, ADC
import time

#sensors libraries
from ads1x15 import ADS1115
import bme280
from mh_z19 import MH_Z19
from PMS5003 import PMS5003

i2c=I2C(1,sda=Pin(2), scl=Pin(3), freq=50000) #I2C
spi0 = SPI(0, baudrate=10000000, sck=Pin(18), mosi=Pin(19), miso=Pin(16))

class interrupts:
    def __init__(self) -> None:
        self.interrupts = {}
        comparator1 = Pin(6, Pin.IN)
        comparator2 = Pin(7, Pin.IN)
        comparator3 = Pin(8, Pin.IN)
        comparator4 = Pin(9, Pin.IN)

        wind_pin = Pin(10, Pin.IN)
        rainfall_pin = Pin(11, Pin.IN)

        wind_pin.irq(trigger=Pin.IRQ_FALLING, handler=self)
        
    def __call__(self, pin) -> None:
        if self.interrupts[pin] == None:
            self.interrupts[pin] = 0
        else:
            self.interrupts[pin] += 1
    
    def start(self):
        self.interrupts["time"] = time.ticks_ms()
        



def PMS_init():
    print("PMS init")
def PMS_read():
    print("PMS read")
    return (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
def MHZ_init():
    print("MHZ init")
def MHZ_read():
    print("MHZ read")
    return 0

def BME_init():
    print("BME init")
        
def BME_read():
    print("BME read")
    return 0, 1, 2
def analog_init():
    print("analog init")
        
'''def analog_read(pin):
    return analog1.raw_to_v(analog1.read(channel1=pin)) if pin < 4 else analog2.raw_to_v(analog2.read(channel1=pin - 4))'''

def multiplexer_init():
    print("multiplexer init")
            
class multiplexer:
    def __init__(self, S0, S1, S2, S3, sig) -> None:
        self.SELECT = [Pin(S0, Pin.OUT), Pin(S1, Pin.OUT), Pin(S2, Pin.OUT), Pin(S3, Pin.OUT), ]
        self.SIG = Pin(sig, Pin.IN)
    
    def read(self, channel):
        self.set_channel(channel)
        return self.SIG.value()
    
    def analogRead(self, channel):
        self.set_channel(channel)
        return ADC(self.SIG).read_u16() * 3.3/65535
    
    def set_channel(self, channel):
        for i,pin in enumerate(self.SELECT):
            pin.value(channel & 0b1 << i)    
        
sensors = [
            [analog_init, lambda: None, ()], #only to setup analog, to read call analog_read
            [multiplexer_init, lambda: None, ()], #only to setup multiplexer, to read call read or analogRead
            [PMS_init, PMS_read, ("PM1.0", "PM2.5", "PM10", "pm0.3", "pm0.5", "pm1.0","pm2.5", "pm5", "pm10")], 
            [MHZ_init, MHZ_read, ("co2",)], 
            [BME_init, BME_read, ("temp", "press", "hum")],            
            ]