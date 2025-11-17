import os
import json
import tempfile
from datetime import datetime
import hashlib

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from werkzeug.utils import secure_filename

import librosa
import numpy as np
import joblib
import qrcode
import speech_recognition as sr
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont

from user_actions import log_action

# Import the Blockchain class
from blockchain import Blockchain
from tts_service import synthesize_to_wav

# —— Flask App Configuration —————————————————————————
app = Flask(__name__)

# Hardcoded secret key (for development)
app.secret_key = 'a_hardcoded_very_secret_key_1234567890'

# Upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# —— Load Your Trained Models —————————————————————————— 
MODEL_PATH = 'model/voice_detector.pkl'
model = joblib.load(MODEL_PATH)

# Text-based scam / behavior classifier trained on BETTER30
SCAM_MODEL_PATH = 'models/better30_scam_text_model.pkl'
scam_text_model = None

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

def generate_file_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def generate_certificate_qr(certificate_data, filename, timestamp_value):
    cert_dir = os.path.join('static', 'certs')
    os.makedirs(cert_dir, exist_ok=True)
    safe_name = os.path.splitext(secure_filename(filename))[0]
    safe_timestamp = str(timestamp_value).replace(":", "").replace(" ", "").replace("-", "")
    qr_filename = f"cert_{safe_name}_{safe_timestamp}.png"
    qr_path = os.path.join(cert_dir, qr_filename)
    if not os.path.exists(qr_path):
        qr_payload = json.dumps(certificate_data, separators=(",", ":"))
        qr = qrcode.QRCode(
            version=2,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6,
            border=2
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img.save(qr_path)
    return qr_path

def generate_certificate_image(certificate_data, filename, timestamp_value):
    cert_dir = os.path.join('static', 'certs')
    os.makedirs(cert_dir, exist_ok=True)
    safe_name = os.path.splitext(secure_filename(filename))[0]
    safe_timestamp = str(timestamp_value).replace(":", "").replace(" ", "").replace("-", "")
    cert_filename = f"certimg_{safe_name}_{safe_timestamp}.jpg"
    cert_path = os.path.join(cert_dir, cert_filename)

    qr_path = generate_certificate_qr(certificate_data, filename, timestamp_value)
    qr_img = Image.open(qr_path).convert("RGB")

    width, height = 1200, 675
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
        font_body = ImageFont.truetype("DejaVuSans.ttf", 22)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((40, 30), "Voice Integrity Certificate", font=font_title, fill=(20, 20, 20))
    draw.line([(40, 90), (width - 40, 90)], fill=(200, 200, 200), width=2)

    left_x = 50
    y = 120
    line_h = 36

    def draw_kv(key, value):
        nonlocal y
        draw.text((left_x, y), f"{key}:", font=font_body, fill=(40, 40, 40))
        draw.text((left_x + 260, y), str(value), font=font_body, fill=(0, 0, 0))
        y += line_h

    draw_kv("File", certificate_data.get("filename"))
    draw_kv("Result", certificate_data.get("result"))
    draw_kv("Model ID", certificate_data.get("model_id"))
    draw_kv("Timestamp", certificate_data.get("timestamp"))

    qr_size = 300
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    qr_x = width - qr_size - 80
    qr_y = 150
    img.paste(qr_img, (qr_x, qr_y))
    draw.text((qr_x, qr_y + qr_size + 10), "Scan for authenticity", font=font_small, fill=(40, 40, 40))

    img.save(cert_path, "JPEG", quality=90)
    return cert_path

# —— Routes ————————————————————————————————————————

@app.route('/')
def index():
    """Render upload form and any flash messages."""
    return render_template('index.html')

def transcribe_audio(audio_path):
    """Convert speech to text using Google's speech recognition."""
    r = sr.Recognizer()
    
    # Convert to WAV if needed (pydub can handle other formats)
    if not audio_path.lower().endswith('.wav'):
        sound = AudioSegment.from_file(audio_path)
        wav_path = audio_path + '.wav'
        sound.export(wav_path, format='wav')
        audio_path = wav_path
    
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data)
            return text
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError as e:
        return f"Could not request results; {e}"
    except Exception as e:
        return f"Error during transcription: {str(e)}"
    finally:
        # Clean up temporary WAV file if it was created
        if 'wav_path' in locals() and os.path.exists(wav_path):
            os.remove(wav_path)


