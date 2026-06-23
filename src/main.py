import time
import config
import gpio_controller
import emotion_detector
import cv2
import threading
from camera import Camera
from gpio_controller import bt
from gpio_controller import add_shutdown_hook, LED_startup
from config import init_gpio

init_gpio()

camera = Camera()
camera.start()
gpio_controller.set_camera(camera)

add_shutdown_hook(camera.stop)

threading.Thread(target=gpio_controller.LED_startup, daemon=True).start()

def main():
    intervale = 1/config.CAMERA_FRAMERATE
    while True:
        try:
            filepath = camera.capture()
            frame = cv2.imread(filepath)
            emotion = emotion_detector.detect(frame)
            print(f"Émotion détectée : {emotion}")
            if emotion and emotion != "neutre":
                gpio_controller.LED_color(emotion)
                camera.emotion(emotion)
            camera.delete_image(filepath)
        except Exception as e:
            print(f"Erreur : {e}")

        time.sleep(intervale)

if __name__ == "__main__":
    main()