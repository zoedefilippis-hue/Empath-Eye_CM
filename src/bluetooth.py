import subprocess  # permet d'exécuter des commandes systèmes depuis Python
import threading   # permet de faire tourner des tâches en parallèle
import os
import sys
import signal
import time

VERIF_INTERVAL = 3  # délai entre chaque vérification de connexion

BLE_SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ble_server.py")


class Bluetooth:
    def __init__(self, power=None):
        self.connected = False
        self.power = power
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.ble_process = None  # sous-processus qui fait tourner ble_server.py

    def enable(self):
        if self.ble_process is not None and self.ble_process.poll() is None:
            # Le sous-processus tourne déjà
            print("[BLE] Déjà actif, on ignore", flush=True)
            return

        self.ensure_bt_service()

        subprocess.run(["bluetoothctl", "select", "hci0"], capture_output=True)
        subprocess.run(["bluetoothctl", "power", "on"], capture_output=True)
        subprocess.run(["sudo", "btmgmt", "advertising", "on"], capture_output=True)
        time.sleep(0.3)
        subprocess.run(["bluetoothctl", "discoverable", "on"], capture_output=True)
        subprocess.run(["bluetoothctl", "pairable", "on"], capture_output=True)
        subprocess.run(["bluetoothctl", "agent", "NoInputNoOutput"], capture_output=True)
        subprocess.run(["bluetoothctl", "default-agent"], capture_output=True)

        self.stop_event.clear()
        self.start_monitor()

        print("[BLE] Démarrage du serveur GATT (processus séparé)", flush=True)
        self.ble_process = subprocess.Popen(
            [sys.executable, "-u", BLE_SERVER_SCRIPT],  # -u = sortie non bufferisée
            cwd=os.path.dirname(BLE_SERVER_SCRIPT),
            stdout=None,  # hérite explicitement du stdout du parent
            stderr=None,  # hérite explicitement du stderr du parent
        )
        print(f"[BLE] Processus BLE lancé (pid={self.ble_process.pid})", flush=True)

    def disable(self):
        print("[BLE] disable() appelé", flush=True)

        self.stop_event.set()

        if self.ble_process is not None:
            pid = self.ble_process.pid
            print(f"[BLE] Arrêt du processus BLE (pid={pid})", flush=True)
            print(f"[BLE] poll() avant signal : {self.ble_process.poll()}", flush=True)
            try:
                self.ble_process.send_signal(signal.SIGTERM)
                print(f"[BLE] SIGTERM envoyé avec succès à pid={pid}", flush=True)
            except Exception as e:
                print(f"[BLE] ERREUR lors de l'envoi du signal : {e}", flush=True)
            try:
                self.ble_process.wait(timeout=5)
                print(f"[BLE] Processus {pid} terminé proprement, code={self.ble_process.returncode}", flush=True)
            except subprocess.TimeoutExpired:
                print(f"[BLE] poll() après timeout : {self.ble_process.poll()}", flush=True)
                print("[BLE] Le processus ne répond pas, kill forcé", flush=True)
                self.ble_process.kill()
                self.ble_process.wait(timeout=5)
            self.ble_process = None
        else:
            print("[BLE] Aucun processus BLE actif", flush=True)

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.monitor_thread = None

        subprocess.run(["bluetoothctl", "discoverable", "off"], capture_output=True)
        subprocess.run(["bluetoothctl", "pairable", "off"], capture_output=True)
        subprocess.run(["bluetoothctl", "power", "off"], capture_output=True)
        self.connected = False

    def ensure_bt_service(self):
        result = subprocess.run(["systemctl", "is-active", "bluetooth"],
                                 capture_output=True, text=True)
        if result.stdout.strip() != "active":
            subprocess.run(["sudo", "systemctl", "start", "bluetooth"], capture_output=True)

        result = subprocess.run(["hciconfig", "hci0"],
                                 capture_output=True, text=True)
        if "hci0" not in result.stdout:
            raise RuntimeError("[Bluetooth] Adapteur hci0 introuvable - vérifier le module BT du CM5")
        if "DOWN" in result.stdout:
            subprocess.run(["sudo", "hciconfig", "hci0", "up"], capture_output=True)

    def any_device_connected(self):
        try:
            result = subprocess.run(
                ["bluetoothctl", "devices", "Connected"], capture_output=True, text=True, timeout=3
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def start_monitor(self):
        self.monitor_thread = threading.Thread(
            target=self.monitor_loop, daemon=True
        )
        self.monitor_thread.start()

    def monitor_loop(self):
        while not self.stop_event.is_set():
            now_connected = self.any_device_connected()

            if now_connected and not self.connected:
                self.connected = True
                print("[BT] Appareil connecté", flush=True)

            elif not now_connected and self.connected:
                self.connected = False
                print("[BT] Appareil déconnecté", flush=True)

            self.stop_event.wait(VERIF_INTERVAL)