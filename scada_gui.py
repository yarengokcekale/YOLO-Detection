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
bip_sound_path = r"C:\Users\yaren\OneDrive\Masaüstü\drone_dataset\alert.wav\alert.wav.wav"

if os.path.exists(bip_sound_path):
    bip_sound = pygame.mixer.Sound(bip_sound_path)
else:
    print("Uyarı: Ses dosyası bulunamadı!")

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
    try:
        bip_sound.play()
    except Exception as e:
        print("Ses çalınamadı:", e)

def fire_action():
    status_label.config(text="Durum: ATEŞ EDİLDİ", fg="red")
    print("ATEŞ ET komutu gönderildi!")

fire_button = Button(window, text="ATEŞ ET", command=fire_action, font=("Arial", 14, "bold"), bg="red", fg="white")
fire_button.pack(pady=10)

# -------------------- GÖRÜNTÜ GÜNCELLEME --------------------
def update_frame():
    ret, frame = cap.read()
    if ret:
        results = model(frame, verbose=False)
        annotated_frame = results[0].plot()

        # Drone varsa ses ve durum
        names = results[0].names
        classes = results[0].boxes.cls.tolist()
        if any(names[int(cls)] == "drone" for cls in classes):
            status_label.config(text="Durum: DRONE TESPİT EDİLDİ", fg="green")
            threading.Thread(target=play_bip).start()
        else:
            status_label.config(text="Durum: Bekleniyor", fg="black")

        # Görüntü Tkinter'da göster
        img = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = ImageTk.PhotoImage(image=img)

        label.imgtk = img
        label.configure(image=img)

    label.after(30, update_frame)

update_frame()
window.mainloop()
cap.release()
cv2.destroyAllWindows()