def analyze_scam_behavior(transcription: str):
    """Analyze transcript text for scam / behavior using the BETTER30 text model.

    Returns a tuple (scam_label, scam_comment). If analysis is unavailable,
    returns (None, None) without raising.
    """
    global scam_text_model

    if not transcription or not isinstance(transcription, str):
        return None, None

    # Lazy-load the text classification model
    if scam_text_model is None:
        if not os.path.exists(SCAM_MODEL_PATH):
            print(f"[SCAM_MODEL] Model file not found at {SCAM_MODEL_PATH}; skipping scam analysis.")
            return None, None
        try:
            scam_text_model = joblib.load(SCAM_MODEL_PATH)
            print("[SCAM_MODEL] Loaded scam behavior model.")
        except Exception as e:
            print(f"[SCAM_MODEL] Error loading scam model: {e}")
            return None, None

    try:
        raw_label = scam_text_model.predict([transcription])[0]
        raw_label_str = str(raw_label).strip().lower()
    except Exception as e:
        print(f"[SCAM_MODEL] Error during scam prediction: {e}")
        return None, None

    # Map raw labels from BETTER30 to user-friendly titles and comments
    label_explanations = {
        'legitimate': {
            'title': 'Legitimate',
            'comment': 'Call content appears legitimate with no obvious scam indicators.'
        },
        'neutral': {
            'title': 'Neutral',
            'comment': 'Call appears neutral with no strong suspicious patterns.'
        },
        'slightly_suspicious': {
            'title': 'Slightly Suspicious',
            'comment': 'Some mild signs of persuasion or pressure are present; call should be handled with caution.'
        },
        'suspicious': {
            'title': 'Suspicious',
            'comment': 'Clear suspicious patterns are present (e.g., urgency, pressure, or requests for sensitive information).'
        },
        'highly_suspicious': {
            'title': 'Highly Suspicious',
            'comment': 'Strong scam-like behavior detected; caller uses heavy pressure, threats, or emotional manipulation.'
        },
        'scam': {
            'title': 'Scam',
            'comment': 'Model considers this call a scam. Do not share personal or financial information.'
        },
        'potential_scam': {
            'title': 'Potential Scam',
            'comment': 'Patterns strongly resemble known scam tactics; independent verification is recommended.'
        },
    }

    info = label_explanations.get(raw_label_str)
    if info:
        return info['title'], info['comment']

    # Fallback if an unknown label is encountered
    fallback_label = raw_label_str or 'Unknown'
    return fallback_label.title(), f"Model classified this call as '{fallback_label}'. Review details carefully."


@app.route('/tts_generate', methods=['POST'])
def tts_generate():
    """Generate speech audio from text using pyttsx3 and return a WAV file."""
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'Text is required'}), 400

    try:
        filename, filepath = synthesize_to_wav(text, UPLOAD_FOLDER)
    except Exception as e:
        return jsonify({'error': f'Failed to synthesize audio: {str(e)}'}), 500

    return send_file(filepath, mimetype='audio/wav', as_attachment=False, download_name=filename)


@app.route('/upload', methods=['POST'])
def handle_upload():
    """Handle file upload, prediction, and transcription."""
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
    file_hash = generate_file_hash(filepath)

    # 4. Extract features & predict
    source = (request.form.get('source') or '').strip().lower()
    features = extract_features(filepath)
    pred = model.predict(features)[0]  # 0 = Real, 1 = Fake
    is_real = (pred == 0)
    label = 'Real' if is_real else 'Fake'

    # If source is TTS, always treat as Fake regardless of model output
    if source == 'tts':
        is_real = False
        label = 'Fake'
    
    # 5. Transcribe the audio
    transcription = transcribe_audio(filepath)

    # 6. Analyze transcript for scam / behavior using text model
    scam_label, scam_comment = analyze_scam_behavior(transcription)

    # 7. Log locally with transcription and scam analysis
    log_action(filename, label, transcription, scam_label=scam_label, scam_comment=scam_comment, file_hash=file_hash)

    # 8. Store the prediction in blockchain
    send_to_blockchain(filename, is_real, datetime.now())

    # 9. Prepare response with detection, transcription, and scam analysis
    messages = [
        f'🎤 Voice detected as: {label}',
        f'📝 Transcription: {transcription}'
    ]
    if scam_label:
        messages.append(f'⚠️ Scam analysis: {scam_label}')
    if scam_comment:
        messages.append(f'🧠 Behavior insight: {scam_comment}')

    flash(messages, 'success' if is_real else 'danger')

    # 10. Remove file from the server after processing
    os.remove(filepath)

    return redirect(url_for('index'))

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
    
    # 5. Transcribe the audio
    transcription = transcribe_audio(filepath)
    
    # 6. Log locally with transcription
    log_action(filename, label, transcription, file_hash=file_hash)

    # 7. Store the prediction in blockchain
    send_to_blockchain(filename, is_real, datetime.now())

    # 8. Prepare response with both detection and transcription
    flash([
        f'🎤 Voice detected as: {label}',
        f'📝 Transcription: {transcription}'
    ], 'success' if is_real else 'danger')

    # 9. Remove file from the server after processing
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

@app.route('/certificate')
def view_certificate():
    timestamp_value = request.args.get('ts')
    if not timestamp_value:
        flash('Certificate generation failed: missing timestamp', 'danger')
        return redirect(url_for('logs'))
    log_file = 'data/sample_alerts.json'
    if not os.path.exists(log_file):
        flash('Certificate generation failed: no detection history available', 'danger')
        return redirect(url_for('logs'))
    with open(log_file, 'r') as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
    selected_log = None
    for log in logs:
        if log.get('timestamp') == timestamp_value:
            selected_log = log
            break
    if not selected_log:
        flash('Certificate generation failed: record not found', 'danger')
        return redirect(url_for('logs'))
    filename = selected_log.get('filename', 'Unknown')
    prediction = selected_log.get('prediction', '')
    result = 'REAL' if str(prediction).lower() == 'real' else 'FAKE'
    model_id = 'voice_detector_v1'
    file_hash = selected_log.get('file_hash')
    if not file_hash:
        file_hash = 'N/A'
    certificate_data = {
        'filename': filename,
        'result': result,
        'model_id': model_id,
        'timestamp': timestamp_value,
        'file_hash': file_hash
    }
    qr_path = generate_certificate_qr(certificate_data, filename, timestamp_value)
    qr_relative = os.path.relpath(qr_path, 'static').replace('\\', '/')
    block = {'data': certificate_data}
    return render_template('certificate.html', block=block, qr_image=qr_relative)

@app.route('/download_certificate')
def download_certificate():
    timestamp_value = request.args.get('ts')
    if not timestamp_value:
        flash('Certificate download failed: missing timestamp', 'danger')
        return redirect(url_for('logs'))
    log_file = 'data/sample_alerts.json'
    if not os.path.exists(log_file):
        flash('Certificate download failed: no detection history available', 'danger')
        return redirect(url_for('logs'))
    with open(log_file, 'r') as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
    selected_log = None
    for log in logs:
        if log.get('timestamp') == timestamp_value:
            selected_log = log
            break
    if not selected_log:
        flash('Certificate download failed: record not found', 'danger')
        return redirect(url_for('logs'))
    filename = selected_log.get('filename', 'Unknown')
    certificate_data = {
        'filename': filename,
        'result': 'REAL' if str(selected_log.get('prediction', '')).lower() == 'real' else 'FAKE',
        'model_id': 'voice_detector_v1',
        'timestamp': timestamp_value,
        'file_hash': selected_log.get('file_hash')
    }
    cert_path = generate_certificate_image(certificate_data, filename, timestamp_value)
    if not os.path.exists(cert_path):
        flash('Certificate download failed: certificate not available', 'danger')
        return redirect(url_for('logs'))
    return send_file(cert_path, mimetype='image/jpeg', as_attachment=True, download_name='Voice_Integrity_Certificate.jpg')

# —— Run the App ————————————————————————————————
if __name__ == '__main__':
    app.run(debug=True)
