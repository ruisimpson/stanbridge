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
from adafruit_onewire.bus import OneWireBus
import adafruit_ds18x20

if __name__ == '__main__':
    # Ignore this if statement, just useful for easy importing of this file
    # Outputs (numbered from pico end down)

    # Onboard led
    led_main_pump = DigitalInOut(board.GP17)   # Relay 1
    led_main_pump.direction = Direction.OUTPUT

    # Red led
    led_steam_gen = DigitalInOut(board.GP21)   # Relay 2
    led_steam_gen.direction = Direction.OUTPUT

    # Green led
    led_door_sol = DigitalInOut(board.GP27)    # Relay 3
    led_door_sol.direction = Direction.OUTPUT

    # Blue led
    led_dosing_pump = DigitalInOut(board.GP22) # Relay 4
    led_dosing_pump.direction = Direction.OUTPUT

    # LCD- I2C interface
    lcd = hd44780.HD44780(busio.I2C(board.GP1, board.GP0), address=0x27)

    # Wireless module
    esp32_cs = DigitalInOut(board.GP7)
    esp32_ready = DigitalInOut(board.GP10)
    esp32_reset = DigitalInOut(board.GP11)

    spi = busio.SPI(board.GP18, board.GP19, board.GP16)
    esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs,
                                           esp32_ready, esp32_reset)

    # Inputs (numbered from pico end down)
    # Button 1
    super_wash = DigitalInOut(board.GP2)
    super_wash.direction = Direction.INPUT
    super_wash.pull = Pull.DOWN

    # Button 2
    reg_wash = DigitalInOut(board.GP3)
    reg_wash.direction = Direction.INPUT
    reg_wash.pull = Pull.DOWN

    # Terminal block 1
    float_switch = DigitalInOut(board.GP13)      
    float_switch.direction = Direction.INPUT
    float_switch.pull = Pull.UP

    # Terminal block 2
    foot_switch = DigitalInOut(board.GP26)       
    foot_switch.direction = Direction.INPUT
    foot_switch.pull = Pull.UP

    # Terminal block 3
    door_microswitch = DigitalInOut(board.GP14)  
    door_microswitch.direction = Direction.INPUT
    door_microswitch.pull = Pull.UP
    
    # Button reset
    # reset_switch
    btn = DigitalInOut(board.GP4)
    btn.direction = Direction.OUTPUT

    # ADC for pentiometer to simulate temperature
    ow_bus = OneWireBus(board.GP28)
    devices = ow_bus.scan()
    temperature = adafruit_ds18x20.DS18X20(ow_bus, devices[0])    
      
    # Water_sensor
    overflow = DigitalInOut(board.GP15)
    overflow.direction = Direction.INPUT


class Diagnostics:
    """Diagnostics runs and saves machine information."""
    service_cycle_count = 100

    def __init__(self, error_list=[]):
        self.error_list = error_list
        self.timeout = 300    # Timeout for steam generator
        self.overflow_timer = -300

    def __str__(self):  
        """The diagnostics can be printed for debugging."""
        return ('Errors for cycle ' + str(self.read_count() + 1) + ': '
                + ' | '.join(map(str, self.error_list)))


    def connect_to_wifi(self): 
        """Attempts to connect to Wifi, with 5 tries."""
        print('Attempting to connect to WiFi')
        if not esp.is_connected:
            for _ in range(5):  # 5 attempts
                print('Not connected to WiFi: Attempting to connect')
                try:
                    esp.connect_AP(secrets['ssid'], secrets['password'])
                except RuntimeError as i:
                    print('could not connect to WiFi: ', i)
                    continue
                if esp.is_connected:
                    print('Connected to WiFi')
                    socket.set_interface(esp)
                    requests.set_socket(socket, esp)
                    break
                else:
                    print("Could not connect to WiFi")
            io = IO_HTTP(secrets['aio_username'], secrets['aio_key'], requests)
        else:
            print('Already connected to wifi')


    def post_errors(self):
        """Posts errors from the error_list file to Errors."""
        self.write_errors()
        self.connect_to_wifi()
        if esp.is_connected:
            print('Posting errors')
            io = IO_HTTP(secrets['aio_username'], secrets['aio_key'], requests)
            try:
                feed = io.get_feed('errors')
            except AdafruitIO_RequestError:  # If no feed exists, create one
                feed = io.create_new_feed('errors')

            io.send_data(feed['key'],
                         'Cycle '
                         + str(self.read_count() + 1) + ': '
                         + ' | '.join(map(str, self.error_list)))
            # For checking the data we just transmitted
            # received_data = io.receive_data(feed['key'])  
            # print('Data from feed: ', received_data['value'])
        else:
            print("Could not post errors: No Wifi connection")
    
    
    def read_count(self) -> int:
        """Reads the cycle count from the cycle count file.

        Written to every cycle.
        """
        
        self.count_file = open('count.txt', 'r')
        
        # Reading and saving the cycle count from the file
        self.cycle_count = int(self.count_file.readline().split()[4])  
        self.count_file.close()
        return self.cycle_count


    def update_cycle_count(self):
        """increases cycle count by 1, which is saved in the count file"""
        file_errors = open('Errors.txt', 'w')
        file_count = open('count.txt', 'w')  # Creates file
        file_count.write('Number of cycles is: ' + str(self.cycle_count + 1))
        file_count.flush()
        if self.cycle_count == self.service_cycle_count:
            time_start = time.localtime()
            # Records time when first service warning is given
            file_errors.write('. Service warning given on ')
            file_errors.write(
    '{year:>04d}/{month:>02d}/{day:>02d} {HH:>02d}:{MM:>02d}:{SS:>02d}'.format(
    year=time_start[0], month=time_start[1], day=time_start[2],
    HH=time_start[3], MM=time_start[4], SS=time_start[5])
    )
            file_errors.flush()
        if self.cycle_count > self.service_cycle_count:
            # Writes/ records service warning
            self.error_list.append('Unit needs service')
            write_clear('Unit needs service', 1)
            wait_update(3)
        file_count.flush()


    def print_cycle_count(self):
        """Prints the cycle count to the 4th line on the LCD."""
        write_clear('Cycle count: ' + str(self.read_count()), 4)


    def write_errors(self):
        """Commits the errors for the current cycle to the file_errors file."""
        file_errors = open('Errors.txt', 'a')
        file_errors.write('\n' + '\n'.join(self.error_list))
        file_errors.close()

    
    def find_errors(self):
        """Reads and produces a set of all the lifetime errors."""
        file_errors = open('Errors.txt', 'r')
        
        # Finds the non duplicated set of all lifetime errors 
        print(set(file_errors.read().split('\n')[1:]))
        
        
