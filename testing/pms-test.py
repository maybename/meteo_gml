from machine import UART, Pin


pms = UART(0, baudrate=9600, tx=Pin(12), rx=Pin(13))


