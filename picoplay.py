import machine
import utime
import _thread
from machine import I2C
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

I2C_ADDR     = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16

#outputs
led_onboard = machine.Pin(25, machine.Pin.OUT)
led_1_external = machine.Pin(15, machine.Pin.OUT)
i2c = I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

#inputs
button_1 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN)


def lcd_lines(message1, message2):
    line1 = message1[:16] + (16-len(message1)) * ' '
    lcd.clear()
    lcd.putstr(line1)
    lcd.putstr(message2)

def lcd_change_line(message1, linenumber):
    if linenumber == 0:
        lcd.move_to(0,0)
        for char in message1[:16]:
            lcd.putchar(char)
        lcd.putstr(' ' * (16-len(message1[:16])))
    elif linenumber == 1:
        lcd.move_to(0,1)
        for char in message1[:16]:
            lcd.putchar(char)
        lcd.putstr(' ' * (16-len(message1[:16])))
    else:
        print("Invalid line number")

def button_pressed_thread():
    global button_pressed
    while True:
        if button_1.value() == 1:
            button_pressed = True
        utime.sleep(0.01)


if __name__ == "__main__": 
    global button_pressed
    button_pressed = False
    _thread.start_new_thread(button_pressed_thread, ())
    while True:
        if button_pressed == 1:
            lcd_lines("The first line is too long", "The second line")
            utime.sleep(3)
            lcd_change_line("Different",1)
            led_1_external.toggle()
            utime.sleep(0.5)
            led_1_external.toggle()
            button_pressed = False
        
