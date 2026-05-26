import subprocess
import config
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color #librairie qui contrôle la LED

GPIO.setmode(GPIO.BCM)
GPIO.setup(config.PIN_MAP["BTN_BT_ON"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.PIN_MAP["BTN_BT_OFF"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.PIN_MAP["BTN_POWER_OFF"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

strip = PixelStrip(config.LED_count, config.LED_EMOTION_PIN, config.LED_FREQ_HZ, config.LED_DMA, config.LED_INVERT, config.LED_BRIGHTNESS)
strip.begin()

def bluetooth_ON(channel=None):
    subprocess.run(["bluetoothctl", "power", "on"])

def bluetooth_OFF(channel=None):
    subprocess.run(["bluetoothctl", "power", "off"])

def shutdown(channel=None):
    subprocess.run(["sudo", "shutdown", "-h", "now"])

def LED_color():


GPIO.add_event_detect(config.PIN_MAP["BTN_BT_ON"], GPIO.FALLING, callback=bluetooth_ON)
GPIO.add_event_detect(config.PIN_MAP["BTN_BT_OFF"], GPIO.FALLING, callback=bluetooth_OFF)
GPIO.add_event_detect(config.PIN_MAP["BTN_POWER_OFF"], GPIO.FALLING, callback=shutdown)

