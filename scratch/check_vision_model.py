import torch
from ultralytics import YOLO
from app.vision import config

def check_model():
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Device: {torch.cuda.get_device_name(0)}")
    
    print("\n--- Smoke Model ---")
    try:
        model = YOLO(config.MODELS["smoke"])
        print(f"Model path: {config.MODELS['smoke']}")
        print(f"Classes: {model.names}")
        print(f"Threshold: {config.CONFIDENCE['smoke']}")
    except Exception as e:
        print(f"Error loading smoke model: {e}")

    print("\n--- Video Source ---")
    import cv2
    cap = cv2.VideoCapture(config.VIDEO_SOURCE)
    if cap.isOpened():
        print(f"Video source {config.VIDEO_SOURCE} opened successfully")
        ret, frame = cap.read()
        if ret:
            print(f"Frame shape: {frame.shape}")
        cap.release()
    else:
        print(f"Failed to open video source {config.VIDEO_SOURCE}")

if __name__ == "__main__":
    check_model()
