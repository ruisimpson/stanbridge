
import board
import busio
from digitalio import DigitalInOut
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests as requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

from adafruit_io import adafruit_io


try:
    from secrets import secrets
except ImportError:
    print("WiFi information is kept in secrets.py, add them there!")
    raise

esp32_cs = DigitalInOut(board.GP7)
esp32_ready = DigitalInOut(board.GP10)
esp32_reset = DigitalInOut(board.GP11)

spi = busio.SPI(board.GP18, board.GP19, board.GP16)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

print("Connecting to WIFI")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except RuntimeError as i:
        print("could not connect to WIFI. Trying again: ", i)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

socket.set_interface(esp)
requests.set_socket(socket, esp)

aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

def post_data(data, feed_name):
    """posts data to feed on adafruit IO"""  
    try:
        
        feed = io.get_feed(feed_name)
    except AdafruitIO_RequestError:
        # If no 'temperature' feed exists, create one
        feed = io.create_new_feed(feed_name)

    # Send data to the feed
    
    print("Sending data to " + feed_name + " feed...".format(data))
    io.send_data(feed["key"], data)
    print("Sent")

    # Retrieve data value from the feed
    print("Retrieving data from " + feed_name + " feed")
    received_data = io.receive_data(feed["key"])
    print("Data from " + feed_name +  " feed: ", received_data["value"])

    
    
post_data('yellow','temperature')

post_data('cat goes meow','temperature')

