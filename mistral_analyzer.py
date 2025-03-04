"""
Integration with Dolphin Mistral Free via Open Router for data analysis.
"""

import requests
import json
import logging
from typing import List, Dict, Any, Union
import time
from config import OPEN_ROUTER_API_KEY, OPEN_ROUTER_ENDPOINT, OPEN_ROUTER_MODEL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_with_mistral(text: str, prompt: str) -> Dict[str, Any]:
    """
    Analyze text using Dolphin Mistral Free via Open Router
    
    Args:
        text: Text to analyze
        prompt: Specific instruction for the analysis
        
    Returns:
        Dictionary with analysis results
    """
    headers = {
        "Authorization": f"Bearer {OPEN_ROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Construct the payload
    payload = {
        "model": OPEN_ROUTER_MODEL,
        "messages": [
            {
                "role": "system", 
                "content": "You are an expert data analyst specializing in identifying business milestones. Extract key information accurately and concisely."
            },
            {
                "role": "user", 
                "content": f"{prompt}\n\nHERE IS THE TEXT:\n{text}"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 300
    }
    
    try:
        logger.info("Sending request to Dolphin Mistral Free")
        response = requests.post(OPEN_ROUTER_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            logger.info("Successfully received analysis from Mistral")
            return {"status": "success", "content": content}
        else:
            logger.error(f"Unexpected response format: {result}")
            return {"status": "error", "content": "Unexpected response format"}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while calling OpenRouter API: {str(e)}")
        return {"status": "error", "content": str(e)}

def analyze_business(business: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze basic business information
    
    Args:
        business: Dictionary with business information from Google Maps
        
    Returns:
        Dictionary with analysis
    """
    business_text = f"Business Name: {business.get('name', '')}\n"
    business_text += f"Address: {business.get('address', '')}\n"
    business_text += f"Website: {business.get('website', '')}\n"
    business_text += f"Business Type: {business.get('business_type', '')}"
    
    prompt = "Please analyze this business and provide a brief description of what they do based on the information provided."
    
    result = analyze_with_mistral(business_text, prompt)
    
    return {
        "business_id": business.get('place_id', ''),
        "business_name": business.get('name', ''),
        "description": result.get('content', '')
    }

def analyze_linkedin_posts(business_name: str, posts: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Analyze LinkedIn posts for milestone information
    
    Args:
        business_name: Name of the business
        posts: List of dictionaries containing LinkedIn posts
        
    Returns:
        Dictionary with milestone analysis
    """
    if not posts:
        return {"status": "no_data", "milestone_description": ""}
    
    # Combine posts into a single text for analysis
    combined_text = f"Business: {business_name}\n\n"
    for i, post in enumerate(posts, 1):
        combined_text += f"Post {i}: {post.get('text', '')}\n"
        combined_text += f"Date: {post.get('date', 'Unknown')}\n\n"
    
    prompt = """Please analyze these LinkedIn posts and identify any major business milestones.
    Extract the following information:
    1. Type of milestone (funding round, expansion, product launch, award, etc.)
    2. When it happened (date if available)
    3. Key details of the milestone
    
    Format your response as a concise 1-2 sentence description of the most significant milestone."""
    
    result = analyze_with_mistral(combined_text, prompt)
    
    return {
        "status": result.get('status', 'unknown'),
        "milestone_description": result.get('content', '')
    }

def analyze_search_results(business_name: str, search_results: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Analyze Google search results for milestone information
    
    Args:
        business_name: Name of the business
        search_results: List of dictionaries containing search results
        
    Returns:
        Dictionary with milestone analysis
    """
    if not search_results:
        return {"status": "no_data", "milestone_description": ""}
    
    # Combine search results into a single text for analysis
    combined_text = f"Business: {business_name}\n\n"
    for i, result in enumerate(search_results, 1):
        combined_text += f"Result {i} - Title: {result.get('title', '')}\n"
        combined_text += f"Snippet: {result.get('snippet', '')}\n"
        combined_text += f"Source: {result.get('link', '')}\n\n"
    
    prompt = """Please analyze these search results and identify any major business milestones.
    Extract the following information:
    1. Type of milestone (funding round, expansion, product launch, award, etc.)
    2. When it happened (date if available)
    3. Key details of the milestone
    
    Format your response as a concise 1-2 sentence description of the most significant milestone."""
    
    result = analyze_with_mistral(combined_text, prompt)
    
    return {
        "status": result.get('status', 'unknown'),
        "milestone_description": result.get('content', '')
    }

def combine_milestone_analyses(linkedin_analysis: Dict[str, Any], search_analysis: Dict[str, Any]) -> str:
    """
    Combine milestone analyses from different sources
    
    Args:
        linkedin_analysis: Analysis from LinkedIn posts
        search_analysis: Analysis from Google search results
        
    Returns:
        Combined milestone description
    """
    combined_text = ""
    
    if linkedin_analysis.get("status") == "success":
        combined_text += linkedin_analysis.get("milestone_description", "")
    
    if search_analysis.get("status") == "success":
        search_milestone = search_analysis.get("milestone_description", "")
        if combined_text and search_milestone:
            # Use Mistral to combine the analyses
            prompt = f"""You have two milestone descriptions for the same company:
            
            Description 1: {combined_text}
            Description 2: {search_milestone}
            
            Please combine these into a single, concise, and comprehensive 1-2 sentence milestone description."""
            
            result = analyze_with_mistral(f"{combined_text}\n\n{search_milestone}", prompt)
            if result.get("status") == "success":
                combined_text = result.get("content", combined_text)
        elif not combined_text:
            combined_text = search_milestone
    
    return combined_text if combined_text else "No significant milestones identified."