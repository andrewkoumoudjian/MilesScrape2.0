"""
Configuration settings for Milestone Lead Generator
"""

import os
import logging

logger = logging.getLogger(__name__)

class Config:
    """Base configuration class"""
    
    def __init__(self):
        # Environment
        self.ENV = os.environ.get('ENVIRONMENT', 'production')
        
        # Google Cloud project and region
        self.GCP_PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'milesscrape')
        self.GCP_REGION = os.environ.get('GCP_REGION', 'northamerica-northeast1')
        
        # Storage
        self.STORAGE_BUCKET_NAME = os.environ.get('STORAGE_BUCKET_NAME', 'milestone-lead-generator')
        
        # LinkedIn credentials
        self.LINKEDIN_USERNAME = os.environ.get('LINKEDIN_USERNAME', '')
        self.LINKEDIN_PASSWORD = os.environ.get('LINKEDIN_PASSWORD', '')
        
        # OpenAI API
        self.OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
        
        # App settings
        self.DEBUG = os.environ.get('DEBUG', 'False') == 'True'
        self.TESTING = os.environ.get('TESTING', 'False') == 'True'
        self.SECRET_KEY = os.environ.get('SECRET_KEY', 'milesscrape-dev-key')
        
        # Logging
        logging_level = os.environ.get('LOGGING_LEVEL', 'INFO')
        self.LOGGING_LEVEL = getattr(logging, logging_level)
        
        # Auth settings
        self.AUTH_ENABLED = os.environ.get('AUTH_ENABLED', 'True') == 'True'
        
        logger.info(f"Loaded configuration for environment: {self.ENV}")