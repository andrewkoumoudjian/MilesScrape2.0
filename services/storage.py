"""
Google Cloud Storage integration for MilesScrape 2.0
"""

import os
import json
import logging
import tempfile
from typing import List, Dict, Any
from google.cloud import storage
from google.oauth2 import service_account

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.client = self._get_storage_client()
        self.bucket_name = self._get_bucket_name()
        
    def _get_storage_client(self):
        """Get authenticated Google Cloud Storage client"""
        try:
            # Try to get credentials from environment variable
            if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                return storage.Client()
            
            # Otherwise look for credentials file
            credentials_path = os.path.join(os.path.dirname(__file__), '../credentials.json')
            if os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                return storage.Client(credentials=credentials)
            
            # If both methods fail, try default authentication
            return storage.Client()
        
        except Exception as e:
            logger.error(f"Error getting storage client: {str(e)}")
            raise

    def _get_bucket_name(self):
        """Get the bucket name from environment variable or config"""
        # Default bucket name
        default_bucket = "milescrape-data"
        
        # Try to get from environment variable
        return os.environ.get("GOOGLE_CLOUD_BUCKET", default_bucket)

    def save_to_cloud_storage(self, data: List[Dict[str, Any]], filename: str) -> str:
        """
        Save data to Google Cloud Storage
        
        Args:
            data: List of dictionaries with processed data
            filename: Name for the file in cloud storage
            
        Returns:
            Cloud storage URL of the saved file
        """
        try:
            bucket = self.client.bucket(self.bucket_name)
            
            # Create a temporary local file
            with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as temp_file:
                json.dump(data, temp_file, indent=2)
                temp_file_path = temp_file.name
            
            # Upload to Google Cloud Storage
            blob = bucket.blob(filename)
            blob.upload_from_filename(temp_file_path)
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            logger.info(f"Data saved to gs://{self.bucket_name}/{filename}")
            return f"gs://{self.bucket_name}/{filename}"
        
        except Exception as e:
            logger.error(f"Error saving to cloud storage: {str(e)}")
            raise

    def list_bucket_files(self) -> List[Dict[str, Any]]:
        """
        List files in the Google Cloud Storage bucket
        
        Returns:
            List of file information dictionaries
        """
        try:
            bucket = self.client.bucket(self.bucket_name)
            
            files = []
            for blob in bucket.list_blobs():
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "content_type": blob.content_type
                })
            
            # Sort by updated time, most recent first
            if files:
                files.sort(key=lambda x: x.get('updated', ''), reverse=True)
                
            return files
        
        except Exception as e:
            logger.error(f"Error listing bucket files: {str(e)}")
            raise

    def download_from_cloud_storage(self, filename: str) -> str:
        """
        Download a file from Google Cloud Storage
        
        Args:
            filename: Name of the file to download
            
        Returns:
            Local path to the downloaded file
        """
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(filename)
            
            # Create a temporary directory to store the file
            temp_dir = tempfile.gettempdir()
            local_path = os.path.join(temp_dir, filename)
            
            blob.download_to_filename(local_path)
            logger.info(f"Downloaded {filename} to {local_path}")
            
            return local_path
        
        except Exception as e:
            logger.error(f"Error downloading from cloud storage: {str(e)}")
            raise
