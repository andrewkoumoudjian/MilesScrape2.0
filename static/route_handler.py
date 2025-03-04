"""
Route handler for the Milestone Lead Generator web interface.
This file integrates the frontend with the backend API.
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_frontend_routes(app):
    """
    Register frontend routes with the Flask application
    """
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
            "version": "1.0.0"
        })
    
    # API endpoint for dashboard stats
    @app.route('/stats', methods=['GET'])
    def get_stats():
        """Get dashboard statistics"""
        try:
            # In production, this would query your database or storage
            # For now, return mock data
            return jsonify({
                "totalLeads": 248,
                "scansRun": 52,
                "conversionRate": "32%",
                "locationsCount": 12
            })
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return jsonify({"error": "Failed to retrieve statistics"}), 500
    
    logger.info("Frontend routes registered successfully")
    return app