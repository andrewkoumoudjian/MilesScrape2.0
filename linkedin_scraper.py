"""LinkedIn web scraping module for milestone posts."""

import time
import random
import logging
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

from config import (
    LINKEDIN_USERNAME,
    LINKEDIN_PASSWORD,
    TARGET_LOCATION,
    RADIUS_KM,
    MILESTONE_KEYWORDS,
    HEADLESS,
    CHROME_DRIVER_PATH
)

logger = logging.getLogger(__name__)

class LinkedInScraper:
    """Web scraper for LinkedIn posts based on location and keywords."""
    
    def __init__(self):
        self.driver = None
        self.logged_in = False
    
    def setup_driver(self):
        """Set up and configure Chrome WebDriver."""
        options = Options()
        if HEADLESS:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--start-maximized")
        
        # Add user agent to avoid detection
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
        
        if CHROME_DRIVER_PATH:
            service = Service(CHROME_DRIVER_PATH)
            self.driver = webdriver.Chrome(service=service, options=options)
        else:
            self.driver = webdriver.Chrome(options=options)
        
        self.driver.set_page_load_timeout(30)
        return self.driver
    
    def login(self):
        """Login to LinkedIn."""
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
            self.driver.find_element(By.ID, "username").send_keys(LINKEDIN_USERNAME)
            self.driver.find_element(By.ID, "password").send_keys(LINKEDIN_PASSWORD)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # Wait for login to complete
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'feed-identity-module')]"))
            )
            
            logger.info("Successfully logged in to LinkedIn")
            self.logged_in = True
            
            # Add a random delay to seem more human
            time.sleep(random.uniform(2, 5))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to login to LinkedIn: {str(e)}")
            return False
    
    def search_for_companies(self, location=TARGET_LOCATION):
        """Search for companies in the target location."""
        if not self.logged_in and not self.login():
            return []
        
        companies = []
        
        try:
            # Navigate to company search
            self.driver.get("https://www.linkedin.com/search/results/companies/")
            
            # Wait for search page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'search-results')]"))
            )
            
            # Add location filter
            try:
                # Click on location filter
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Locations')]"))
                ).click()
                
                # Enter location
                location_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Add a location')]"))
                )
                location_input.send_keys(location)
                
                # Wait for suggestions and select first one
                time.sleep(2)  # Wait for suggestions to appear
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'basic-typeahead__selectable')]"))
                ).click()
                
                # Apply filters
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Show results')]"))
                ).click()
                
                # Wait for results to load
                time.sleep(3)
            except Exception as e:
                logger.warning(f"Error setting location filter: {str(e)}")
            
            # Scroll and collect companies
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            company_count = 0
            max_companies = 50
            
            while company_count < max_companies:
                # Parse current page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                company_elements = soup.select('div.entity-result')
                
                for company_element in company_elements:
                    if company_count >= max_companies:
                        break
                    
                    try:
                        name_element = company_element.select_one('span.entity-result__title-text a')
                        if name_element:
                            company_name = name_element.get_text(strip=True)
                            company_link = name_element.get('href', '')
                            company_id = self._extract_company_id(company_link)
                            
                            # Extract description if available
                            description = ""
                            desc_element = company_element.select_one('p.entity-result__summary')
                            if desc_element:
                                description = desc_element.get_text(strip=True)
                            
                            companies.append({
                                'name': company_name,
                                'id': company_id,
                                'url': f"https://www.linkedin.com/company/{company_id}/",
                                'description': description
                            })
                            company_count += 1
                    except Exception as e:
                        logger.error(f"Error parsing company element: {str(e)}")
                
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Check if we've reached the bottom
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            logger.info(f"Found {len(companies)} companies in {location}")
            
        except Exception as e:
            logger.error(f"Error searching for companies: {str(e)}")
        
        return companies
    
    def get_company_posts(self, company_id, max_posts=10):
        """Get recent posts from a specific company."""
        if not self.logged_in and not self.login():
            return []
        
        posts = []
        
        try:
            # Navigate to company posts
            self.driver.get(f"https://www.linkedin.com/company/{company_id}/posts/")
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ember-view')]"))
            )
            
            # Add a random delay to seem more human
            time.sleep(random.uniform(1, 3))
            
            # Scroll a few times to load more posts
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(1, 2))
            
            # Parse posts
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            post_elements = soup.select('div.feed-shared-update-v2')
            
            for post_element in post_elements[:max_posts]:
                try:
                    # Extract post text
                    text_element = post_element.select_one('div.feed-shared-update-v2__description')
                    post_text = ""
                    if text_element:
                        post_text = text_element.get_text(strip=True)
                    
                    # Extract post link/id
                    post_id = ""
                    link_element = post_element.select_one('a.app-aware-link[data-id]')
                    if link_element:
                        post_id = link_element.get('data-id', '')
                        if not post_id:
                            # Try to extract from href
                            href = link_element.get('href', '')
                            post_id = self._extract_post_id(href)
                    
                    # Extract timestamp
                    timestamp = datetime.now().timestamp() * 1000  # Default to current time
                    time_element = post_element.select_one('span.feed-shared-actor__sub-description')
                    if time_element:
                        time_text = time_element.get_text(strip=True)
                        timestamp = self._parse_relative_time(time_text)
                    
                    # Create post object
                    post = {
                        'id': post_id,
                        'text': post_text,
                        'timestamp': timestamp,
                        'url': f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else "",
                        'company_id': company_id,
                        'source': "LinkedIn"
                    }
                    
                    # Check if post contains milestone keywords
                    if any(keyword.lower() in post_text.lower() for keyword in MILESTONE_KEYWORDS):
                        post['contains_milestone_keyword'] = True
                    else:
                        post['contains_milestone_keyword'] = False
                    
                    posts.append(post)
                    
                except Exception as e:
                    logger.error(f"Error parsing post element: {str(e)}")
            
            logger.info(f"Found {len(posts)} posts for company ID {company_id}")
            
        except Exception as e:
            logger.error(f"Error getting company posts: {str(e)}")
        
        return posts
    
    def search_posts_by_keywords(self, days_back=30, max_results=100):
        """Search for posts containing milestone keywords."""
        if not self.logged_in and not self.login():
            return []
        
        all_posts = []
        posts_found = 0
        
        # Search for each milestone keyword
        for keyword in MILESTONE_KEYWORDS:
            if posts_found >= max_results:
                break
                
            try:
                # Construct search URL
                search_url = f"https://www.linkedin.com/search/results/content/?keywords=%22{keyword}%22&origin=GLOBAL_SEARCH_HEADER"
                
                if TARGET_LOCATION:
                    # Add location parameter if configured
                    search_url += f"&locationId=LOCATION.{TARGET_LOCATION.replace(' ', '-').lower()}"
                
                # Navigate to search results
                self.driver.get(search_url)
                
                # Wait for results to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'search-results')]"))
                )
                
                # Add a random delay
                time.sleep(random.uniform(1, 3))
                
                # Scroll to load more results
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                
                for _ in range(5):  # Scroll a few times to load more posts
                    if posts_found >= max_results:
                        break
                        
                    # Scroll down
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(random.uniform(1, 2))
                    
                    # Parse current view
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    post_elements = soup.select('div.search-result--occlusion-enabled')
                    
                    for post_element in post_elements:
                        if posts_found >= max_results:
                            break
                            
                        try:
                            # Extract post text
                            text_element = post_element.select_one('span.search-result__snippet')
                            if not text_element:
                                continue
                                
                            post_text = text_element.get_text(strip=True)
                            
                            # Extract post link/id
                            link_element = post_element.select_one('a.search-result__result-link')
                            if not link_element:
                                continue
                                
                            post_url = link_element.get('href', '')
                            post_id = self._extract_post_id(post_url)
                            
                            # Extract author/company
                            author_element = post_element.select_one('span.search-result__title-text')
                            company_name = ""
                            if author_element:
                                company_name = author_element.get_text(strip=True)
                            
                            # Create post object
                            post = {
                                'id': post_id,
                                'text': post_text,
                                'timestamp': datetime.now().timestamp() * 1000,  # Default to current time
                                'url': f"https://www.linkedin.com{post_url}" if post_url.startswith('/') else post_url,
                                'company_name': company_name,
                                'source': "LinkedIn",
                                'contains_milestone_keyword': True,
                                'milestone_keyword': keyword
                            }
                            
                            # Skip duplicate posts
                            if any(p['id'] == post_id for p in all_posts):
                                continue
                                
                            all_posts.append(post)
                            posts_found += 1
                            
                        except Exception as e:
                            logger.error(f"Error parsing search result: {str(e)}")
                    
                    # Check if we've reached the bottom
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                
                # Add a random delay between keyword searches
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.error(f"Error searching for posts with keyword '{keyword}': {str(e)}")
        
        logger.info(f"Found {len(all_posts)} total posts matching milestone keywords")
        return all_posts
    
    def scan_for_milestone_posts(self, days_back=30, max_results=100):
        """Scan LinkedIn for milestone posts using multiple methods."""
        all_posts = []
        
        # Method 1: Direct keyword search
        keyword_posts = self.search_posts_by_keywords(days_back, max_results // 2)
        all_posts.extend(keyword_posts)
        
        # Method 2: Find companies in target location and check their posts
        if len(all_posts) < max_results:
            companies = self.search_for_companies(TARGET_LOCATION)
            remaining_slots = max_results - len(all_posts)
            posts_per_company = 3
            
            for company in companies[:remaining_slots // posts_per_company]:
                company_posts = self.get_company_posts(company['id'], max_posts=posts_per_company)
                
                # Add company name to posts
                for post in company_posts:
                    post['company_name'] = company['name']
                
                # Filter posts with milestone keywords
                milestone_posts = [p for p in company_posts if p.get('contains_milestone_keyword', False)]
                all_posts.extend(milestone_posts)
                
                # Add a random delay between company checks
                time.sleep(random.uniform(1, 3))
        
        # Close the browser when done
        self.quit()
        
        return all_posts
    
    def quit(self):
        """Close the browser."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.logged_in = False
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")
    
    def _extract_company_id(self, url):
        """Extract company ID from LinkedIn URL."""
        # Pattern: /company/{company-id}/
        match = re.search(r'/company/([^/]+)/?', url)
        if match:
            return match.group(1)
        return ""
    
    def _extract_post_id(self, url):
        """Extract post ID from LinkedIn URL."""
        # Pattern: /feed/update/urn:li:activity:{id}/
        match = re.search(r'urn:li:activity:(\d+)', url)
        if match:
            return f"urn:li:activity:{match.group(1)}"
        return ""
    
    def _parse_relative_time(self, time_text):
        """Convert LinkedIn's relative time to timestamp."""
        now = datetime.now()
        
        if 'minute' in time_text or 'min' in time_text:
            minutes = int(re.search(r'\d+', time_text).group() or 0)
            post_time = now - timedelta(minutes=minutes)
        elif 'hour' in time_text or 'hr' in time_text:
            hours = int(re.search(r'\d+', time_text).group() or 0)
            post_time = now - timedelta(hours=hours)
        elif 'day' in time_text:
            days = int(re.search(r'\d+', time_text).group() or 0)
            post_time = now - timedelta(days=days)
        elif 'week' in time_text or 'wk' in time_text:
            weeks = int(re.search(r'\d+', time_text).group() or 0)
            post_time = now - timedelta(weeks=weeks)
        elif 'month' in time_text or 'mo' in time_text:
            months = int(re.search(r'\d+', time_text).group() or 0)
            post_time = now - timedelta(days=months * 30)
        elif 'year' in time_text or 'yr' in time_text:
            years = int(re.search(r'\d+', time_text).group() or 0)
            post_time = now - timedelta(days=years * 365)
        else:
            # Default to current time if pattern not recognized
            post_time = now
        
        return int(post_time.timestamp() * 1000)