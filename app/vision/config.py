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
    "weapon": 0.60,   # Tumne bola 0.6
    "smoke":  0.60,   # 0.6 - smoke ke liye bhi same
    "bag":    0.40,   # Bag ke liye thoda low (recall 0.393 hai model ki)
    "scan":   0.65,   # Scanner ke liye thoda high (false positive dangerous)
}

# ══════════════════════════════════════════
#  TRIGGER LOGIC SETTINGS
# ══════════════════════════════════════════

# Weapon: Turant trigger - ek frame mein mili = alert
WEAPON_INSTANT_TRIGGER = True

# Smoke: 3 consecutive frames mein dike tab trigger
SMOKE_CONSECUTIVE_FRAMES = 3

# Bag: Kitne seconds tak stationary rahe tab trigger
BAG_STATIC_SECONDS = 2

# Scanner: Device connected hai ya nahi
SCANNER_CONNECTED = False     # True karo jab scanner attach karo

# ══════════════════════════════════════════
#  ALERT / TOKEN SAVING SETTINGS
# ══════════════════════════════════════════

# Ek hi type ka alert kitne seconds baad dobara bheja jaye
ALERT_COOLDOWN_SECONDS = {
    "weapon": 60,    # 1 minute
    "smoke":  45,    # 45 seconds
    "bag":    120,   # 2 minutes
    "scan":   60,    # 1 minute
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
