import sys
import os
import json
import time
import signal
import subprocess
import threading
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

from config import EMO_DIR, IMAGE_DIR, SAVE_IMAGE_DIR

CHUNK_SIZE = 490
CHUNK_DELAY = 0.05
WAIT = 2

SERVICE_UUID  = "948c621a-6017-443d-8f75-fd00cf7af340"
CHAR_TRANSFER = "fbd3e679-420f-4027-86ac-528d8251ae94"
CHAR_COMMAND  = "5ef1754d-6049-4a93-a80e-9f162316b6ae"

DIRS_TO_CLEAR = [EMO_DIR, IMAGE_DIR, SAVE_IMAGE_DIR]

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
            "LocalName":      dbus.String("EmpathEye"),
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
        if not self.notifying:
            return
        payload = json.dumps({"name": filename, "size": filesize})
        value = dbus.Array([dbus.Byte(b) for b in payload.encode()], signature="y")
        self.PropertiesChanged(GATT_CHAR_IFACE, {"Value": value}, [])

    def notify_chunk(self, chunk: bytes):
        if not self.notifying:
            return
        value = dbus.Array([dbus.Byte(b) for b in chunk], signature="y")
        self.PropertiesChanged(GATT_CHAR_IFACE, {"Value": value}, [])


class CharCommand(dbus.service.Object):
    PATH = "/org/bluez/empahteye/service0/char2"

    def __init__(self, bus, server):
        dbus.service.Object.__init__(self, bus, self.PATH)
        self.server = server

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return {
            "Service": dbus.ObjectPath("/org/bluez/empahteye/service0"),
            "UUID":    dbus.String(CHAR_COMMAND),
            "Flags":   dbus.Array(["write", "write-without-response"], signature="s"),
        }

    @dbus.service.method(GATT_CHAR_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        cmd = bytes(value).decode(errors="ignore").strip()
        print(f"[BLE] Commande reçue : {cmd}", flush=True)
        if cmd == "REQUEST_FILES":
            time.sleep(WAIT)
            threading.Thread(target=self.server.send_all_files, daemon=True).start()
        elif cmd == "TRANSFER_OK":
            self.server.clear_all_data()
        else:
            print(f"[BLE] Commande inconnue : {cmd}", flush=True)


class GattService(dbus.service.Object):
    PATH = "/org/bluez/empahteye/service0"

    def __init__(self, bus, server):
        dbus.service.Object.__init__(self, bus, self.PATH)
        self.char_transfer = CharTransfer(bus)
        self.char_command  = CharCommand(bus, server)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, iface):
        return {
            "UUID":    dbus.String(SERVICE_UUID),
            "Primary": dbus.Boolean(True),
        }


class Application(dbus.service.Object):
    """
    Objet racine enregistré auprès de BlueZ via RegisterApplication.
    BlueZ appelle GetManagedObjects ici pour découvrir services et caractéristiques.
    Doit être instancié dans le même thread que la GLib loop.
    """
    PATH = "/org/bluez/empahteye"

    def __init__(self, bus, server):
        dbus.service.Object.__init__(self, bus, self.PATH)
        # Les objets dbus sont créés ici, dans le thread de la loop
        self.service = GattService(bus, server)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        return {
            GattService.PATH:  {GATT_SERVICE_IFACE: self.service.GetAll(GATT_SERVICE_IFACE)},
            CharTransfer.PATH: {GATT_CHAR_IFACE:    self.service.char_transfer.GetAll(GATT_CHAR_IFACE)},
            CharCommand.PATH:  {GATT_CHAR_IFACE:    self.service.char_command.GetAll(GATT_CHAR_IFACE)},
        }


