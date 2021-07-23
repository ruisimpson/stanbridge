import board
import time
import busio
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
import hd44780

#from picoplay import lcd_change_line  # Functions for writing to multiple lines with lcd
#from machine import I2C
#from pico_i2c_lcd import I2cLcd  # Interfacing with the LCD

n = 0

#file_errors = open("errors.txt", "w")



if __name__ == "__main__":  # Ignore this if statement, just useful for easy importing of this file as a module
    # outputs (numbered from pico end down)
    
     # Main Pump
    main_pump = DigitalInOut(board.GP17)      #True = off, False = on
    main_pump.direction = Direction.OUTPUT
    main_pump.value = True
    
      # Steam Generator
    steam_gen = DigitalInOut(board.GP15)       #True = off, False = on
    steam_gen.direction = Direction.OUTPUT
    steam_gen.value = True
    
      # Door Solenoid
    door_sol = DigitalInOut(board.GP13)         #True = off, False = on
    door_sol.direction = Direction.OUTPUT
    door_sol.value = True
    
     # Dosing pump
    dosing_pump=DigitalInOut(board.GP21)
    dosing_pump.direction = Direction.OUTPUT
    dosing_pump.value = False
        
    #lcd = hd44780.HD44780(busio.I2C(board.GP1,board.GP0), address=0x27)  # (i2c, address, rows, columns) for lcd
    
    # inputs (numbered from pico end down)
     # button 1
    super_wash = DigitalInOut(board.GP3)
    super_wash.direction = Direction.INPUT
    super_wash.pull = Pull.DOWN
    
      # button 2
    reg_wash = DigitalInOut(board.GP4)
    reg_wash.direction = Direction.INPUT
    reg_wash.pull = Pull.DOWN
    
      # Float switch
    float_switch = DigitalInOut(board.GP5)
    float_switch.direction = Direction.INPUT
    float_switch.pull = Pull.DOWN
    
     # Foot switch
    foot_switch = DigitalInOut(board.GP6)
    foot_switch.direction = Direction.INPUT
    foot_switch.pull = Pull.DOWN
    
    # Door microswitch (Checks status of door, open=True or closed=False)
    door_microswitch = DigitalInOut(board.GP16)
    door_microswitch.direction = Direction.INPUT
    door_microswitch.pull = Pull.UP
   
    # adc for pentiometer to simulate temperature
    temperature = AnalogIn(board.GP26)

def write_clear(message : str, linenumber : int):
    #lcd.write(message + " " * (20 - len(message)), linenumber)
    return 0
    
    
