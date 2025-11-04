import os
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

import librosa
import numpy as np
import joblib

from user_actions import log_action  # your helper to append to data/sample_alerts.json

# Import the Blockchain class
from blockchain import Blockchain

# —— Flask App Configuration —————————————————————————
app = Flask(__name__)

# Hardcoded secret key (for development)
app.secret_key = 'a_hardcoded_very_secret_key_1234567890'

# Upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# —— Load Your Trained Model —————————————————————————— 
MODEL_PATH = 'model/voice_detector.pkl'
model = joblib.load(MODEL_PATH)

# —— Initialize Blockchain ———————————————————————————
blockchain = Blockchain()  # Create a new blockchain instance

# —— Helper Functions ——————————————————————————————
def allowed_file(filename):
    """Only allow .wav uploads."""
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

def extract_features(file_path):
    """
    Load a WAV, compute 12 MFCCs + 3 spectral features.
    Returns shape (1,15) to match the trained model.
    """
    y, sr = librosa.load(file_path, sr=22050, duration=10)
    
    # Extract MFCCs (12 features)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfcc.T, axis=0)[:12]
    
    # Extract spectral features (3 features)
    spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
    spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))
    zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(y))
    
    # Combine all features (12 + 3 = 15)
    features = np.concatenate([
        mfcc_mean,
        [spectral_centroid / 1000],  # Normalize
        [spectral_rolloff / 1000],
        [zero_crossing_rate]
    ])
    
    return features.reshape(1, -1)

def send_to_blockchain(filename: str, is_real: bool, timestamp: datetime):
    """
    Add a new block to the blockchain with the prediction.
    """
    predicted_label = 'REAL' if is_real else 'FAKE'
    confidence = 1 if is_real else 0
    last_block = blockchain.get_last_block()
    prev_hash = last_block['hash'] if last_block else 'GENESIS'
    blockchain.create_new_block(predicted_label, confidence, prev_hash)
    print(f"[BLOCKCHAIN] Stored in blockchain: {predicted_label} with confidence: {confidence}")

# —— Routes ————————————————————————————————————————

@app.route('/')
def index():
    """Render upload form and any flash messages."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    # 1. Validate file present
    if 'file' not in request.files:
        flash('No file part in request', 'danger')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('index'))

    # 2. Validate extension
    if not allowed_file(file.filename):
        flash('Invalid file type; please upload a .wav file', 'danger')
        return redirect(url_for('index'))

    # 3. Save file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # 4. Extract features & predict
    features = extract_features(filepath)
    pred = model.predict(features)[0]  # 0 = Real, 1 = Fake
    is_real = (pred == 0)
    label = 'Real' if is_real else 'Fake'
    flash(f'🎤 Voice detected as: {label}', 'success' if is_real else 'danger')

    # 5. Log locally
    log_action(filename, label)

    # 6. Store the prediction in blockchain
    send_to_blockchain(filename, is_real, datetime.now())

    # 7. (Optional) Remove file from the server after processing to save space
    os.remove(filepath)

    return redirect(url_for('index'))

@app.route('/logs')
def logs():
    """
    Read the JSON log and render it as a table.
    """
    log_file = 'data/sample_alerts.json'
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            logs = json.load(f)
    else:
        logs = []
    return render_template('logs.html', logs=logs)

@app.route('/blockchain')
def view_blockchain():
    """Render the blockchain data from the database."""
    blockchain_data = blockchain.chain
    return render_template('blockchain.html', blockchain=blockchain_data)

# —— Run the App ————————————————————————————————
if __name__ == '__main__':
    app.run(debug=True)
