import machine
import utime
import _thread
from picoplay import lcd_lines, lcd_change_line
from machine import I2C
from pico_i2c_lcd import I2cLcd

I2C_ADDR = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16

# outputs
led_onboard = machine.Pin(25, machine.Pin.OUT)
led_red = machine.Pin(15, machine.Pin.OUT)
led_blue = machine.Pin(13, machine.Pin.OUT)
led_green = machine.Pin(12, machine.Pin.OUT)
i2c = I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

# inputs
button_1 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN)


# noinspection PyArgumentList
def button_pressed_thread():
    global button_pressed
    button_pressed = False
    while True:
        if button_1.value() == 1:
            button_pressed = True
        utime.sleep_ms(10)


def wash():
    lcd_change_line("Washing", 0)
    for i in range(10):
        led_red.toggle()
        utime.sleep_ms(100)
        led_blue.toggle()
        utime.sleep_ms(100)
        led_green.toggle()
        utime.sleep_ms(100)


def disinfect():
    lcd_change_line("Disinfecting", 0)
    for i in range(20):
        led_red.toggle()
        led_blue.toggle()
        led_green.toggle()
        utime.sleep_ms(200)
    led_red.value(0)
    led_blue.value(0)
    led_green.value(0)


global button_pressed
_thread.start_new_thread(button_pressed_thread, ())
temperature = 15
text_line_2 = "Temperature: " + str(temperature) + "C"
lcd_lines("Ready", text_line_2)

while True:
    if button_pressed:
        # pretend washer cycle
        wash()
        disinfect()
        lcd_change_line("Cycle complete", 0)
        utime.sleep(1)
        lcd_change_line("Refilling tank", 0)
        utime.sleep(5)
        lcd_change_line("Ready", 0)
        button_pressed = False
