"""
LinkedIn scraper service for Milestone Lead Generator
"""

import os
import time
import logging
import threading
import traceback
from datetime import datetime, timedelta
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import json

logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self, headless=True, storage_service=None):
        """
        Initialize the LinkedIn scraper
        
        Args:
            headless: Whether to run Chrome in headless mode
            storage_service: Storage service for persisting data
        """
        self.headless = headless
        self.storage_service = storage_service
        self.active_scans = {}
        self.driver = None
        self.initialized = False
        self.linkedin_username = os.environ.get('LINKEDIN_USERNAME', '')
        self.linkedin_password = os.environ.get('LINKEDIN_PASSWORD', '')
        
        # Initialize driver and log in if credentials are available
        if self.linkedin_username and self.linkedin_password:
            try:
                self.init_driver()
                self.login()
                self.initialized = True
            except Exception as e:
                logger.error(f"Error initializing LinkedIn scraper: {e}")
                self.initialized = False
    
    def init_driver(self):
        """Initialize the Chrome WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        
        # Add user agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
        except Exception:
            # Fall back to system ChromeDriver in production
            self.driver = webdriver.Chrome(options=chrome_options)
            
        logger.info("Chrome WebDriver initialized")
    
    def login(self):
        """Log in to LinkedIn"""
        if not self.driver:
            self.init_driver()
            
        try:
            # Navigate to LinkedIn login page
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Enter username
            username_field = self.driver.find_element(By.ID, "username")
            username_field.send_keys(self.linkedin_username)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(self.linkedin_password)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if login was successful
            if "feed" in self.driver.current_url:
                logger.info("Successfully logged in to LinkedIn")
                return True
            else:
                logger.error("Failed to log in to LinkedIn")
                return False
        except Exception as e:
            logger.error(f"Error logging in to LinkedIn: {e}")
            return False
    
    def start_scan_async(self, scan_id, location, radius_km, days_back, milestone_types):
        """
        Start a scan asynchronously
        
        Args:
            scan_id: Unique ID for the scan
            location: Location to search (e.g., "New York, NY")
            radius_km: Radius in kilometers
            days_back: Days back to search
            milestone_types: List of milestone types to search for
        """
        # Update scan status to in_progress
        scan_data = self.storage_service.get_scan(scan_id)
        scan_data['status'] = 'in_progress'
        scan_data['started_at'] = datetime.utcnow().isoformat()
        self.storage_service.save_scan(scan_id, scan_data)
        
        # Start scan in a separate thread
        thread = threading.Thread(target=self.run_scan, args=(scan_id, location, radius_km, days_back, milestone_types))
        thread.daemon = True
        thread.start()
        
        # Store thread reference
        self.active_scans[scan_id] = thread
        
        logger.info(f"Started scan {scan_id} for {location} in background thread")
        
        return scan_id
    
    def run_scan(self, scan_id, location, radius_km, days_back, milestone_types):
        """
        Run the scan process
        
        Args:
            scan_id: Unique ID for the scan
            location: Location to search
            radius_km: Radius in kilometers
            days_back: Days back to search
            milestone_types: List of milestone types to search for
        """
        try:
            # Update scan log
            self.update_scan_log(scan_id, f"Starting scan for {location} with {radius_km}km radius")
            
            # Get scan data
            scan_data = self.storage_service.get_scan(scan_id)
            
            # Find companies in the area
            self.update_scan_progress(scan_id, 10, "Searching for companies in the area")
            companies = self.find_companies_in_location(location, radius_km)
            
            # Update scan stats
            scan_data = self.storage_service.get_scan(scan_id)
            scan_data['stats']['companies'] = len(companies)
            self.storage_service.save_scan(scan_id, scan_data)
            
            # Check if scan was cancelled
            if self.check_if_scan_cancelled(scan_id):
                return
            
            # Find milestones for each company
            total_posts = 0
            total_leads = 0
            progress = 10
            
            for i, company in enumerate(companies):
                # Check if scan was cancelled
                if self.check_if_scan_cancelled(scan_id):
                    return
                
                # Calculate progress
                progress = 10 + int(85 * ((i + 1) / len(companies)))
                
                # Update scan log
                self.update_scan_log(scan_id, f"Searching milestones for {company['name']}")
                
                # Look for milestone posts
                milestone_posts = self.find_company_milestones(company, days_back, milestone_types)
                
                # Process milestone posts
                for post in milestone_posts:
                    total_posts += 1
                    
                    # Create lead if confidence score is high enough
                    if post['score'] >= 0.75:
                        lead_id = f"lead-{scan_id}-{total_leads}"
                        
                        # Create lead
                        lead = {
                            "id": lead_id,
                            "company_name": company['name'],
                            "milestone": post['milestone_type'].capitalize(),
                            "milestone_type": post['milestone_type'],
                            "score": post['score'],
                            "location": location,
                            "date": post['date'],
                            "post": post['content'],
                            "company_info": company,
                            "created_at": datetime.utcnow().isoformat(),
                            "scan_id": scan_id
                        }
                        
                        # Save lead
                        self.storage_service.save_lead(lead_id, lead)
                        total_leads += 1
                
                # Update scan progress and stats
                self.update_scan_progress(
                    scan_id, 
                    progress,
                    f"Processed {i+1} of {len(companies)} companies"
                )
                
                # Update scan stats
                scan_data = self.storage_service.get_scan(scan_id)
                scan_data['stats']['posts'] = total_posts
                scan_data['stats']['leads'] = total_leads
                self.storage_service.save_scan(scan_id, scan_data)
                
                # Avoid rate limiting
                time.sleep(random.uniform(1, 3))
            
            # Mark scan as completed
            self.complete_scan(scan_id, total_posts, total_leads)
            
        except Exception as e:
            # Log error
            logger.error(f"Error running scan {scan_id}: {e}")
            logger.error(traceback.format_exc())
            
            # Mark scan as failed
            self.fail_scan(scan_id, str(e))
    
    def find_companies_in_location(self, location, radius_km):
        """
        Find companies in a specific location
        
        Args:
            location: Location to search (e.g., "New York, NY")
            radius_km: Radius in kilometers
            
        Returns:
            List of company dictionaries
        """
        # In production, this would use actual scraping or API calls
        # For demo purposes, returning mock data
        
        # Simulate variable number of companies based on location
        location_hash = hash(location) % 100
        company_count = 50 + location_hash
        
        companies = []
        for i in range(company_count):
            companies.append({
                "name": f"Company {i+1} - {location}",
                "industry": random.choice(["Technology", "Healthcare", "Finance", "Education", "Retail"]),
                "size": random.choice(["1-10", "11-50", "51-200", "201-500", "501-1000", "1001+"]),
                "founded": 2010 + (i % 15),
                "website": f"https://company{i}.example.com",
                "linkedin_url": f"https://linkedin.com/company/company{i}"
            })
        
        return companies
    
    def find_company_milestones(self, company, days_back, milestone_types):
        """
        Find milestones for a specific company
        
        Args:
            company: Company dictionary
            days_back: Days back to search
            milestone_types: List of milestone types to search for
            
        Returns:
            List of milestone post dictionaries
        """
        # In production, this would use actual scraping or API calls
        # For demo purposes, returning mock data
        
        # Probability of finding a milestone (0.0 to 1.0)
        milestone_probability = 0.3
        
        # Randomly determine if we found any milestones
        if random.random() > milestone_probability:
            return []
        
        # Generate 1-3 milestone posts
        num_posts = random.randint(1, 3)
        milestone_posts = []
        
        for _ in range(num_posts):
            # Choose a random milestone type from the allowed types
            milestone_type = random.choice(milestone_types)
            
            # Generate post content based on milestone type
            content = self.generate_mock_milestone_content(company['name'], milestone_type)
            
            # Generate random date within days_back
            days_ago = random.randint(1, days_back)
            post_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            # Generate confidence score between 0.7 and 0.98
            score = round(random.uniform(0.7, 0.98), 2)
            
            milestone_posts.append({
                "milestone_type": milestone_type,
                "content": content,
                "date": post_date,
                "score": score
            })
        
        return milestone_posts
    
    def generate_mock_milestone_content(self, company_name, milestone_type):
        """
        Generate mock milestone post content
        
        Args:
            company_name: Company name
            milestone_type: Type of milestone
            
        Returns:
            Post content string
        """
        if milestone_type == 'funding':
            round_type = random.choice(['Seed', 'Series A', 'Series B', 'Series C', 'Growth'])
            amount = random.choice([1, 2, 5, 10, 20, 50, 100])
            unit = 'M' if amount >= 5 else 'M'
            return f"Excited to announce that {company_name} has secured ${amount}{unit} in {round_type} funding! This investment will help us accelerate our growth and bring our vision to more customers. #funding #startuplife #growth"
        
        elif milestone_type == 'expansion':
            location = random.choice(['New York', 'San Francisco', 'London', 'Singapore', 'Toronto', 'Berlin'])
            return f"Thrilled to announce that {company_name} is expanding to {location}! This marks an important milestone in our journey as we continue to grow globally. #expansion #growth #newmarkets"
        
        elif milestone_type == 'anniversary':
            years = random.randint(1, 15)
            return f"Today marks {years} incredible years since {company_name} was founded! Thank you to our amazing team, customers, and partners who have been with us on this journey. Here's to many more years of innovation and success! #anniversary #milestone"
        
        elif milestone_type == 'award':
            awards = [
                "Innovation Award",
                "Best Workplace Award",
                "Industry Leadership Award",
                "Customer Excellence Award",
                "Sustainability Award"
            ]
            award = random.choice(awards)
            return f"Honored and humbled that {company_name} has been recognized with the {award}. This achievement is a testament to the hard work and dedication of our entire team. #award #recognition #proud"
        
        elif milestone_type == 'launch':
            product = f"new {random.choice(['platform', 'service', 'product', 'feature', 'solution'])}"
            return f"Introducing our {product} at {company_name}! After months of hard work, we're excited to finally share it with the world. This launch represents a significant step forward in our mission to deliver value to our customers. #productlaunch #innovation"
        
        else:
            return f"Exciting news from {company_name}! We're celebrating a major milestone in our company's journey. Stay tuned for more updates. #milestone #companyupdate"
    
    def update_scan_progress(self, scan_id, progress, message=None):
        """
        Update scan progress
        
        Args:
            scan_id: Scan ID
            progress: Progress percentage (0-100)
            message: Progress message
        """
        try:
            # Get scan data
            scan_data = self.storage_service.get_scan(scan_id)
            
            if not scan_data:
                logger.error(f"Scan {scan_id} not found when updating progress")
                return
            
            # Update progress
            scan_data['progress'] = progress
            scan_data['updated_at'] = datetime.utcnow().isoformat()
            
            if message:
                scan_data['recent_log'] = message
                self.update_scan_log(scan_id, message)
            
            # Save scan
            self.storage_service.save_scan(scan_id, scan_data)
        except Exception as e:
            logger.error(f"Error updating scan progress: {e}")
    
    def update_scan_log(self, scan_id, message):
        """
        Add entry to scan log
        
        Args:
            scan_id: Scan ID
            message: Log message
        """
        try:
            # Get scan logs
            logs = self.storage_service.get_scan_logs(scan_id)
            
            if logs is None:
                logs = []
            
            # Add log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "message": message
            }
            
            logs.append(log_entry)
            
            # Save logs
            self.storage_service.save_scan_logs(scan_id, logs)
        except Exception as e:
            logger.error(f"Error updating scan log: {e}")
    
    def check_if_scan_cancelled(self, scan_id):
        """
        Check if a scan has been cancelled
        
        Args:
            scan_id: Scan ID
            
        Returns:
            True if scan was cancelled, False otherwise
        """
        try:
            # Get scan data
            scan_data = self.storage_service.get_scan(scan_id)
            
            if not scan_data:
                logger.error(f"Scan {scan_id} not found when checking if cancelled")
                return True
            
            # Check status
            return scan_data['status'] == 'cancelled'
        except Exception as e:
            logger.error(f"Error checking if scan cancelled: {e}")
            return False
    
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
