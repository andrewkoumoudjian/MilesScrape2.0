import os
import requests
from utils.cache import cache_result
from config import active_config as config

class OpenRouterClient:
    """Client for interacting with OpenRouter API for NLP tasks"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or config.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
            
        self.base_url = "https://openrouter.ai/api/v1"
        
    @cache_result
    def analyze(self, text, task=None, model="anthropic/claude-3-opus:2023-01-01"):
        """
        General method to analyze text using OpenRouter
        
        Args:
            text (str): The text to analyze
            task (str, optional): The task type to include in the prompt
            model (str): The model to use for analysis
            
        Returns:
            dict: The analysis result
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Construct system message based on task
        if task:
            system_message = f"Your task is to {task}. Respond with a JSON object containing your analysis."
        else:
            system_message = "Analyze the following text. Respond with a JSON object containing your analysis."
            
        payload = {
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": text}
            ],
            "model": model,
            "response_format": {"type": "json_object"}
        }
            
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract the content from the response
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                # Try to parse the JSON response
                try:
                    import json
                    return json.loads(content)
                except:
                    return {"raw_response": content}
            else:
                return {"error": "No content in response"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def extract_keywords(self, text):
        """Extract keywords from a user prompt"""
        return self.analyze(
            text,
            task="extract the most important keywords for searching social media posts. Return a JSON with a 'keywords' array of strings.",
            model="anthropic/claude-3-haiku:2023-01-01"  # Using a smaller model for efficiency
        )
    
    def classify_milestone(self, text):
        """Determine if a post mentions a business milestone"""
        return self.analyze(
            text,
            task="determine if this text mentions a business milestone like funding, acquisition, product launch, or expansion. Return a JSON with 'is_milestone' (boolean) and 'milestone_type' (string) fields.",
            model="anthropic/claude-3-haiku:2023-01-01"
        )
    
    def extract_entities(self, text):
        """Extract named entities like company, person, location from text"""
        return self.analyze(
            text,
            task="extract named entities from this text. Return a JSON with fields for 'company', 'person', 'job_title', 'location', and 'industry'. Use null for any missing values.",
            model="anthropic/claude-3-sonnet:2023-01-01"
        )
    
    def determine_seniority(self, job_title):
        """Determine seniority level from job title"""
        return self.analyze(
            job_title,
            task="determine the seniority level from this job title. Return a JSON with a 'level' field containing exactly one of: 'executive', 'senior', 'mid', 'entry', or 'unknown'.",
            model="anthropic/claude-3-haiku:2023-01-01"
        )
    
    def estimate_company_size(self, company_description):
        """Estimate company size from description"""
        return self.analyze(
            company_description,
            task="estimate the company size (number of employees) from this description. Return a JSON with 'min_employees' and 'max_employees' as integer fields.",
            model="anthropic/claude-3-haiku:2023-01-01"
        )
        
    def score_lead_relevance(self, user_prompt, lead_info):
        """Score how relevant a lead is to the user's search intent"""
        combined_text = f"User is looking for: {user_prompt}\n\nLead information:\n{lead_info}"
        return self.analyze(
            combined_text,
            task="score how relevant this lead is to the user's search intent on a scale of 0-100. Return a JSON with a 'relevance_score' integer field.",
            model="anthropic/claude-3-haiku:2023-01-01"
        )