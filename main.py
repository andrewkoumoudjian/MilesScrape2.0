"""
Main entry point for the MilesScrape 2.0 application.
"""

import argparse
import asyncio
import logging
import time
from typing import List, Dict, Any
import json

from maps_api import get_businesses
from linkedin_scraper import LinkedInScraper
from google_search import search_company_milestones
from mistral_analyzer import analyze_business, analyze_linkedin_posts, analyze_search_results, combine_milestone_analyses
from data_processor import process_business_data
from storage import save_to_cloud_storage, list_bucket_files
from config import DEFAULT_LOCATION, DEFAULT_BUSINESS_TYPES, MAX_RESULTS_PER_QUERY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("milescrape.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def process_business(business: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single business to extract milestone information"""
    try:
        company_name = business.get('name', '')
        logger.info(f"Processing business: {company_name}")
        
        # Initialize LinkedIn scraper
        linkedin_scraper = LinkedInScraper()
        
        # Step 1: Find LinkedIn company page
        linkedin_url = linkedin_scraper.find_company_linkedin(company_name, business.get('website', ''))
        
        # Step 2: Scrape LinkedIn posts if company page found
        linkedin_posts = []
        owner_info = {"name": "", "profile_url": ""}
        if linkedin_url:
            linkedin_posts = linkedin_scraper.scrape_linkedin_posts(linkedin_url)
            owner_info = linkedin_scraper.find_company_owner(linkedin_url)
        
        # Step 3: Search Google for additional milestone information
        search_results = search_company_milestones(company_name)
        
        # Step 4: Analyze data with Dolphin Mistral Free
        linkedin_analysis = analyze_linkedin_posts(company_name, linkedin_posts)
        search_analysis = analyze_search_results(company_name, search_results)
        
        # Step 5: Combine milestone analyses
        milestone_description = combine_milestone_analyses(linkedin_analysis, search_analysis)
        
        # Close the LinkedIn scraper
        linkedin_scraper.close_driver()
        
        # Process and return the final data
        linkedin_data = {
            "company_url": linkedin_url,
            "posts": linkedin_posts,
            "owner": owner_info
        }
        
        processed_data = process_business_data(
            business,
            linkedin_data,
            search_results,
            milestone_description
        )
        
        return processed_data
        
    except Exception as e:
        logger.error(f"Error processing business {business.get('name', '')}: {str(e)}")
        return {
            "company_name": business.get('name', ''),
            "error": str(e),
            "status": "failed"
        }

async def process_businesses(businesses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process multiple businesses concurrently"""
    tasks = [process_business(business) for business in businesses]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions
    processed_data = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Task exception: {str(result)}")
        else:
            processed_data.append(result)
    
    return processed_data

def run_scraper(location: str = DEFAULT_LOCATION, 
                business_types: List[str] = DEFAULT_BUSINESS_TYPES,
                max_results: int = MAX_RESULTS_PER_QUERY) -> List[Dict[str, Any]]:
    """Run the full scraping process"""
    
    all_businesses = []
    for business_type in business_types:
        businesses = get_businesses(location, business_type, max_results)
        all_businesses.extend(businesses)
    
    if not all_businesses:
        logger.warning(f"No businesses found for {business_types} in {location}")
        return []
    
    logger.info(f"Found {len(all_businesses)} businesses. Processing...")
    
    # Run the async processing
    loop = asyncio.get_event_loop()
    processed_data = loop.run_until_complete(process_businesses(all_businesses))
    
    # Save to Google Cloud Storage
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"milestone_data_{timestamp}.json"
    save_to_cloud_storage(processed_data, filename)
    
    return processed_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MilesScrape 2.0 - Business milestone scraper")
    parser.add_argument("--location", type=str, default=DEFAULT_LOCATION, help="Location to search for businesses")
    parser.add_argument("--business-type", type=str, nargs="*", default=DEFAULT_BUSINESS_TYPES, 
                        help="Types of businesses to search for")
    parser.add_argument("--max-results", type=int, default=MAX_RESULTS_PER_QUERY, 
                        help="Maximum number of results per business type")
    
    args = parser.parse_args()
    
    run_scraper(args.location, args.business_type, args.max_results)