def write_clear(message: str, linenumber: int):
    """Writing to the LCD by line.

    Also ensures the previous text is overwritten
    """
    lcd.write(message[:20] + ' ' * (20 - len(message)), linenumber)


def update():
    """Performs all background processes.

    Updates temperature, door status, reset status.
    """
    write_clear(f'Temperature: {round(temperature.temperature)}C', 2)

    # IRL 120, temperature limited by hardware as well, but additional safety
    if temperature.temperature > 110:
        led_steam_gen.value = False
    if not door_microswitch.value:
        write_clear('Door closed', 3)
    else:
        write_clear('Door open', 3)
    
    
def check_overflow():    
    if overflow.value:
       machine_1.error_list.append('Overflow sensor error')
       write_clear('Overflow detected', 1)
       if time.monotonic() - machine_1.overflow_timer > 300:
           machine_1.post_errors()
           machine_1.overflow_timer = time.monotonic()
           
    else:
        write_clear('Ready', 1)


def reset_all():
    if reset_switch.value:
        file_count=open("count.txt","w")
        file_count.close()
        file_errors=open("errors.txt","w")
        file_errors.close()
        time.sleep(0.5)       

      
def wait_update(time_s: float) -> float:
    """Continously updates background features while holding.
    
    Returns the actual elapsed time. (For validating the accuracy)
    Should accurately time within 200ms. Will always time for too long."""
    start_time = time.monotonic()
    while time.monotonic() < start_time + time_s:
        # Loops the update() until inputted time has elapsed
        update()
    return time.monotonic() - start_time  


def test_pump() -> list:
    """Tests the pump/ float switch are functioning.
    
    Checks if float switch is still active after
    the main pump has reduced the tank level. If float switch and main pump
    are both working this test will pass.
    Should only be tested once the pump has been activated for some time.
    """
    print("Testing the pump")
    if led_main_pump.value and not float_switch.value:
        write_clear('ERROR DETECTED', 1)
        for _ in range(5):
            if led_main_pump.value and not float_switch.value:
                wait_update(0.1)
                continue
            else:
                write_clear('Cycle continued', 1)
                machine_1.error_list.append(
                    'Inconclusive main pump/float switch error')
                return
        machine_1.error_list.append('Main pump/float switch error')
        machine_1.write_errors()
        turn_off_machine()
        raise Exception('PUMP/FLOAT SWITCH ERROR')


def turn_off_machine():
    """Turns off the machine, and writes to the display."""
    led_main_pump.value, led_steam_gen.value, led_dosing_pump.value = 0, 0, 0
    write_clear('CYCLE ABORTED', 3)
    write_clear('PLEASE RESTART', 4)
    
    
def hold_for_water():
    """Waits until the tank is full."""
    write_clear('Holding for water', 1)
    while float_switch.value:
        update()
        print(f'waiting, value = {float_switch.value}')


