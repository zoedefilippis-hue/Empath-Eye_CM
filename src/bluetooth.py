import subprocess #permet d'exécuter des commandes systèmes depuis Python
import threading #permet de faire tourner des tâches en parallèle
import os #gère les dossiers
import json
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from config import BT_SHARE_DIR1, BT_SHARE_DIR2, IMAGE_DIR, SAVE_IMAGE_DIR

CHUNK_SIZE = 490
VERIF_INTERVAL = 3 #délai entre chaque vérification de connexion

SERVICE_UUID = "948c621a-6017-443d-8f75-fd00cf7af340" #UUID de service qui assure la connexion
CHAR_TRANSFER = "fbd3e679-420f-4027-86ac-528d8251ae94" #UUID qui transmet les données
CHAR_COMMAND = "5ef1754d-6049-4a93-a80e-9f162316b6ae" #UUID d'état

DIRS_TO_CLEAR = [BT_SHARE_DIR1, BT_SHARE_DIR2, IMAGE_DIR, SAVE_IMAGE_DIR]

BLUEZ_SERVICE       = "org.bluez"
BLUEZ_ADAPTER_IFACE = "org.bluez.Adapter1"
GATT_MANAGER_IFACE  = "org.bluez.GattManager1"
GATT_SERVICE_IFACE  = "org.bluez.GattService1"
GATT_CHAR_IFACE     = "org.bluez.GattCharacteristic1"
LE_ADV_MANAGER      = "org.bluez.LEAdvertisingManager1"
LE_ADV_IFACE        = "org.bluez.LEAdvertisement1"
DBUS_PROP_IFACE     = "org.freedesktop.DBus.Properties"
DBUS_OM_IFACE       = "org.freedesktop.DBus.ObjectManager"


class BLEAdvertisement(dbus.service.Object):
    PATH = "/org/bluez/empahteye/advertisement0"

    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, self.PATH)
 
    @dbus.service.method(DBUS_PROP_IFACE, in_signature="ss", out_signature="v")
    def Get(self, iface, prop):
        props = self.get_props()
        if prop not in props:
            raise dbus.exceptions.DBusException("org.freedesktop.DBus.Error.InvalidArgs")
        return props[prop]
 
    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return self.get_props()
 
    def get_props(self):
        return {
            "Type":           dbus.String("peripheral"),
            "ServiceUUIDs":   dbus.Array([SERVICE_UUID], signature="s"),
            "LocalName":      dbus.String("Empath'Eye"),
            "IncludeTxPower": dbus.Boolean(True),
        }

    @dbus.service.method(LE_ADV_IFACE)
    def Release(self):
        pass


class CharTransfer(dbus.service.Object):
    PATH = "/org/bluez/empahteye/service0/char0"
 
    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, self.PATH)
        self.notifying = False
 
    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return {
            "Service":   dbus.ObjectPath("/org/bluez/empahteye/service0"),
            "UUID":      dbus.String(CHAR_TRANSFER),
            "Flags":     dbus.Array(["notify"], signature="s"),
            "Notifying": dbus.Boolean(self.notifying),
        }
 
    @dbus.service.method(GATT_CHAR_IFACE)
    def StartNotify(self):
        self.notifying = True
 
    @dbus.service.method(GATT_CHAR_IFACE)
    def StopNotify(self):
        self.notifying = False
 
    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, iface, changed, invalidated):
        pass
 
    def notify_meta(self, filename, filesize):
        """
        Envoie les métadonnées d'un fichier avant ses chunks.
        Format JSON : {"name": "fichier.json", "size": 1234}
        Marqueur de fin : {"name": "__END__", "size": 0}
        Marqueur batterie : {"name": "__BATTERY__", "size": 0}
        """
        if not self.notifying:
            return
        payload = json.dumps({"name": filename, "size": filesize})
        value   = dbus.Array([dbus.Byte(b) for b in payload.encode()], signature="y")
        self.PropertiesChanged(GATT_CHAR_IFACE, {"Value": value}, [])
 
    def notify_chunk(self, chunk: bytes):
        """Envoie un chunk brut de fichier."""
        if not self.notifying:
            return
        value = dbus.Array([dbus.Byte(b) for b in chunk], signature="y")
        self.PropertiesChanged(GATT_CHAR_IFACE, {"Value": value}, [])


