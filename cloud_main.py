"""
Milestone Lead Generator - Main Cloud Application
Production backend API service
"""

import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# Import service modules
from services.linkedin_scraper import LinkedInScraper
from services.data_processor import DataProcessor
from services.analysis import LeadAnalyzer
from services.storage import StorageService

# Import API routes
from api.routes import register_api_routes

# Import configuration
from config.settings import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='static')
app.wsgi_app = ProxyFix(app.wsgi_app)
CORS(app)  # Enable CORS for all routes

# Load configuration
config = Config()
app.config.from_object(config)

# Initialize services
storage_service = StorageService(
    bucket_name=os.environ.get('STORAGE_BUCKET_NAME', 'milestone-lead-generator'),
    project_id=os.environ.get('GCP_PROJECT_ID', 'milesscrape')
)

linkedin_scraper = LinkedInScraper(
    headless=True,
    storage_service=storage_service
)

data_processor = DataProcessor(storage_service)
lead_analyzer = LeadAnalyzer(storage_service)

# Register routes with services injected
app = register_api_routes(app, {
    'storage_service': storage_service,
    'linkedin_scraper': linkedin_scraper,
    'data_processor': data_processor,
    'lead_analyzer': lead_analyzer
})

# Serve main application page
@app.route('/', methods=['GET'])
def index():
    """Serve the main web application frontend"""
    return send_from_directory('static', 'index.html')

# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    """Serve static assets"""
    return send_from_directory('static', path)

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "storage": storage_service.health_check(),
        "scraper": linkedin_scraper.health_check()
    })

if __name__ == '__main__':
    # This is used when running locally
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)