# def check_door() -> bool:
#     """Performs a check of the foot switch
# 
#     Might not be necessary to do it this way
#     """
#     if foot_switch.value:
#         led_door_sol.value = True
#         return True
#     else:
#         led_door_sol.value = False
#         return False


def door_checker():
    """Checks the door.

    Waits until the door microswitch has opened to stop the door solenoid.
    """
    if not foot_switch.value:
        led_door_sol.value = True
        print("door opening")
        while not door_microswitch.value:
            time.sleep(0.01)
        #wait_update(0.200)
        led_door_sol.value = False


def disinfect() -> list:
    """Disinfection.
    
    Ensures the bedpans are subjected to 85C+ for 70 seconds.
    """
    write_clear('Disinfecting', 1)
    time_start_disinfect = time.monotonic()
    led_steam_gen.value = False
    
    while time.monotonic() < time_start_disinfect + 70:  # 70 seconds IRL
        # Check chamber temperature isn't too low.
        if temperature.temperature < 80:
            write_clear('ERROR: LOW TEMP', 1)
            machine_1.error_list.append('Low temperature error')
            wait_update(1)
            write_clear('Heating steam', 1)
            
            # Wait for chamber temp
            while temperature.temperature < 85:
                update()
            disinfect()  # Recursively retry cycle.
            break
        
        # Check chamber temperature isn't too high.
        if temperature.temperature > 80:  
            led_steam_gen.value = False
            #write_clear('ERROR: HIGH TEMP', 1)
            #machine_1.error_list.append('High temperature error')
            #wait_update(1)
            #write_clear('COOLING', 1)
            # Let chamber cool until it is <90C
        update()
    led_steam_gen.value = False


def do_super_wash():
    print("superwash")
    wait_update(1)
    led_door_sol.value = False
    hold_for_water()
    write_clear('Washing', 1)
    led_main_pump.value = True
    wait_update(20)  # 30 seconds IRL
    led_main_pump.value = False
    do_reg_wash()



def do_reg_wash():
    print("Regular wash")
    wait_update(1)
    led_door_sol.value = False
    
    hold_for_water()
    
    write_clear('Washing', 1)
    led_main_pump.value = True
    led_steam_gen.value = True
    led_dosing_pump.value = True
    wait_update(10)  # 10 seconds IRL (I think)
    
    # Once water has depleted we can check the float switch 
    print("test pump ommitted")
    #test_pump()
    led_dosing_pump.value, led_main_pump.value = False, False
    
    hold_for_water()
    
    write_clear('Washing', 1)
    for _ in range(12):  # Pulsing the pump
        led_main_pump.value = not led_main_pump.value 
        wait_update(5)

    write_clear('Heating steam', 1)
    start_temperature = temperature.temperature
    time_start_temperature = time.monotonic()
    
    # Checking chamber temp to see if it is up to temperature yet
    while temperature.temperature < 80:
        update()
        if time.monotonic() > time_start_temperature + machine_1.timeout:
            # If machine hasn't reached temperature before the timeout
            # stop the machine and report error
            led_steam_gen.value = False                                    
            machine_1.error_list.append('Steam generator timeout')
            machine_1.write_errors()
            machine_1.post_errors()
            turn_off_machine()
            raise Exception('Machine steam generator timeout')
        
    disinfect()
    led_steam_gen.value = False
    
    write_clear('Chamber cooling', 1)
    wait_update(30)
    hold_for_water()
    
    write_clear('Rinsing', 1)
    led_main_pump.value = True
    wait_update(10)  # 5-10 seconds IRL
    led_main_pump.value = False
    
    write_clear('Chamber cooling', 1)
    # Waits for safe chamber temperature
    while temperature.temperature > 60:  
        update()
    machine_1.post_errors()
    machine_1.write_errors()
    print(machine_1)
    write_clear('Door Unlocked', 1)
    return True


def main():
    door_closed = True  # Fake initial state of door so code may be run
    write_clear('Ready', 1)
    while True:
        if super_wash.value:
            if door_closed:
                write_clear('Superwash', 1)
                do_super_wash()
                machine_1.update_cycle_count()
                machine_1.print_cycle_count()
                write_clear('Ready', 1)
            else:
                write_clear('DOOR NOT SHUT', 1)
                wait_update(1)
                write_clear('Ready', 1)
        elif reg_wash.value:
            if door_closed:
                write_clear('Regular Wash', 1)
                do_reg_wash()
                wait_update(1)
                machine_1.update_cycle_count()
                machine_1.print_cycle_count()
                write_clear('Ready', 1)
            else:
                write_clear('DOOR NOT SHUT', 1)
                wait_update(1)
                write_clear('Ready', 1)
        machine_1.print_cycle_count()
        update()
        door_checker()
        check_overflow()



if __name__ == '__main__':
    machine_1 = Diagnostics()
    main()

