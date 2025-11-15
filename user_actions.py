import json
import os
from datetime import datetime

LOG_FILE = 'data/sample_alerts.json'
os.makedirs('data', exist_ok=True)

def log_action(filename, label, transcription=None, scam_label=None, scam_comment=None, file_hash=None):
    """
    Logs a file prediction result with timestamp and transcription into a JSON file.
    
    Args:
        filename (str): Name of the audio file
        label (str): Prediction label ('Real' or 'Fake')
        transcription (str, optional): Transcribed text from the audio
    """
    entry = {
        'filename': filename,
        'prediction': label,
        'transcription': transcription,
        'scam_label': scam_label,
        'scam_comment': scam_comment,
        'file_hash': file_hash,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Load existing logs safely
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
    else:
        logs = []

    # Add new log entry
    logs.append(entry)

    # Save updated logs
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=4)
