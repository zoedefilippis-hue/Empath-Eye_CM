import time
from config import LOOP_INTERVAL_SEC
from gpio_controller import set_led, blink_led, set_fan_speed, is_button_pressed


def main():
    print("Démarrage du projet CM5…")

    try:
        while True:
            # Bouton utilisateur
            if is_button_pressed():
                print("Bouton pressé")

            # Ventilateur : vitesse selon niveau batterie
            set_fan_speed(1.0)

            time.sleep(LOOP_INTERVAL_SEC)

    except KeyboardInterrupt:
        print("Arrêt propre.")
        set_led(False)
        set_fan_speed(0)

if __name__ == "__main__":
    main()