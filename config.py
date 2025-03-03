"""Configuration settings for the Milestone Lead Generator."""

# LinkedIn credentials for login
LINKEDIN_USERNAME = "your-email@example.com"
LINKEDIN_PASSWORD = "your-password"

# Location settings
TARGET_LOCATION = "New York, NY"  # Your target area
RADIUS_KM = 50  # Search radius in kilometers

# Google search settings
GOOGLE_API_KEY = "your-google-api-key"  # Optional, for Google Custom Search
GOOGLE_CSE_ID = "your-google-cse-id"    # Optional, for Google Custom Search

# OpenRouter settings for analysis
OPENROUTER_API_KEY = "your-openrouter-api-key"

# Search parameters
MILESTONE_KEYWORDS = [
    "anniversary", 
    "milestone", 
    "achievement", 
    "award", 
    "funding", 
    "expansion",
    "new office", 
    "acquisition", 
    "merger", 
    "launch", 
    "IPO",
    "series A", 
    "series B", 
    "series C",
    "achieved",
    "celebrating",
    "proud to announce"
]

# Company types to filter
TARGET_COMPANY_TYPES = [
    "small business",
    "startup",
    "tech company",
    "local business",
    "restaurant",
    "retail",
    "service business"
]

# Sentiment analysis thresholds
POSITIVE_SENTIMENT_THRESHOLD = 0.7

# Storage settings
DATA_DIRECTORY = "data"
LEADS_FILE = "high_value_leads.json"
ALL_POSTS_FILE = "all_scanned_posts.json"

# Browser settings
HEADLESS = True  # Set to False to see the browser while scraping
CHROME_DRIVER_PATH = None  # Set path to chromedriver if needed