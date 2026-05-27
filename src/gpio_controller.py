import subprocess
import config
import RPi.GPIO as GPIO
from rpi_ws281x import PixelStrip, Color #librairie qui contrôle la LED
from bluetooth import Bluetooth

GPIO.setmode(GPIO.BCM)


# BTN_CAM

GPIO.setup(config.PIN_MAP["BTN_SAVE"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

_camera = None

def set_camera(cam):
    global _camera
    _camera = cam

def take_photo(channel = None):
    try:
        filepath = _camera.capture_save()
        print(f"Photo sauvegardée : {filepath}")
    except Exception as e :
        print(f"Erreur photo : {e}")

GPIO.add_event_detect(config.PIN_MAP["BTN_SAVE"], GPIO.FALLING, callback=take_photo, bouncetime=200)


# BLUETOOTH

bt = Bluetooth()
GPIO.setup(config.PIN_MAP["BTN_BT_ON"], GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(config.PIN_MAP["BTN_BT_OFF"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

def bluetooth_ON(channel=None):
    bt.enable()

def bluetooth_OFF(channel=None):
    bt.disable()

GPIO.add_event_detect(config.PIN_MAP["BTN_BT_ON"], GPIO.FALLING, callback=bluetooth_ON, bouncetime=300)
GPIO.add_event_detect(config.PIN_MAP["BTN_BT_OFF"], GPIO.FALLING, callback=bluetooth_OFF, bouncetime=300)

# OFF

GPIO.setup(config.PIN_MAP["BTN_POWER_OFF"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

def shutdown(channel=None):
    bt.disable() #arrêt du bluetooth avant d'éteindre l'appareil
    subprocess.run(["sudo", "shutdown", "-h", "now"])

GPIO.add_event_detect(config.PIN_MAP["BTN_POWER_OFF"], GPIO.FALLING, callback=shutdown)


# LED

strip = PixelStrip(config.LED_COUNT, config.LED_EMOTION_PIN, config.LED_FREQ_HZ, config.LED_DMA, config.LED_INVERT, config.LED_BRIGHTNESS)
strip.begin()

def set_color(r,g,b):
    strip.setPixelColor(0, Color(r,g,b))
    strip.show()

def LED_color(emotion):
    if emotion == "Happy":
        set_color(255, 255, 0)
    elif emotion == "Anger":
        set_color(255, 0, 0)
    elif emotion == "Surprise":
        set_color(128, 0, 128)
    elif emotion == "Sad":
        set_color(0, 0, 255)
    elif emotion == "Neutral":
        set_color(180, 180, 180)




