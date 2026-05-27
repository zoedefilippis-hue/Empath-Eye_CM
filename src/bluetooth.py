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
        self.ensure_bt_service() #vérifie que le service bluetooth tourne et que l'adapteur est disponible
        
        #capture_output=True permet de ne pas regarder la sortie de la commande
        subprocess.run(["bluetoothctl", "select", "hci0"], capture_output=True) #force l'utilisation de l'adapteur
        subprocess.run(["bluetoothctl", "power", "on"], capture_output=True) #allume le module bluetooth
        subprocess.run(["bluetoothctl", "discoverable", "on"], capture_output=True) #rend la carte visible lors d'un scan bluetooth par les autres appareils
        subprocess.run(["bluetoothctl", "pairable", "on"], capture_output=True) #autorise la carte à accepter de nouveaux appairages
        subprocess.run(["bluetoothctl", "agent", "NoInputNoOutput"], capture_output=True) #type d'appairage sans écran ni clavier
        subprocess.run(["bluetoothctl", "default-agent"], capture_output=True) #enregistre l'agent comme agent par défaut
        
        self.start_obex_server() #lance le serveur de fichiers OBEX
        self.stop_event.clear() #remets l'interrupteur partagé à False
        self.start_monitor() #lance le thread qui vérifie toutes les 3s que la connexion est maintenue 
        self.start_command_listener() #lance le thread qui verifie que le transfert est effectué correctement

    def disable(self):
        self.stop_event.set() #stop les threads
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5) #attend pdt 5s que le thread soit fini, puis l'arrête
        if self.cmd_thread:
            self.cmd_thread.join(timeout=5) #attend pdt 5s que le thread soit fini, puis l'arrête
        
        self.stop_obex_server() #envoie un terminate au processus OBEX
        subprocess.run(["bluetoothctl", "discoverable", "off"], capture_output=True) #rend la carte invisible lors d'un scan bluetooth par les autres appareils
        subprocess.run(["bluetoothctl", "pairable", "off"], capture_output=True) #retire l'autorisation de la carte à accepter de nouveaux appairages 
        subprocess.run(["bluetoothctl", "power", "off"], capture_output=True) #éteint le module bluetooth
        self.connected = False #remet la connexion à False

    
    
    def ensure_bt_service(self): #vérifie que le service bluetooth tourne et que l'adapteur est disponible
        result = subprocess.run(["systemectl1", "is-active", "bluetooth"],
                                capture_outpout = True, text = True)
        if result.stdout.strip() != "active": #service bluetooth inactif
            subprocess.run(["sudo", "systemectl1", "start", "bluetooth"], capture_output = True)

        result = subprocess.run(["hciconfig", "hci0"],
                                capture_outpout = True, text = True)
        if "hci0" not in result.stdout:
            raise RuntimeError("[Bluetooth] Adapteur hci0 introuvable - vérifier le module BT du CM5")
        if "DOWN" in result.stdout: #pour lever le hci0
            subprocess.run(["sudo", "hciconfig", "hci0", "up"], capture_output = True)

    
    
    def start_obex_serveur(self): #crèe une racine OBEX pour pouvoir pull les fichiers sur l'appareil
        os.makedirs(OBEX_ROOT, exist_ok = True)

        for share_dir in [BT_SHARE_DIR1, BT_SHARE_DIR2]:
            os.makedirs(share_dir, exist_ok = True)
            link_name = os.path.join(OBEX_ROOT, os.path.basename(share_dir))
            if not os.path.islink(link_name):
                os.symlink(share_dir, link_name)
        
        if self.server_process and self.server_process.poll() is None:
            return
        
        try:
            self.server_process = subprocess.Popen(
                ["obexpushd", "-B", "-n", "-o", OBEX_ROOT],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ) #serveur OBEX démarré
        except FileNotFoundError: #OBEX introuvable
            
    
    def stop_obex_server(self):
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            self.server_process.wait()
        self.server_process = None



