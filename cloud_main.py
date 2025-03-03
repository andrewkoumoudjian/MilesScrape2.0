"""Main execution script for cloud-based Milestone Lead Generator."""

import os
import logging
import time
import json
import base64
from typing import Dict, Any
from datetime import datetime
from flask import Flask, request, jsonify

from cloud_linkedin_scraper import CloudLinkedInScraper
from analysis import OpenRouterAnalyzer
from gcp_integration import GCPIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize Flask app for Cloud Run
app = Flask(__name__)

class CloudMilestoneLeadGenerator:
    """Cloud-based lead generator for business milestones."""
    
    def __init__(self):
        """Initialize components."""
        self.linkedin_scraper = CloudLinkedInScraper()
        self.analyzer = OpenRouterAnalyzer()
        self.gcp = GCPIntegration()
    
    def run_scan(self, location=None, days_back=30) -> Dict[str, Any]:
        """Run a complete scan cycle."""
        start_time = time.time()
        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Override target location if provided
        if location:
            self.linkedin_scraper.target_location = location
        
        # Log scan parameters
        logger.info(f"Starting milestone lead scan for {self.linkedin_scraper.target_location} ({days_back} days back)")
        
        results = {
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat(),
            "location": self.linkedin_scraper.target_location,
            "days_back": days_back,
            "status": "started"
        }
        
        try:
            # Step 1: Find companies in the target location using Google Maps API
            companies = self.linkedin_scraper.search_for_companies_with_maps_api()
            results["companies_found"] = len(companies)
            
            # Step 2: Initialize the LinkedIn scraper
            if not self.linkedin_scraper.login():
                results["status"] = "error"
                results["error"] = "LinkedIn login failed"
                return results
            
            # Step 3: Scan LinkedIn for milestone posts
            linkedin_posts = self.linkedin_scraper.search_posts_by_keywords(days_back=days_back)
            results["linkedin_posts_found"] = len(linkedin_posts)
            
            # Step 4: For each company found via Maps API, try to find their LinkedIn page
            company_posts = []
            for company in companies[:50]:  # Limit to 50 companies to avoid rate limiting
                try:
                    # Search for company on LinkedIn
                    company_name = company.get('name', '')
                    if company_name:
                        # Extract company posts
                        posts = self.linkedin_scraper.search_company_posts(company_name)
                        
                        # Add company info to posts
                        for post in posts:
                            post['company_name'] = company_name
                            post['company_details'] = company
                        
                        company_posts.extend(posts)
                except Exception as e:
                    logger.warning(f"Error processing company {company.get('name', '')}: {str(e)}")
            
            results["company_posts_found"] = len(company_posts)
            
            # Step 5: Combine all posts
            all_posts = linkedin_posts + company_posts
            results["total_posts_found"] = len(all_posts)
            
            # Store raw posts data
            raw_posts_path = self.gcp.store_blob(all_posts, f"raw_posts/{scan_id}_raw_posts.json")
            results["raw_posts_path"] = raw_posts_path
            
            # Step 6: Analyze posts for sentiment and milestone details
            if all_posts:
                analyzed_posts, high_value_leads = self.analyzer.analyze_posts(all_posts)
                results["posts_analyzed"] = len(analyzed_posts)
                results["leads_found"] = len(high_value_leads)
                
                # Store analyzed posts and leads
                analyzed_path = self.gcp.store_blob(analyzed_posts, f"analyzed_posts/{scan_id}_analyzed_posts.json")
                leads_path = self.gcp.store_blob(high_value_leads, f"leads/{scan_id}_leads.json")
                
                results["analyzed_posts_path"] = analyzed_path
                results["leads_path"] = leads_path
                
                # Store leads in Firestore for easier querying
                self.gcp.store_leads_firestore(high_value_leads)
                
                # Load data to BigQuery for analytics
                try:
                    self.gcp.load_data_to_bigquery(
                        high_value_leads, 
                        dataset_id="milestone_leads", 
                        table_id="high_value_leads"
                    )
                except Exception as e:
                    logger.warning(f"Error loading data to BigQuery: {str(e)}")
            
            # Update final status
            duration = time.time() - start_time
            results["status"] = "completed"
            results["duration_seconds"] = round(duration, 2)
            
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            logger.error(f"Error in scan cycle: {str(e)}", exc_info=True)
        
        # Store final results
        self.gcp.store_blob(results, f"scan_results/{scan_id}_results.json")
        
        # Close the browser
        try:
            self.linkedin_scraper.quit()
        except:
            pass
            
        return results


# Flask routes for Cloud Run
@app.route('/', methods=['GET'])
def home():
    """Home route."""
    return jsonify({
        "service": "Milestone Lead Generator",
        "status": "running",
        "endpoints": {
            "/scan": "POST - Run a scan",
            "/leads": "GET - Get high value leads"
        }
    })

@app.route('/scan', methods=['POST'])
def scan():
    """Run a scan."""
    # Get parameters from request
    data = request.get_json() or {}
    location = data.get('location')
    days_back = int(data.get('days_back', 30))
    
    # Run scan
    generator = CloudMilestoneLeadGenerator()
    results = generator.run_scan(location=location, days_back=days_back)
    
    return jsonify(results)

@app.route('/leads', methods=['GET'])
def get_leads():
    """Get high value leads."""
    # Get parameters
    limit = int(request.args.get('limit', 100))
    min_sentiment = float(request.args.get('sentiment', 0.7))
    
    # Initialize GCP integration
    gcp = GCPIntegration()
    
    # Query leads
    leads = gcp.query_leads(
        limit=limit,
        min_sentiment=min_sentiment,
        has_milestone=request.args.get('milestone', 'false').lower() == 'true'
    )
    
    return jsonify({
        "count": len(leads),
        "leads": leads
    })

@app.route('/pubsub', methods=['POST'])
def pubsub_handler():
    """Handle Pub/Sub messages for scheduled scans."""
    envelope = request.get_json()
    if not envelope:
        return jsonify(error="no Pub/Sub message received"), 400
        
    # Extract the message
    if not isinstance(envelope, dict) or 'message' not in envelope:
        return jsonify(error="invalid Pub/Sub message format"), 400
        
    # Decode message data
    message = envelope['message']
    if 'data' in message:
        try:
            data = json.loads(base64.b64decode(message['data']).decode('utf-8'))
        except:
            data = {}
    else:
        data = {}
    
    # Run scan with message parameters
    generator = CloudMilestoneLeadGenerator()
    results = generator.run_scan(
        location=data.get('location'),
        days_back=int(data.get('days_back', 30))
    )
    
    return jsonify(results)

if __name__ == "__main__":
    # This is used when running locally
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)