import time
import config
import gpio_controller
import emotion_detector
from camera import Camera
from gpio_controller import bt

camera = Camera()
camera.start()
gpio_controller.set_camera(camera)

def main():
    intervale = 1/config.CAMERA_FRAMERATE
    while True:
        try:
            capture = camera.capture()
            emotion = emotion_detector.detect(capture)
            if emotion:
                gpio_controller.LED_color(emotion)
        except Exception as e:
            print(f"Erreur : {e}")

        time.sleep(intervale)

if __name__ == "__main__":
    main()