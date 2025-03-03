"""Main execution script for the Milestone Lead Generator."""

import logging
import time
import sys
import argparse
from datetime import datetime
import json
from typing import List, Dict, Any

from linkedin_scraper import LinkedInScraper
from google_search import GoogleSearch
from analysis import OpenRouterAnalyzer
from storage import DataStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('milestone_scanner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class MilestoneLeadGenerator:
    """Main class for generating business milestone leads using web scraping."""
    
    def __init__(self):
        """Initialize components."""
        self.linkedin_scraper = LinkedInScraper()
        self.google_search = GoogleSearch()
        self.analyzer = OpenRouterAnalyzer()
        self.storage = DataStorage()
    
    def run_scan(self, days_back: int = 30) -> None:
        """Run a complete scan cycle."""
        logger.info(f"Starting milestone lead scan ({days_back} days back)")
        start_time = time.time()
        
        try:
            # Step 1: Scan LinkedIn for milestone posts
            logger.info("Scanning LinkedIn...")
            linkedin_posts = self.linkedin_scraper.scan_for_milestone_posts(days_back=days_back)
            logger.info(f"Found {len(linkedin_posts)} posts on LinkedIn")
            
            # Step 2: Scan Google Search for milestone posts (optional)
            google_posts = []
            try:
                logger.info("Scanning Google Search...")
                google_posts = self.google_search.search_for_milestones(days_back=days_back)
                logger.info(f"Found {len(google_posts)} posts on Google")
            except Exception as e:
                logger.warning(f"Google search failed: {str(e)}")
            
            # Combine posts
            all_posts = linkedin_posts + google_posts
            logger.info(f"Total posts collected: {len(all_posts)}")
            
            if not all_posts:
                logger.warning("No posts found to analyze")
                return
            
            # Step 3: Analyze posts for sentiment and milestone details
            logger.info("Analyzing posts with OpenRouter...")
            analyzed_posts, high_value_leads = self.analyzer.analyze_posts(all_posts)
            
            # Step 4: Store results
            logger.info(f"Storing {len(analyzed_posts)} analyzed posts")
            self.storage.save_all_posts(analyzed_posts)
            
            logger.info(f"Identified {len(high_value_leads)} high-value leads")
            self.storage.save_high_value_leads(high_value_leads)
            
            # Export to CSV for easy access
            csv_path = self.storage.export_leads_csv()
            logger.info(f"Exported leads to CSV: {csv_path}")
            
            duration = time.time() - start_time
            logger.info(f"Scan completed in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in scan cycle: {str(e)}", exc_info=True)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Milestone Lead Generator")
    parser.add_argument(
        "--days", 
        type=int, 
        default=30,
        help="Number of days back to scan"
    )
    
    args = parser.parse_args()
    generator = MilestoneLeadGenerator()
    generator.run_scan(days_back=args.days)

if __name__ == "__main__":
    main()