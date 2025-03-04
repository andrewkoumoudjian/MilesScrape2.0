            # Sort by start time (newest first)
            active_scans.sort(key=lambda x: x.get('started_at', ''), reverse=True)
            
            return active_scans
        except Exception as e:
            logger.error(f"Error getting active scans: {e}")
            return []
    
    def get_scans(self, limit=10, status=None):
        """
        Get scans with optional filtering
        
        Args:
            limit: Maximum number of scans to return
            status: Filter by status
            
        Returns:
            List of scan data dictionaries
        """
        try:
            scans = []
            
            if self.bucket:
                # List scans from Cloud Storage
                blobs = self.client.list_blobs(self.bucket_name, prefix="scans/")
                
                # Get all scans
                for blob in blobs:
                    if blob.name.endswith('.json'):
                        try:
                            json_data = blob.download_as_string()
                            scan = json.loads(json_data)
                            
                            # Apply status filter if provided
                            if status and scan.get('status') != status:
                                continue
                                
                            scans.append(scan)
                        except Exception as e:
                            logger.error(f"Error loading scan {blob.name}: {e}")
            else:
                # Local storage fallback
                try:
                    os.makedirs('data/scans', exist_ok=True)
                    for filename in os.listdir('data/scans'):
                        if filename.endswith('.json'):
                            with open(f"data/scans/{filename}", 'r') as f:
                                scan = json.load(f)
                                
                                # Apply status filter if provided
                                if status and scan.get('status') != status:
                                    continue
                                    
                                scans.append(scan)
                except Exception as e:
                    logger.error(f"Error loading scans from local storage: {e}")
            
            # Sort by creation time (newest first)
            scans.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Apply limit
            return scans[:limit]
        except Exception as e:
            logger.error(f"Error getting scans: {e}")
            return []
    
    def get_dashboard_stats(self):
        """
        Get dashboard statistics
        
        Returns:
            Dictionary with dashboard statistics
        """
        try:
            # Check if cached stats are still valid (less than 5 minutes old)
            if (self.dashboard_stats_cache and self.dashboard_stats_last_updated and
                (datetime.utcnow() - self.dashboard_stats_last_updated).total_seconds() < 300):
                return self.dashboard_stats_cache
            
            # Count total leads
            total_leads = 0
            
            # Count total scans
            total_scans = 0
            
            # Count locations
            locations = set()
            
            # Count leads by milestone type
            milestone_counts = {
                'funding': 0,
                'expansion': 0,
                'anniversary': 0,
                'award': 0,
                'launch': 0
            }
            
            # Calculate average score
            total_score = 0
            score_count = 0
            
            # Process leads
            leads = self.get_leads(limit=1000)  # Get all leads (up to 1000)
            total_leads = len(leads)
            
            for lead in leads:
                # Add location
                locations.add(lead.get('location', '').lower())
                
                # Add milestone type
                milestone_type = lead.get('milestone_type', '')
                if milestone_type in milestone_counts:
                    milestone_counts[milestone_type] += 1
                
                # Add score
                score = lead.get('score', 0)
                if score > 0:
                    total_score += score
                    score_count += 1
            
            # Process scans
            scans = self.get_scans(limit=1000)  # Get all scans (up to 1000)
            total_scans = len(scans)
            
            # Calculate conversion rate (leads per scan)
            conversion_rate = 0
            if total_scans > 0:
                conversion_rate = round((total_leads / total_scans) * 100)
            
            # Calculate average score
            avg_score = 0
            if score_count > 0:
                avg_score = round(total_score / score_count, 2)
            
            # Create stats dictionary
            stats = {
                "totalLeads": total_leads,
                "scansRun": total_scans,
                "conversionRate": f"{conversion_rate}%",
                "locationsCount": len(locations),
                "avgScore": avg_score,
                "milestones": milestone_counts,
                "updated_at": datetime.utcnow().isoformat(),
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            }
            
            # Cache the stats
            self.dashboard_stats_cache = stats
            self.dashboard_stats_last_updated = datetime.utcnow()
            
            return stats
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {
                "totalLeads": 0,
                "scansRun": 0,
                "conversionRate": "0%",
                "locationsCount": 0
            }
    
    def update_dashboard_stats(self):
        """Update dashboard statistics"""
        try:
            # Invalidate cache
            self.dashboard_stats_last_updated = None
            
            # Get updated stats
            stats = self.get_dashboard_stats()
            
            # Save stats to storage
            if self.bucket:
                # Convert to JSON
                json_data = json.dumps(stats)
                
                # Upload to Cloud Storage
                blob = self.bucket.blob("dashboard/stats.json")
                blob.upload_from_string(json_data, content_type='application/json')
            else:
                # Local storage fallback
                os.makedirs('data/dashboard', exist_ok=True)
                with open("data/dashboard/stats.json", 'w') as f:
                    json.dump(stats, f)
                    
            return stats
        except Exception as e:
            logger.error(f"Error updating dashboard stats: {e}")
            return None
    
    def health_check(self):
        """
        Check the health of the storage service
        
        Returns:
            Dictionary with health status
        """
        try:
            if self.bucket:
                # Test write to Cloud Storage
                test_blob = self.bucket.blob("health_check.txt")
                test_blob.upload_from_string(f"Health check: {datetime.utcnow().isoformat()}")
                
                return {
                    "status": "healthy",
                    "provider": "Google Cloud Storage",
                    "bucket": self.bucket_name
                }
            else:
                # Test write to local storage
                os.makedirs('data', exist_ok=True)
                with open("data/health_check.txt", 'w') as f:
                    f.write(f"Health check: {datetime.utcnow().isoformat()}")
                    
                return {
                    "status": "healthy",
                    "provider": "Local Storage",
                    "path": "data/"
                }
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }