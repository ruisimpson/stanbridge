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

n = 0

if __name__ == '__main__':  # Ignore this if statement, just useful for easy importing of this file as a module
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
    led_dosing_pump = DigitalInOut(board.GP20)
    led_dosing_pump.direction = Direction.OUTPUT

    # LCD
    lcd = hd44780.HD44780(busio.I2C(board.GP1, board.GP0), address=0x27)  # (i2c, address, rows, columns) for lcd

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

    # button wifi
    door_microswitch = DigitalInOut(board.GP12)
    door_microswitch.direction = Direction.INPUT
    door_microswitch.pull = Pull.UP

    # adc for pentiometer to simulate temperature
    temperature = AnalogIn(board.GP26)


class Diagnostics:
    '''This class handles all of the WiFi and cycle count features of the machines'''
    service_cycle_count = 100

    def __init__(self, error_list=[]):
        self.error_list = error_list
        self.read_count()

    def __str__(self):  # The diagnostics can be printed for debugging
        return 'Errors for cycle ' + str(self.read_count() + 1) + ': ' + ' | '.join(map(str, self.error_list))

    def connect_to_wifi(self): # Attempts to connect to Wifi, with 5 tries
        print('Attempting to connect to WiFi')
        if not esp.is_connected:
            for _ in range(5):  # 5 attempts to connect to WiFi
                print('Not connected to WiFi: Attempting to connect')
                try:
                    esp.connect_AP(secrets['ssid'], secrets['password'])
                except RuntimeError as i:
                    print('could not connect to WiFi: ', i)
                    continue
                print('Connected to WiFi')
                socket.set_interface(esp)
                requests.set_socket(socket, esp)
                break
            io = IO_HTTP(secrets['aio_username'], secrets['aio_key'], requests)
        else:
            print('Already connected to wifi')

    def post_errors(self):  # Posts errors from the error_list file to the errors feed
        self.connect_to_wifi()
        print('Posting errors')
        io = IO_HTTP(secrets['aio_username'], secrets['aio_key'], requests)
        try:
            feed = io.get_feed('errors')
        except AdafruitIO_RequestError:  # If no feed exists, create one
            feed = io.create_new_feed('errors')

        io.send_data(feed['key'],
                     'Errors for cycle ' + str(self.read_count() + 1) + ': ' + ' | '.join(map(str, self.error_list)))
        received_data = io.receive_data(
            feed['key'])  # For checking the data we just transmitted. This may be something to be removed to save time
        print('Data from feed: ', received_data['value'])

    def read_count(self) -> int:  # Reads the cycle count from the cycle count file, which is written to every cycle
        self.count_file = open('count.txt', 'r')
        self.cycle_count = int(
            self.count_file.readline().split()[4])  # reading and saving the cycle count from the file
        self.count_file.close()
        return self.cycle_count

    def update_cycle_count(self):  # increases cycle count by 1, which is saved in the count file
        file_count = open('count.txt', 'w')  # creates file
        file_count.write('Number of cycles is: ' + str(self.cycle_count + 1))  # records n value
        file_count.flush()
        if self.cycle_count == self.service_cycle_count:
            time_start = time.localtime()  # records time when first service warning is given
            file_errors.open('Errors.txt', 'w')
            file_errors.write('. Service warning given on ')  # puts service warning in log
            file_errors.write('{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}'.format(
                year=time_start[0], month=time_start[1], day=time_start[2],
                HH=time_start[3], MM=time_start[4], SS=time_start[5]))  # with time
            file_errors.flush()
        if self.cycle_count > self.service_cycle_count:
            self.error_list.append('Unit needs service')
            write_clear('Unit needs service', 1)  # puts service warning on LCD after more than 1 press
            wait_update(3)
        file_count.flush()

    def print_cycle_count(self):  # Prints the cycle count to the 4th line on the LCD
        write_clear('Cycle count: ' + str(self.read_count()), 4)

    def write_errors(self):  # Commits the errors for the current cycle to the file_errors file
        file_errors = open('Errors.txt', 'w')
        file_errors.write(str(self.error_list))
        file_errors.close()


def write_clear(message: str, linenumber: int):  # Writing to the LCD by line,
    # and ensuring the previous text is overwritten
    lcd.write(message[:20] + ' ' * (20 - len(message)), linenumber)


def update():  # Writes the 'temperature' to the lcd. Takes 207.6 (+-0.1%) ms to update
    write_clear('Temperature: ' + str(temperature.value // 700 + 20) + 'C', 2)  # updating the temperature
    if temperature.value // 700 + 20 > 110:  # IRL 120, temperature limited by hardware as well, but additional safety
        led_steam_gen.value = False
    if door_microswitch.value:
        write_clear('Door closed', 3)
    else:
        write_clear('Door open', 3)


def wait_update(time_s: float) -> float:  # Should accurately time within 200ms. Will always time for too long
    start_time = time.monotonic()
    while time.monotonic() < start_time + time_s:  # Loops the update() until inputted time has elapsed
        update()
    return time.monotonic() - start_time  # Returns the actual elapsed time (For validating the accuracy)


def test_pump() -> list:  # Checks if float switch is still active after pump has reduced the tank level
    if led_main_pump.value and float_switch.value:  # Should only be tested after pump has been active for some time
        write_clear('ERROR DETECTED', 1)
        for _ in range(5):
            if led_main_pump.value and float_switch.value:
                wait_update(1)
                continue
            else:
                write_clear('Cycle continued', 1)
                machine_1.error_list.append('Inconclusive main pump/float switch error')
                return
        machine_1.error_list.append('Main pump/float switch error')
        machine_1.write_errors()
        turn_off_machine()
        raise Exception('PUMP/FLOAT SWITCH ERROR')


def turn_off_machine():
    led_main_pump.value, led_steam_gen.value, led_dosing_pump.value = 0, 0, 0
    write_clear('CYCLE ABORTED', 3)
    write_clear('PLEASE RESTART', 4)
    
def hold_for_water():  # Waits until the tank is full
    write_clear('Holding for water', 1)
    while not float_switch.value:  # checking main tank is full of (cold) water
        update()


def check_door() -> bool:  # Performs a check of the foot switch. Might not be necessary to do it this way
    if foot_switch.value == 1:
        led_door_sol.value = True
        return True
    else:
        led_door_sol.value = False
        return False


def door_checker():   # Checks the door, and waits until the door microswitch has opened to stop the door solenoid
    if foot_switch.value:
        door_sol.value = True
        #        while not door_microswitch.value:   # waits for door to have opened to stop door solenoid
        #            time.sleep(0.01)
        wait_update(0.200)
        door_sol.value = False


def disinfect() -> list:
    write_clear('Disinfecting', 1)
    for _ in range(50):  # 70 seconds IRL
        if temperature.value // 700 + 20 < 85:  # check chamber temp
            write_clear('ERROR: LOW TEMP', 1)
            machine_1.error_list.append('Low temperature error')
            wait_update(1)
            write_clear('Heating steam', 1)
            while temperature.value // 700 + 20 < 85:  # wait for chamber temp
                update()
            disinfect()  # recursively retry cycle
            break
        if temperature.value // 700 + 20 > 110:  # check chamber temp
            led_steam_gen.value = False
            write_clear('ERROR: HIGH TEMP', 1)
            machine_1.error_list.append('High temperature error')
            wait_update(1)
            write_clear('COOLING', 1)
            while temperature.value // 700 + 20 > 90:  # let chamber cool until it is <90C
                update()
            led_steam_gen.value = True
            disinfect()
            break
        update()
    led_steam_gen.value = False


def do_super_wash():
    wait_update(1)
    led_door_sol.value = False
    hold_for_water()
    write_clear('Washing', 1)
    led_main_pump.value = True
    wait_update(4)  # 30 seconds IRL
    led_main_pump.value = False
    do_reg_wash()


def do_reg_wash(error_list: list = []) -> bool:
    wait_update(1)
    led_door_sol.value = False
    hold_for_water()
    write_clear('Washing', 1)
    led_main_pump.value = True
    led_steam_gen.value = True
    led_dosing_pump.value = True
    wait_update(3)  # is this timing correct? Unsure IRL time
    test_pump()
    led_dosing_pump.value = False
    for _ in range(8):  # Pulsing the pump
        led_main_pump.value = True
        wait_update(0.200)
        led_main_pump.value = False
        wait_update(0.200)
    write_clear('Heating steam', 1)
    while temperature.value // 700 + 20 < 85:  # checking chamber temp to see if it is disinfecting yet
        update()
    disinfect()
    led_steam_gen.value = False
    hold_for_water()
    write_clear('Rinsing', 1)
    led_main_pump.value = True
    wait_update(2)  # 5-10 seconds IRL
    led_main_pump.value = False
    write_clear('Chamber cooling', 1)
    while temperature.value // 700 + 20 > 60:  # Waits for safe chamber temperature
        update()
    machine_1.post_errors()
    print(machine_1)
    write_clear('Door Unlocked', 1)
    return True


def main():
    door_closed = True  # Fake initial state of door so code may be run
    write_clear('Ready', 1)
    while True:
        if super_wash.value:
            if door_closed:
                led_door_sol.value = True
                write_clear('Superwash', 1)
                do_super_wash()
                while not check_door():
                    update()
                machine_1.update_cycle_count()
                machine_1.print_cycle_count()
                write_clear('Ready', 1)
            else:
                write_clear('DOOR NOT SHUT', 1)
                wait_update(1)
                write_clear('Ready', 1)
        elif reg_wash.value:
            if door_closed:
                led_door_sol.value = True
                write_clear('Regular Wash', 1)
                do_reg_wash()
                wait_update(1)
                while not check_door():
                    update()
                machine_1.update_cycle_count()
                machine_1.print_cycle_count()
                write_clear('Ready', 1)
            else:
                write_clear('DOOR NOT SHUT', 1)
                wait_update(1)
                write_clear('Ready', 1)
        machine_1.print_cycle_count()
        update()


if __name__ == '__main__':
    machine_1 = Diagnostics()
    machine_1.print_cycle_count()
    time.sleep(1)
    machine_1.update_cycle_count()
    machine_1.print_cycle_count()
    
    main()

