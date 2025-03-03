# Milestone Lead Generator

A tool to generate warm leads by scanning for businesses that have recently achieved milestones using LinkedIn and Google Search APIs, with OpenRouter for analysis.

## Features

- Scans LinkedIn for company posts about milestones
- Uses Google Search API to find business milestone mentions
- Analyzes content sentiment using OpenRouter AI
- Identifies high-value leads based on milestone significance and sentiment
- Stores results in JSON and CSV formats
- Scheduled scanning for continuous lead generation

## Setup

### Requirements

- Python 3.8+
- Google Cloud project with Custom Search API enabled
- LinkedIn Developer account with API access
- OpenRouter API account

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/milestone-lead-generator.git
   cd milestone-lead-generator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your API credentials in `config.py`:
   - LinkedIn API credentials
   - Google API key and Custom Search Engine ID
   - OpenRouter API key

### LinkedIn API Setup

1. Create a LinkedIn Developer application at https://www.linkedin.com/developers/
2. Request Marketing Developer Platform access
3. Configure OAuth 2.0 settings and obtain an access token with appropriate scopes
4. Add your credentials to `config.py`

### Google Search API Setup

1. Create a Google Cloud project
2. Enable the Custom Search JSON API
3. Create API credentials
4. Create a Custom Search Engine at https://programmablesearchengine.google.com/
5. Add your API key and Search Engine ID to `config.py`

### OpenRouter Setup

1. Create an account at https://openrouter.ai/
2. Generate an API key
3. Add your API key to `config.py`

## Usage

### Run a single scan

```bash
python main.py --mode once --days 30
```

### Schedule recurring scans

```bash
python main.py --mode schedule
```

### Generate a report of current leads

```bash
python main.py --mode report
```

### Output

The tool will generate:

- `data/all_scanned_posts.json` - All posts found in scanning
- `data/high_value_leads.json` - Filtered high-value leads
- `data/high_value_leads.csv` - CSV format of high-value leads for easy import

## Customization

Edit the `config.py` file to:

- Add or modify milestone keywords to search for
- Adjust sentiment threshold for considering a post positive
- Change the scan frequency

## License

This project is licensed under the MIT License - see the LICENSE file for details.