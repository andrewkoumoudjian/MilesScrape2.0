"""
Configuration settings for MilesScrape 2.0
"""

import os

# API Keys - Fetch from environment variables for security
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")
OPEN_ROUTER_API_KEY = os.environ.get("OPEN_ROUTER_API_KEY", "YOUR_OPEN_ROUTER_API_KEY")

# Google Cloud Storage Settings
GOOGLE_CLOUD_BUCKET = os.environ.get("GOOGLE_CLOUD_BUCKET", "milescrape-data")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")

# Scraping settings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15"
]

# Request delays (in seconds)
MIN_DELAY = 2
MAX_DELAY = 5

# Open Router settings
OPEN_ROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
OPEN_ROUTER_MODEL = "mistralai/mistral-small"

# Search parameters
DEFAULT_LOCATION = "San Francisco"
DEFAULT_BUSINESS_TYPES = ["tech startup", "small business", "medium business"]
MAX_RESULTS_PER_QUERY = 20

# Milestone keywords for filtering
MILESTONE_KEYWORDS = [
    "milestone", "achievement", "funding", "series", "raised", 
    "launch", "expansion", "growth", "acquisition", "partnership",
    "new office", "award", "recognition", "revenue", "profit",
    "IPO", "merger", "customer", "contract", "investment"
]

# Rate limiting settings
MAX_REQUESTS_PER_MINUTE = 10
RATE_LIMIT_SLEEP = 60 / MAX_REQUESTS_PER_MINUTE