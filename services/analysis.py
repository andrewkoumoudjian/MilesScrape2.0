"""
Lead analysis service for Milestone Lead Generator
"""

import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class LeadAnalyzer:
    def __init__(self, storage_service=None):
        """
        Initialize the lead analyzer
        
        Args:
            storage_service: Storage service for persisting data
        """
        self.storage_service = storage_service
        
        # OpenAI API key for sentiment analysis (would be retrieved from secret manager)
        self.openai_api_key = None
        try:
            self.openai_api_key = self.get_openai_api_key()
        except Exception as e:
            logger.error(f"Error getting OpenAI API key: {e}")
    
    def get_openai_api_key(self):
        """Get OpenAI API key from environment or secret manager"""
        import os
        return os.environ.get('OPENAI_API_KEY')
    
    def analyze_lead(self, lead):
        """
        Analyze lead data to extract insights and sentiment
        
        Args:
            lead: Lead data
            
        Returns:
            Analysis results
        """
        try:
            # Check if analysis already exists
            if 'analysis' in lead:
                return lead['analysis']
            
            # Generate analysis based on lead data
            milestone_type = lead.get('milestone_type', '').lower()
            post_content = lead.get('post', '')
            company_info = lead.get('company_info', {})
            
            # In production, this would use OpenAI/GPT for analysis
            # For demo purposes, generating structured analysis based on milestone type
            analysis_result = self.generate_mock_analysis(lead)
            
            # Save analysis to lead
            if 'analysis' not in lead:
                lead['analysis'] = analysis_result
                if self.storage_service:
                    self.storage_service.save_lead(lead['id'], lead)
            
            return analysis_result
        except Exception as e:
            logger.error(f"Error analyzing lead: {e}")
            return "Analysis could not be completed due to an error."
    
    def generate_mock_analysis(self, lead):
        """
        Generate mock analysis for a lead
        
        Args:
            lead: Lead data
            
        Returns:
            Mock analysis text
        """
        milestone_type = lead.get('milestone_type', '').lower()
        company_name = lead.get('company_name', 'the company')
        
        analysis_templates = {
            'funding': [
                f"{company_name} has secured new funding which indicates strong growth potential. This investment will likely be used to expand operations, develop new products, or enter new markets. Companies are typically most receptive to new partnerships and solutions immediately after funding rounds, making this an opportune time for outreach.",
                f"The recent funding round for {company_name} demonstrates investor confidence in their business model. Companies that have just raised capital are often looking to accelerate growth through new tools and partnerships. This presents a high-value opportunity for targeted engagement offering solutions that support their expansion plans.",
            ],
            'expansion': [
                f"{company_name} is in expansion mode, suggesting they're experiencing growth and have the resources to invest in new solutions. Geographic expansion typically requires new infrastructure, technology, and services. This milestone indicates they may be receptive to offerings that can support their growth in new markets.",
                f"The expansion announced by {company_name} signals a strategic growth phase. Companies undergoing expansion often need to scale their operations quickly and efficiently. This creates opportunities for solutions that can help them manage increased complexity while maintaining quality and consistency across locations."
            ],
            'anniversary': [
                f"{company_name} is celebrating a significant milestone in their company history. Anniversaries often coincide with strategic reviews and forward-looking planning. This reflective period can be an excellent time to approach with innovative solutions that align with their future vision.",
                f"The anniversary milestone for {company_name} indicates stability and longevity in their market. Companies at anniversary milestones often evaluate their current tools and look for upgrades to carry them into the next phase. This creates a window of opportunity for introducing solutions that represent advancement over their current systems."
            ],
            'award': [
                f"{company_name} has received recognition for excellence, suggesting they value quality and innovation. Award-winning companies often leverage their achievements in marketing efforts and may be open to solutions that help maintain or enhance their leadership position in the industry.",
                f"The recent award received by {company_name} highlights their commitment to excellence in their field. Companies that have been recognized with awards are often looking to maintain their competitive edge. This presents an opportunity to introduce solutions that can help them stay ahead of industry trends."
            ],
            'launch': [
                f"{company_name} has launched a new product or service, indicating innovation and growth. Product launches are resource-intensive and often reveal operational gaps as the company scales. This creates opportunities for solutions that can address these emerging challenges.",
                f"The product launch by {company_name} demonstrates their commitment to innovation and market expansion. Companies in the post-launch phase are typically focused on adoption and scaling. This makes it an ideal time to present solutions that can support customer onboarding, scaling operations, or market penetration."
            ]
        }
        
        # Get templates for the milestone type, or use a generic one
        templates = analysis_templates.get(milestone_type, [
            f"This milestone indicates significant activity at {company_name} that may signal receptiveness to new solutions. The timing appears favorable for engagement with decision-makers who may be evaluating their current tools and processes."
        ])
        
        # Select a random template
        base_analysis = random.choice(templates)
        
        # Add lead score commentary
        score = lead.get('score', 0.75)
        score_commentary = ""
        
        if score >= 0.9:
            score_commentary = " The very high confidence score (0.9+) suggests this lead is particularly valuable and warrants prompt, personalized outreach."
        elif score >= 0.8:
            score_commentary = " The high confidence score indicates this is a quality lead that should be prioritized for follow-up."
        else:
            score_commentary = " The moderate confidence score suggests this lead has potential but may benefit from additional research before outreach."
        
        # Add industry-specific advice if available
        industry_commentary = ""
        industry = lead.get('company_info', {}).get('industry', '')
        
        if industry == 'Technology':
            industry_commentary = " As a technology company, they may be particularly interested in solutions that improve efficiency, integrate with their tech stack, or help with talent acquisition."
        elif industry == 'Healthcare':
            industry_commentary = " In the healthcare sector, focus on how your solutions address compliance, patient outcomes, or operational efficiency to resonate with their specific challenges."
        elif industry == 'Finance':
            industry_commentary = " Financial services companies typically prioritize security, compliance, and efficiency. Highlighting these aspects of your solution may increase engagement."
        elif industry == 'Education':
            industry_commentary = " Educational institutions often have unique procurement cycles and budget constraints. Consider timing outreach to align with their fiscal planning periods."
        elif industry == 'Retail':
            industry_commentary = " Retail organizations are typically focused on customer experience and operational efficiency. Positioning your solution to address these areas may increase receptiveness."
        
        # Combine all parts
        full_analysis = base_analysis + score_commentary + industry_commentary
        
        # Add recommended actions
        recommended_actions = "\n\nRecommended Actions:\n1. Research key decision-makers at the company.\n2. Prepare personalized outreach highlighting relevant case studies.\n3. Reference their recent milestone in initial communication."
        
        return full_analysis + recommended_actions