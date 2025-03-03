"""Analysis module for the Milestone Lead Generator using OpenRouter."""

import json
import logging
import requests
from typing import Dict, Any, List, Tuple
import time

from config import (
    OPENROUTER_API_KEY,
    MILESTONE_KEYWORDS,
    POSITIVE_SENTIMENT_THRESHOLD
)

logger = logging.getLogger(__name__)

class OpenRouterAnalyzer:
    """Uses OpenRouter API to analyze post content."""
    
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/milestone-lead-generator"  # Your app's URL for tracking
        }
        # Using Claude Instant for efficiency and cost savings
        self.model = "anthropic/claude-instant-v1"
    
    def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text, return score between 0 (negative) and 1 (positive)."""
        try:
            prompt = f"""Analyze the sentiment of the following text. Output only a number between 0 and 1 where 0 is extremely negative, 0.5 is neutral, and 1 is extremely positive. No explanation needed, just the number.

Text: {text}

Sentiment score (0-1):"""
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # Low temperature for consistency
                }
            )
            
            if response.status_code == 200:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                # Extract the sentiment score from the response
                try:
                    # Find the number in the response
                    import re
                    score_match = re.search(r'(\d+\.\d+|\d+)', content)
                    if score_match:
                        score = float(score_match.group(1))
                        # Ensure score is between 0 and 1
                        score = max(0.0, min(1.0, score))
                        return score
                except Exception as e:
                    logger.error(f"Error extracting sentiment score: {str(e)}")
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                
            return 0.5  # Default to neutral if analysis fails
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return 0.5
    
    def identify_milestone_details(self, text: str) -> Dict[str, Any]:
        """Identify specific milestone details from text."""
        try:
            prompt = f"""Analyze the following text and extract milestone information about a business.
            
Text: {text}

Please provide the following information in JSON format:
{{
  "has_milestone": true/false,
  "milestone_type": "funding/expansion/award/anniversary/acquisition/other",
  "milestone_description": "brief description of the milestone",
  "relevance_score": number between 0-10 indicating how significant this milestone is
}}

Return only valid JSON with no explanation:"""
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }
            )
            
            if response.status_code == 200:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON response: {content}")
                    return {
                        "has_milestone": False,
                        "milestone_type": "unknown",
                        "milestone_description": "",
                        "relevance_score": 0
                    }
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return {
                    "has_milestone": False,
                    "milestone_type": "unknown", 
                    "milestone_description": "",
                    "relevance_score": 0
                }
                
        except Exception as e:
            logger.error(f"Error identifying milestone details: {str(e)}")
            return {
                "has_milestone": False,
                "milestone_type": "unknown",
                "milestone_description": "",
                "relevance_score": 0
            }
    
    def analyze_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a post for sentiment and milestone details."""
        # Combine title and text for better analysis if both are available
        text = post.get("title", "")
        if "text" in post and post["text"]:
            if text:
                text += " - "
            text += post["text"]
        
        # Skip empty posts
        if not text:
            return {**post, "sentiment": 0.5, "milestone_details": {
                "has_milestone": False,
                "milestone_type": "unknown",
                "milestone_description": "",
                "relevance_score": 0
            }}
        
        # Analyze sentiment
        sentiment = self.analyze_sentiment(text)
        
        # If post already mentions milestone keywords or has good sentiment, analyze deeper
        if post.get("contains_milestone_keyword", False) or sentiment > POSITIVE_SENTIMENT_THRESHOLD:
            milestone_details = self.identify_milestone_details(text)
        else:
            milestone_details = {
                "has_milestone": False,
                "milestone_type": "unknown",
                "milestone_description": "",
                "relevance_score": 0
            }
        
        # Add the analysis results to the post
        analyzed_post = {
            **post,
            "sentiment": sentiment,
            "milestone_details": milestone_details
        }
        
        return analyzed_post
    
    def analyze_posts(self, posts: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Analyze a list of posts and return both all analyzed posts and high-value leads."""
        analyzed_posts = []
        high_value_leads = []
        
        for post in posts:
            # Analyze post
            analyzed_post = self.analyze_post(post)
            analyzed_posts.append(analyzed_post)
            
            # Determine if this is a high-value lead
            sentiment = analyzed_post.get("sentiment", 0)
            milestone_details = analyzed_post.get("milestone_details", {})
            
            is_high_value = (
                sentiment > POSITIVE_SENTIMENT_THRESHOLD or
                milestone_details.get("has_milestone", False) or
                analyzed_post.get("contains_milestone_keyword", False)
            )
            
            if is_high_value:
                high_value_leads.append(analyzed_post)
            
            # Respect API rate limits
            time.sleep(1)
        
        return analyzed_posts, high_value_leads