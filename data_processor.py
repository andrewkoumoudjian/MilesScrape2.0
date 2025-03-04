"""
Process and combine data from all sources.
"""

import logging
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_business_data(business: Dict[str, Any], 
                         linkedin_data: Dict[str, Any], 
                         search_data: List[Dict[str, str]], 
                         milestone_description: str) -> Dict[str, Any]:
    """
    Process and combine all data sources for a business
    
    Args:
        business: Dictionary with business information
        linkedin_data: Dictionary with LinkedIn information
        search_data: List of search result dictionaries
        milestone_description: Combined milestone description
        
    Returns:
        Dictionary with processed data
    """
    processed_data = {
        "company_name": business.get("name", ""),
        "company_address": business.get("address", ""),
        "company_website": business.get("website", ""),
        "company_owner": linkedin_data.get("owner", {}).get("name", ""),
        "linkedin_profile": linkedin_data.get("owner", {}).get("profile_url", ""),
        "linkedin_company_url": linkedin_data.get("company_url", ""),
        "milestone_description": milestone_description,
        "data_sources": {
            "google_maps": bool(business),
            "linkedin": bool(linkedin_data.get("posts")),
            "google_search": bool(search_data)
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return processed_data

def save_to_csv(data: List[Dict[str, Any]], filename: str = "company_milestones.csv") -> str:
    """
    Save processed data to CSV
    
    Args:
        data: List of dictionaries with processed data
        filename: Name of output CSV file
        
    Returns:
        Path to saved file
    """
    df = pd.DataFrame(data)
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    filepath = os.path.join("output", filename)
    
    df.to_csv(filepath, index=False)
    logger.info(f"Data saved to {filepath}")
    
    return filepath

def save_to_json(data: List[Dict[str, Any]], filename: str = "company_milestones.json") -> str:
    """
    Save processed data to JSON
    
    Args:
        data: List of dictionaries with processed data
        filename: Name of output JSON file
        
    Returns:
        Path to saved file
    """
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    filepath = os.path.join("output", filename)
    
    pd.DataFrame(data).to_json(filepath, orient="records", indent=4)