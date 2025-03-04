"""
Data processor service for Milestone Lead Generator
"""

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self, storage_service=None):
        """
        Initialize the data processor
        
        Args:
            storage_service: Storage service for persisting data
        """
        self.storage_service = storage_service
    
    def process_lead(self, lead_data):
        """
        Process raw lead data to extract useful information
        
        Args:
            lead_data: Raw lead data
            
        Returns:
            Processed lead data
        """
        try:
            # Extract company information from lead data
            lead_data = self.extract_company_info(lead_data)
            
            # Extract contact information
            lead_data = self.extract_contact_info(lead_data)
            
            # Extract milestone details
            lead_data = self.extract_milestone_details(lead_data)
            
            # Validate and clean data
            lead_data = self.validate_and_clean(lead_data)
            
            return lead_data
        except Exception as e:
            logger.error(f"Error processing lead data: {e}")
            return lead_data
    
    def extract_company_info(self, lead_data):
        """
        Extract company information from lead data
        
        Args:
            lead_data: Lead data
            
        Returns:
            Lead data with extracted company information
        """
        # We would extract additional company information here
        # For demo purposes, ensure company_info exists
        if 'company_info' not in lead_data:
            lead_data['company_info'] = {
                'name': lead_data.get('company_name', 'Unknown Company'),
                'industry': 'Unknown',
                'size': 'Unknown',
                'founded': 'Unknown'
            }
        
        return lead_data
    
    def extract_contact_info(self, lead_data):
        """
        Extract contact information from lead data
        
        Args:
            lead_data: Lead data
            
        Returns:
            Lead data with extracted contact information
        """
        # In a real implementation, this would extract contacts from the post content
        # or company page. For demo purposes, adding placeholder contacts
        
        # Skip if contacts already exist
        if 'contacts' in lead_data:
            return lead_data
        
        # Add placeholder contact based on company name
        company_name = lead_data.get('company_name', 'Unknown Company')
        first_name = "John" if hash(company_name) % 2 == 0 else "Jane"
        last_name = "Doe" if hash(company_name) % 3 == 0 else "Smith"
        
        lead_data['contacts'] = [
            {
                'name': f"{first_name} {last_name}",
                'title': "CEO" if hash(company_name) % 5 == 0 else "Marketing Director",
                'email': f"{first_name.lower()}.{last_name.lower()}@example.com"
            }
        ]
        
        return lead_data
    
    def extract_milestone_details(self, lead_data):
        """
        Extract milestone details from lead data
        
        Args:
            lead_data: Lead data
            
        Returns:
            Lead data with extracted milestone details
        """
        milestone_type = lead_data.get('milestone_type', '').lower()
        post_content = lead_data.get('post', '')
        
        # Skip if milestone_details already exists
        if 'milestone_details' in lead_data:
            return lead_data
        
        milestone_details = {
            'type': milestone_type,
            'extracted_data': {}
        }
        
        # Extract different information based on milestone type
        if milestone_type == 'funding':
            # Extract funding amount using regex
            funding_pattern = r'\$(\d+(?:\.\d+)?)\s*([kmbt])'
            funding_match = re.search(funding_pattern, post_content, re.IGNORECASE)
            
            if funding_match:
                amount = float(funding_match.group(1))
                unit = funding_match.group(2).lower()
                
                # Convert to actual value
                if unit == 'k':
                    amount *= 1000
                elif unit == 'm':
                    amount *= 1000000
                elif unit == 'b':
                    amount *= 1000000000
                elif unit == 't':
                    amount *= 1000000000000
                
                milestone_details['extracted_data']['funding_amount'] = amount
                
                # Try to extract funding round
                round_pattern = r'(seed|series\s+[a-z]|growth|angel)'
                round_match = re.search(round_pattern, post_content, re.IGNORECASE)
                
                if round_match:
                    milestone_details['extracted_data']['funding_round'] = round_match.group(1).capitalize()
        
        elif milestone_type == 'expansion':
            # Extract location using named entity recognition (simplified here)
            # In a real implementation, you would use NLP models for this
            location_pattern = r'to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            location_match = re.search(location_pattern, post_content)
            
            if location_match:
                milestone_details['extracted_data']['expansion_location'] = location_match.group(1)
        
        elif milestone_type == 'anniversary':
            # Extract years
            years_pattern = r'(\d+)\s*(?:years|year)'
            years_match = re.search(years_pattern, post_content, re.IGNORECASE)
            
            if years_match:
                milestone_details['extracted_data']['years'] = int(years_match.group(1))
        
        # Add timestamp
        milestone_details['timestamp'] = lead_data.get('date', datetime.utcnow().isoformat())
        
        # Add milestone details to lead data
        lead_data['milestone_details'] = milestone_details
        
        return lead_data
    
    def validate_and_clean(self, lead_data):
        """
        Validate and clean lead data
        
        Args:
            lead_data: Lead data
            
        Returns:
            Validated and cleaned lead data
        """
        # Ensure required fields exist
        required_fields = ['id', 'company_name', 'milestone', 'milestone_type', 'score', 'location']
        
        for field in required_fields:
            if field not in lead_data:
                if field == 'id':
                    lead_data['id'] = f"lead-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                elif field == 'score':
                    lead_data['score'] = 0.75
                else:
                    lead_data[field] = "Unknown"
        
        # Ensure date is in ISO format
        if 'date' not in lead_data:
            lead_data['date'] = datetime.utcnow().isoformat()
        
        # Ensure company_name is title case
        lead_data['company_name'] = lead_data['company_name'].title()
        
        return lead_data