import machine

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# List of pins to test
pins = [
    machine.Pin(i, machine.Pin.OUT) for i in range(0, 29) if (i < 23 or i > 25) and i != 16  # GPIO 0-29 (exclude any reserved or power pins)
]

def reset_output():
    global output
    output = [[i for i in range(0, 29) if (i < 23 or i > 25) and i != 16]]

def set_pins(high: bool):
    mode = machine.Pin.PULL_DOWN
    if high:
        mode = machine.Pin.PULL_UP
    for pin in pins:
        pin.init(machine.Pin.IN, mode)

def read_pins() -> list:
    return [pin.value() for pin in pins]

def main():
    reset_output()
    set_pins(False)
    for i, pin in enumerate(pins):
        pin.init(machine.Pin.OUT)
        pin.value(1)
        o = read_pins()
        o[i] = "X"
        output.append([output[0][i]] + o)
        pin.value(0)
        pin.init(machine.Pin.IN, machine.Pin.PULL_DOWN)
        
    print("HIGH PIN TEST")
    print_output()

    reset_output()
    set_pins(True)
    for i, pin in enumerate(pins):
        pin.init(machine.Pin.OUT)
        pin.value(0)
        o = read_pins()
        o[i] = "X"
        output.append([output[0][i]] + o)
        pin.value(1)
        pin.init(machine.Pin.IN, machine.Pin.PULL_UP)

    print("LOW PIN TEST")
    print_output()

def print_output():
    #print(output)
    t = " XX |"
    for i in output[0]:
        if i < 10:
            t += f" 0{i} |"
        else:
            t += f" {i} |"
    print(t)
    print("_" * (5 * len(output[0]) + 5))
    for row in output[1:]:
        line = ""
        line += f" {row[0]} |" if row[0] > 9 else f" 0{row[0]} |"
        for i in row[1:]:
            if i == "X":
                line += f" {YELLOW}XX{RESET} |"
            elif i:
                line += f" {GREEN}HH{RESET} |"
            else:
                line += f" {RED}LL{RESET} |"
        print(line)

print(len(pins))
main()
