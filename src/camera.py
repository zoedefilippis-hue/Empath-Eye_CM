from picamera2 import Picamera2 #pour piloter la caméra
import os #pour créer un fichier de sauvegarde
import datetime #pour horodater le fichier
from config import CAMERA_WIDTH, CAMERA_HEIGHT, SAVE_DIR

SD_ADRESS = SAVE_DIR

class Camera:
    def __init__(self):
        self.cam = None #camera nulle tant que start non appelée
        self.ready = False #True si la camera démarre

    def start(self):
        try:
            self.cam = Picamera2()
            config = self.cam.create_still_configuration(
                main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"}
            )
            self.cam.configure(config)
            self.cam.start()
            self.ready = True

        except Exception as e:
            self.ready = False
            raise

    def verify_sd(self):
        if not os.path.exists(SD_ADRESS):
            raise RuntimeError(f"Carte SD non trouvée")
        if not os.access(SD_ADRESS, os.W_OK):
            raise PermissionError(f"Impossible d'écrire sur la carte SD")
    
    def capture(self, filename=None):
        if not self.ready:
            raise RuntimeError("Caméra non-initialisée")
        self.verify_sd()

        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"

        os.makedirs(SD_ADRESS, exist_ok = True)
        filepath = os.path.join(SD_ADRESS, filename)

        self.cam.capture_file(filepath)
        
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise IOError (f"Fichier manquant ou vide {filepath}")
        
        return filepath
    def stop(self): ##Pas sure de garder cette fonction
        if self.cam and self.ready:
            self.cam.stop()
            self.cam.close()
            self.ready = False

    @property
    def is_ready(self):
        return self.ready