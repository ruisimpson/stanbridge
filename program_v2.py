import machine
import utime
import _thread
from picoplay import lcd_lines, lcd_change_line #Functions for writing to multiple lines with lcd
from machine import I2C
from pico_i2c_lcd import I2cLcd
from program_v1 import wait_update, wait_update_ms #Functions for waiting whilst updating the temperature reading

if __name__ == "__main__": #Ignore this if statement, just useful for easy importing of this file as a module
    # outputs (numbered from pico end down)
    led_main_pump = machine.Pin(25, machine.Pin.OUT)                      #onboard led
    led_steam_gen = machine.Pin(15, machine.Pin.OUT)                      #red led
    led_cold_water = machine.Pin(14, machine.Pin.OUT)                     #blue led 1
    led_door_sol = machine.Pin(13, machine.Pin.OUT)                       #green led
    led_dosing_pump = machine.Pin(8, machine.Pin.OUT)                     #blue led 2
    i2c = I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)
    lcd = I2cLcd(i2c, 0x27, 2, 16)                                        #(i2c, address, rows, columns) for lcd
     
    # inputs (numbered from pico end down)
    super_wash = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_DOWN)   #button 1
    reg_wash = machine.Pin(11, machine.Pin.IN, machine.Pin.PULL_DOWN)     #button 2
    float_switch = machine.Pin(10, machine.Pin.IN, machine.Pin.PULL_DOWN) #button 3
    foot_switch = machine.Pin(9, machine.Pin.IN, machine.Pin.PULL_DOWN)   #button 4
    temperature = machine.ADC(machine.Pin(26))                            #adc for pentiometer to simulate temperature

def update_temp(): #Writes the "temperature" to the lcd
    lcd_change_line("Temperature: "+str(temperature.read_u16()//700)+"C", 1) #reading the temperature and updating the display    

def wait_update(time): #Time must be integer. Updates the temperature while idle
    for _ in range(time*10):
        update_temp()
        if float_switch.value(): #change me
            led_cold_water.value(0)
        else:
            led_cold_water.value(1)
            
        utime.sleep_ms(100)

def wait_update_ms(time): #For wait times < 1s
    for _ in range(time//100):
        update_temp()
        if float_switch.value():
            led_cold_water.value(0)
        else:
            led_cold_water.value(1)
        utime.sleep_ms(100)

def hold_for_water():
    lcd_change_line("Holding for water", 0)
    while not float_switch.value(): #checking main tank is full of (cold) water
        wait_update_ms(100)
        
def do_super_wash():
    hold_for_water()
    lcd_change_line("Washing", 0)
    led_main_pump.value(1)
    wait_update(4) #30 seconds IRL
    led_main_pump.value(0)
    do_reg_wash()
    
def do_reg_wash():
    wait_update(1)
    led_door_sol.value(0)
    hold_for_water()
    lcd_change_line("Washing", 0)
    led_main_pump.value(1)
    led_steam_gen.value(1)
    led_dosing_pump.value(1)
    wait_update(3) #is this timing correct? Unsure IRL time
    led_dosing_pump.value(0)
    for _ in range(8):   #Pulsing the pump
        led_main_pump.value(1)
        wait_update_ms(200)
        led_main_pump.value(0)
        wait_update_ms(200)
    lcd_change_line("Heating Steam", 0)
    while temperature.read_u16()//670 < 85: #checking chamber temp to see if it is disinfecting yet
        wait_update(1)
    lcd_change_line("Disinfecting", 0)
    wait_update(5) #70 seconds IRL
    led_steam_gen.value(0)
    hold_for_water()
    lcd_change_line("Rinsing", 0)
    led_main_pump.value(1)
    wait_update(2) #5-10 seconds IRL
    led_main_pump.value(0)
    lcd_change_line("Cycle complete", 0)
    led_door_sol.value(1)
    wait_update(1)
    led_door_sol.value(0)
    lcd_change_line("Door Unlocked", 0)

def main():
    lcd_change_line("Ready", 0)
    while True:
        if super_wash.value():
            led_door_sol.value(1)
            lcd_change_line("Superwash started", 0)
            do_super_wash()
            lcd_change_line("Ready", 0)
        elif reg_wash.value():
            led_door_sol.value(1)
            lcd_change_line("Regular Wash", 0)
            do_reg_wash()
            lcd_change_line("Ready", 0)
        wait_update_ms(100)

if __name__ == "__main__":
    main()


