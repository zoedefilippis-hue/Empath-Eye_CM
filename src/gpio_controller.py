import subprocess
import config
from gpiozero import Button
from rpi_ws281x import PixelStrip, Color #librairie qui contrôle la LED
from bluetooth import Bluetooth
from config import init_gpio

init_gpio()
shutdown_hooks = []

# BTN_CAM

btn_save = Button(config.PIN_MAP["BTN_SAVE"], pull_up=True)

_camera = None

def set_camera(cam):
    global _camera
    _camera = cam

def take_photo(channel = None):
    if _camera is None:
        print("Caméra non prête")
        return
    try:
        filepath = _camera.capture_save()
        print(f"Photo sauvegardée : {filepath}")
    except Exception as e :
        print(f"Erreur photo : {e}")

btn_save.when_pressed = take_photo

# BLUETOOTH

bt = Bluetooth()
btn_bt_on = Button(config.PIN_MAP["BTN_BT_ON"], pull_up=True)
btn_bt_off = Button(config.PIN_MAP["BTN_BT_OFF"], pull_up=True)

def bluetooth_ON(channel=None):
    bt.enable()

def bluetooth_OFF(channel=None):
    bt.disable()

btn_bt_on.when_pressed = bluetooth_ON
btn_bt_off.when_pressed = bluetooth_OFF

# OFF
btn_power_off = Button(config.PIN_MAP["BTN_POWER_OFF"], pull_up=True)

def add_shutdown_hook(fn):
    shutdown_hooks.append(fn)

def shutdown(channel=None):
    for hook in shutdown_hooks:
        try:
           hook()
        except Exception as e:
           continue
    bt.disable() #arrêt du bluetooth avant d'éteindre l'appareil
    subprocess.run(["sudo", "shutdown", "-h", "now"])

btn_power_off.when_pressed = shutdown

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