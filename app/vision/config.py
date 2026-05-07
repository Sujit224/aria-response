# config.py - Saari settings ek jagah
# Sirf is file ko change karo, baaki sab automatically update hoga

# ══════════════════════════════════════════
#  MODEL PATHS
# ══════════════════════════════════════════
MODELS = {
    "weapon": "models/guns.pt",           # Danger-Place-detection (gun, knife, blood)
    "smoke":  "models/smoke.pt",          # Smoke-Fire-detection (fire, smoke)
    "bag":    "models/bag_model.pt",      # Abandoned bag detection
    "scan":   "models/scaner.pt",         # Scanner/X-ray model (dormant by default)
}

# ══════════════════════════════════════════
#  DETECTION CLASSES (Notebook se liya)
# ══════════════════════════════════════════

# Weapon model - Roboflow "danger-place-detection" dataset
# Jo bhi classes tumhare data.yaml mein hain
WEAPON_TRIGGER_CLASSES = [
    "gun", "pistol", "rifle", "knife",
    "blood", "weapon", "handgun", "bomb"
]

# Smoke model - "smoke-fire-detection-yolo" dataset
# Notebook mein clearly dikh raha hai: nc:2, names: ["fire", "smoke"]
SMOKE_TRIGGER_CLASSES = [
    "fire", "smoke"
]

# Bag model - abandoned bag
BAG_TRIGGER_CLASSES = [
    "bag", "backpack", "luggage", "suitcase", "handbag"
]

# Scanner model - weapons in X-ray
SCAN_TRIGGER_CLASSES = [
    "gun", "knife", "explosive", "weapon"
]

# ══════════════════════════════════════════
#  CONFIDENCE THRESHOLDS
# ══════════════════════════════════════════
CONFIDENCE = {
    "weapon": 0.85,   # Higher threshold for fewer false positives
    "smoke":  0.75,   # Same as weapon - only confident detections
    "bag":    0.70,   # Balanced for bag recall vs precision
    "scan":   0.65,   # Scanner ke liye thoda high (false positive dangerous)
}

# ══════════════════════════════════════════
#  TRIGGER LOGIC SETTINGS
# ══════════════════════════════════════════

# Weapon: Turant trigger - ek frame mein mili = alert
WEAPON_INSTANT_TRIGGER = True

# Smoke: 3 consecutive frames mein dike tab trigger
SMOKE_CONSECUTIVE_FRAMES = 2

# Bag: Kitne seconds tak stationary rahe tab trigger
BAG_STATIC_SECONDS = 30

# Bag: Minimum YOLO confidence required to emit an alert
# (YOLO runs at 0.40 for recall, but alerts need stronger detections)
BAG_MIN_ALERT_CONFIDENCE = 0.50

# Scanner: Device connected hai ya nahi
SCANNER_CONNECTED = True     # True karo jab scanner attach karo

# ══════════════════════════════════════════
#  ALERT / TOKEN SAVING SETTINGS
# ══════════════════════════════════════════

# Ek hi type ka alert kitne seconds baad dobara bheja jaye
ALERT_COOLDOWN_SECONDS = {
    "weapon": 10,    # 1 minute
    "smoke":  10,    # 45 seconds
    "bag":    30,   # 2 minutes
    "scan":   30,    # 1 minute
}

# ══════════════════════════════════════════
#  INPUT / OUTPUT
# ══════════════════════════════════════════
VIDEO_SOURCE  = 0         # 0 = webcam, ya "video.mp4" path
SHOW_WINDOW   = True      # Debug window dikhani hai?
FRAME_WIDTH   = 1280
FRAME_HEIGHT  = 720

# Scanner image input folder (jab SCANNER_CONNECTED = True)
SCANNER_INPUT_FOLDER = "scanner_input/"

# ══════════════════════════════════════════
#  LLM SETTINGS
# ══════════════════════════════════════════
LLM_PROVIDER    = "groq"    # "groq" ya "openai"
LLM_MAX_TOKENS  = 200       # Short response - token saving
LLM_TEMPERATURE = 0.3

# ══════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════
LOG_FILE        = "logs/threat_log.txt"   # Sab alerts yahan save honge
ENABLE_LOGGING  = True