class BleServer:
    def __init__(self):
        self.bus          = None
        self.app          = None   # Application (racine dbus)
        self.adv          = None
        self.loop         = None
        self.adapter_path = None

    def find_adapter(self, bus):
        manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE, "/"), DBUS_OM_IFACE)
        for path, ifaces in manager.GetManagedObjects().items():
            if BLUEZ_ADAPTER_IFACE in ifaces:
                return path
        return None

    def start(self):
        """
        Appelé depuis on_loop_ready() — s'exécute donc dans le thread
        principal (celui de la GLib loop). Tous les objets dbus.service.Object
        sont créés ici pour que D-Bus puisse les retrouver.
        """
        self.bus = dbus.SystemBus()
        self.adapter_path = self.find_adapter(self.bus)
        print(f"[BLE] Adaptateur trouvé : {self.adapter_path}", flush=True)
        if not self.adapter_path:
            raise RuntimeError("[BLE] Adaptateur GATT introuvable sur dbus")

        # Nettoyage défensif (cycle précédent mal terminé)
        try:
            dbus.Interface(
                self.bus.get_object(BLUEZ_SERVICE, self.adapter_path), GATT_MANAGER_IFACE
            ).UnregisterApplication(Application.PATH)
            print("[BLE] Ancienne application GATT nettoyée", flush=True)
        except Exception:
            pass

        try:
            dbus.Interface(
                self.bus.get_object(BLUEZ_SERVICE, self.adapter_path), LE_ADV_MANAGER
            ).UnregisterAdvertisement(BLEAdvertisement.PATH)
            print("[BLE] Ancien advertisement nettoyé", flush=True)
        except Exception:
            pass

        # Instanciation dans le thread de la loop
        self.app = Application(self.bus, self)
        self.adv = BLEAdvertisement(self.bus)

        # --- Enregistrement GATT (asynchrone) ---
        # RegisterApplication est asynchrone OBLIGATOIREMENT : BlueZ rappelle
        # GetManagedObjects pendant l'appel. Si on bloque le thread principal
        # (qui est aussi la GLib loop) avec un appel synchrone, la loop ne peut
        # pas traiter ce callback entrant → deadlock → "No object received".
        gatt_manager = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE, self.adapter_path), GATT_MANAGER_IFACE
        )
        gatt_manager.RegisterApplication(
            Application.PATH,
            dbus.Dictionary({}, signature="sv"),
            reply_handler=lambda: print("[BLE] Service GATT enregistré", flush=True),
            error_handler=lambda e: print(f"[BLE] Erreur GATT : {e}", flush=True),
        )

        # --- Enregistrement advertisement (asynchrone) ---
        adv_manager = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE, self.adapter_path), LE_ADV_MANAGER
        )
        adv_manager.RegisterAdvertisement(
            BLEAdvertisement.PATH,
            dbus.Dictionary({}, signature="sv"),
            reply_handler=lambda: print("[BLE] Advertisement BLE enregistré", flush=True),
            error_handler=lambda e: print(f"[BLE] Erreur advertisement : {e}", flush=True),
        )

    def stop(self):
        print("[BLE-SUBPROCESS] stop() - début", flush=True)
        if self.bus and self.adv:
            try:
                dbus.Interface(
                    self.bus.get_object(BLUEZ_SERVICE, self.adapter_path), LE_ADV_MANAGER
                ).UnregisterAdvertisement(BLEAdvertisement.PATH)
                print("[BLE-SUBPROCESS] stop() - advertisement désenregistrée", flush=True)
            except Exception as e:
                print(f"[BLE] Erreur unregister adv : {e}", flush=True)

        if self.bus and self.app:
            try:
                dbus.Interface(
                    self.bus.get_object(BLUEZ_SERVICE, self.adapter_path), GATT_MANAGER_IFACE
                ).UnregisterApplication(Application.PATH)
                print("[BLE-SUBPROCESS] stop() - GATT désenregistré", flush=True)
            except Exception as e:
                print(f"[BLE] Erreur unregister GATT : {e}", flush=True)

        if self.loop:
            self.loop.quit()
        print("[BLE-SUBPROCESS] stop() - fin", flush=True)

    def send_all_files(self):
        if not self.app:
            return
        char = self.app.service.char_transfer
        for directory in EMO_DIR:
            if not os.path.exists(directory):
                continue
            for filename in sorted(os.listdir(directory)):
                if not filename.endswith(".json"):
                    continue
                filepath = os.path.join(directory, filename)
                filesize = os.path.getsize(filepath)
                char.notify_meta(filename, filesize)
                time.sleep(CHUNK_DELAY)
                print(f"[BLE] Envoi fichier : {filename} ({filesize} octets)", flush=True)
                with open(filepath, "rb") as f:
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        char.notify_chunk(chunk)
                        time.sleep(CHUNK_DELAY)
                print(f"[BLE] Fichier envoyé : {filename}", flush=True)
        char.notify_meta("__END__", 0)
        print("[BLE] Tous les fichiers envoyés", flush=True)

    def clear_all_data(self):
        total = 0
        for directory in DIRS_TO_CLEAR:
            if not os.path.exists(directory):
                continue
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                try:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        total += 1
                except Exception as e:
                    print(f"Impossible de supprimer {filepath} : {e}", flush=True)
        print(f"[BLE] Nettoyage terminé — {total} fichier(s) supprimé(s)", flush=True)


def main():
    # DBusGMainLoop dans le thread principal, avant toute connexion dbus
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    loop = GLib.MainLoop()
    server = BleServer()
    server.loop = loop

    def handle_signal():
        try:
            print("[BLE-SUBPROCESS] handle_signal() appelé !", flush=True)
            server.stop()
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stdout)
            sys.stdout.flush()
            os._exit(1)
        return False

    GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, handle_signal)
    GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, handle_signal)

    def on_loop_ready():
        """
        S'exécute dans le thread principal via idle_add, donc dans la GLib loop.
        server.start() crée tous les objets dbus.service.Object ici —
        même thread que la loop, ce qui est obligatoire pour que BlueZ
        puisse appeler GetManagedObjects sur ces objets.
        """
        print("[BLE-SUBPROCESS] Loop GLib démarrée, appel de server.start()", flush=True)
        try:
            server.start()
        except Exception as e:
            import traceback
            print(f"[BLE-SUBPROCESS] EXCEPTION dans server.start() : {e}", flush=True)
            traceback.print_exc(file=sys.stdout)
            sys.stdout.flush()
            loop.quit()
        return False  # ne pas répéter

    GLib.idle_add(on_loop_ready)

    # Loop dans le thread principal : traite D-Bus, signaux Unix et idle callbacks
    loop.run()

    print("[BLE] Processus BLE terminé", flush=True)


if __name__ == "__main__":
    main()
