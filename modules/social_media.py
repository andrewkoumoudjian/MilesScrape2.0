import tweepy
import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import active_config as config

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self):
        """Initialize Twitter API client"""
        try:
            auth = tweepy.OAuthHandler(
                config.TWITTER_CONSUMER_KEY,
                config.TWITTER_CONSUMER_SECRET
            )
            auth.set_access_token(
                config.TWITTER_ACCESS_TOKEN,
                config.TWITTER_ACCESS_TOKEN_SECRET
            )
            self.api = tweepy.API(auth, wait_on_rate_limit=True)
            self.api.verify_credentials()
            logger.info("Twitter API authentication successful")
        except Exception as e:
            logger.error(f"Twitter API authentication failed: {str(e)}")
            self.api = None
            
    def search_posts(self, query, count=100, lang="en", result_type="recent"):
        """
        Search for tweets matching the query
        
        Args:
            query (str): Search query
            count (int): Number of tweets to retrieve
            lang (str): Language filter
            result_type (str): Type of results (recent, popular, mixed)
            
        Returns:
            list: List of processed tweets
        """
        if not self.api:
            logger.error("Twitter API client not initialized")
            return []
            
        try:
            tweets = self.api.search_tweets(
                q=query,
                count=count,
                lang=lang,
                result_type=result_type,
                tweet_mode="extended"
            )
            
            return [self._process_tweet(tweet) for tweet in tweets]
        except Exception as e:
            logger.error(f"Error searching Twitter: {str(e)}")
            return []
    
    def _process_tweet(self, tweet):
        """Process a tweet object into a standardized format"""
        # Get the full text (handle retweets correctly)
        if hasattr(tweet, 'retweeted_status'):
            text = tweet.retweeted_status.full_text
        else:
            text = tweet.full_text
            
        # Extract user information
        user = tweet.user
        
        return {
            "id": tweet.id_str,
            "text": text,
            "created_at": tweet.created_at,
            "user": {
                "id": user.id_str,
                "name": user.name,
                "screen_name": user.screen_name,
                "description": user.description,
                "location": user.location,
                "followers_count": user.followers_count
            },
            "source": "twitter",
            "url": f"https://twitter.com/{user.screen_name}/status/{tweet.id_str}"
        }


