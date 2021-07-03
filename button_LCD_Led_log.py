import utime
import _thread
import machine
from machine import I2C
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

#LDC specs
I2C_ADDR     = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16

#inputs
button_1 = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_DOWN)
button_2 = machine.Pin(11, machine.Pin.IN, machine.Pin.PULL_DOWN)

#Outputs
led_red = machine.Pin(15, machine.Pin.OUT)
led_blue = machine.Pin(14, machine.Pin.OUT)
led_green = machine.Pin(13, machine.Pin.OUT)

i2c = I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)    

lcd.putstr("Press button to turn on LED")
n=0 #starts cycle count at 0



while True:
    if button_1.value() == 1: #press button to turn on LEDs
        print("pressed 1")
        lcd.clear()
        led_red.value(1)
        utime.sleep(1)
        led_blue.value(1)
        utime.sleep(0.5)
        led_green.value(1)
        led_red.value(0)
        lcd.putstr("You pressed the button")
        utime.sleep(1)
        led_blue.value(0)
        utime.sleep(1)
        lcd.clear()
        lcd.putstr("LED on")
        led_blue.value(1)
        
       
        utime.sleep(2)
        led_red.value(0)
        led_blue.value(0)
        led_green.value(0)
        lcd.clear()
        
        
        n=n+1 #adds one to cycle count
        file=open("presses.txt","w") #creates file
        file.write("Number of presses is: ") #records n value
        file.write(str(n))
        file.flush()
        
        if n==2:
            time = utime.localtime() # records time when first service warning is given
            
        if n>1:
            lcd.clear()
            lcd.putstr("Unit needs      servicing") #puts service warning on LCD after more than 1 press
            utime.sleep(3)
            lcd.clear()
            file.write(". Service warning given on ") #puts service warning in log
            
            file.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
            year=time[0], month=time[1], day=time[2],
            HH=time[3], MM=time[4], SS=time[5])) #with time
            file.flush()
            
            
        lcd.putstr("Press button to turn on LED")
            
       
       
    if button_2.value() == 1: 
        lcd.clear()
        print("pressed 2")
        lcd.putstr("Number of       presses is ") #displays number of cycles on LCD when button two is pressed
        lcd.putstr(str(n))
        
    
            
        
    