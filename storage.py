"""Storage module for the Milestone Lead Generator."""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

from config import (
    DATA_DIRECTORY,
    LEADS_FILE,
    ALL_POSTS_FILE
)

logger = logging.getLogger(__name__)

class DataStorage:
    """Handles storage and retrieval of scanned posts and leads."""
    
    def __init__(self):
        """Initialize data storage."""
        # Ensure data directory exists
        if not os.path.exists(DATA_DIRECTORY):
            os.makedirs(DATA_DIRECTORY)
    
    def save_all_posts(self, posts: List[Dict[str, Any]]) -> None:
        """Save all scanned posts to file."""
        try:
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(DATA_DIRECTORY, f"posts_{timestamp}.json")
            
            # Save to JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(posts)} posts to {filename}")
            
            # Also update the main all posts file
            self._update_main_file(posts, ALL_POSTS_FILE)
            
        except Exception as e:
            logger.error(f"Error saving posts: {str(e)}")
    
    def save_high_value_leads(self, leads: List[Dict[str, Any]]) -> None:
        """Save high value leads to file."""
        try:
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(DATA_DIRECTORY, f"leads_{timestamp}.json")
            
            # Save to JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(leads, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(leads)} high-value leads to {filename}")
            
            # Also update the main leads file
            self._update_main_file(leads, LEADS_FILE)
            
        except Exception as e:
            logger.error(f"Error saving leads: {str(e)}")
    
    def _update_main_file(self, new_items: List[Dict[str, Any]], filename: str) -> None:
        """Update main file with new items, avoiding duplicates."""
        file_path = os.path.join(DATA_DIRECTORY, filename)
        
        try:
            # Load existing items if file exists
            existing_items = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_items = json.load(f)
            
            # Create ID set for quick duplicate checking
            existing_ids = {item.get('id', '') for item in existing_items}
            
            # Add only new items
            updated_items = existing_items.copy()
            added_count = 0
            
            for item in new_items:
                item_id = item.get('id', '')
                if item_id and item_id not in existing_ids:
                    updated_items.append(item)
                    existing_ids.add(item_id)
                    added_count += 1
            
            # Write updated list back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(updated_items, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Added {added_count} new items to {filename}")
            
        except Exception as e:
            logger.error(f"Error updating {filename}: {str(e)}")
    
    def load_recent_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Load most recent posts from storage."""
        file_path = os.path.join(DATA_DIRECTORY, ALL_POSTS_FILE)
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                posts = json.load(f)
            
            # Sort by timestamp descending (most recent first)
            posts.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            # Return limited number
            return posts[:limit]
            
        except Exception as e:
            logger.error(f"Error loading posts: {str(e)}")
            return []
    
    def load_high_value_leads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Load high value leads from storage."""
        file_path = os.path.join(DATA_DIRECTORY, LEADS_FILE)
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                leads = json.load(f)
            
            # Sort by sentiment score and relevance score descending
            leads.sort(key=lambda x: (
                x.get('sentiment', 0) + 
                x.get('milestone_details', {}).get('relevance_score', 0) / 10
            ), reverse=True)
            
            # Return limited number
            return leads[:limit]
            
        except Exception as e:
            logger.error(f"Error loading leads: {str(e)}")
            return []
    
    def export_leads_csv(self) -> str:
        """Export leads to CSV format."""
        import csv
        
        file_path = os.path.join(DATA_DIRECTORY, LEADS_FILE)
        csv_path = os.path.join(DATA_DIRECTORY, "high_value_leads.csv")
        
        if not os.path.exists(file_path):
            return "No leads data available"
        
        try:
            # Load leads
            with open(file_path, 'r', encoding='utf-8') as f:
                leads = json.load(f)
            
            # Define CSV fields
            fields = [
                'company_name', 
                'milestone_type', 
                'milestone_description',
                'sentiment', 
                'url', 
                'timestamp',
                'text'
            ]
            
            # Write CSV file
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields)
                writer.writeheader()
                
                for lead in leads:
                    # Convert timestamp to readable date
                    timestamp = lead.get('timestamp', 0)
                    if timestamp:
                        date_str = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d')
                    else:
                        date_str = "unknown"
                    
                    # Extract relevant fields
                    row = {
                        'company_name': lead.get('company_name', 'Unknown'),
                        'milestone_type': lead.get('milestone_details', {}).get('milestone_type', 'unknown'),
                        'milestone_description': lead.get('milestone_details', {}).get('milestone_description', ''),
                        'sentiment': lead.get('sentiment', 0),
                        'url': lead.get('url', ''),
                        'timestamp': date_str,
                        'text': lead.get('text', '')[:100] + '...'  # Truncate long text
                    }
                    writer.writerow(row)
            
            return csv_path
            
        except Exception as e:
            logger.error(f"Error exporting leads to CSV: {str(e)}")
            return f"Error: {str(e)}"