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

lcd = hd44780.HD44780(busio.I2C(board.GP1,board.GP0), address=0x27)  # (i2c, address, rows, columns) for lcd


def write_scroll(message, linenumber):
    while True:
        for i in range(len(message)):
            lcd.write(message[i:i+20], linenumber)
            time.sleep(0.2)
        


write_scroll("Hey this is a long message that I'm scrolling across the display", 1)