import board
import time
import busio
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
import hd44780
from secrets import secrets
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests as requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError
from adafruit_io import adafruit_io


#from picoplay import lcd_change_line  # Functions for writing to multiple lines with lcd
#from machine import I2C
#from pico_i2c_lcd import I2cLcd  # Interfacing with the LCD

n = 0

#file_errors = open("errors.txt", "w")



if __name__ == "__main__":  # Ignore this if statement, just useful for easy importing of this file as a module
    # outputs (numbered from pico end down)
    
        # onboard led
    led_main_pump = DigitalInOut(board.GP25)
    led_main_pump.direction = Direction.OUTPUT
    
        # red led
    led_steam_gen = DigitalInOut(board.GP15)
    led_steam_gen.direction = Direction.OUTPUT
    
        # green led
    led_door_sol = DigitalInOut(board.GP13)
    led_door_sol.direction = Direction.OUTPUT
    
        # blue led
    led_dosing_pump=DigitalInOut(board.GP14)
    led_dosing_pump.direction = Direction.OUTPUT

    while True:
        led_main_pump.value = not led_main_pump.value
        led_dosing_pump.value = not led_dosing_pump.value
        led_steam_gen.value = not led_steam_gen.value
        led_door_sol.value = not led_door_sol.value
        time.sleep(0.1)