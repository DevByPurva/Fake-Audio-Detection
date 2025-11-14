"""Utility functions for scam detection."""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

def load_dataset(data_dir='data', filename='call_transcripts.csv'):
    """
    Load and preprocess the dataset.
    
    Args:
        data_dir (str): Directory containing the dataset
        filename (str): Name of the dataset file
        
    Returns:
        pd.DataFrame: Processed dataframe with text and labels
    """
    try:
        filepath = os.path.join(data_dir, filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            print(f"Warning: Dataset file not found at {filepath}")
            # Create a minimal dataset to prevent errors
            return pd.DataFrame({
                'TEXT': [
                    "This is a sample legitimate call.",
                    "Your computer has a virus, call us immediately!",
                    "You've won a prize, just pay the processing fee.",
                    "This is your grandson, I need money for bail.",
                    "I'm calling from the IRS about your tax refund."
                ],
                'LABEL': [
                    'legitimate',
                    'tech_support_scam',
                    'lottery_scam',
                    'grandparent_scam',
                    'impersonation_scam'
                ]
            })
        
        # Load the dataset
        df = pd.read_csv(filepath)
        
        # Basic validation
        required_columns = ['TEXT', 'LABEL']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Clean text data
        df = df[required_columns].dropna()
        df['TEXT'] = df['TEXT'].astype(str).str.strip()
        
        # Map labels to standard format
        label_mapping = {
            'scam': 'scam',
            'suspicious': 'scam',
            'highly_suspicious': 'scam',
            'potential_scam': 'scam',
            'legitimate': 'legitimate',
            'neutral': 'neutral',
            'tech_support': 'tech_support_scam',
            'impersonation': 'impersonation_scam',
            'charity': 'charity_fraud',
            'grandparent': 'grandparent_scam',
            'lottery': 'lottery_scam'
        }
        
        df['LABEL'] = (
            df['LABEL']
            .str.lower()
            .str.strip()
            .map(label_mapping)
            .fillna('neutral')
        )
        
        return df
        
    except Exception as e:
        print(f"Error loading dataset: {str(e)}")
        # Return a minimal dataset to prevent complete failure
        return pd.DataFrame({
            'TEXT': [
                "This is a sample legitimate call.",
                "Your computer has a virus, call us immediately!",
                "You've won a prize, just pay the processing fee.",
                "This is your grandson, I need money for bail.",
                "I'm calling from the IRS about your tax refund."
            ],
            'LABEL': [
                'legitimate',
                'tech_support_scam',
                'lottery_scam',
                'grandparent_scam',
                'impersonation_scam'
            ]
        })

def prepare_dataset_for_training(df, test_size=0.2, random_state=42):
    """
    Prepare the dataset for model training.
    
    Args:
        df (pd.DataFrame): Input dataframe
        test_size (float): Proportion of data to use for testing
        random_state (int): Random seed for reproducibility
        
    Returns:
        tuple: (X_train, X_test, y_train, y_test)
    """
    try:
        # Balance the dataset (simple undersampling for demo)
        min_samples = df['LABEL'].value_counts().min()
        balanced_df = (
            df
            .groupby('LABEL')
            .apply(lambda x: x.sample(min_samples, random_state=random_state) 
                  if len(x) > min_samples else x)
            .reset_index(drop=True)
        )
        
        # Split into features and target
        X = balanced_df['TEXT']
        y = balanced_df['LABEL']
        
        # Split into train and test sets
        return train_test_split(
            X, y, 
            test_size=test_size, 
            random_state=random_state,
            stratify=y
        )
        
    except Exception as e:
        print(f"Error preparing dataset: {str(e)}")
        # Return empty arrays if preparation fails
        return np.array([]), np.array([]), np.array([]), np.array([])
