import machine
import utime
import _thread
from picoplay import lcd_lines, lcd_change_line #Functions for writing to multiple lines with lcd
from machine import I2C
from pico_i2c_lcd import I2cLcd

if __name__ == "__main__": #Ignore this if statement, just useful for easy importing of this file as a module
    # outputs
    led_onboard = machine.Pin(25, machine.Pin.OUT)
    led_red = machine.Pin(15, machine.Pin.OUT)
    led_blue = machine.Pin(13, machine.Pin.OUT)
    led_green = machine.Pin(12, machine.Pin.OUT)
    i2c = I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)
    lcd = I2cLcd(i2c, 0x27, 2, 16) #(i2c, address, rows, columns) for lcd
     
    # inputs
    button_1 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_DOWN)
    adc = machine.ADC(machine.Pin(26)) #adc for pentiometer to simulate temperature


def button_pressed_thread(): #Run as a thread that constantly checks if the button has been pressed
    global button_pressed
    while True:
        if button_1.value() == 1:
            button_pressed = True
        utime.sleep_ms(10)

def update_temp(): #Writes the "temperature" to the lcd
    lcd_change_line("Temperature: "+str(adc.read_u16()//700)+"C", 1) #reading the temperature and updating the display    

def wait_update(time): #Time must be integer. Updates the temperature while idle
    for _ in range(time*10):
        update_temp()
        utime.sleep_ms(100)

def wait_update_ms(time): #For wait times < 1s
    for _ in range(time//100):
         update_temp()
         utime.sleep_ms(100)

def wash(): #dummy wash cycle
    lcd_change_line("Washing", 0)
    for i in range(10):
        led_red.toggle()
        wait_update_ms(100)
        led_blue.toggle()
        wait_update_ms(100)
        led_green.toggle()
        wait_update_ms(100)


def disinfect(): #dummy disinfection cycle
    lcd_change_line("Disinfecting", 0)
    for i in range(20):
        led_red.toggle()
        led_blue.toggle()
        led_green.toggle()
        utime.sleep_ms(200)
        update_temp()
    led_red.value(0)
    led_blue.value(0)
    led_green.value(0)

if __name__ == "__main__": #Ignore this if statement, just for easy importing of this file as a module
    global button_pressed
    button_pressed = False
    _thread.start_new_thread(button_pressed_thread, ())
    lcd_change_line("Ready", 0)

    while True:
        if button_pressed:
            # pretend washer cycle
            wash()
            disinfect()
            lcd_change_line("Cycle complete", 0)
            wait_update(1)
            lcd_change_line("Refilling tank", 0)
            wait_update(5)
            lcd_change_line("Ready", 0)
            button_pressed = False
        wait_update(1)