class LinkedInScraper:
    def __init__(self):
        """Initialize LinkedIn scraper using Selenium"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {str(e)}")
            self.driver = None
    
    def __del__(self):
        """Clean up WebDriver resources"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
    
    def login(self, email, password):
        """Login to LinkedIn (required for most scraping)"""
        if not self.driver:
            logger.error("WebDriver not initialized")
            return False
        
        try:
            self.driver.get("https://www.linkedin.com/login")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            self.driver.find_element(By.ID, "username").send_keys(email)
            self.driver.find_element(By.ID, "password").send_keys(password)
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
            # Wait for login to complete
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".feed-identity-module"))
            )
            
            logger.info("LinkedIn login successful")
            return True
        except Exception as e:
            logger.error(f"LinkedIn login failed: {str(e)}")
            return False
    
    def search_posts(self, query, count=20):
        """
        Search for LinkedIn posts matching the query
        
        Args:
            query (str): Search query
            count (int): Maximum number of posts to retrieve
            
        Returns:
            list: List of processed LinkedIn posts
        """
        if not self.driver:
            logger.error("WebDriver not initialized")
            return []
        
        posts = []
        try:
            # Encode query for URL
            encoded_query = query.replace(' ', '%20')
            self.driver.get(f"https://www.linkedin.com/search/results/content/?keywords={encoded_query}&origin=GLOBAL_SEARCH_HEADER")
            
            # Wait for search results
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".search-results__list"))
            )
            
            # Scroll down to load more results if needed
            current_height = 0
            posts_found = 0
            
            while posts_found < count and posts_found < 100:  # LinkedIn typically limits to ~100 results
                # Scroll down
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(1)  # Allow time for content to load
                
                # Check if we've reached the bottom
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == current_height:
                    break
                current_height = new_height
                
                # Find all post elements that we haven't processed yet
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, ".search-result__occluded-item")
                
                for i in range(posts_found, min(len(post_elements), count)):
                    try:
                        post = self._process_linkedin_post(post_elements[i])
                        if post:
                            posts.append(post)
                            posts_found += 1
                    except Exception as e:
                        logger.error(f"Error processing LinkedIn post: {str(e)}")
                        continue
                        
                # Break if we're not finding any new posts
                if posts_found == 0 and len(post_elements) == 0:
                    break
            
            logger.info(f"Found {len(posts)} LinkedIn posts matching query")
            return posts
            
        except Exception as e:
            logger.error(f"Error searching LinkedIn: {str(e)}")
            return []
    
    def _process_linkedin_post(self, element):
        """Process a LinkedIn post element into a standardized format"""
        try:
            # Extract post content
            try:
                text_element = element.find_element(By.CSS_SELECTOR, ".search-result__snippet")
                text = text_element.text
            except NoSuchElementException:
                text = ""
            
            # Extract author information
            try:
                author_element = element.find_element(By.CSS_SELECTOR, ".app-aware-link")
                author_name = author_element.text
                profile_url = author_element.get_attribute("href")
            except NoSuchElementException:
                author_name = "Unknown"
                profile_url = ""
                
            # Extract post date
            try:
                date_element = element.find_element(By.CSS_SELECTOR, ".search-result__time-ago")
                date_text = date_element.text  # Like "2 days ago"
                created_at = self._parse_relative_date(date_text)
            except NoSuchElementException:
                created_at = datetime.now()
                
            # Extract post URL
            try:
                url_element = element.find_element(By.CSS_SELECTOR, ".app-aware-link.search-result__result-link")
                url = url_element.get_attribute("href")
            except NoSuchElementException:
                url = ""
                
            return {
                "text": text,
                "created_at": created_at,
                "user": {
                    "name": author_name,
                    "profile_url": profile_url,
                    "description": ""  # Would need to visit profile to get this
                },
                "source": "linkedin",
                "url": url
            }
        except Exception as e:
            logger.error(f"Error processing LinkedIn post element: {str(e)}")
            return None
    
    def _parse_relative_date(self, date_text):
        """Convert LinkedIn relative date (e.g., '2 days ago') to datetime"""
        now = datetime.now()
        
        if "minute" in date_text:
            minutes = int(''.join(filter(str.isdigit, date_text)))
            return now - timedelta(minutes=minutes)
        elif "hour" in date_text:
            hours = int(''.join(filter(str.isdigit, date_text)))
            return now - timedelta(hours=hours)
        elif "day" in date_text:
            days = int(''.join(filter(str.isdigit, date_text)))
            return now - timedelta(days=days)
        elif "week" in date_text:
            weeks = int(''.join(filter(str.isdigit, date_text)))
            return now - timedelta(weeks=weeks)
        elif "month" in date_text:
            months = int(''.join(filter(str.isdigit, date_text)))
            return now - timedelta(days=months*30)  # Approximation
        else:
            return now  # Default to now if we can't parse


class SocialMediaManager:
    """Manager to handle data collection from multiple social media platforms"""
    
    def __init__(self):
        self.twitter = TwitterClient() if 'twitter' in config.SEARCH_PLATFORMS else None
        self.linkedin = LinkedInScraper() if 'linkedin' in config.SEARCH_PLATFORMS else None
        
    def search_all_platforms(self, query, count_per_platform=50):
        """Search across all configured social media platforms"""
        results = []
        
        if self.twitter:
            twitter_results = self.twitter.search_posts(query, count=count_per_platform)
            results.extend(twitter_results)
            
        if self.linkedin:
            linkedin_results = self.linkedin.search_posts(query, count=count_per_platform)
            results.extend(linkedin_results)
            
        # Sort by date (newest first)
        results.sort(key=lambda x: x.get('created_at', datetime.now()), reverse=True)
        
        return results