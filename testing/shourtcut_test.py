import machine
import utime

# List of pins to test
pins = [
    machine.Pin(i, machine.Pin.OUT) for i in range(0, 29) if (i < 23 or i > 25) and i != 16  # GPIO 0-29 (exclude any reserved or power pins)
]

# Helper function to reset pins
def reset_pins():
    for pin in pins:
        pin.init(machine.Pin.IN, machine.Pin.PULL_DOWN)

def test_pins():
    print("Starting pin connectivity test...")

    for i, output_pin in enumerate(pins):
        # Set current pin as output and drive it HIGH
        output_pin.init(machine.Pin.OUT)
        output_pin.value(1)

        print(f"Testing pin {i}:")
        
        # Check all other pins as inputs
        for j, input_pin in enumerate(pins):
            if i == j:
                continue

            input_pin.init(machine.Pin.IN, machine.Pin.PULL_DOWN)
            pin_value = input_pin.value()

            if pin_value == 1 and not input_pin == machine.Pin(23) and not input_pin == machine.Pin(16):
                print(f"  - Pin {j} detects HIGH (connection found)")
            #else:
            #    print(f"  - Pin {j} detects LOW (no connection)")

        # Reset the output pin to input
        output_pin.init(machine.Pin.IN, machine.Pin.PULL_DOWN)
        utime.sleep(0.1)  # Small delay for stability

    print("Pin connectivity test complete.")

# Ensure pins are reset at the start and end of the test
try:
    reset_pins()
    test_pins()
finally:
    reset_pins()
