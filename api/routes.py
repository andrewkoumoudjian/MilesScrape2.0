"""
API routes for the Milestone Lead Generator
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import request, jsonify, Blueprint

# Configure logging
logger = logging.getLogger(__name__)

def register_api_routes(app, services):
    """
    Register API routes with the Flask application
    
    Args:
        app: Flask application
        services: Dictionary of service instances
    """
    # Extract services from dictionary
    storage_service = services.get('storage_service')
    linkedin_scraper = services.get('linkedin_scraper')
    data_processor = services.get('data_processor')
    lead_analyzer = services.get('lead_analyzer')
    
    # API endpoint for dashboard stats
    @app.route('/stats', methods=['GET'])
    def get_stats():
        """Get dashboard statistics"""
        try:
            # Get actual stats from storage
            stats = storage_service.get_dashboard_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return jsonify({"error": "Failed to retrieve statistics"}), 500
    
    # API endpoint for scanning
    @app.route('/scan', methods=['POST'])
    def start_scan():
        """Start a new lead scanning process"""
        try:
            data = request.json
            logger.info(f"Received scan request: {data}")
            
            # Extract parameters
            location = data.get('location')
            radius_km = data.get('radius_km', 50)
            days_back = data.get('days_back', 30)
            milestone_types = data.get('milestone_types', ['funding', 'expansion', 'anniversary', 'award', 'launch'])
            
            if not location:
                return jsonify({"error": "Location is required"}), 400
            
            # Create a unique scan ID
            scan_id = f"scan-{uuid.uuid4().hex[:8]}"
            
            # Save scan configuration
            scan_config = {
                "id": scan_id,
                "location": location,
                "radius_km": radius_km,
                "days_back": days_back,
                "milestone_types": milestone_types,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "progress": 0,
                "stats": {
                    "companies": 0,
                    "posts": 0,
                    "leads": 0
                }
            }
            
            # Save scan to storage
            storage_service.save_scan(scan_id, scan_config)
            
            # Start scan in background
            linkedin_scraper.start_scan_async(scan_id, location, radius_km, days_back, milestone_types)
            
            return jsonify({
                "scan_id": scan_id,
                "message": "Scan initiated successfully",
                "status": "in_progress"
            })
        except Exception as e:
            logger.error(f"Error starting scan: {e}")
            return jsonify({"error": f"Failed to start scan: {str(e)}"}), 500

    # Get scan status
    @app.route('/scan/<scan_id>/status', methods=['GET'])
    def get_scan_status(scan_id):
        """Get the status of an ongoing scan"""
        try:
            # Get scan from storage
            scan_data = storage_service.get_scan(scan_id)
            
            if not scan_data:
                return jsonify({"error": f"Scan {scan_id} not found"}), 404
            
            return jsonify(scan_data)
        except Exception as e:
            logger.error(f"Error getting scan status: {e}")
            return jsonify({"error": "Failed to get scan status"}), 500

    # Cancel a scan
    @app.route('/scan/<scan_id>/cancel', methods=['POST'])
    def cancel_scan(scan_id):
        """Cancel an ongoing scan"""
        try:
            # Get scan from storage
            scan_data = storage_service.get_scan(scan_id)
            
            if not scan_data:
                return jsonify({"error": f"Scan {scan_id} not found"}), 404
            
            if scan_data['status'] not in ['pending', 'in_progress']:
                return jsonify({"error": "Scan cannot be cancelled in its current state"}), 400
            
            # Update scan status
            scan_data['status'] = 'cancelled'
            scan_data['cancelled_at'] = datetime.utcnow().isoformat()
            
            # Save updated scan
            storage_service.save_scan(scan_id, scan_data)
            
            # Stop the scan process
            linkedin_scraper.cancel_scan(scan_id)
            
            return jsonify({
                "message": f"Scan {scan_id} cancelled successfully",
                "scan_id": scan_id
            })
        except Exception as e:
            logger.error(f"Error cancelling scan: {e}")
            return jsonify({"error": "Failed to cancel scan"}), 500

    # Get active scan
    @app.route('/scan/active', methods=['GET'])
    def get_active_scan():
        """Get the currently active scan if any"""
        try:
            # Get active scans from storage
            active_scans = storage_service.get_active_scans()
            
            if not active_scans:
                return jsonify({"message": "No active scans found"}), 404
            
            # Return the most recent active scan
            return jsonify(active_scans[0])
        except Exception as e:
            logger.error(f"Error getting active scan: {e}")
            return jsonify({"error": "Failed to get active scan"}), 500

    # Get all scans
    @app.route('/scans', methods=['GET'])
    def get_all_scans():
        """Get all scans with optional filtering"""
        try:
            # Parse query parameters
            limit = request.args.get('limit', 10, type=int)
            status = request.args.get('status', None)
            
            # Get scans from storage
            scans = storage_service.get_scans(limit=limit, status=status)
            
            return jsonify({"scans": scans})
        except Exception as e:
            logger.error(f"Error getting scans: {e}")
            return jsonify({"error": "Failed to retrieve scans"}), 500

    # Get leads with filtering
    @app.route('/leads', methods=['GET'])
    def get_leads():
        """Get leads based on filters"""
        try:
            # Parse query parameters
            limit = request.args.get('limit', 10, type=int)
            offset = request.args.get('offset', 0, type=int)
            location = request.args.get('location', '')
            milestone_type = request.args.get('milestone_type', '')
            min_sentiment = request.args.get('min_sentiment', 0.5, type=float)
            sort = request.args.get('sort', 'recent')  # recent, score
            
            # Get leads from storage
            leads = storage_service.get_leads(
                limit=limit,
                offset=offset,
                location=location,
                milestone_type=milestone_type,
                min_sentiment=min_sentiment,
                sort=sort
            )
            
            return jsonify({"leads": leads})
        except Exception as e:
            logger.error(f"Error getting leads: {e}")
            return jsonify({"error": "Failed to retrieve leads"}), 500

    # Get specific lead details
    @app.route('/leads/<lead_id>', methods=['GET'])
    def get_lead_details(lead_id):
        """Get detailed information about a specific lead"""
        try:
            # Get lead from storage
            lead = storage_service.get_lead(lead_id)
            
            if not lead:
                return jsonify({"error": f"Lead {lead_id} not found"}), 404
            
            # Add analysis if not already present
            if 'analysis' not in lead:
                lead['analysis'] = lead_analyzer.analyze_lead(lead)
                storage_service.save_lead(lead_id, lead)
            
            return jsonify(lead)
        except Exception as e:
            logger.error(f"Error getting lead details: {e}")
            return jsonify({"error": "Failed to retrieve lead details"}), 500
    
    # Save lead as favorite
    @app.route('/leads/<lead_id>/favorite', methods=['POST'])
    def favorite_lead(lead_id):
        """Mark a lead as favorite"""
        try:
            data = request.json or {}
            user = data.get('user', 'anonymous')
            
            # Get lead from storage
            lead = storage_service.get_lead(lead_id)
            
            if not lead:
                return jsonify({"error": f"Lead {lead_id} not found"}), 404
            
            # Update lead's favorite status
            if 'favorites' not in lead:
                lead['favorites'] = []
                
            if user not in lead['favorites']:
                lead['favorites'].append(user)
            
            # Save updated lead
            storage_service.save_lead(lead_id, lead)
            
            return jsonify({
                "message": f"Lead {lead_id} marked as favorite",
                "favorites_count": len(lead['favorites'])
            })
        except Exception as e:
            logger.error(f"Error favoriting lead: {e}")
            return jsonify({"error": "Failed to mark lead as favorite"}), 500
            
    logger.info("API routes registered successfully")
    return app