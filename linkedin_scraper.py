"""
LinkedIn scraper for collecting company milestones from public profiles.
"""

import time
import random
import logging
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from config import USER_AGENTS, MIN_DELAY, MAX_DELAY, MILESTONE_KEYWORDS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self):
        self.driver = None
        
    def initialize_driver(self):
        """Initialize Selenium WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        
        # Initialize Chrome WebDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            
    def find_company_linkedin(self, company_name: str, company_website: str = None) -> Optional[str]:
        """
        Find LinkedIn company page URL
        
        Args:
            company_name: Name of the company
            company_website: Company website if available
            
        Returns:
            LinkedIn company page URL or None if not found
        """
        if not self.driver:
            self.initialize_driver()
            
        # Search for company LinkedIn profile via Google
        search_query = f"{company_name} LinkedIn company"
        if company_website:
            search_query += f" site:{company_website}"
            
        google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        
        try:
            logger.info(f"Searching for LinkedIn profile for {company_name}")
            self.driver.get(google_url)
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
            # Find search results containing LinkedIn company URLs
            links = self.driver.find_elements(By.CSS_SELECTOR, "a")
            linkedin_urls = [link.get_attribute("href") for link in links 
                           if link.get_attribute("href") and "linkedin.com/company" in link.get_attribute("href")]
            
            if linkedin_urls:
                logger.info(f"Found LinkedIn page for {company_name}: {linkedin_urls[0]}")
                return linkedin_urls[0]
                
            logger.warning(f"LinkedIn page for {company_name} not found")
            return None
        
        except Exception as e:
            logger.error(f"Error finding LinkedIn page for {company_name}: {str(e)}")
            return None
    
    def scrape_linkedin_posts(self, linkedin_url: str) -> List[Dict[str, str]]:
        """
        Scrape posts from LinkedIn company page
        
        Args:
            linkedin_url: LinkedIn company page URL
            
        Returns:
            List of post dictionaries with text, date, and engagement metrics
        """
        if not self.driver:
            self.initialize_driver()
            
        if not linkedin_url:
            logger.warning("No LinkedIn URL provided for scraping")
            return []
            
        posts_url = f"{linkedin_url}/posts" if not linkedin_url.endswith("/posts") else linkedin_url
        
        try:
            logger.info(f"Scraping posts from {posts_url}")
            self.driver.get(posts_url)
            
            # Wait for posts to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            
            # Scroll to load more posts (optional)
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # Find all post elements
            post_elements = self.driver.find_elements(By.TAG_NAME, "article")
            
            posts = []
            for post in post_elements:
                try:
                    # Extract post text
                    post_text_elements = post.find_elements(By.CSS_SELECTOR, "span.break-words")
                    post_text = " ".join([elem.text for elem in post_text_elements if elem.text])
                    
                    # Extract date if available
                    try:
                        post_date = post.find_element(By.CSS_SELECTOR, "span.visually-hidden").text
                    except NoSuchElementException:
                        post_date = "Unknown date"
                    
                    # Only include posts that might contain milestone information
                    if any(keyword.lower() in post_text.lower() for keyword in MILESTONE_KEYWORDS):
                        posts.append({
                            "text": post_text,
                            "date": post_date,
                            "source": posts_url
                        })
                except Exception as e:
                    logger.error(f"Error processing post: {str(e)}")
                    continue
            
            logger.info(f"Found {len(posts)} milestone-related posts")
            return posts
        
        except TimeoutException:
            logger.warning(f"Timeout waiting for posts to load at {posts_url}")
            return []
        except Exception as e:
            logger.error(f"Error scraping LinkedIn posts: {str(e)}")
            return []
    
    def find_company_owner(self, linkedin_url: str) -> Dict[str, str]:
        """
        Attempt to find company owner/founder profile on LinkedIn
        
        Args:
            linkedin_url: LinkedIn company page URL
            
        Returns:
            Dictionary with owner name and profile link
        """
        if not self.driver:
            self.initialize_driver()
            
        if not linkedin_url:
            return {"name": "", "profile_url": ""}
            
        about_url = f"{linkedin_url}/about" if not linkedin_url.endswith("/about") else linkedin_url
        
        try:
            logger.info(f"Looking for company owner at {about_url}")
            self.driver.get(about_url)
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
            # Try to find leadership section
            leader_elements = self.driver.find_elements(By.XPATH, 
                "//dt[contains(text(), 'CEO') or contains(text(), 'Founder') or contains(text(), 'Owner')]/following-sibling::dd[1]/a")
            
            if leader_elements:
                leader = leader_elements[0]
                name = leader.text
                profile_url = leader.get_attribute("href")
                logger.info(f"Found company leader: {name}")
                return {
                    "name": name,
                    "profile_url": profile_url
                }
            
            logger.warning("No company owner found on LinkedIn page")
            return {"name": "", "profile_url": ""}
            
        except Exception as e:
            logger.error(f"Error finding company owner: {str(e)}")
            return {"name": "", "profile_url": ""}