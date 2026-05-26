import subprocess
import config
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color #librairie qui contrôle la LED

GPIO.setmode(GPIO.BCM)
GPIO.setup(config.PIN_MAP["BTN_BT_ON"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.PIN_MAP["BTN_BT_OFF"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.PIN_MAP["BTN_POWER_OFF"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

strip = PixelStrip(config.LED_COUNT, config.LED_EMOTION_PIN, config.LED_FREQ_HZ, config.LED_DMA, config.LED_INVERT, config.LED_BRIGHTNESS)
strip.begin()

def bluetooth_ON(channel=None):
    subprocess.run(["bluetoothctl", "power", "on"])

def bluetooth_OFF(channel=None):
    subprocess.run(["bluetoothctl", "power", "off"])

def shutdown(channel=None):
    subprocess.run(["sudo", "shutdown", "-h", "now"])

def set_color(r,g,b):
    strip.setPixelColor(0, Color(r,g,b))
    strip.show()

def LED_color(emotion):
    if emotion == "Happy":
        set_color(0, 255, 255)
    elif emotion == "Anger":
        set_color(0, 0, 255)
    elif emotion == "Surprise":
        set_color(128, 0, 128)
    elif emotion == "Sad":
        set_color(255, 0, 0)
    elif emotion == "Neutral":
        set_color(180, 180, 180)


GPIO.add_event_detect(config.PIN_MAP["BTN_BT_ON"], GPIO.FALLING, callback=bluetooth_ON)
GPIO.add_event_detect(config.PIN_MAP["BTN_BT_OFF"], GPIO.FALLING, callback=bluetooth_OFF)
GPIO.add_event_detect(config.PIN_MAP["BTN_POWER_OFF"], GPIO.FALLING, callback=shutdown)

