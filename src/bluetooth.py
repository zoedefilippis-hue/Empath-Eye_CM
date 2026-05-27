import subprocess #permet d'exécuter des commandes systèmes depuis Python
import threading #permet de faire tourner des tâches en parallèle
import socket #fournit l'interface réseau (permet de vérifier le bon échange entre les appareils connectés en bluetooth)
import os #gère les dossiers
from config import BT_SHARE_DIR1, BT_SHARE_DIR2, IMAGE_DIR, SAVE_IMAGE_DIR

VERIF_INTERVAL = 3 #délai entre chaque vérification de connexion

OBEX_ROOT = "/tmp/bt_share" #racine OBEX

DIRS_TO_CLEAR = [BT_SHARE_DIR1, BT_SHARE_DIR2, IMAGE_DIR, SAVE_IMAGE_DIR]

class Bluetooth:
    def __init__(self):
        self.connected = False #connecté ?
        self.server_process = None #processus obex
        self.monitor_thread = None #processus thread
        self.cmd_thread = None #processus thread 2
        self.stop_event = threading.Event() #interrupteur de thread

    def enable(self):
        self.ensure_bt_service()
        subprocess.run(["bluetoothctl", "select", "hci0"], capture_output=True)
        subprocess.run(["bluetoothctl", "power", "on"], capture_output=True)
        subprocess.run(["bluetoothctl", "discoverable", "on"], capture_output=True)
        subprocess.run(["bluetoothctl", "pairable", "on"], capture_output=True)
        subprocess.run(["bluetoothctl", "agent", "NoInputNoOutput"], capture_output=True)
        subprocess.run(["bluetoothctl", "default-agent"], capture_output=True)
        self._start_obex_server()
        self._stop_event.clear()
        self._start_monitor()
        self._start_command_listener()

    def disable(self):
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.cmd_thread:
            self.cmd_thread.join(timeout=5)
        self.stop_obex_server()
        subprocess.run(["bluetoothctl", "discoverable", "off"], capture_output=True)
        subprocess.run(["bluetoothctl", "pairable", "off"], capture_output=True)
        subprocess.run(["bluetoothctl", "power", "off"], capture_output=True)
        self.connected = False
