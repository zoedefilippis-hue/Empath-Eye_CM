import time
import config
import gpio_controller
from camera import Camera
from gpio_controller import bt

camera = Camera()
camera.start()
gpio_controller.set_camera(camera)

def main():
    intervale = 1/config.CAMERA_FRAMERATE
    while True:
        try:
            camera.capture()
        except Exception as e:
            print(f"Erreur : {e}")

        time.sleep(intervale)

if __name__ == "__main__":
    main()