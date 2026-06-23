import os


#initialisation PIN
LED_EMOTION_PIN = 18

BUTTON_SAVE_PIN = 24
BUTTON_POWER_OFF_PIN = 22

BUTTON_BLUETOOTH_ON_PIN = 17
BUTTON_BLUETOOTH_OFF_PIN = 27


GPIO_MODE = "BCM"
def init_gpio():
    pass

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
IMAGE_DIR = "/home/empatheye1/empatheye/image/loop" #A MODIFIER AVEC L'ADRESSE DE LA CARTE SD
SAVE_IMAGE_DIR = "/home/empatheye1/empatheye/image/saved" #A MODIFIER AVEC L'ADRESSE DE LA CARTE SD
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FRAMERATE = 1

#LED 
LED_COUNT = 1          
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False

#communication IA
EMO_DIR = "/home/empatheye1/empatheye/emo" #A MODIFIER AVEC L'ADRESSE DE LA CARTE SD
#MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_model_2.pth")
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_model.pth")
#MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best_model_3.pth")