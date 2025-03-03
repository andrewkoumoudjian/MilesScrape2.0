import firebase_admin
from firebase_admin import firestore
import pandas as pd
from google.cloud import storage
from datetime import datetime
import os
import json
import logging

logger = logging.getLogger(__name__)

class LeadStorage:
    """Storage utilities for leads and search results"""
    
    def __init__(self):
        self.db = firestore.client()
        self.bucket_name = os.environ.get('GCS_BUCKET_NAME', f"{os.environ.get('GOOGLE_CLOUD_PROJECT', 'leadbot')}-leads")
    
    def save_leads_to_firestore(self, leads, user_id=None, search_id=None):
        """
        Save leads to Firestore
        
        Args:
            leads (list): List of lead objects
            user_id (str): ID of the user who ran the search
            search_id (str): ID of the search
        
        Returns:
            list: List of Firestore document IDs
        """
        lead_ids = []
        
        for lead in leads:
            lead_data = lead.copy()
            
            # Add metadata
            lead_data['user_id'] = user_id
            lead_data['search_id'] = search_id
            lead_data['saved_at'] = datetime.now()
            
            # Convert datetime objects to strings
            for key, value in lead_data.items():
                if isinstance(value, datetime):
                    lead_data[key] = value.isoformat()
            
            # Save to Firestore
            doc_ref = self.db.collection('leads').add(lead_data)
            lead_ids.append(doc_ref[1].id)
        
        logger.info(f"Saved {len(lead_ids)} leads to Firestore")
        return lead_ids
    
    def save_leads_to_csv(self, leads, search_query=None):
        """
        Save leads to CSV file in Google Cloud Storage
        
        Args:
            leads (list): List of lead objects
            search_query (str): The search query used
            
        Returns:
            str: URL of the CSV file
        """
        if not leads:
            return None
        
        try:
            # Convert leads to DataFrame
            df = pd.DataFrame(leads)
            
            # Format datetime columns
            for col in df.columns:
                if df[col].dtype == 'datetime64[ns]':
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leads_{timestamp}.csv"
            local_path = f"/tmp/{filename}"
            
            # Save locally first
            df.to_csv(local_path, index=False)
            
            # Upload to Google Cloud Storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            
            # Create bucket if it doesn't exist
            if not bucket.exists():
                bucket = storage_client.create_bucket(self.bucket_name)
            
            blob = bucket.blob(f"leads/{filename}")
            blob.upload_from_filename(local_path)
            
            # Make the file publicly accessible
            blob.make_public()
            
            # Clean up local file
            os.remove(local_path)
            
            logger.info(f"Saved leads to GCS: {blob.public_url}")
            return blob.public_url
            
        except Exception as e:
            logger.error(f"Error saving leads to CSV: {str(e)}")
            return None
    
    def get_leads_for_user(self, user_id, limit=100):
        """Get leads associated with a specific user"""
        leads_ref = self.db.collection('leads')
        query = leads_ref.where('user_id', '==', user_id).limit(limit)
        
        results = []
        for doc in query.stream():
            lead = doc.to_dict()
            lead['id'] = doc.id
            results.append(lead)
            
        return results
    
    def get_leads_for_search(self, search_id, limit=100):
        """Get leads associated with a specific search"""
        leads_ref = self.db.collection('leads')
        query = leads_ref.where('search_id', '==', search_id).limit(limit)
        
        results = []
        for doc in query.stream():
            lead = doc.to_dict()
            lead['id'] = doc.id
            results.append(lead)
            
        return results
    
    def save_search_results(self, search_params, user_prompt, lead_count, user_id=None):
        """
        Save search configuration and metadata
        
        Returns:
            str: ID of the saved search
        """
        search_data = {
            'user_prompt': user_prompt,
            'search_params': search_params,
            'lead_count': lead_count,
            'user_id': user_id,
            'created_at': datetime.now()
        }
        
        doc_ref = self.db.collection('searches').add(search_data)
        search_id = doc_ref[1].id
        
        return search_id