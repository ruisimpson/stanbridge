import board
import time
import busio
from digitalio import DigitalInOut, Direction, Pull

from picoplay import lcd_change_line  # Functions for writing to multiple lines with lcd
from machine import I2C
from pico_i2c_lcd import I2cLcd  # Interfacing with the LCD
from program_v1 import wait_update, wait_update_ms  # Functions for waiting whilst updating the temperature reading

n = 0

file_errors = open("errors.txt", "w")

if __name__ == "__main__":  # Ignore this if statement, just useful for easy importing of this file as a module
    # outputs (numbered from pico end down)
    
     # onboard led
    led_main_pump = DigitalInOut(board.GP25)
    led_main_pump.direction = Direction.OUTPUT
    
      # red led
    led_steam_gen = DigitalInOut(board.GP15)
    led_steam_gen.direction = Direction.OUTPUT
    
     # blue led 1
    led_cold_water = DigitalInOut(board.GP14)
    led_cold_water.direction = Direction.OUTPUT
    
      # green led
    led_door_sol = DigitalInOut(board.GP13)
    led_door_sol.direction = Direction.OUTPUT
    
     # blue led 2
    led_dosing_pump=DigitalInOut(board.GP8)
    led_dosing_pump.direction = Direction.OUTPUT
    
    i2c = I2C(0, sda=machine.Pin(0), scl=machine.Pin(1), freq=400000)
    
    lcd = I2cLcd(i2c, 0x27, 2, 16)  # (i2c, address, rows, columns) for lcd

    # inputs (numbered from pico end down)
     # button 1
    super_wash= DigitalInOut(board.GP12)
    super_wash.direction = Direction.INPUT
    super_wash.pull = Pull.UP
    
      # button 2
    reg_wash = DigitalInOut(board.GP12)
    reg_wash.direction = Direction.INPUT
    red_wash.pull = Pull.UP
    
      # button 3
    float_switch = DigitalInOut(board.GP10)
    float_switch.direction = Direction.INPUT
    float_switch = Pull.UP
    
     # button 4
    foot_switch = DigitalInOut(board.GP9)
    foot_switch.direction = Direction.INPUT
    foot_switch.pull = Pull.UP
   
   temperature = machine.ADC(machine.Pin(26))  # adc for pentiometer to simulate temperature


def update():  # Writes the "temperature" to the lcd. Takes 207.6 (+-0.1%) ms to update
    lcd_change_line("Temperature: " + str(temperature.read_u16() // 700 + 20) + "C", 1)  # updating the temperature
    if temperature.read_u16() // 700 + 20 > 110:  # IRL 120, temperature limited
        led_steam_gen.value(0)
    if float_switch.value():  # updates the cold water valve to the float switch
        led_cold_water.value(0)
    else:
        led_cold_water.value(1)


def wait_update(time_s: int):  # Time must be integer. Updates the temperature while idle
    for _ in range(time_s * 5):
        update()               # Assuming update time of ~200 ms


def wait_update_ms(time_ms: int):  # For wait times < 1s
    for _ in range(time_ms // 200):
        update()


def update_cycle_count(cycle_count: int):  # input the new cycle count
    file_count = open("count.txt", "w")  # creates file
    file_count.write("Number of cycles is: ")  # records n value
    file_count.write(str(cycle_count))
    file_count.flush()
    if cycle_count == 14:
        time = utime.localtime()  # records time when first service warning is given
        file_errors.write(". Service warning given on ")  # puts service warning in log
        file_errors.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
            year=time[0], month=time[1], day=time[2],
            HH=time[3], MM=time[4], SS=time[5]))  # with time
        file_errors.close()
    if cycle_count > 15:
        lcd_change_line("Unit needs servicing", 0)  # puts service warning on LCD after more than 1 press
        wait_update(3)
    file_count.close()


def read_count() -> int:
    f_count = open("count.txt", "r")
    current_cycle_count = int(f_count.readline().split()[4])  # reading and saving the cycle count from the file
    f_count.close()
    return current_cycle_count


def print_cycle_count(current_cycle_count: int):
    lcd_change_line("Cycle count: " + str(current_cycle_count), 0)
    wait_update(2)


def hold_for_water():
    lcd_change_line("Holding for water", 0)
    while not float_switch.value():  # checking main tank is full of (cold) water
        update()


def check_door() -> bool:
    if foot_switch.value() == 1:
        led_door_sol.value(1)
        return True
    else:
        led_door_sol.value(0)
        return False


def disinfect():
    lcd_change_line("Disinfecting", 0)
    for _ in range(50):  # 70 seconds IRL
        if temperature.read_u16() // 700 + 20 < 85:  # check chamber temp
            lcd_change_line("ERROR: LOW TEMP", 0)
            wait_update(1)
            lcd_change_line("Heating steam", 0)
            file_errors.write(". Low temperature warning ")  # puts service warning in log
            time_low_temp = utime.localtime()  # records time when first service warning is given
            file_errors.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
                year=time_low_temp[0], month=time_low_temp[1], day=time_low_temp[2],
                HH=time_low_temp[3], MM=time_low_temp[4], SS=time_low_temp[5]))  # with time
            file_errors.flush()
            while temperature.read_u16() // 700 + 20 < 85:  # wait for chamber temp
                update()
            disinfect()  # recursively retry cycle
            break
        if temperature.read_u16() // 700 + 20 > 110:  # check chamber temp
            lcd_change_line("ERROR: HIGH TEMP", 0)
            wait_update(1)
            file_errors.write(". High temperature warning given ")  # puts service warning in log
            time_high_temp = utime.localtime()  # records time when first service warning is given
            file_errors.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
                year=time_high_temp[0], month=time_high_temp[1], day=time_high_temp[2],
                HH=time_high_temp[3], MM=time_high_temp[4], SS=time_high_temp[5]))  # with time
            file_errors.flush()
            lcd_change_line("COOLING", 0)
            led_steam_gen.value(0)
            while temperature.read_u16() // 700 + 20 > 90:  # let chamber cool until it is <90C
                update()
            led_steam_gen.value(1)
            disinfect()
            break
        update()
    led_steam_gen.value(0)


