"""Scam classification for call transcripts."""

import os
import numpy as np
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier

class ScamClassifier:
    """Classify call transcripts into scam categories."""

    def __init__(self, model_path='models/scam_classifier.pkl', 
                 vectorizer_path='models/tfidf_vectorizer.pkl'):
        """Initialize the classifier with model paths."""
        self.model_path = model_path
        self.vectorizer_path = vectorizer_path
        self.model = None
        self.vectorizer = None
        self.scam_types = {
            'impersonation_scam': {
                'indicators': ['irs', 'tax', 'arrest', 'warrant', 'police', 'sheriff', 
                             'fbi', 'arrest warrant', 'social security', 'government'],
                'description': 'Caller pretends to be from a government agency or authority figure.'
            },
            'tech_support_scam': {
                'indicators': ['computer', 'virus', 'microsoft', 'windows', 'mac', 
                             'hacked', 'security alert', 'tech support', 'remote access'],
                'description': 'Caller claims to be from tech support about computer issues.'
            },
            'charity_fraud': {
                'indicators': ['donation', 'charity', 'children', 'disaster', 
                             'relief', 'fundraiser', 'help needed', 'urgent help'],
                'description': 'Caller requests donations for fake charities.'
            },
            'grandparent_scam': {
                'indicators': ['grandchild', 'grandson', 'granddaughter', 'jail', 
                             'hospital', 'emergency', 'bail', 'stranded', 'relative'],
                'description': 'Caller pretends to be a relative in distress.'
            },
            'lottery_scam': {
                'indicators': ['winner', 'prize', 'lottery', 'sweepstakes', 
                             'claim your prize', 'jackpot', 'congratulations', 'you won'],
                'description': 'Caller claims you won a prize but need to pay fees.'
            }
        }
        self.load_or_train()

    def preprocess_text(self, text):
        """Basic text preprocessing."""
        if not isinstance(text, str):
            return ""
        return ' '.join(str(text).lower().split())

    def load_or_train(self):
        """Load existing model or train a new one."""
        os.makedirs('models', exist_ok=True)
        
        if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
            try:
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                return
            except Exception as e:
                print(f"Error loading model: {str(e)}")
                print("Retraining model...")
        
        self.train_model()

    def train_model(self, data_path='data/call_transcripts.csv'):
        """Train the scam classification model."""
        from .utils import load_dataset, prepare_dataset_for_training
        
        try:
            # Load and preprocess data
            df = load_dataset()
            if df.empty:
                raise ValueError("No data available for training")
                
            df = prepare_dataset_for_training(df)
            df['text'] = df['TEXT'].apply(self.preprocess_text)
            
            # Initialize and fit vectorizer
            self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
            X = self.vectorizer.fit_transform(df['text'])
            
            # Train model
            self.model = RandomForestClassifier(
                n_estimators=100, 
                random_state=42,
                class_weight='balanced'
            )
            self.model.fit(X, df['LABEL'])
            
            # Save model and vectorizer
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
            
            print("Model trained and saved successfully.")
            
        except Exception as e:
            print(f"Error training model: {str(e)}")
            # Initialize with a dummy model if training fails
            self.vectorizer = TfidfVectorizer(stop_words='english')
            self.model = RandomForestClassifier()

    def classify_call(self, transcript, context=""):
        """Classify a call and return detailed analysis."""
        try:
            if not transcript or not isinstance(transcript, str):
                return self.get_default_response()
                
            # Combine transcript and context
            text = self.preprocess_text(f"{transcript} {context}")
            
            # Transform text using the vectorizer
            try:
                X = self.vectorizer.transform([text])
            except:
                # If vectorizer fails, update vocabulary
                self.vectorizer.fit([text])
                X = self.vectorizer.transform([text])
            
            # Get prediction
            if hasattr(self.model, 'predict_proba'):
                probs = self.model.predict_proba(X)[0]
                classes = self.model.classes_
                confidence = max(probs)
                predicted_class = classes[np.argmax(probs)]
            else:
                predicted_class = self.model.predict(X)[0]
                confidence = 0.8  # Default confidence
            
            # Get scam type details
            scam_type = predicted_class.lower()
            scam_info = self.scam_types.get(scam_type, {
                'description': 'No specific scam pattern detected.',
                'indicators': []
            })
            
            # Find matching indicators
            indicators_found = [
                word for word in scam_info['indicators'] 
                if word in text
            ]
            
            # If no indicators found but classified as scam, use default description
            if not indicators_found and 'scam' in scam_type:
                scam_info['description'] = 'Suspicious call pattern detected.'
            
            return {
                'classification': scam_type.replace('_', ' ').title(),
                'confidence': f"{min(confidence * 100, 99):.1f}%",
                'description': scam_info['description'],
                'indicators_found': indicators_found[:5],  # Limit to top 5 indicators
                'recommended_action': self.get_recommended_action(scam_type),
                'context_analysis': self.analyze_context(text, scam_type)
            }
            
        except Exception as e:
            print(f"Error in classification: {str(e)}")
            return self.get_default_response()

    def get_recommended_action(self, scam_type):
        """Get recommended action based on scam type."""
        actions = {
            'impersonation_scam': (
                'Do not provide personal information. Hang up and contact the official agency '
                'directly using verified contact information.'
            ),
            'tech_support_scam': (
                'Never grant remote access to your computer. Hang up and contact the company '
                'directly if concerned about your device.'
            ),
            'charity_fraud': (
                'Do not make any payments. Verify the charity through official channels '
                'before donating.'
            ),
            'grandparent_scam': (
                'Verify the caller\'s identity by asking personal questions only the real '
                'person would know before taking any action.'
            ),
            'lottery_scam': (
                'Remember that legitimate lotteries do not ask for payment to claim prizes. '
                'Do not send any money or personal information.'
            )
        }
        return actions.get(scam_type, 'Exercise caution and verify the caller\'s identity before proceeding.')

    def analyze_context(self, text, scam_type):
        """Provide context-specific analysis."""
        analysis = {
            'impersonation_scam': (
                'Caller is using authority and urgency to pressure immediate action, a common '
                'tactic in government impersonation scams.'
            ),
            'tech_support_scam': (
                'Caller is creating a false sense of urgency about computer issues to gain '
                'remote access or payment information.'
            ),
            'charity_fraud': (
                'Caller is using emotional appeals and high-pressure tactics to solicit '
                'donations for potentially fake causes.'
            ),
            'grandparent_scam': (
                'Caller is exploiting family relationships and creating a sense of emergency '
                'to solicit money quickly.'
            ),
            'lottery_scam': (
                'Caller is using the promise of a large prize to extract upfront payments or '
                'personal information.'
            )
        }
        return analysis.get(scam_type, 'Standard call handling procedures recommended.')

    def get_default_response(self):
        """Return default response when classification fails."""
        return {
            'classification': 'Unknown',
            'confidence': 'N/A',
            'description': 'Unable to analyze the call at this time.',
            'indicators_found': [],
            'recommended_action': 'Proceed with caution and verify the caller\'s identity.',
            'context_analysis': 'Insufficient data for detailed analysis.'
        }
