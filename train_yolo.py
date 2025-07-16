from ultralytics import YOLO

# Hazır YOLOv8n modeli ile transfer öğrenme
model = YOLO("yolov8n.pt")

# Eğitimi başlat
model.train(
    data="C:/Users/yaren/OneDrive/Masaüstü/drone_dataset/data.yaml",
    epochs=50,
    imgsz=640,
    batch=8
)
