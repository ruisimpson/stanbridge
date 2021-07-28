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
    led_dosing_pump=DigitalInOut(board.GP20)
    led_dosing_pump.direction = Direction.OUTPUT
    
        # LCD
    lcd = hd44780.HD44780(busio.I2C(board.GP1,board.GP0), address=0x27)  # (i2c, address, rows, columns) for lcd
    
        # Wireless module
    esp32_cs = DigitalInOut(board.GP7)
    esp32_ready = DigitalInOut(board.GP10)
    esp32_reset = DigitalInOut(board.GP11)

    spi = busio.SPI(board.GP18, board.GP19, board.GP16)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

    # inputs (numbered from pico end down)
        # button 1
    super_wash = DigitalInOut(board.GP2)
    super_wash.direction = Direction.INPUT
    super_wash.pull = Pull.DOWN
    
        # button 2
    reg_wash = DigitalInOut(board.GP3)
    reg_wash.direction = Direction.INPUT
    reg_wash.pull = Pull.DOWN
    
        # button 3
    float_switch = DigitalInOut(board.GP4)
    float_switch.direction = Direction.INPUT
    float_switch.pull = Pull.DOWN
    
        # button 4
    foot_switch = DigitalInOut(board.GP5)
    foot_switch.direction = Direction.INPUT
    foot_switch.pull = Pull.DOWN
    
        #button wifi
    door_microswitch = DigitalInOut(board.GP12)
    door_microswitch.direction = Direction.INPUT
    door_microswitch.pull = Pull.UP
   
    # adc for pentiometer to simulate temperature
    temperature = AnalogIn(board.GP26)

def write_clear(message : str, linenumber : int):
    lcd.write(message + " " * (20 - len(message)), linenumber)
    
    
def update():  # Writes the "temperature" to the lcd. Takes 207.6 (+-0.1%) ms to update
    write_clear("Temperature: " + str(temperature.value // 700 + 20) + "C", 2)  # updating the temperature
    if temperature.value // 700 + 20 > 110:  # IRL 120, temperature limited # Might need to change read_u16 for circuitPY
        led_steam_gen.value=False
    if door_microswitch.value:
        write_clear("Door closed", 3)
    else:
        write_clear("Door open", 3)


def wait_update(time_s : float) -> float: # Should accurately time within 200ms. Will always time for too long
    start_time = time.monotonic()
    while time.monotonic() < start_time + time_s:   # Loops the update() until inputted time has elapsed
        update()
    return time.monotonic() - start_time # Returns the actual elapsed time (For validating the accuracy)

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


def post_data(data, feed_name):
    if not esp.is_connected:
        for _ in range(5):
            print("Not connected to WiFi: Attempting to connect")
            try:
                esp.connect_AP(secrets["ssid"], secrets["password"])
            except RuntimeError as i:
                print("could not connect to WiFi: ", i)
                continue
            print("Connected to WiFi")
            socket.set_interface(esp)
            requests.set_socket(socket, esp)
            break

        # Initialize an Adafruit IO HTTP API object
        io = IO_HTTP(secrets["aio_username"], secrets["aio_key"], requests)


    else:
        print("Already connected to wifi")
    # Send data to the feed
    io = IO_HTTP(secrets["aio_username"], secrets["aio_key"], requests)

    try:
        feed = io.get_feed(feed_name)
    except AdafruitIO_RequestError:
        # If no feed exists, create one
        feed = io.create_new_feed(feed_name)
    
    print("Sending data to " + feed_name + " feed...".format(data))
    io.send_data(feed["key"], data)
    print("Sent")

    # Retrieve data value from the feed
    print("Retrieving data from " + feed_name + " feed")
    received_data = io.receive_data(feed["key"])
    print("Data from " + feed_name +  " feed: ", received_data["value"])


def hold_for_water():
    write_clear("Holding for water", 1)
    while not float_switch.value:  # checking main tank is full of (cold) water
        update()


def check_door() -> bool:
    if foot_switch.value == 1:
        led_door_sol.value=True
        return True
    else:
        led_door_sol.value=False
        return False


def door_checker():
    if foot_switch.value:
        door_sol.value = True
#        while not door_microswitch.value:   # waits for door to have opened to stop door solenoid
#            time.sleep(0.01)
        wait_update(0.200)
        door_sol.value = False


def disinfect(error_list: list) -> list:
    write_clear("Disinfecting", 1)
    for _ in range(50):  # 70 seconds IRL
        if temperature.value // 700 + 20 < 85:  # check chamber temp
            write_clear("ERROR: LOW TEMP", 1)
            error_list.append("Low temperature error")
            wait_update(1)
            write_clear("Heating steam", 1)
            file_errors.write(". Low temperature warning ")  # puts service warning in log
            time_low_temp = time.localtime()  # records time of error
            file_errors.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
               year=time_low_temp[0], month=time_low_temp[1], day=time_low_temp[2],
               HH=time_low_temp[3], MM=time_low_temp[4], SS=time_low_temp[5]))  # with time
            file_errors.flush()
            while temperature.value // 700 + 20 < 85:  # wait for chamber temp
                update()
            disinfect(error_list)  # recursively retry cycle
            break
        if temperature.value // 700 + 20 > 110:  # check chamber temp
            write_clear("ERROR: HIGH TEMP", 1)
            error_list.append("High temperature error")
            wait_update(1)
            file_errors.write(". High temperature warning given ")  # puts service warning in log
            time_high_temp = time.localtime()  # records time of error
            file_errors.write("{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}".format(
               year=time_high_temp[0], month=time_high_temp[1], day=time_high_temp[2],
               HH=time_high_temp[3], MM=time_high_temp[4], SS=time_high_temp[5]))  # with time
            file_errors.flush()
            write_clear("COOLING", 1)
            led_steam_gen.value=False
            while temperature.value // 700 + 20 > 90:  # let chamber cool until it is <90C
                update()
            led_steam_gen.value=False
            disinfect(error_list)
            break
        update()
    led_steam_gen.value=False
    return error_list


