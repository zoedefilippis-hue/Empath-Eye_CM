import time
import config
import gpio_controller
import emotion_detector
import cv2
from camera import Camera
from power import Power
from gpio_controller import bt
from config import init_gpio

init_gpio()

camera = Camera()
camera.start()
gpio_controller.set_camera(camera)

power = Power()
power.init()
bt.power = power

def main():
    intervale = 1/config.CAMERA_FRAMERATE
    while True:
        try:
            filepath = camera.capture()
            frame = cv2.imread(filepath)
            emotion = emotion_detector.detect(frame)
            if emotion:
                gpio_controller.LED_color(emotion)
        except Exception as e:
            print(f"Erreur : {e}")

        time.sleep(intervale)

if __name__ == "__main__":
    main()