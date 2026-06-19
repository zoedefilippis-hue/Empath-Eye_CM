from picamera2 import Picamera2 #pour piloter la caméra
import os #pour créer un fichier de sauvegarde
import datetime #pour horodater le fichier
import json
import numpy as np
from collections import Counter
from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, IMAGE_DIR, SAVE_IMAGE_DIR, EMO_DIR

SD_ADRESS_IMAGE = IMAGE_DIR
SD_ADRESS_SAVE_IMAGE = SAVE_IMAGE_DIR

class Camera:
    def __init__(self):
        self.cam = None #camera nulle tant que start non appelée
        self.ready = False #True si la camera démarre

    def start(self):
        try:
            self.cam = Picamera2(CAMERA_INDEX)
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
        if not os.path.exists(SD_ADRESS_IMAGE) or not os.path.exists(SD_ADRESS_SAVE_IMAGE):
            raise RuntimeError(f"Carte SD non trouvée")
        if not os.access(SD_ADRESS_IMAGE, os.W_OK) or not os.access(SD_ADRESS_SAVE_IMAGE, os.W_OK):
            raise PermissionError(f"Impossible d'écrire sur la carte SD")
    
    def capture(self, filename=None):
        if not self.ready:
            raise RuntimeError("Caméra non-initialisée")
        
        self.verify_sd()

        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"

        os.makedirs(SD_ADRESS_IMAGE, exist_ok = True)
        filepath = os.path.join(SD_ADRESS_IMAGE, filename)

        self.cam.capture_file(filepath)
        
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise IOError (f"Fichier manquant ou vide {filepath}")
        
        return filepath

    def capture_burst(self, n=5, delay=0.0):
        """
        Capture n images in a row and return their filepaths.
        delay: optional pause (seconds) between captures, e.g. to let
        auto-exposure settle slightly between frames.
        """
        if not self.ready:
            raise RuntimeError("Caméra non-initialisée")

        self.verify_sd()
        os.makedirs(SD_ADRESS_IMAGE, exist_ok=True)

        filepaths = []
        for i in range(n):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"burst_{timestamp}_{i}.jpg"
            filepath = os.path.join(SD_ADRESS_IMAGE, filename)

            self.cam.capture_file(filepath)

            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                raise IOError(f"Fichier manquant ou vide {filepath}")

            filepaths.append(filepath)

            if delay > 0:
                time.sleep(delay)

        return filepaths
    
    def capture_save(self, filename=None):
        if not self.ready:
            raise RuntimeError("Caméra non-initialisée")
        
        self.verify_sd()

        if filename is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"

        os.makedirs(SD_ADRESS_SAVE_IMAGE, exist_ok = True)
        filepath = os.path.join(SD_ADRESS_SAVE_IMAGE, filename)

        self.cam.capture_file(filepath)
        
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            raise IOError (f"Fichier manquant ou vide {filepath}")
        
        return filepath

    @staticmethod
    def average_predictions(predictions, emotion_labels=None):
        """
        Combine multiple model outputs into one final emotion.

        predictions: list of either
            - probability arrays/lists (one per image, e.g. softmax output)
            - plain integer/string labels (one per image)

        emotion_labels: optional dict {index: name}, used to convert the
        final index into a readable label when predictions are probability
        arrays.

        Returns: (final_label_or_index, confidence)
        """
        if not predictions:
            raise ValueError("predictions list is empty")

        first = predictions[0]

        # Case 1: predictions are probability vectors -> average them
        if isinstance(first, (list, tuple, np.ndarray)):
            probs = np.array(predictions, dtype=float)   # shape (n, num_classes)
            mean_probs = probs.mean(axis=0)
            best_idx = int(np.argmax(mean_probs))
            confidence = float(mean_probs[best_idx])
            label = emotion_labels[best_idx] if emotion_labels else best_idx
            return label, confidence

        # Case 2: predictions are plain labels (majority vote)
        counts = Counter(predictions)
        label, count = counts.most_common(1)[0]
        confidence = count / len(predictions)
        return label, confidence
    
    def emotion(self, emotion):
        os.makedirs(EMO_DIR, exist_ok=True)
        filepath = os.path.join(EMO_DIR, "emotions.json")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
        else:
            data = []
        
        data.append({"emotion": emotion, "timestamp": timestamp, "saved?": False})
        
        with open(filepath, "w") as f:
            json.dump(data, f)
        
        return filepath
    
    def save_emotion(self, emotion):
        os.makedirs(EMO_DIR, exist_ok=True)
        filepath = os.path.join(EMO_DIR, "emotions.json")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
        else:
            data = []
        
        data.append({"emotion": emotion, "timestamp": timestamp, "saved?": True})
        
        with open(filepath, "w") as f:
            json.dump(data, f)
        
        return filepath
    
    def delete_image(self, filename=None):
        filepath = os.path.join(IMAGE_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    def delete_burst(self, filepaths):
        """Delete a list of captured burst images."""
        for filepath in filepaths:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def stop(self): ##Pas sure de garder cette fonction
        if self.cam and self.ready:
            self.cam.stop()
            self.cam.close()
            self.ready = False

    @property
    def is_ready(self):
        return self.ready