def do_super_wash():
    wait_update(1)
    led_door_sol.value(0)
    hold_for_water()
    lcd_change_line("Washing", 0)
    led_main_pump.value(1)
    wait_update(4)  # 30 seconds IRL
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
    wait_update(3)  # is this timing correct? Unsure IRL time
    led_dosing_pump.value(0)
    for _ in range(8):  # Pulsing the pump
        led_main_pump.value(1)
        wait_update_ms(200)
        led_main_pump.value(0)
        wait_update_ms(200)
    lcd_change_line("Heating steam", 0)
    while temperature.read_u16() // 700 + 20 < 85:  # checking chamber temp to see if it is disinfecting yet
        update()
    disinfect()
    led_steam_gen.value(0)
    hold_for_water()
    lcd_change_line("Rinsing", 0)
    led_main_pump.value(1)
    wait_update(2)  # 5-10 seconds IRL
    led_main_pump.value(0)
    lcd_change_line("Chamber cooling", 0)
    while temperature.read_u16() // 700 + 20 > 60:  # Waits for safe chamber temperature
        update()
    lcd_change_line("Door Unlocked", 0)


def main():
    door_closed = True  # Fake initial state of door so code may be run
    lcd_change_line("Ready", 0)
    while True:
        if super_wash.value():
            if door_closed:
                led_door_sol.value(1)
                lcd_change_line("Superwash", 0)
                do_super_wash()
                while not check_door():
                    update()
                update_cycle_count(read_count() + 1)  # Updates the cycle count to the previous count + 1
                lcd_change_line("Ready", 0)
            else:
                lcd_change_line("DOOR NOT SHUT", 0)
                wait_update(1)
                lcd_change_line("Ready", 0)
        elif reg_wash.value():
            if door_closed:
                led_door_sol.value(1)
                lcd_change_line("Regular Wash", 0)
                do_reg_wash()
                wait_update(1)
                while not check_door():
                    update()
                update_cycle_count(read_count() + 1)  # Updates the cycle count to the previous count + 1
                lcd_change_line("Ready", 0)
            else:
                lcd_change_line("DOOR NOT SHUT", 0)
                wait_update(1)
                lcd_change_line("Ready", 0)
        update()


if __name__ == "__main__":
    print_cycle_count(read_count())     # Demonstrating how the machine will remember cycle counts
    update_cycle_count(read_count() + 1)    # Increasing cycle count
    print_cycle_count(read_count())
    main()

