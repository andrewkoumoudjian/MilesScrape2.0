"""LinkedIn scanning module for the Milestone Lead Generator."""

import json
import logging
from datetime import datetime, timedelta
import requests
from requests.exceptions import RequestException
from urllib.parse import urlencode
import time

from config import (
    LINKEDIN_ACCESS_TOKEN,
    MILESTONE_KEYWORDS,
)

logger = logging.getLogger(__name__)

class LinkedInScanner:
    """Scanner for LinkedIn posts and company information."""
    
    def __init__(self):
        self.access_token = LINKEDIN_ACCESS_TOKEN
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
    
    def search_companies(self, keywords, limit=25):
        """Search for companies using keywords."""
        try:
            # LinkedIn Organization Search API endpoint
            search_endpoint = f"{self.base_url}/organizationSearch"
            
            # Combine milestone keywords for search
            query = " OR ".join(keywords)
            
            params = {
                "q": "search",
                "keywords": query,
                "count": limit,
            }
            
            response = requests.get(
                search_endpoint, 
                headers=self.headers, 
                params=params
            )
            
            if response.status_code == 200:
                return response.json().get("elements", [])
            else:
                logger.error(f"LinkedIn API error: {response.status_code} - {response.text}")
                return []
                
        except RequestException as e:
            logger.error(f"Error searching LinkedIn companies: {str(e)}")
            return []
    
    def get_company_updates(self, organization_id, limit=10):
        """Get recent updates from a specific company."""
        try:
            # LinkedIn Organization Updates API endpoint
            updates_endpoint = f"{self.base_url}/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity=urn:li:organization:{organization_id}"
            
            response = requests.get(
                updates_endpoint, 
                headers=self.headers
            )
            
            if response.status_code == 200:
                # Get the share URNs from the statistics
                share_stats = response.json().get("elements", [])
                share_urns = [stat.get("organizationalEntityShare") for stat in share_stats][:limit]
                
                # Now get the actual content for each share
                posts = []
                for share_urn in share_urns:
                    share_id = share_urn.split(":")[-1]
                    share_data = self.get_share_content(share_id)
                    if share_data:
                        posts.append(share_data)
                
                return posts
            else:
                logger.error(f"LinkedIn API error: {response.status_code} - {response.text}")
                return []
                
        except RequestException as e:
            logger.error(f"Error getting company updates: {str(e)}")
            return []
    
    def get_share_content(self, share_id):
        """Get the content of a specific share."""
        try:
            # LinkedIn Share API endpoint
            share_endpoint = f"{self.base_url}/shares/{share_id}"
            
            response = requests.get(
                share_endpoint, 
                headers=self.headers
            )
            
            if response.status_code == 200:
                share_data = response.json()
                # Extract relevant information
                content = {
                    "id": share_id,
                    "text": share_data.get("text", {}).get("text", ""),
                    "timestamp": share_data.get("created", {}).get("time", 0),
                    "author": share_data.get("author", ""),
                    "source": "LinkedIn",
                    "url": f"https://www.linkedin.com/feed/update/urn:li:share:{share_id}"
                }
                return content
            else:
                logger.error(f"LinkedIn API error: {response.status_code} - {response.text}")
                return None
                
        except RequestException as e:
            logger.error(f"Error getting share content: {str(e)}")
            return None
    
    def scan_for_milestone_posts(self, days_back=30, limit_per_company=5):
        """Scan LinkedIn for milestone-related posts."""
        # Get companies that match our milestone keywords
        companies = self.search_companies(MILESTONE_KEYWORDS)
        all_milestone_posts = []
        
        for company in companies:
            company_id = company.get("id")
            company_name = company.get("name", "Unknown Company")
            
            logger.info(f"Scanning posts for company: {company_name}")
            
            # Get recent updates from this company
            company_posts = self.get_company_updates(company_id, limit=limit_per_company)
            
            # Add company information to each post
            for post in company_posts:
                post["company_name"] = company_name
                post["company_id"] = company_id
                
                # Check if the post contains milestone keywords
                if any(keyword.lower() in post.get("text", "").lower() for keyword in MILESTONE_KEYWORDS):
                    post["contains_milestone_keyword"] = True
                else:
                    post["contains_milestone_keyword"] = False
                
                all_milestone_posts.append(post)
                
            # Respect API rate limits
            time.sleep(1)
            
        return all_milestone_posts