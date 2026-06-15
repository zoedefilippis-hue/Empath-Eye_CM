import torch
import torch.nn as nn
from torchvision import transforms, models
from torchvision.models import efficientnet_b2
from PIL import Image
import cv2
from config import MODEL_DIR

class EmotionEfficientNet(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        self.backbone = efficientnet_b2(weights=None)
        for module in self.backbone.modules():
            if hasattr(module, 'stochastic_depth'):
                module.stochastic_depth.p = 0.3
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(in_features, 256),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(256, num_classes)
        )
    def forward(self, x):
        return self.backbone(x)

class EmotionResNet(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        self.backbone = models.resnet18(weights=None) #couches neuronales qui reprend resnet
        self.backbone.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )
    def forward(self, x):
        return self.backbone(x)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = EmotionEfficientNet(num_classes=5).to(device)
#model = EmotionResNet(num_classes=5).to(device)
model.load_state_dict(torch.load(MODEL_DIR, map_location=device))
model.eval()

emotion_labels = {0: "Happy", 1: "Surprise", 2: "Sad", 3: "Anger", 4: "Neutral"}

transform = transforms.Compose([
    transforms.Resize((260, 260)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def detect(frame):
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    if len(faces) == 0:
        return None

    (x, y, w, h) = faces[0]
    margin = int(0.2 * w)
    x1 = max(0, x - margin)
    y1 = max(0, y - margin)
    x2 = min(frame.shape[1], x + w + margin)
    y2 = min(frame.shape[0], y + h + margin)

    face_img = frame[y1:y2, x1:x2]
    pil_img  = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
    tensor   = transform(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(tensor)  # ← ici le modèle analyse l'image
        probs  = torch.softmax(output, dim=1)[0]
        pred   = torch.argmax(probs).item()

    return emotion_labels[pred]