def do_super_wash():
    wait_update(1)
    led_door_sol.value=False
    hold_for_water()
    write_clear("Washing", 1)
    led_main_pump.value=True
    wait_update(4)  # 30 seconds IRL
    led_main_pump.value=False
    do_reg_wash()


def do_reg_wash():
    wait_update(1)
    led_door_sol.value=False
    hold_for_water()
    write_clear("Washing", 1)
    led_main_pump.value=True
    led_steam_gen.value=True
    led_dosing_pump.value=True
    wait_update(3)  # is this timing correct? Unsure IRL time
    led_dosing_pump.value=False
    for _ in range(8):  # Pulsing the pump
        led_main_pump.value=True
        wait_update(0.200)
        led_main_pump.value=False
        wait_update(0.200)
    write_clear("Heating steam", 1)
    while temperature.value // 700 + 20 < 85:  # checking chamber temp to see if it is disinfecting yet
        update()
    error_list = disinfect([])
    led_steam_gen.value=False
    hold_for_water()
    write_clear("Rinsing", 1)
    led_main_pump.value=True
    wait_update(2)  # 5-10 seconds IRL
    led_main_pump.value=False
    write_clear("Chamber cooling", 1)
    while temperature.value // 700 + 20 > 60:  # Waits for safe chamber temperature
        update()
    post_data('Errors for cycle '  + str(read_count() + 1) + ': ' + ' | '.join(map(str, error_list)), 'errors')
    write_clear("Door Unlocked", 1)


def main():
    print_cycle_count(read_count())
    door_closed = True  # Fake initial state of door so code may be run
    write_clear("Ready", 1)
    while True:
        if super_wash.value==1:
            if door_closed:
                led_door_sol.value=True
                write_clear("Superwash", 1)
                do_super_wash()
                while not check_door():
                    update()
                print_cycle_count(read_count())
                update_cycle_count(read_count() + 1)  # Updates the cycle count to the previous count + 1
                write_clear("Ready", 1)
            else:
                write_clear("DOOR NOT SHUT", 1)
                wait_update(1)
                write_clear("Ready", 1)
        elif reg_wash.value==1:
            if door_closed:
                led_door_sol.value=True
                write_clear("Regular Wash", 1)
                do_reg_wash()
                wait_update(1)
                while not check_door():
                    update()
                print_cycle_count(read_count())
                update_cycle_count(read_count() + 1)  # Updates the cycle count to the previous count + 1
                write_clear("Ready", 1)
            else:
                write_clear("DOOR NOT SHUT", 1)
                wait_update(1)
                write_clear("Ready", 1)
        update()


if __name__ == "__main__":
    main()

