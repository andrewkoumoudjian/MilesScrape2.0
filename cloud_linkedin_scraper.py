"""LinkedIn web scraping module optimized for cloud deployment."""

import time
import random
import logging
import re
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

from gcp_integration import GCPIntegration

logger = logging.getLogger(__name__)

class CloudLinkedInScraper:
    """Web scraper for LinkedIn optimized for cloud environments."""
    
    def __init__(self):
        self.driver = None
        self.logged_in = False
        self.gcp = GCPIntegration()
        
        # Get LinkedIn credentials from Secret Manager
        self.linkedin_username = self.gcp.get_secret('linkedin-username')
        self.linkedin_password = self.gcp.get_secret('linkedin-password')
        
        # Get location settings
        self.target_location = os.environ.get('TARGET_LOCATION', 'New York, NY')
        self.radius_km = int(os.environ.get('RADIUS_KM', '50'))
        
        # Get milestone keywords
        self.milestone_keywords = self._get_milestone_keywords()
    
    def _get_milestone_keywords(self):
        """Get milestone keywords from storage or use default."""
        keywords = self.gcp.retrieve_blob('config/milestone_keywords.json')
        if keywords:
            return keywords
        else:
            return [
                "anniversary", "milestone", "achievement", "award", "funding", 
                "expansion", "new office", "acquisition", "merger", "launch", 
                "IPO", "series A", "series B", "series C", "achieved",
                "celebrating", "proud to announce"
            ]
    
    def setup_driver(self):
        """Set up Chrome WebDriver for cloud environment."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--single-process")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        
        # Add user agent to avoid detection
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
        
        # Set up ChromeDriver
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {str(e)}")
            # Fallback for Cloud environments where ChromeDriverManager might not work
            self.driver = webdriver.Chrome(options=options)
        
        self.driver.set_page_load_timeout(30)
        return self.driver
    
    def login(self):
        """Login to LinkedIn."""
        if not self.linkedin_username or not self.linkedin_password:
            logger.error("LinkedIn credentials not found in Secret Manager")
            return False
            
        if not self.driver:
            self.setup_driver()
        
        try:
            logger.info("Logging in to LinkedIn...")
            self.driver.get("https://www.linkedin.com/login")
            
            # Wait for login page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            # Enter credentials
            self.driver.find_element(By.ID, "username").send_keys(self.linkedin_username)
            self.driver.find_element(By.ID, "password").send_keys(self.linkedin_password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # Wait for login to complete
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'feed-identity-module')]"))
            )
            
            logger.info("Successfully logged in to LinkedIn")
            self.logged_in = True
            
            # Save cookies for future use
            cookies = self.driver.get_cookies()
            self.gcp.store_blob(cookies, 'cookies/linkedin_cookies.json')
            
            # Add a random delay to seem more human
            time.sleep(random.uniform(2, 5))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to login to LinkedIn: {str(e)}")
            
            # Save screenshot for debugging
            try:
                screenshot_path = f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                self.driver.save_screenshot(f"/tmp/{screenshot_path}")
                self.gcp.store_blob(open(f"/tmp/{screenshot_path}", "rb").read(), f"debug/{screenshot_path}")
                logger.info(f"Saved error screenshot to {screenshot_path}")
            except Exception as screenshot_error:
                logger.error(f"Failed to save screenshot: {str(screenshot_error)}")
                
            return False

    # Rest of the methods continue with Cloud adaptations...
    
    def search_for_companies_with_maps_api(self):
        """Search for companies using Google Maps API instead of LinkedIn search."""
        companies = []
        
        try:
            # Get location data using Google Maps Geocoding API
            location_data = self.gcp.geocode_location(self.target_location)
            
            if not location_data:
                logger.error(f"Could not geocode location: {self.target_location}")
                return []
            
            lat = location_data.get('lat')
            lng = location_data.get('lng')
            
            # Use Places API to find businesses nearby
            for keyword in ["business", "company", "startup", "enterprise"]:
                businesses = self.gcp.find_businesses_nearby(
                    lat=lat,
                    lng=lng,
                    radius=self.radius_km * 1000,  # Convert km to meters
                    keyword=keyword
                )
                
                for business in businesses:
                    companies.append({
                        'name': business.get('name', ''),
                        'id': business.get('place_id', ''),  # Using place_id as identifier
                        'url': f"https://www.google.com/maps/place/?q=place_id:{business.get('place_id', '')}",
                        'description': business.get('address', ''),
                        'lat': business.get('lat', 0),
                        'lng': business.get('lng', 0),
                        'source': 'Google Maps'
                    })
            
            logger.info(f"Found {len(companies)} companies via Google Maps API")
            
            # Store the company list for future reference
            self.gcp.store_blob(companies, f"companies/{self.target_location.replace(' ', '_')}_companies.json")
            
        except Exception as e:
            logger.error(f"Error searching for companies with Maps API: {str(e)}")
        
        return companies

    # Add other methods from the original scraper with cloud adaptations...