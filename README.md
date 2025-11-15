# Voice Deepfake Detection System

A Flask web application that detects AI-generated/fake audio using a trained machine learning model. All predictions are stored in an immutable blockchain ledger.

## Features

- 🎤 **Real-time Detection** - Upload WAV files and get instant results
- 🔗 **Blockchain Ledger** - Immutable record of all predictions
- 📊 **Detection History** - View all past detections with timestamps
- ⚡ **Fast Processing** - Results in < 0.01 seconds
- 🎯 **High Accuracy** - >80% accuracy on AI-generated speech (TTS)
- 🧠 **Transcript & Scam Analysis** - Automatic transcription plus scam/behavior comments for every call
- 📝 **Text Scam Model** - Classifies transcripts from the BETTER30 dataset into scam/behavior categories

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Initialize Database

```bash
python3 db.py
```

### 3. Run the Application

```bash
python3 app.py
```

### 4. Open in Browser

```
http://127.0.0.1:5000
```

### 5. (Optional) Retrain Scam Text Model

The repository includes a pre-trained scam/behavior text model at `models/better30_scam_text_model.pkl`.
If you update `BETTER30.csv` or want to retrain:

```bash
python3 train_better30_scam_classifier.py
```

## Usage

1. **Upload Audio**: Click "Choose File" and select a `.wav` file
2. **Analyze**: Click "Analyze" to detect if audio is real or fake
3. **View Results**: See instant classification (REAL ✅ or FAKE 🚨)
4. **Check Logs**: Visit `/logs` to view detection history
5. **View Blockchain**: Visit `/blockchain` to see immutable records

## Project Structure

```
Mini-Project-PSDL-main/
├── app.py                  # Main Flask application
├── blockchain.py           # Blockchain implementation
├── db.py                   # Database initialization
├── user_actions.py         # Logging utilities
├── BETTER30.csv            # Text dataset for scam/behavior labels
├── train_better30_scam_classifier.py  # Scam/behavior text model training
├── model/
│   └── voice_detector.pkl  # Trained audio ML model
├── models/
│   └── better30_scam_text_model.pkl  # Trained scam/behavior text model
├── templates/
│   ├── index.html          # Upload page
│   ├── logs.html           # Detection history
│   └── blockchain.html     # Blockchain viewer
├── static/                 # CSS and JS files
├── data/
│   └── sample_alerts.json  # Detection logs
└── blockchain.db           # Blockchain database
```

## Model Information

- **Type**: Random Forest Classifier
- **Features**: 12 MFCC coefficients
- **Training Accuracy**: 84.6%
- **Test Accuracy**: 82.3%
- **Detection**: AI speech (TTS), synthetic audio, voice modulation

## Scam / Behavior Text Model (Transcripts)

- **Dataset**: `BETTER30.csv` (multi-class labels for different call scenarios and risk levels)
- **Script**: `train_better30_scam_classifier.py`
- **Output Model**: `models/better30_scam_text_model.pkl`
- **Integration**:
  - After upload, the system:
    - Transcribes the audio into text.
    - Classifies the transcript into behavior labels such as *Legitimate*, *Neutral*, *Slightly Suspicious*, *Suspicious*, *Highly Suspicious*, *Scam*, or *Potential Scam*.
    - Displays the transcript, scam label, and a short behavior comment on the dashboard.
    - Stores scam label and comment in the detection history (`/logs`).

## Requirements

- Python 3.9+
- Flask 2.3.3
- librosa 0.10.1
- scikit-learn 1.6.1
- numpy 1.26.4
- soundfile 0.12.1

## API Endpoints

- `GET /` - Main upload page
- `POST /upload` - Upload and analyze audio
- `GET /logs` - View detection history
- `GET /blockchain` - View blockchain ledger

## Notes

- Only `.wav` files are accepted
- Uploaded files are automatically deleted after processing
- All predictions are permanently stored in the blockchain
- The blockchain ensures tamper-proof audit trails

---

**Status**: ✅ Operational  
**Model**: Retrained with 82.3% accuracy on AI speech  
**Ready**: Yes 🚀
