"""
Flask API server for MilesScrape 2.0
"""

from flask import Flask, render_template, request, jsonify, send_file
import threading
import json
import os
import logging
from typing import Dict, Any, List
import time

from main import run_scraper
from storage import list_bucket_files, download_from_cloud_storage
from config import DEFAULT_LOCATION, DEFAULT_BUSINESS_TYPES, MAX_RESULTS_PER_QUERY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("milescrape_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')

# Store active scraping jobs
active_jobs = {}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/settings')
def settings():
    """Render the settings page"""
    return render_template('settings.html')

@app.route('/results')
def results():
    """Render the results page"""
    return render_template('results.html')

@app.route('/api/start_scraping', methods=['POST'])
def start_scraping():
    """Start a new scraping job"""
    try:
        data = request.json
        location = data.get('location', DEFAULT_LOCATION)
        business_types = data.get('business_types', DEFAULT_BUSINESS_TYPES)
        max_results = int(data.get('max_results', MAX_RESULTS_PER_QUERY))
        
        job_id = f"job_{int(time.time())}"
        active_jobs[job_id] = {
            "status": "running",
            "location": location,
            "business_types": business_types,
            "max_results": max_results,
            "start_time": time.time(),
            "results": None
        }
        
        # Start scraping in a background thread
        def run_job():
            try:
                results = run_scraper(location, business_types, max_results)
                active_jobs[job_id]["status"] = "completed"
                active_jobs[job_id]["end_time"] = time.time()
                active_jobs[job_id]["results"] = results
            except Exception as e:
                active_jobs[job_id]["status"] = "failed"
                active_jobs[job_id]["error"] = str(e)
                logger.error(f"Job {job_id} failed: {str(e)}")
        
        thread = threading.Thread(target=run_job)
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "success", "job_id": job_id})
    
    except Exception as e:
        logger.error(f"Error starting scraping job: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/job_status/<job_id>', methods=['GET'])
def job_status(job_id):
    """Get the status of a job"""
    if job_id not in active_jobs:
        return jsonify({"status": "error", "message": "Job not found"}), 404
    
    job = active_jobs[job_id]
    response = {
        "status": job["status"],
        "location": job["location"],
        "business_types": job["business_types"],
        "max_results": job["max_results"],
        "start_time": job["start_time"]
    }
    
    if job["status"] == "completed":
        response["end_time"] = job.get("end_time")
        # Don't include full results, just count
        if job.get("results"):
            response["result_count"] = len(job["results"])
    
    if job["status"] == "failed":
        response["error"] = job.get("error", "Unknown error")
    
    return jsonify(response)

@app.route('/api/job_results/<job_id>', methods=['GET'])
def job_results(job_id):
    """Get the results of a completed job"""
    if job_id not in active_jobs:
        return jsonify({"status": "error", "message": "Job not found"}), 404
    
    job = active_jobs[job_id]
    if job["status"] != "completed":
        return jsonify({"status": "error", "message": "Job not completed yet"}), 400
    
    return jsonify({
        "status": "success",
        "results": job.get("results", [])
    })

@app.route('/api/list_files', methods=['GET'])
def list_files():
    """List files in Google Cloud Storage bucket"""
    try:
        files = list_bucket_files()
        return jsonify({"status": "success", "files": files})
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download a file from Google Cloud Storage"""
    try:
        local_path = download_from_cloud_storage(filename)
        return send_file(local_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)