def update():  # Writes the "temperature" to the lcd. Takes 207.6 (+-0.1%) ms to update
    write_clear("Temperature: " + str(temperature.value // 700 + 20) + "C", 2)  # updating the temperature
    if temperature.value // 700 + 20 > 110:  # IRL 120, temperature limited # Might need to change read_u16 for circuitPY
        steam_gen.value=True
    if not door_microswitch.value:
        write_clear("Door closed", 3)
    else:
        write_clear("Door open", 3)


# def wait_update(time_s: int):  # Time must be integer. Updates the temperature while idle CLEVER WAY OF DOING IT???????? BY WAITING UNTIL TIME = TIME+X
#     for _ in range(time_s * 5):
#         update()               # Assuming update time of ~200 ms


def wait_update(time_s : int):
    start_time = time.time()
    while time.time() < start_time + time_s:   # Loops the update() until inputted time has elapsed
        update()
    
    
def wait_update_ms(time_ms: int):  # For wait times < 1s
    for _ in range(time_ms // 200):
        update()


def update_cycle_count(cycle_count: int):  # input the new cycle count
    file_count = open("count.txt", "w")  # creates file
    file_count.write("Number of cycles is: ")  # records n value
    file_count.write(str(cycle_count))
    file_count.flush()
    if cycle_count == 14:
        time = time.localtime()  # records time when first service warning is given
        file_errors.write(". Service warning given on ")  # puts service warning in log
        file_errors.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
            year=time[0], month=time[1], day=time[2],
            HH=time[3], MM=time[4], SS=time[5]))  # with time
        file_errors.flush()
    if cycle_count > 15:
        write_clear("Unit needs servicing", 1)  # puts service warning on LCD after more than 1 press
        wait_update(3)
    file_count.flush()


def read_count() -> int:
    f_count = open("count.txt", "r")
    current_cycle_count = int(f_count.readline().split()[4])  # reading and saving the cycle count from the file
    f_count.close()
    return current_cycle_count


def print_cycle_count(current_cycle_count: int):
    write_clear("Cycle count: " + str(current_cycle_count), 4)


def hold_for_water():
    write_clear("Holding for water", 1)
    while float_switch.value:  # checking main tank is full of (cold) water
        update()


def check_door() -> bool:
    if not foot_switch.value:
        door_sol.value=True
        return True
    else:
        door_sol.value=False
        return False
    

def door_checker():
    if not foot_switch.value:
        door_sol.value = False
        while not door_microswitch.value:
            time.sleep(0.01)
        door_sol.value = True
        

def disinfect():
    write_clear("Disinfecting", 1)
    for _ in range(70):  # 70 seconds IRL
        if temperature.value // 700 + 20 < 80:  # check chamber temp
            write_clear("ERROR: LOW TEMP", 1)
            wait_update_ms(1000)
            write_clear("Heating steam", 1)
#            file_errors.write(". Low temperature warning ")  # puts service warning in log
#            time_low_temp = time.localtime()  # records time when first service warning is given
#            file_errors.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
#                year=time_low_temp[0], month=time_low_temp[1], day=time_low_temp[2],
#                HH=time_low_temp[3], MM=time_low_temp[4], SS=time_low_temp[5]))  # with time
#            file_errors.flush()
            while temperature.value // 700 + 20 < 80:  # wait for chamber temp
                update()
            disinfect()  # recursively retry cycle
            break
        if temperature.value // 700 + 20 > 95:  # check chamber temp
            write_clear("ERROR: HIGH TEMP", 1)
            wait_update_ms(1000)
#            file_errors.write(". High temperature warning given ")  # puts service warning in log
#            time_high_temp = time.localtime()  # records time when first service warning is given
#            file_errors.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
#                year=time_high_temp[0], month=time_high_temp[1], day=time_high_temp[2],
#                HH=time_high_temp[3], MM=time_high_temp[4], SS=time_high_temp[5]))  # with time
#            file_errors.flush()
            write_clear("COOLING", 1)
            steam_gen.value=True
            while temperature.value // 700 + 20 > 90:  # let chamber cool until it is <90C
                update()
            steam_gen.value=True
            disinfect()
            break
        wait_update_ms(1000)
    steam_gen.value=True


def do_super_wash():
    #door_sol.value=True
    hold_for_water()
    write_clear("Washing", 1)
    main_pump.value=False
    wait_update(30)  # 30 seconds IRL
    main_pump.value=True
    do_reg_wash()


def do_reg_wash():
    #door_sol.value=True
    hold_for_water()
    write_clear("Washing", 1)
    main_pump.value=False
    steam_gen.value=False
    dosing_pump.value=True
    wait_update(10)  # is this timing correct? Unsure IRL time
    dosing_pump.value=False
    for _ in range(12):  # Pulsing the pump
        main_pump.value = not main_pump.value 
        wait_update(5)
    main_pump.value = True
    write_clear("Heating steam", 1)
    while temperature.value // 700 + 20 < 80:  # checking chamber temp to see if it is disinfecting yet
        update()
    disinfect()
    steam_gen.value=True
    hold_for_water()
    write_clear("Rinsing", 1)
    main_pump.value=False
    wait_update(10)  # 5-10 seconds IRL
    main_pump.value=True
    write_clear("Chamber cooling", 1)
    while temperature.value // 700 + 20 > 60:  # Waits for safe chamber temperature
        update()
    write_clear("Door Unlocked", 1)


def main():
    print_cycle_count(read_count())  # Fake initial state of door so code may be run
    write_clear("Ready", 1)
    while True:
        if super_wash.value==1:
            if not door_microswitch.value:
                write_clear("Superwash", 1)
                wait_update_ms(1000)
                do_super_wash()
                while foot_switch.value: #checks for footpedal
                    update()
                door_sol.value = False
                while not door_microswitch.value:  #waits until door registers open then cancels the door solenoid
                    time.sleep(0.01)
                door_sol.value = True
                print_cycle_count(read_count())
                #update_cycle_count(read_count() + 1)  # Updates the cycle count to the previous count + 1
                write_clear("Ready", 1)
            else:
                write_clear("DOOR NOT SHUT", 1)
                wait_update_ms(1000)
                write_clear("Ready", 1)
        elif reg_wash.value==1:
            if not door_microswitch.value:
                write_clear("Regular Wash", 1)
                wait_update_ms(1000)
                do_reg_wash()
                while foot_switch.value: #checks for footpedal
                    update()
                door_sol.value = False
                while not door_microswitch.value:  #waits until door registers open then cancels the door solenoid
                    time.sleep(0.01)
                door_sol.value = True
                print_cycle_count(read_count())
                #update_cycle_count(read_count() + 1)  # Updates the cycle count to the previous count + 1
                write_clear("Ready", 1)
            else:
                write_clear("DOOR NOT SHUT", 1)
                wait_update_ms(1000)
                write_clear("Ready", 1)
        door_checker()
        update()
        


if __name__ == "__main__":
    main()
    
#main()
#    print_cycle_count(read_count())     # Demonstrating how the machine will remember cycle counts
#    update_cycle_count(read_count() + 1)    # Increasing cycle count
#    print_cycle_count(read_count())
#    write_clear("Testing inputs", 1)
#    for i in range(10):
        #steam_gen.value = not steam_gen.value
        #door_sol.value = not door_sol.value
        #dosing_pump.value = not dosing_pump.value
        #main_pump.value = not main_pump.value
#        time.sleep(1)
#     while not super_wash:
#         print("super wash value: " + str(super_wash.value))
#         print("reg wash value: " + str(reg_wash.value))
#         print("float switch value: " + str(float_switch.value))
#         print("foot switch value: " + str(foot_switch.value))
#         print("temperature: " + str(temperature.value))
#     print_cycle_count(read_count())
#     update_cycle_count(read_count() + 1)   #need to fix read-only filesystem
#     wait_update_ms(1000)
#     print_cycle_count(read_count())
#     time.sleep(10
#main()