class CharCommand(dbus.service.Object):
    PATH = "/org/bluez/empahteye/service0/char2"
 
    def __init__(self, bus, bluetooth_instance):
        dbus.service.Object.__init__(self, bus, self.PATH)
        self.bt = bluetooth_instance  # référence vers Bluetooth pour appeler ses méthodes
 
    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return {
            "Service": dbus.ObjectPath("/org/bluez/empahteye/service0"),
            "UUID":    dbus.String(CHAR_COMMAND),
            "Flags":   dbus.Array(["write", "write-without-response"], signature="s"),
        }
 
    @dbus.service.method(GATT_CHAR_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        """Reçoit une commande de l'app et la traite."""
        cmd = bytes(value).decode(errors="ignore").strip()
        print(f"[BLE] Commande reçue : {cmd}")
 
        if cmd == "REQUEST_FILES":
            # Lance le transfert dans un thread pour ne pas bloquer la boucle DBUS
            threading.Thread(target=self.bt.send_all_files, daemon=True).start()
 
        elif cmd == "TRANSFER_OK":
            self.bt.clear_all_data()
 
        elif cmd == "GET_BATTERY":
            threading.Thread(target=self.bt.send_battery, daemon=True).start()
 
        else:
            print(f"[BLE] Commande inconnue : {cmd}")

class GattService(dbus.service.Object):
    PATH = "/org/bluez/empahteye/service0"
 
    def __init__(self, bus, bluetooth_instance):
        dbus.service.Object.__init__(self, bus, self.PATH)
        self.char_transfer = CharTransfer(bus)                      # Pi → App
        self.char_command  = CharCommand(bus, bluetooth_instance)   # App → Pi
 
    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return {
            "UUID":    dbus.String(SERVICE_UUID),
            "Primary": dbus.Boolean(True),
        }
 
    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        return {
            self.PATH:          {GATT_SERVICE_IFACE: self.GetAll(GATT_SERVICE_IFACE)},
            CharTransfer.PATH:  {GATT_CHAR_IFACE: self.char_transfer.GetAll(GATT_CHAR_IFACE)},
            CharCommand.PATH:   {GATT_CHAR_IFACE: self.char_command.GetAll(GATT_CHAR_IFACE)},
        }

    
class Bluetooth:
    def __init__(self, power = None):
        self.connected = False #connecté ?
        self.power = power
        self.monitor_thread = None #processus thread
        self.stop_event = threading.Event() #interrupteur de thread
        self.glib_loop     = None
        self.glib_thread   = None
        self.service       = None
        self.adv           = None



    def enable(self):
        self.ensure_bt_service() #vérifie que le service bluetooth tourne et que l'adapteur est disponible
        
        #capture_output=True permet de ne pas regarder la sortie de la commande
        subprocess.run(["bluetoothctl", "select", "hci0"], capture_output=True) #force l'utilisation de l'adapteur
        subprocess.run(["bluetoothctl", "power", "on"], capture_output=True) #allume le module bluetooth
        subprocess.run(["bluetoothctl", "discoverable", "on"], capture_output=True) #rend la carte visible lors d'un scan bluetooth par les autres appareils
        subprocess.run(["bluetoothctl", "pairable", "on"], capture_output=True) #autorise la carte à accepter de nouveaux appairages
        subprocess.run(["bluetoothctl", "agent", "NoInputNoOutput"], capture_output=True) #type d'appairage sans écran ni clavier
        subprocess.run(["bluetoothctl", "default-agent"], capture_output=True) #enregistre l'agent comme agent par défaut
        
        self.stop_event.clear() #remets l'interrupteur partagé à False
        self.start_monitor() #lance le thread qui vérifie toutes les 3s que la connexion est maintenue 
        self.start_gatt_server() #lance le thread qui verifie que le transfert est effectué correctement


    def disable(self):
        self.stop_event.set() #stop les threads
        
        if self.glib_loop:
            self.glib_loop.quit()
        if self.glib_thread:
            self.glib_thread.join(timeout=5)
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        
        #subprocess: exécute des commandes Linux
        subprocess.run(["bluetoothctl", "discoverable", "off"], capture_output=True) #rend la carte invisible lors d'un scan bluetooth par les autres appareils
        subprocess.run(["bluetoothctl", "pairable", "off"], capture_output=True) #retire l'autorisation de la carte à accepter de nouveaux appairages 
        subprocess.run(["bluetoothctl", "power", "off"], capture_output=True) #éteint le module bluetooth
        self.connected = False #remet la connexion à False

    
    
    def ensure_bt_service(self): #vérifie que le service bluetooth tourne et que l'adapteur est disponible
        #subprocess: exécute des commandes Linux
        result = subprocess.run(["systemctl", "is-active", "bluetooth"],
                                capture_output = True, text = True) #vérifie si le service Bluetooth est actif
        if result.stdout.strip() != "active": #service bluetooth inactif
            subprocess.run(["sudo", "systemctl", "start", "bluetooth"], capture_output = True) #active le service  bluetooth

        result = subprocess.run(["hciconfig", "hci0"],
                                capture_output = True, text = True) #vérifie que le controleur hci0 existe
        if "hci0" not in result.stdout:
            raise RuntimeError("[Bluetooth] Adapteur hci0 introuvable - vérifier le module BT du CM5")
        if "DOWN" in result.stdout: #controleur hci0 désactivé
            subprocess.run(["sudo", "hciconfig", "hci0", "up"], capture_output = True) #active le controleur

    def start_gatt_server(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
 
        # Récupère le chemin de l'adaptateur hci0
        adapter_path = self.find_adapter(bus)
        if not adapter_path:
            raise RuntimeError("[BLE] Adaptateur GATT introuvable sur dbus")
 
        # Crée le service GATT et l'advertisement
        self.service = GattService(bus, self)
        self.adv     = BLEAdvertisement(bus)
 
        # Enregistre le service GATT auprès de BlueZ
        gatt_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE, adapter_path), GATT_MANAGER_IFACE
        )
        gatt_manager.RegisterApplication(
            "/org/bluez/empahteye/service0",
            {},
            reply_handler=lambda: print("[BLE] Service GATT enregistré"),
            error_handler=lambda e: print(f"[BLE] Erreur GATT : {e}")
        )
 
        # Enregistre l'advertisement BLE
        adv_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE, adapter_path), LE_ADV_MANAGER
        )
        adv_manager.RegisterAdvertisement(
            BLEAdvertisement.PATH,
            {},
            reply_handler=lambda: print("[BLE] Advertisement BLE enregistré"),
            error_handler=lambda e: print(f"[BLE] Erreur advertisement : {e}")
        )
 
        # Lance la boucle GLib dans un thread dédié
        self.glib_loop   = GLib.MainLoop()
        self.glib_thread = threading.Thread(
            target=self.glib_loop.run, daemon=True
        )
        self.glib_thread.start()

    def find_adapter(self, bus):
        """Retourne le chemin dbus de l'adaptateur hci0."""
        manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE, "/"), DBUS_OM_IFACE
        )
        for path, ifaces in manager.GetManagedObjects().items():
            if BLUEZ_ADAPTER_IFACE in ifaces:
                return path
        return None


    def send_all_files(self):
        """
        Appelé quand l'app envoie REQUEST_FILES.
        Pour chaque fichier JSON : envoie d'abord les métadonnées (notify_meta)
        puis le contenu par chunks (notify_chunk), le tout sur CHAR_TRANSFER.
        """
        if not self.service:
            return
 
        char = self.service.char_transfer
 
        dirs = [BT_SHARE_DIR1, BT_SHARE_DIR2]
        for directory in dirs:
            if not os.path.exists(directory):
                continue
            for filename in sorted(os.listdir(directory)):
                if not filename.endswith(".json"):
                    continue
                filepath = os.path.join(directory, filename)
                filesize = os.path.getsize(filepath)
 
                # 1. Métadonnées
                char.notify_meta(filename, filesize)
                print(f"[BLE] Envoi fichier : {filename} ({filesize} octets)")
 
                # 2. Chunks
                with open(filepath, "rb") as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        char.notify_chunk(chunk)
 
                print(f"[BLE] Fichier envoyé : {filename}")
 
        # Marqueur de fin — l'app sait que tous les fichiers ont été envoyés
        char.notify_meta("__END__", 0)
        print("[BLE] Tous les fichiers envoyés")


    def send_battery(self):
        """Répond à GET_BATTERY via CHAR_TRANSFER : d'abord le marqueur, puis le payload."""
        if not self.service:
            return
        if self.power is None:
            payload = "BATTERIE NON RECONNUE"
        else:
            level    = self.power.get_battery_level()
            charging = self.power.is_charging()
            if level is not None:
                status  = "EN COURS DE CHARGEMENT" if charging else "EN COURS D'UTILISATION"
                payload = f"BATTERY:{level}:{status}"
            else:
                payload = "BATTERIE NON RECONNUE"
 
        char = self.service.char_transfer
        char.notify_meta("__BATTERY__", len(payload.encode()))
        char.notify_chunk(payload.encode())




    def clear_all_data(self): #supression des fichiers si l'envoi des émotions est réussi
        total = 0
        for directory in DIRS_TO_CLEAR:
            if not os.path.exists(directory):
                continue
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                try:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f"Impossible de supprimer {filepath} : {e}")
        print(f"[BLE] Nettoyage terminé — {total} fichier(s) supprimé(s)")


    

    def any_device_connected(self): #vérifie si un appareil est connecté
        try:
            result = subprocess.run(
                ["bluetoothctl",  "devices", "Connected"], capture_output = True, text = True, timeout = 3
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    

    def start_monitor(self):
        self.monitor_thread = threading.Thread(
            target = self.monitor_loop, daemon = True
        )
        self.monitor_thread.start()

    
    def monitor_loop(self): #vérifie la connexion toutes les 3s
        while not self.stop_event.is_set():
            now_connected =self.any_device_connected()

            if now_connected and not self.connected:
                self.connected = True
                print("[BT] Appareil connecté")

            elif not now_connected and self.connected:
                self.connected = False
                print("[BT] Appareil déconnecté")
            
            self.stop_event.wait(VERIF_INTERVAL)