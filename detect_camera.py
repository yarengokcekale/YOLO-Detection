import cv2
from ultralytics import YOLO

# Eğitilmiş modeli yükle
model = YOLO("runs/detect/train/weights/best.pt")

# Kamerayı başlat (0 → dahili kamera)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Model ile tahmin yap
    results = model(frame)

    # Sonuçları ekranda göster
    annotated_frame = results[0].plot()
    cv2.imshow("Drone Detection", annotated_frame)

    # 'q' tuşuna basıldığında çık
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
