"""Google Maps integration for location-based business searches."""

import logging
import time
import json
import os
from typing import List, Dict, Any
import requests
import googlemaps
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleMapsBusinessFinder:
    """Class to find and collect business information from Google Maps."""
    
    def __init__(self, api_key=None):
        """Initialize the Maps client."""
        self.api_key = api_key or os.environ.get('MAPS_API_KEY')
        if self.api_key:
            self.gmaps = googlemaps.Client(key=self.api_key)
        else:
            self.gmaps = None
            logger.warning("No Google Maps API key provided. Some features limited.")
    
    def search_businesses_by_keyword(self, keyword: str, location: str, 
                                   radius_meters: int = 5000, 
                                   language: str = 'fr', 
                                   max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for businesses using the Places API."""
        if not self.gmaps:
            logger.error("Google Maps client not initialized. Cannot search businesses.")
            return []
            
        all_businesses = []
        next_page_token = None
        
        try:
            # Initial search
            logger.info(f"Searching for '{keyword}' businesses near {location}")
            
            # Geocode the location first to get coordinates
            geocode_result = self.gmaps.geocode(location)
            
            if not geocode_result:
                logger.error(f"Could not geocode location: {location}")
                return []
                
            lat = geocode_result[0]['geometry']['location']['lat']
            lng = geocode_result[0]['geometry']['location']['lng']
            
            # Now search for businesses with the keyword
            places_result = self.gmaps.places_nearby(
                location=(lat, lng),
                radius=radius_meters,
                keyword=keyword,
                language=language
            )
            
            # Process results
            if 'results' in places_result:
                all_businesses.extend(places_result['results'])
                next_page_token = places_result.get('next_page_token')
                
                # Google requires a delay before using next_page_token
                if next_page_token:
                    time.sleep(2)
            
            # Get additional pages of results
            while next_page_token and len(all_businesses) < max_results:
                places_result = self.gmaps.places_nearby(
                    page_token=next_page_token
                )
                
                if 'results' in places_result:
                    all_businesses.extend(places_result['results'])
                    next_page_token = places_result.get('next_page_token')
                    
                    if next_page_token:
                        time.sleep(2)
                else:
                    break
                    
                if len(all_businesses) >= max_results:
                    break
            
            # Format the business data
            formatted_businesses = []
            for business in all_businesses[:max_results]:
                formatted_business = {
                    'name': business.get('name', ''),
                    'place_id': business.get('place_id', ''),
                    'address': business.get('vicinity', ''),
                    'location': {
                        'lat': business.get('geometry', {}).get('location', {}).get('lat', 0),
                        'lng': business.get('geometry', {}).get('location', {}).get('lng', 0)
                    },
                    'types': business.get('types', []),
                    'rating': business.get('rating', 0),
                    'user_ratings_total': business.get('user_ratings_total', 0),
                    'search_keyword': keyword,
                    'retrieved_at': datetime.now().isoformat()
                }
                
                formatted_businesses.append(formatted_business)
            
            logger.info(f"Found {len(formatted_businesses)} businesses matching '{keyword}' in {location}")
            return formatted_businesses
            
        except Exception as e:
            logger.error(f"Error searching for businesses: {str(e)}")
            return []
    
    def get_business_details(self, place_id: str) -> Dict[str, Any]:
        """Get detailed information about a business using its place_id."""
        if not self.gmaps:
            logger.error("Google Maps client not initialized. Cannot get business details.")
            return {}
            
        try:
            # Get place details
            place_details = self.gmaps.place(
                place_id=place_id,
                fields=['name', 'formatted_address', 'formatted_phone_number', 
                        'website', 'url', 'opening_hours', 'rating',
                        'reviews', 'photos', 'international_phone_number']
            )
            
            if 'result' not in place_details:
                logger.warning(f"No details found for place ID: {place_id}")
                return {}
            
            # Format the result
            result = place_details['result']
            
            # Get the website domain if available
            website = result.get('website', '')
            website_domain = website.replace('http://', '').replace('https://', '').split('/')[0] if website else ''
            
            business_details = {
                'name': result.get('name', ''),
                'place_id': place_id,
                'address': result.get('formatted_address', ''),
                'phone': result.get('formatted_phone_number', ''),
                'international_phone': result.get('international_phone_number', ''),
                'website': website,
                'website_domain': website_domain,
                'google_maps_url': result.get('url', ''),
                'rating': result.get('rating', 0),
                'retrieved_at': datetime.now().isoformat()
            }
            
            # Add opening hours if available
            if 'opening_hours' in result and 'weekday_text' in result['opening_hours']:
                business_details['opening_hours'] = result['opening_hours']['weekday_text']
            
            return business_details
            
        except Exception as e:
            logger.error(f"Error getting business details for {place_id}: {str(e)}")
            return {}
    
    def find_social_media_profiles(self, business_name: str, website_domain: str = None) -> Dict[str, str]:
        """Find social media profiles for a business."""
        social_media = {}
        
        if not website_domain:
            return social_media
            
        try:
            # Check for common social media links on website
            website_url = f"https://{website_domain}" if not website_domain.startswith(('http://', 'https://')) else website_domain
            
            try:
                response = requests.get(website_url, timeout=10)
                
                # Look for common social media links
                social_patterns = {
                    'linkedin': ['linkedin.com', 'company'],
                    'facebook': ['facebook.com', 'fb.com'],
                    'twitter': ['twitter.com', 'x.com'],
                    'instagram': ['instagram.com'],
                }
                
                for platform, patterns in social_patterns.items():
                    for pattern in patterns:
                        if pattern in response.text:
                            # This is a simple check - a real implementation would use regex to extract the actual URL
                            social_media[platform] = f"Found on website (detailed extraction not implemented)"
            
            except requests.RequestException:
                logger.warning(f"Could not fetch website content for {website_domain}")
        
        except Exception as e: ▋