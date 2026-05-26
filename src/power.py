import smbus2 #bibliothèque pour communiquer en I2C
import RPi.GPIO as GPIO #gestion des broches, permet de connaitre l'état de la batterie
from config import HAT_I2C_ADDRESS, HAT_I2C_BUS

REG_STATUS = 0xB0

class Power:
    def __init__(self):
        self.bus = None
        self.ready = False

    def init(self):
        try:
            self.bus = smbus2.SMBus(HAT_I2C_BUS)
            self.ready = True

        except Exception as e:
            self.ready = False
            raise
    
    def read_status(self):
        if not self.ready:
            return None
        try:
            raw = self.bus.read_byte_data(HAT_I2C_ADDRESS, REG_STATUS)
            return raw
        except Exception as e:
            return None
        
    def get_battery_level(self):
        raw = self.read_raw_status()
        if raw is None:
            return None
        level = raw & 0x7F #vérifier la valeur du masque en mettant la batterie à 100% puis à 0% et voir la valeur retournée
        level = max(0, min(100, level))
        return level
    
    def is_charging(self):
        raw = self.read_raw_status()
        if raw is None:
            return False
        charging = bool(raw & 0x80) #vérifier la valeur du masque en branchant et débranchant la batterie et voir la valeur retournée
        return charging
    
    def stop(self):
        if self.bus:
            self.bus.close()
            self.ready = False