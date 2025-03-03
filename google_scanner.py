"""Google Search scanning module for the Milestone Lead Generator."""

import json
import logging
from datetime import datetime, timedelta
import requests
from requests.exceptions import RequestException
import time
from typing import List, Dict, Any
import re

from config import (
    GOOGLE_API_KEY,
    GOOGLE_CSE_ID,
    MILESTONE_KEYWORDS,
)

logger = logging.getLogger(__name__)

class GoogleScanner:
    """Scanner for business milestone mentions using Google Search."""
    
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    def search_for_milestones(self, days_back=30, limit=100) -> List[Dict[str, Any]]:
        """Search for recent business milestone mentions."""
        milestone_posts = []
        posts_found = 0
        
        # Calculate date range for filtering
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        date_restrict = f"d{days_back}"  # Last X days
        
        # Search for each milestone keyword
        for keyword in MILESTONE_KEYWORDS:
            if posts_found >= limit:
                break
                
            try:
                # Build search query focusing on business milestones
                query = f'"{keyword}" business'
                
                # Set up search parameters
                params = {
                    'key': self.api_key,
                    'cx': self.cse_id,
                    'q': query,
                    'dateRestrict': date_restrict,
                    'num': min(10, limit - posts_found),  # Max 10 results per request
                }
                
                response = requests.get(self.base_url, params=params)
                
                if response.status_code == 200:
                    search_results = response.json()
                    items = search_results.get('items', [])
                    
                    for item in items:
                        # Extract company name from title or snippet
                        company_name = self._extract_company_name(item)
                        
                        post = {
                            'id': item.get('cacheId', item.get('link', '')[-20:]),
                            'title': item.get('title', ''),
                            'text': item.get('snippet', ''),
                            'url': item.get('link', ''),
                            'timestamp': self._extract_date(item),
                            'company_name': company_name,
                            'source': 'Google',
                            'contains_milestone_keyword': True,
                            'milestone_keyword': keyword,
                        }
                        
                        milestone_posts.append(post)
                        posts_found += 1
                        
                        if posts_found >= limit:
                            break
                else:
                    logger.error(f"Google API error: {response.status_code} - {response.text}")
            
            except RequestException as e:
                logger.error(f"Error searching Google: {str(e)}")
            
            # Respect API rate limits
            time.sleep(2)
        
        return milestone_posts
    
    def _extract_company_name(self, search_item: Dict[str, Any]) -> str:
        """Extract company name from search result."""
        # Try to extract from title using common patterns
        title = search_item.get('title', '')
        
        # Pattern 1: "Company Name Announces..."
        announces_match = re.search(r'^([^|:]+?)(?:\s+Announces|\s+Achieves|\s+Celebrates)', title)
        if announces_match:
            return announces_match.group(1).strip()
        
        # Pattern 2: "Company Name | Something"
        pipe_split = title.split('|')
        if len(pipe_split) > 1:
            return pipe_split[0].strip()
        
        # Pattern 3: Check in snippet for company patterns
        snippet = search_item.get('snippet', '')
        company_patterns = [
            r'([A-Z][A-Za-z0-9\s,\.]+?),?\s+a\s+(?:leading|premier|global)',
            r'([A-Z][A-Za-z0-9\s,\.]+?),?\s+(?:announced|celebrated|achieved)',
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, snippet)
            if match:
                return match.group(1).strip()
        
        # Default to domain name from URL as fallback
        url = search_item.get('link', '')
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if domain_match:
            domain = domain_match.group(1)
            # Remove TLD
            domain_parts = domain.split('.')
            if len(domain_parts) >= 2:
                return domain_parts[-2].capitalize()
        
        return "Unknown Company"
    
    def _extract_date(self, search_item: Dict[str, Any]) -> int:
        """Extract date from search result if available, or estimate it."""
        # Some search results have metadata with date
        if 'pagemap' in search_item and 'metatags' in search_item['pagemap']:
            metatags = search_item['pagemap']['metatags'][0]
            date_candidates = [
                metatags.get('article:published_time'),
                metatags.get('date'),
                metatags.get('og:article:published_time')
            ]
            
            for date_str in date_candidates:
                if date_str:
                    try:
                        # Try to parse ISO format date
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        return int(dt.timestamp() * 1000)
                    except ValueError:
                        pass
        
        # If we can't find a date, use a reasonable estimate based on the search restriction
        # (halfway between now and the days_back parameter)
        now = datetime.now()
        estimated_date = now - timedelta(days=15)  # Rough estimate, middle of the 30-day window
        return int(estimated_date.timestamp() * 1000)