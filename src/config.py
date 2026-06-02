import RPi.GPIO as GPIO
import os

#initialisation PIN
LED_EMOTION_PIN = 18

BUTTON_SAVE_PIN = 16
# Pas de bouton Power
#BUTTON_POWER_ON_PIN = 11
BUTTON_POWER_OFF_PIN = 13

BUTTON_BLUETOOTH_ON_PIN = 15
BUTTON_BLUETOOTH_OFF_PIN = 29


GPIO_MODE = "BCM"
def init_gpio():
    GPIO.setmode(GPIO.BCM)

PIN_MAP = {
    "LED_EMOTION"      : LED_EMOTION_PIN,
    "BTN_SAVE"         : BUTTON_SAVE_PIN,
    #"BTN_POWER_ON"     : BUTTON_POWER_ON_PIN,
    "BTN_POWER_OFF"    : BUTTON_POWER_OFF_PIN,
    "BTN_BT_ON"        : BUTTON_BLUETOOTH_ON_PIN,
    "BTN_BT_OFF"       : BUTTON_BLUETOOTH_OFF_PIN,
}

#caméra
CAMERA_INDEX = 0
IMAGE_DIR = "/media/pi/NOM_DE_TA_SD/captures" #A MODIFIER AVEC L'ADRESSE DE LA CARTE SD
SAVE_IMAGE_DIR = "/media/pi/NOM_DE_TA_SD/saved/captures" #A MODIFIER AVEC L'ADRESSE DE LA CARTE SD
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FRAMERATE = 9

#HAT
HAT_I2C_BUS = 1
HAT_I2C_ADDRESS = 0x3C

#LED 
LED_COUNT = 1          
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False

#communication IA
EMO_DIR = "/media/pi/NOM_DE_TA_SD/emo" #A MODIFIER AVEC L'ADRESSE DE LA CARTE SD
SAVE_EMO_DIR = "/media/pi/NOM_DE_TA_SD/saved/emo" #A MODIFIER AVEC L'ADRESSE DE LA CARTE SD
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_model(1).pth")

#bluetooth
BT_SHARE_DIR1 = EMO_DIR #endroit où le bluetooth va chercher des fichiers à transmettre
BT_SHARE_DIR2 = SAVE_EMO_DIR #endroit où le bluetooth va chercher des fichiers à transmettre