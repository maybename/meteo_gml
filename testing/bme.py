import bme280
import sensors

bme = bme280.BME280(i2c=sensors.i2c)
print(bme.values)