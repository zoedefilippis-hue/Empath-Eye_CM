import subprocess
import config
import board
import neopixel
import camera
import emotion_detector
import cv2
import threading
from gpiozero import Button
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
    print("Bouton 18 appuyé !")
    if _camera is None:
        print("Caméra non prête")
        return
    try:
        filepath = _camera.capture_save()
        frame = cv2.imread(filepath)
        emotion = emotion_detector.detect(frame)
        if emotion:
            LED_color(emotion)
            _camera.save_emotion(emotion)
        print(f"Photo sauvegardée : {filepath}")
    except Exception as e :
        print(f"Erreur photo : {e}")

btn_save.when_pressed = take_photo

# BLUETOOTH

bt = Bluetooth()
btn_bt_on = Button(config.PIN_MAP["BTN_BT_ON"], pull_up=True, bounce_time=0.2)
btn_bt_off = Button(config.PIN_MAP["BTN_BT_OFF"], pull_up=True, bounce_time=0.2)

print(f"[DEBUG] État initial BT_ON (17) : {'fermé' if btn_bt_on.is_pressed else 'ouvert'}")
print(f"[DEBUG] État initial BT_OFF (27) : {'fermé' if btn_bt_off.is_pressed else 'ouvert'}")


def bluetooth_ON(channel=None):
    print("[BTN] Bouton ON appuyé")
    bt.enable()

def bluetooth_OFF(channel=None):
    print("[BTN] Bouton OFF appuyé")
    bt.disable()

btn_bt_on.when_pressed = bluetooth_ON
btn_bt_off.when_pressed = bluetooth_OFF

# OFF
btn_power_off = Button(config.PIN_MAP["BTN_POWER_OFF"], pull_up=True, bounce_time=0.05)

def add_shutdown_hook(fn):
    shutdown_hooks.append(fn)

def shutdown(channel=None):
    LED_OFF()
    for hook in shutdown_hooks:
        try:
           hook()
        except Exception as e:
           continue
    bt.disable() #arrêt du bluetooth avant d'éteindre l'appareil
    subprocess.run(["sudo", "shutdown", "-h", "now"])

btn_power_off.when_pressed = shutdown

# LED

pixel = neopixel.NeoPixel(board.D18, config.LED_COUNT, brightness=config.LED_BRIGHTNESS/255)
led_timer = None
led_lock = threading.Lock()

def set_color(r,g,b):
    pixel[0] = (r, g, b)

def LED_OFF():
    set_color(0,0,0)

def LED_color(emotion):
    global led_timer
    couleurs = {
        "joie":(110, 180, 0),
        "colere":(0, 255, 0),
        "surprise":(0, 150, 180),
        "tristesse":(0, 0, 255),
    }
    couleur=couleurs.get(emotion)
    if couleur is None:
        return

    print(f"[LED] Couleur pour émotion : {emotion} → {couleur}")

    with led_lock:
        if led_timer is not None:
            led_timer.cancel()

        set_color(*couleur)

        led_timer = threading.Timer(1.0, LED_OFF)
        led_timer.daemon = True
        led_timer.start()