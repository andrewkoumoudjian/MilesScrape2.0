# MilesScrape 2.0

MilesScrape 2.0 is a powerful tool for generating leads by scraping and analyzing business milestones from multiple sources including LinkedIn, Google Maps Places API, and Google Search. The application leverages Dolphin Mistral Free via Open Router for advanced data analysis.

## Features

- **Multi-source Data Collection**: Gathers business information from Google Maps, LinkedIn, and Google Search
- **Milestone Identification**: Automatically identifies significant business milestones like funding, expansion, product launches, etc.
- **AI-Powered Analysis**: Uses Dolphin Mistral Free for intelligent data analysis and milestone description generation
- **Google Cloud Storage Integration**: Stores results securely in Google Cloud Storage for easy access and sharing
- **User-friendly Web Interface**: Simple dashboard to configure, run, and view scraping jobs

## Prerequisites

- Python 3.8+
- Google Maps Places API key
- Open Router API key (for Dolphin Mistral Free)
- Google Cloud service account credentials with Storage access
- Chrome browser (for Selenium-based scraping)

## Installation

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/andrewkoumoudjian/MilesScrape2.0.git
   cd MilesScrape2.0