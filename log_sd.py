from machine import Pin
import sdcard, uos
import time

class log:
    def __init__(self, spi, cs) -> None:
        self._to_write = []
        sd = sdcard.SDCard(spi, cs)
          
        # Mount filesystem
        vfs = uos.VfsFat(sd)
        uos.mount(vfs, "/sd")
    
    def add(self, *args: str | int | float | function):
        line = ''
        for arg in args:
            if not type(arg) == str:
                arg = str(arg)
            
            line += arg

        self._to_write.append((time.ticks_ms(), line))
        
    def write_all(self):
        with open("/sd/test01.txt", "w") as file:
            for line in self._to_write:
                file.write(line + "\n")