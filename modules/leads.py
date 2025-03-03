from datetime import datetime, timedelta
from modules.nlp import OpenRouterClient
import logging

logger = logging.getLogger(__name__)

class LeadProcessor:
    """Process social media posts into qualified leads"""
    
    def __init__(self, nlp_client=None):
        self.nlp = nlp_client or OpenRouterClient()
    
    def process_posts(self, posts, user_prompt, search_params):
        """
        Process a list of social media posts into leads
        
        Args:
            posts (list): List of posts from social media platforms
            user_prompt (str): Original user search prompt
            search_params (dict): Search parameters for filtering
            
        Returns:
            list: List of processed and scored leads
        """
        leads = []
        
        for post in posts:
            try:
                # Check if post contains a business milestone
                milestone_analysis = self.nlp.classify_milestone(post['text'])
                if not milestone_analysis.get('is_milestone', False):
                    continue
                
                # Extract entities from the post
                entities = self.nlp.extract_entities(post['text'])
                
                # Get company size if company was identified
                company_size = {"min": 0, "max": 0}
                if entities.get('company'):
                    company_description = f"Company: {entities.get('company')}"
                    if 'user' in post and post['user'].get('description'):
                        company_description += f"\nDescription: {post['user']['description']}"
                    
                    size_estimate = self.nlp.estimate_company_size(company_description)
                    company_size = {
                        "min": size_estimate.get('min_employees', 0),
                        "max": size_estimate.get('max_employees', 0),
                        "average": (size_estimate.get('min_employees', 0) + size_estimate.get('max_employees', 0)) / 2
                    }
                
                # Determine seniority level
                seniority = "unknown"
                if entities.get('job_title'):
                    seniority_analysis = self.nlp.determine_seniority(entities.get('job_title'))
                    seniority = seniority_analysis.get('level', 'unknown')
                
                # Create lead object
                lead = {
                    "company": entities.get('company'),
                    "person": entities.get('person'),
                    "job_title": entities.get('job_title'),
                    "location": entities.get('location'),
                    "industry": entities.get('industry'),
                    "milestone_type": milestone_analysis.get('milestone_type'),
                    "seniority_level": seniority,
                    "company_size": company_size.get('average', 0),
                    "company_size_range": f"{company_size.get('min', 0)}-{company_size.get('max', 0)}",
                    "source": post.get('source', 'unknown'),
                    "source_url": post.get('url', ''),
                    "text": post.get('text', ''),
                    "created_at": post.get('created_at', datetime.now()),
                    "processed_at": datetime.now()
                }
                
                # Apply filters
                if self._filter_lead(lead, search_params):
                    # Score the lead
                    lead['relevance_score'] = self._score_lead(lead, user_prompt, search_params)
                    leads.append(lead)
                    
            except Exception as e:
                logger.error(f"Error processing post: {str(e)}")
                continue
        
        # Sort leads by relevance score (highest first)
        leads.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return leads
    
    def _filter_lead(self, lead, search_params):
        """
        Filter leads based on search parameters
        
        Returns:
            bool: True if lead passes all filters, False otherwise
        """
        try:
            # Location filter
            if search_params.get('location') and lead.get('location'):
                matching_location = False
                for location in search_params['location']:
                    if location.lower() in lead['location'].lower():
                        matching_location = True
                        break
                if not matching_location:
                    return False
            
            # Time/age filter
            if search_params.get('max_age_days') and lead.get('created_at'):
                age_days = (datetime.now() - lead['created_at']).days
                if age_days > search_params['max_age_days']:
                    return False
            
            # Seniority filter
            if search_params.get('seniority_levels') and lead.get('seniority_level'):
                if lead['seniority_level'] not in search_params['seniority_levels']:
                    return False
            
            # Company size filter
            if search_params.get('company_size') and lead.get('company_size'):
                min_size = search_params['company_size'].get('min', 0)
                max_size = search_params['company_size'].get('max', 1000000)
                if not (min_size <= lead['company_size'] <= max_size):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in lead filtering: {str(e)}")
            return False
    
    def _score_lead(self, lead, user_prompt, search_params):
        """
        Score a lead based on relevance to user prompt and quality
        
        Returns:
            int: Score from 0-100
        """
        try:
            # Base score
            score = 50
            
            # Prompt relevance (using NLP)
            lead_info = f"Company: {lead.get('company')}\n"
            lead_info += f"Industry: {lead.get('industry')}\n"
            lead_info += f"Milestone: {lead.get('milestone_type')}\n"
            lead_info += f"Text: {lead.get('text')}"
            
            relevance_analysis = self.nlp.score_lead_relevance(user_prompt, lead_info)
            relevance_score = relevance_analysis.get('relevance_score', 50)
            
            # Recency bonus (up to 15 points)
            if lead.get('created_at'):
                age_days = (datetime.now() - lead['created_at']).days
                recency_score = max(0, 15 - (age_days / 2))
                score += recency_score
            
            # Seniority bonus
            seniority_scores = {
                "executive": 20,
                "senior": 15,
                "mid": 10,
                "entry": 5,
                "unknown": 0
            }
            score += seniority_scores.get(lead.get('seniority_level', 'unknown'), 0)
            
            # Apply ML-derived relevance
            score = (score + relevance_score) / 2
            
            # Cap score at 100
            return min(round(score), 100)
            
        except Exception as e:
            logger.error(f"Error in lead scoring: {str(e)}")
            return 50  # Default score