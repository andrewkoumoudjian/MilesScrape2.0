"""
Google Maps Places API integration for finding businesses.
"""

import requests
import time
import random
from typing import List, Dict, Any
import logging
from config import GOOGLE_MAPS_API_KEY, MIN_DELAY, MAX_DELAY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_businesses(location: str, business_type: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieve businesses from Google Maps Places API based on location and business type.
    
    Args:
        location: Location to search (e.g., "San Francisco")
        business_type: Type of business (e.g., "tech startup")
        max_results: Maximum number of results to retrieve
        
    Returns:
        List of business dictionaries with name, address, website, etc.
    """
    logger.info(f"Searching for {business_type} businesses in {location}")
    
    # Format query for URL
    query = f"{business_type} in {location}".replace(' ', '+')
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&key={GOOGLE_MAPS_API_KEY}"
    
    all_businesses = []
    next_page_token = None
    
    try:
        # First request
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        businesses = data.get('results', [])
        all_businesses.extend(businesses)
        next_page_token = data.get('next_page_token')
        
        # Continue if there are more pages and we haven't reached max results
        while next_page_token and len(all_businesses) < max_results:
            # Google requires a delay before using the next_page_token
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
            next_url = f"{url}&pagetoken={next_page_token}"
            response = requests.get(next_url)
            response.raise_for_status()
            data = response.json()
            
            businesses = data.get('results', [])
            all_businesses.extend(businesses)
            next_page_token = data.get('next_page_token')
        
        # Limit to max_results
        all_businesses = all_businesses[:max_results]
        
        # Extract required fields
        processed_businesses = []
        for business in all_businesses:
            processed_business = {
                'name': business.get('name', ''),
                'address': business.get('formatted_address', ''),
                'place_id': business.get('place_id', ''),
                'business_type': business_type,
                'location': location
            }
            
            # Get more details including website if available
            if business.get('place_id'):
                details = get_place_details(business['place_id'])
                processed_business.update(details)
                
            processed_businesses.append(processed_business)
            
        logger.info(f"Found {len(processed_businesses)} businesses")
        return processed_businesses
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching businesses: {str(e)}")
        return []

def get_place_details(place_id: str) -> Dict[str, Any]:
    """
    Get additional details for a place using its place_id
    
    Args:
        place_id: Google Maps Place ID
        
    Returns:
        Dictionary of place details including website, phone, etc.
    """
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=website,formatted_phone_number,international_phone_number&key={GOOGLE_MAPS_API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'OK':
            result = data.get('result', {})
            return {
                'website': result.get('website', ''),
                'phone': result.get('formatted_phone_number', '')
            }
        else:
            logger.warning(f"Failed to get details for place_id {place_id}: {data.get('status')}")
            return {}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching place details: {str(e)}")
        return {}