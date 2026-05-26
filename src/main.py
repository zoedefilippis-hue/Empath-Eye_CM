import time
import config
import gpio_controller
from camera import Camera

camera = Camera()
camera.start
gpio_controller.set_camera(camera)

def main():
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()

