import time
import board
import busio
from digitalio import DigitalInOut, Direction, Pull


from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager

print("ESP32 SPI webclient test")

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

esp32_cs = DigitalInOut(board.GP7)
esp32_ready = DigitalInOut(board.GP10)
esp32_reset = DigitalInOut(board.GP11)

led=DigitalInOut(board.GP25)
led.direction = Direction.OUTPUT

spi = busio.SPI(board.GP18, board.GP19, board.GP16)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)


wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets)

counter = 0
btn = DigitalInOut(board.GP12)
btn.direction = Direction.INPUT
btn.pull = Pull.UP


while True:
    if not btn.value==1:
        print("BTN is down")
        led.value=True
        try:
            print("Posting data...", end="")
            data = counter
            feed = "test"
            payload = {"value": data}
            response = wifi.post(
                "https://io.adafruit.com/api/v2/"
                + secrets["aio_username"]
                + "/feeds/"
                + feed
                + "/data",
                json=payload,
                headers={"X-AIO-KEY": secrets["aio_key"]},
            )
            print(response.json())
            response.close()
            counter = counter + 1
            print("OK")
        except (ValueError, RuntimeError) as e:
            print("Failed to get data, retrying\n", e)
            wifi.reset()
            continue
        response = None
        
        led.value=False


    
    