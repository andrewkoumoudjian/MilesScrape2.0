    def complete_scan(self, scan_id, total_posts, total_leads):
        """
        Mark a scan as completed
        
        Args:
            scan_id: Scan ID
            total_posts: Total number of posts found
            total_leads: Total number of leads found
        """
        try:
            # Get scan data
            scan_data = self.storage_service.get_scan(scan_id)
            
            if not scan_data:
                logger.error(f"Scan {scan_id} not found when completing scan")
                return
            
            # Update scan status and stats
            scan_data['status'] = 'completed'
            scan_data['completed_at'] = datetime.utcnow().isoformat()
            scan_data['progress'] = 100
            scan_data['stats']['posts'] = total_posts
            scan_data['stats']['leads'] = total_leads
            
            # Save scan
            self.storage_service.save_scan(scan_id, scan_data)
            
            # Update scan log
            self.update_scan_log(scan_id, f"Scan completed successfully with {total_posts} posts and {total_leads} leads")
            
            # Remove from active scans
            if scan_id in self.active_scans:
                del self.active_scans[scan_id]
                
            # Update dashboard stats
            self.storage_service.update_dashboard_stats()
            
            logger.info(f"Completed scan {scan_id} with {total_posts} posts and {total_leads} leads")
        except Exception as e:
            logger.error(f"Error completing scan: {e}")
    
    def fail_scan(self, scan_id, error_message):
        """
        Mark a scan as failed
        
        Args:
            scan_id: Scan ID
            error_message: Error message
        """
        try:
            # Get scan data
            scan_data = self.storage_service.get_scan(scan_id)
            
            if not scan_data:
                logger.error(f"Scan {scan_id} not found when failing scan")
                return
            
            # Update scan status
            scan_data['status'] = 'failed'
            scan_data['failed_at'] = datetime.utcnow().isoformat()
            scan_data['error'] = error_message
            
            # Save scan
            self.storage_service.save_scan(scan_id, scan_data)
            
            # Update scan log
            self.update_scan_log(scan_id, f"Scan failed: {error_message}")
            
            # Remove from active scans
            if scan_id in self.active_scans:
                del self.active_scans[scan_id]
                
            logger.error(f"Failed scan {scan_id}: {error_message}")
        except Exception as e:
            logger.error(f"Error marking scan as failed: {e}")
    
    def cancel_scan(self, scan_id):
        """
        Cancel a scan
        
        Args:
            scan_id: Scan ID
        """
        # The scan will detect the cancellation on its next iteration
        # via the check_if_scan_cancelled method
        logger.info(f"Requested cancellation of scan {scan_id}")
    
    def health_check(self):
        """
        Check the health of the LinkedIn scraper
        
        Returns:
            Dictionary with health status
        """
        return {
            "initialized": self.initialized,
            "active_scans": len(self.active_scans),
            "driver_ready": self.driver is not None
        }
        
    def __del__(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass