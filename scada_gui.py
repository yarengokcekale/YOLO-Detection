import tkinter as tk
from tkinter import Label, Button
import cv2
from PIL import Image, ImageTk
from ultralytics import YOLO
import pygame
import threading
import os

# -------------------- MODEL YOLU --------------------
model_path = r"C:\Users\yaren\OneDrive\Masaüstü\drone_dataset\runs\detect\train\weights\best.pt"
model = YOLO(model_path)

# -------------------- SES AYARI --------------------
pygame.init()
pygame.mixer.init()
# Doğru ses dosyası yolu güncellendi
bip_sound_path = r"C:\Users\yaren\OneDrive\Masaüstü\drone_dataset\alert.wav"

# bip_sound'u başlangıçta None olarak tanımla
bip_sound = None

if os.path.exists(bip_sound_path):
    try:
        bip_sound = pygame.mixer.Sound(bip_sound_path)
        print(f"Ses dosyası başarıyla yüklendi: {bip_sound_path}")
    except pygame.error as e:
        print(f"Uyarı: Ses dosyası yüklenirken hata oluştu: {e}")
        print(f"Lütfen '{bip_sound_path}' yolundaki dosyanın geçerli bir WAV dosyası olduğundan emin olun.")
else:
    print(f"Uyarı: Ses dosyası bulunamadı! Beklenen yol: {bip_sound_path}")
    print("Drone tespit edildiğinde ses çalınmayacaktır.")

# -------------------- KAMERA --------------------
cap = cv2.VideoCapture(0)

# -------------------- TKINTER ARAYÜZÜ --------------------
window = tk.Tk()
window.title("Drone Tespit SCADA Arayüzü")
window.geometry("900x700")
window.configure(bg="#f0f0f0")

label = Label(window)
label.pack()

status_label = Label(window, text="Durum: Bekleniyor", font=("Arial", 14), bg="#f0f0f0")
status_label.pack(pady=10)

def play_bip():
    # bip_sound'un yüklenip yüklenmediğini kontrol et
    if bip_sound:
        try:
            bip_sound.play()
        except Exception as e:
            print(f"Ses çalınamadı: {e}")
    else:
        # Ses dosyası yüklenmediyse uyarı ver
        pass # Zaten başlangıçta uyarı verildiği için burada tekrar yazdırmaya gerek yok

def fire_action():
    status_label.config(text="Durum: ATEŞ EDİLDİ", fg="red")
    print("ATEŞ ET komutu gönderildi!")

fire_button = Button(window, text="ATEŞ ET", command=fire_action, font=("Arial", 14, "bold"), bg="red", fg="white")
fire_button.pack(pady=10)

# -------------------- GÖRÜNTÜ GÜNCELLEME --------------------
def update_frame():
    ret, frame = cap.read()
    if ret:
        # Görüntüyü döndür (kameraya göre değişebilir, gerekirse kaldırın)
        # frame = cv2.flip(frame, 1)

        results = model(frame, verbose=False)
        annotated_frame = results[0].plot()

        # Drone varsa ses ve durum
        names = results[0].names
        classes = results[0].boxes.cls.tolist()
        
        drone_detected = False
        for cls in classes:
            if int(cls) < len(names) and names[int(cls)] == "drone":
                drone_detected = True
                break

        if drone_detected:
            status_label.config(text="Durum: DRONE TESPİT EDİLDİ", fg="green")
            # Sesi ayrı bir iş parçacığında çal
            threading.Thread(target=play_bip).start()
        else:
            status_label.config(text="Durum: Bekleniyor", fg="black")

        # Görüntüyü Tkinter'da göster
        img = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = ImageTk.PhotoImage(image=img)

        label.imgtk = img
        label.configure(image=img)

    # Her 30 milisaniyede bir tekrar güncelle
    label.after(30, update_frame)

# -------------------- UYGULAMAYI BAŞLAT --------------------
update_frame()
window.mainloop()

# -------------------- TEMİZLİK --------------------
cap.release()
cv2.destroyAllWindows()
pygame.mixer.quit() # Pygame mikserini kapat
pygame.quit() # Pygame'i kapat
