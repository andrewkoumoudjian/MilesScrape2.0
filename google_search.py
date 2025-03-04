"""
Google Search scraper for finding company milestone information.
"""

import requests
import time
import random
import re
import logging
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from config import USER_AGENTS, MIN_DELAY, MAX_DELAY, MILESTONE_KEYWORDS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def search_company_milestones(company_name: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Search Google for company milestone information
    
    Args:
        company_name: Name of the company
        num_results: Number of search results to process
        
    Returns:
        List of dictionaries containing milestone information
    """
    # Create specific search queries for milestones
    queries = [
        f"{company_name} funding round",
        f"{company_name} milestone announcement",
        f"{company_name} growth expansion",
        f"{company_name} series a b c funding",
        f"{company_name} achievement award"
    ]
    
    all_results = []
    
    for query in queries:
        try:
            logger.info(f"Searching for: {query}")
            
            # Format query for Google search
            formatted_query = query.replace(' ', '+')
            url = f"https://www.google.com/search?q={formatted_query}&num={num_results}"
            
            # Random user agent
            headers = {"User-Agent": random.choice(USER_AGENTS)}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract search results
            search_results = []
            
            # Look for result divs - Google's structure may change, adapt as needed
            results = soup.find_all("div", class_=["g", "tF2Cxc"])
            
            for result in results:
                # Extract title
                title_elem = result.find("h3")
                title = title_elem.text if title_elem else ""
                
                # Extract URL
                link_elem = result.find("a")
                link = link_elem.get("href") if link_elem else ""
                
                # Extract snippet
                snippet_elem = result.find("div", class_=["VwiC3b", "yXK7lf", "MUxGbd", "yDYNvb", "lyLwlc", "lEBKkf"])
                snippet = snippet_elem.text if snippet_elem else ""
                
                # Check if result might contain milestone information
                contains_milestone = any(keyword.lower() in (title + " " + snippet).lower() 
                                       for keyword in MILESTONE_KEYWORDS)
                
                if contains_milestone:
                    search_results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet,
                        "query": query
                    })
            
            logger.info(f"Found {len(search_results)} milestone-related results for query: {query}")
            all_results.extend(search_results)
            
            # Delay before next query to avoid rate limiting
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during search for {query}: {str(e)}")
            continue
    
    return all_results

def extract_milestone_dates(text: str) -> List[str]:
    """
    Extract potential dates from milestone text
    
    Args:
        text: Text to analyze
        
    Returns:
        List of potential dates found
    """
    # Regex patterns for date formats
    patterns = [
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}',  # January 1, 2023
        r'\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}',    # 1 January 2023
        r'\d{4}-\d{1,2}-\d{1,2}',                                                      # 2023-01-01
        r'\d{1,2}/\d{1,2}/\d{4}',                                                      # 01/01/2023
        r'\d{4}'                                                                       # Just the year 2023
    ]
    
    dates = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        dates.extend(matches)
    
    return dates