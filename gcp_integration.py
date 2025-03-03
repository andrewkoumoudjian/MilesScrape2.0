"""Google Cloud Platform integration for Milestone Lead Generator."""

import os
import json
import logging
from datetime import datetime
import base64
from typing import Dict, Any, List, Optional
from google.cloud import storage, secretmanager, firestore, bigquery
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account
import googlemaps

logger = logging.getLogger(__name__)

class GCPIntegration:
    """Handles integration with Google Cloud Platform services."""
    
    def __init__(self):
        """Initialize GCP service clients."""
        # Get project ID from environment or compute engine metadata
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        
        # Initialize service clients
        self.storage_client = storage.Client()
        self.secret_client = secretmanager.SecretManagerServiceClient()
        self.firestore_client = firestore.Client()
        self.bigquery_client = bigquery.Client()
        
        # Get bucket name from environment
        self.bucket_name = os.environ.get('STORAGE_BUCKET_NAME', 'milestone-lead-generator-data')
        
        # Initialize Google Maps client if API key is available
        maps_api_key = self.get_secret('maps-api-key')
        if maps_api_key:
            self.gmaps_client = googlemaps.Client(key=maps_api_key)
        else:
            self.gmaps_client = None
    
    def get_secret(self, secret_id: str) -> Optional[str]:
        """Retrieve secret from Secret Manager."""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_id}: {str(e)}")
            return None
    
    def store_blob(self, data: Any, filename: str) -> str:
        """Store data as a blob in Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(filename)
            
            # Convert data to JSON string if it's not already a string
            if isinstance(data, (dict, list)):
                content = json.dumps(data, indent=2)
            else:
                content = str(data)
            
            blob.upload_from_string(content, content_type='application/json')
            return f"gs://{self.bucket_name}/{filename}"
        except Exception as e:
            logger.error(f"Error storing blob {filename}: {str(e)}")
            return ""
    
    def retrieve_blob(self, filename: str) -> Any:
        """Retrieve blob from Cloud Storage."""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(filename)
            content = blob.download_as_text()
            
            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content
        except NotFound:
            logger.warning(f"Blob {filename} not found in bucket {self.bucket_name}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving blob {filename}: {str(e)}")
            return None
    
    def store_leads_firestore(self, leads: List[Dict[str, Any]]) -> int:
        """Store leads in Firestore database."""
        try:
            batch = self.firestore_client.batch()
            leads_collection = self.firestore_client.collection('leads')
            stored_count = 0
            
            for lead in leads:
                # Use lead ID or generate one
                doc_id = lead.get('id', None)
                if not doc_id:
                    # Create a document reference without an ID
                    doc_ref = leads_collection.document()
                else:
                    # Use the provided ID
                    doc_ref = leads_collection.document(doc_id)
                
                # Add creation timestamp if not present
                if 'created_at' not in lead:
                    lead['created_at'] = datetime.now()
                
                # Add to batch
                batch.set(doc_ref, lead, merge=True)
                stored_count += 1
                
                # Commit in batches of 500 (Firestore limit)
                if stored_count % 500 == 0:
                    batch.commit()
                    batch = self.firestore_client.batch()
            
            # Commit any remaining documents
            if stored_count % 500 != 0:
                batch.commit()
                
            logger.info(f"Stored {stored_count} leads in Firestore")
            return stored_count
            
        except Exception as e:
            logger.error(f"Error storing leads in Firestore: {str(e)}")
            return 0
    
    def query_leads(self, 
                   limit: int = 100, 
                   min_sentiment: float = 0.0,
                   has_milestone: bool = False) -> List[Dict[str, Any]]:
        """Query leads from Firestore with filters."""
        try:
            query = self.firestore_client.collection('leads')
            
            # Apply filters
            if min_sentiment > 0:
                query = query.where('sentiment', '>=', min_sentiment)
            
            if has_milestone:
                query = query.where('milestone_details.has_milestone', '==', True)
            
            # Order by sentiment score (descending)
            query = query.order_by('sentiment', direction=firestore.Query.DESCENDING)
            
            # Limit results
            query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            results = []
            
            for doc in docs:
                lead_data = doc.to_dict()
                lead_data['id'] = doc.id  # Add document ID
                results.append(lead_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying leads from Firestore: {str(e)}")
            return []
    
    def geocode_location(self, location: str) -> Dict[str, Any]:
        """Get precise location data using Google Maps Geocoding API."""
        if not self.gmaps_client:
            logger.warning("Google Maps client not initialized, skipping geocoding")
            return {}
        
        try:
            geocode_result = self.gmaps_client.geocode(location)
            
            if not geocode_result:
                logger.warning(f"No geocoding results for location: {location}")
                return {}
            
            # Extract relevant information
            result = geocode_result[0]
            location_data = {
                'formatted_address': result.get('formatted_address', ''),
                'place_id': result.get('place_id', ''),
                'location_type': result.get('geometry', {}).get('location_type', ''),
                'lat': result.get('geometry', {}).get('location', {}).get('lat', 0),
                'lng': result.get('geometry', {}).get('location', {}).get('lng', 0),
                'viewport': result.get('geometry', {}).get('viewport', {}),
                'bounds': result.get('geometry', {}).get('bounds', {})
            }
            
            return location_data
            
        except Exception as e:
            logger.error(f"Error geocoding location {location}: {str(e)}")
            return {}
    
    def find_businesses_nearby(self, lat: float, lng: float, radius: int = 5000, 
                              keyword: str = None, type: str = 'business') -> List[Dict[str, Any]]:
        """Find businesses near a location using Google Maps Places API."""
        if not self.gmaps_client:
            logger.warning("Google Maps client not initialized, skipping nearby search")
            return []
        
        try:
            places_result = self.gmaps_client.places_nearby(
                location=(lat, lng),
                radius=radius,
                keyword=keyword,
                type=type
            )
            
            businesses = []
            for place in places_result.get('results', []):
                business = {
                    'name': place.get('name', ''),
                    'place_id': place.get('place_id', ''),
                    'address': place.get('vicinity', ''),
                    'lat': place.get('geometry', {}).get('location', {}).get('lat', 0),
                    'lng': place.get('geometry', {}).get('location', {}).get('lng', 0),
                    'types': place.get('types', []),
                    'rating': place.get('rating', 0),
                    'user_ratings_total': place.get('user_ratings_total', 0)
                }
                businesses.append(business)
            
            return businesses
            
        except Exception as e:
            logger.error(f"Error finding nearby businesses: {str(e)}")
            return []
    
    def load_data_to_bigquery(self, data: List[Dict[str, Any]], 
                            dataset_id: str, table_id: str) -> bool:
        """Load data into BigQuery for analysis."""
        try:
            # Reference to the table
            table_ref = self.bigquery_client.dataset(dataset_id).table(table_id)
            
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                autodetect=True  # Auto-detect schema
            )
            
            # Convert data to NDJSON format
            ndjson_data = "\n".join([json.dumps(item) for item in data])
            
            # Load data into BigQuery
            job = self.bigquery_client.load_table_from_string(
                ndjson_data, table_ref, job_config=job_config
            )
            
            # Wait for the job to complete
            job.result()
            
            logger.info(f"Loaded {len(data)} rows into {dataset_id}.{table_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading data to BigQuery: {str(e)}")
            return False