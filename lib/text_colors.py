# simple demo for text highlighting in MicroPython
# works on RPi Pico W if your terminal supports ANSI escape codes

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
RESET = "\033[0m"
HIGHLIGHT = "\033[43m"  # yellow background
# print(RED, "hi", RESET)