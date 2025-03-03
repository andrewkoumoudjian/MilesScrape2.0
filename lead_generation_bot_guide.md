# Building a Lead Generation Bot with Cursor

This guide walks you through creating a lead generation bot using **Cursor**, an AI-powered code editor. The bot scans social media platforms (e.g., Twitter, LinkedIn) to identify warm leads based on company milestones like funding rounds, product launches, or expansions. It uses **OpenRouter** for natural language processing (NLP) and applies customizable search parameters—location, time since milestone, seniority level, and company size—to generate targeted leads.

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Setting Up the Development Environment](#setting-up-the-development-environment)
4. [Configuring API Access](#configuring-api-access)
5. [Creating a Front-end Interface](#creating-a-front-end-interface)
6. [Integrating OpenRouter for NLP](#integrating-openrouter-for-nlp)
7. [Collecting Data from Social Media](#collecting-data-from-social-media)
8. [Analyzing Data with OpenRouter](#analyzing-data-with-openrouter)
9. [Filtering and Scoring Leads](#filtering-and-scoring-leads)
10. [Storing and Managing Leads](#storing-and-managing-leads)
11. [Automating the Bot](#automating-the-bot)
12. [Testing and Troubleshooting](#testing-and-troubleshooting)
13. [Best Practices](#best-practices)
14. [Conclusion](#conclusion)

---

## Introduction
This bot automates lead generation by analyzing social media posts for significant business events. With AI-driven analysis via OpenRouter and tailored search parameters, it identifies high-potential leads for small to medium-sized companies or business owners, saving you time and ensuring relevance. The bot takes user prompts to find specific types of leads across LinkedIn and other social media platforms.

---

## Prerequisites
Before starting, gather these tools and resources:

- **Cursor**: Install from [cursor.sh](https://cursor.sh/).
- **Python 3.8+**: Download from [python.org](https://www.python.org/).
- **API Keys**:
  - Twitter API (for data collection).
  - LinkedIn API (optional, requires LinkedIn Developer approval).
  - OpenRouter API (for NLP tasks).
- **Python Libraries**: Install via `pip`:
  ```bash
  pip install requests pandas tweepy spacy schedule flask beautifulsoup4 selenium
  ```
- **OpenRouter Account**: Sign up at [openrouter.ai](https://openrouter.ai/) for an API key.

---

## Setting Up the Development Environment
1. Open Cursor and create a new project folder (e.g., `lead-gen-bot`).
2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required libraries (listed in Prerequisites).
4. Create a `config.json` file to store API keys and parameters:
   ```json
   {
     "openrouter_api_key": "your_openrouter_api_key",
     "twitter_consumer_key": "your_twitter_consumer_key",
     "twitter_consumer_secret": "your_twitter_consumer_secret",
     "twitter_access_token": "your_twitter_access_token",
     "twitter_access_token_secret": "your_twitter_access_token_secret",
     "linkedin_client_id": "your_linkedin_client_id",
     "linkedin_client_secret": "your_linkedin_client_secret",
     "search_params": {
       "location": ["San Francisco", "New York"],
       "max_age_days": 30,
       "seniority_levels": ["executive", "senior"],
       "company_size": {"min": 50, "max": 200}
     }
   }
   ```

---

## Configuring API Access
### Twitter API
1. Get API keys from a Twitter Developer account (create an app at [developer.twitter.com](https://developer.twitter.com/)).
2. Use `tweepy` to connect:
   ```python
   import tweepy
   import json

   with open('config.json') as f:
       config = json.load(f)

   auth = tweepy.OAuthHandler(config['twitter_consumer_key'], config['twitter_consumer_secret'])
   auth.set_access_token(config['twitter_access_token'], config['twitter_access_token_secret'])
   api = tweepy.API(auth)
   ```

### LinkedIn API
1. For LinkedIn API access (which is limited):
   ```python
   from linkedin_api import Linkedin

   # If you have API access:
   api = Linkedin(config['linkedin_client_id'], config['linkedin_client_secret'])
   
   # Alternative approach using Selenium for web scraping:
   from selenium import webdriver
   from selenium.webdriver.common.by import By
   from selenium.webdriver.chrome.options import Options

   chrome_options = Options()
   chrome_options.add_argument("--headless")
   driver = webdriver.Chrome(options=chrome_options)
   ```

---

## Creating a Front-end Interface
Build a simple web interface to accept user prompts and display results:

1. **Create a Flask Application**:
   ```python
   from flask import Flask, render_template, request, jsonify

   app = Flask(__name__)

   @app.route('/')
   def index():
       return render_template('index.html')

   @app.route('/search', methods=['POST'])
   def search():
       user_prompt = request.form.get('prompt')
       location_filters = request.form.get('locations').split(',')
       days_ago = int(request.form.get('days_ago', 30))
       seniority = request.form.getlist('seniority')
       min_size = int(request.form.get('min_size', 0))
       max_size = int(request.form.get('max_size', 1000))
       
       # Update config with user parameters
       config['search_params']['location'] = location_filters
       config['search_params']['max_age_days'] = days_ago
       config['search_params']['seniority_levels'] = seniority
       config['search_params']['company_size'] = {"min": min_size, "max": max_size}
       
       # Parse user prompt for search keywords
       keywords = analyze_with_openrouter(
           user_prompt, 
           "extract-keywords", 
           "keyword-extractor"
       ).get("keywords", ["funding", "launch", "expansion"])
       
       # Fetch and process leads
       leads = process_leads(user_prompt, keywords)
       
       return jsonify({"leads": leads})

   if __name__ == '__main__':
       app.run(debug=True)
   ```

2. **Create HTML Template** (save in `templates/index.html`):
   ```html
   <!DOCTYPE html>
   <html lang="en">
   <head>
       <meta charset="UTF-8">
       <meta name="viewport" content="width=device-width, initial-scale=1.0">
       <title>Lead Generation Bot</title>
       <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
       <style>
           .container { max-width: 800px; margin-top: 30px; }
           .result-card { margin-bottom: 15px; }
       </style>
   </head>
   <body>
       <div class="container">
           <h1 class="mb-4">Lead Generation Bot</h1>
           <form id="searchForm">
               <div class="mb-3">
                   <label for="prompt" class="form-label">What kind of leads are you looking for?</label>
                   <textarea class="form-control" id="prompt" name="prompt" rows="3" 
                   placeholder="Example: Companies that recently raised Series A funding in the AI space"></textarea>
               </div>
               <div class="row">
                   <div class="col-md-6 mb-3">
                       <label for="locations" class="form-label">Locations (comma-separated)</label>
                       <input type="text" class="form-control" id="locations" name="locations" 
                       value="San Francisco, New York">
                   </div>
                   <div class="col-md-6 mb-3">
                       <label for="days_ago" class="form-label">How recent? (days)</label>
                       <input type="number" class="form-control" id="days_ago" name="days_ago" value="30">
                   </div>
               </div>
               <div class="row">
                   <div class="col-md-6 mb-3">
                       <label class="form-label">Seniority Level</label>
                       <div class="form-check">
                           <input class="form-check-input" type="checkbox" name="seniority" value="executive" checked id="executive">
                           <label class="form-check-label" for="executive">Executive</label>
                       </div>
                       <div class="form-check">
                           <input class="form-check-input" type="checkbox" name="seniority" value="senior" checked id="senior">
                           <label class="form-check-label" for="senior">Senior</label>
                       </div>
                       <div class="form-check">
                           <input class="form-check-input" type="checkbox" name="seniority" value="mid" id="mid">
                           <label class="form-check-label" for="mid">Mid-Level</label>
                       </div>
                   </div>
                   <div class="col-md-6 mb-3">
                       <label class="form-label">Company Size</label>
                       <div class="row">
                           <div class="col-6">
                               <label for="min_size" class="form-label">Min</label>
                               <input type="number" class="form-control" id="min_size" name="min_size" value="50">
                           </div>
                           <div class="col-6">
                               <label for="max_size" class="form-label">Max</label>
                               <input type="number" class="form-control" id="max_size" name="max_size" value="200">
                           </div>
                       </div>
                   </div>
               </div>
               <button type="submit" class="btn btn-primary">Find Leads</button>
           </form>
           
           <div id="results" class="mt-4">
               <h3>Results</h3>
               <div id="loading" style="display: none;">Searching for leads...</div>
               <div id="leadsList"></div>
           </div>
       </div>
       
       <script>
           document.getElementById('searchForm').addEventListener('submit', function(e) {
               e.preventDefault();
               
               document.getElementById('loading').style.display = 'block';
               document.getElementById('leadsList').innerHTML = '';
               
               const formData = new FormData(this);
               
               fetch('/search', {
                   method: 'POST',
                   body: formData
               })
               .then(response => response.json())
               .then(data => {
                   document.getElementById('loading').style.display = 'none';
                   const leadsDiv = document.getElementById('leadsList');
                   
                   if (data.leads.length === 0) {
                       leadsDiv.innerHTML = '<p>No leads found matching your criteria.</p>';
                       return;
                   }
                   
                   data.leads.forEach(lead => {
                       const leadCard = document.createElement('div');
                       leadCard.className = 'card result-card';
                       leadCard.innerHTML = `
                           <div class="card-body">
                               <h5 class="card-title">${lead.company}</h5>
                               <h6 class="card-subtitle mb-2 text-muted">${lead.milestone} - ${lead.post_date}</h6>
                               <p class="card-text">
                                   <strong>Location:</strong> ${lead.location}<br>
                                   <strong>Contact:</strong> ${lead.name || 'Unknown'}<br>
                                   <strong>Seniority:</strong> ${lead.seniority}<br>
                                   <strong>Company Size:</strong> ~${lead.company_size} employees
                               </p>
                               <div class="progress mb-2">
                                   <div class="progress-bar" role="progressbar" style="width: ${lead.score}%;" 
                                   aria-valuenow="${lead.score}" aria-valuemin="0" aria-valuemax="100">
                                       Score: ${lead.score}
                                   </div>
                               </div>
                           </div>
                       `;
                       leadsDiv.appendChild(leadCard);
                   });
               })
               .catch(error => {
                   document.getElementById('loading').style.display = 'none';
                   document.getElementById('leadsList').innerHTML = 
                   `<div class="alert alert-danger">Error: ${error.message}</div>`;
               });
           });
       </script>
       <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
   </body>
   </html>
   ```

3. **Process User Prompt Function**:
   ```python
   def process_leads(user_prompt, keywords):
       # Convert user prompt into search parameters
       search_query = " OR ".join(keywords)
       
       # Get raw data from social media
       social_data = []
       
       # Get Twitter data
       twitter_posts = fetch_twitter_posts(search_query)
       social_data.extend(twitter_posts)
       
       # Get LinkedIn data
       linkedin_posts = fetch_linkedin_posts(search_query)
       social_data.extend(linkedin_posts)
       
       # Analyze data to extract leads based on user prompt
       leads = []
       for post in social_data:
           # Use OpenRouter to determine if post matches user's intent
           relevance = analyze_with_openrouter(
               f"User is looking for: {user_prompt}\nPost content: {post['text']}", 
               "relevance", 
               "relevance-scorer"
           ).get("score", 0)
           
           if relevance > 0.7:  # Only process highly relevant posts
               lead = extract_lead_from_post(post)
               if lead and filter_lead(lead, config):
                   lead['score'] = score_lead(lead, config) * relevance
                   leads.append(lead)
       
       # Sort by score descending
       leads.sort(key=lambda x: x['score'], reverse=True)
       return leads
   ```

---

## Integrating OpenRouter for NLP
OpenRouter powers the bot's NLP capabilities. Here's how to connect:

1. **API Function**:
   ```python
   import requests

   def analyze_with_openrouter(text, task, model):
       url = f"https://openrouter.ai/api/{task}"
       headers = {"Authorization": f"Bearer {config['openrouter_api_key']}"}
       response = requests.post(url, json={"text": text, "model": model}, headers=headers)
       return response.json()
   ```

2. **Example Tasks**:
   - Classify milestones:
     ```python
     milestone = analyze_with_openrouter(post_text, "classify", "milestone-classifier")["classification"]
     ```
   - Extract entities (e.g., company, location):
     ```python
     entities = analyze_with_openrouter(post_text, "ner", "entity-extractor")["entities"]
     ```
   - Determine seniority:
     ```python
     seniority = analyze_with_openrouter(job_title, "classify", "seniority-classifier")["seniority"]
     ```
   - Process user prompt:
     ```python
     keywords = analyze_with_openrouter(user_prompt, "extract-keywords", "keyword-extractor")["keywords"]
     ```

**Note**: Replace model names with actual OpenRouter models.

---

## Collecting Data from Social Media
Gather data from multiple platforms based on user prompt:

1. **Twitter Data Collection**:
   ```python
   def fetch_twitter_posts(search_query):
       tweets = api.search_tweets(q=search_query, lang="en", count=100)
       return [
           {
               "text": tweet.text, 
               "date": tweet.created_at.strftime("%Y-%m-%d"), 
               "user_id": tweet.user.id_str,
               "username": tweet.user.screen_name,
               "description": tweet.user.description,
               "source": "twitter"
           } for tweet in tweets
       ]
   ```

2. **LinkedIn Data Collection**:
   ```python
   def fetch_linkedin_posts(search_query):
       posts = []
       
       try:
           # If using LinkedIn API:
           results = api.search_posts(search_query)
           for result in results:
               posts.append({
                   "text": result.get("text", ""),
                   "date": result.get("date", ""),
                   "user_id": result.get("author_id", ""),
                   "username": result.get("author_name", ""),
                   "description": result.get("author_headline", ""),
                   "source": "linkedin"
               })
       except:
           # Fallback to web scraping (implement with care):
           try:
               # Example using Selenium (simplified):
               driver.get(f"https://www.linkedin.com/search/results/content/?keywords={search_query}")
               # Handle login if needed
               
               # Extract posts
               post_elements = driver.find_elements(By.CSS_SELECTOR, ".search-result__occluded-item")
               
               for element in post_elements[:20]:  # Limit to 20 posts
                   text = element.find_element(By.CSS_SELECTOR, ".search-result__snippet").text
                   author = element.find_element(By.CSS_SELECTOR, ".actor__name").text
                   date_element = element.find_element(By.CSS_SELECTOR, ".search-result__time-ago")
                   posts.append({
                       "text": text,
                       "date": date_element.get_attribute("datetime") or date_element.text,
                       "username": author,
                       "description": "",  # Would need to visit profile to get this
                       "source": "linkedin"
                   })
           except Exception as e:
               print(f"LinkedIn scraping error: {e}")
               
       return posts
   ```

3. **Extract Lead Information**:
   ```python
   def extract_lead_from_post(post):
       # Use OpenRouter to analyze post content
       milestone_analysis = analyze_with_openrouter(post["text"], "classify", "milestone-classifier")
       milestone = milestone_analysis.get("classification")
       
       if not milestone or milestone == "negative":
           return None
           
       # Extract entities
       entities = analyze_with_openrouter(post["text"], "ner", "entity-extractor").get("entities", {})
       
       # Get company size (might need additional API calls)
       company_name = entities.get("company")
       company_size = 0
       
       if company_name:
           # Try to get company size from description or additional API
           company_info = analyze_with_openrouter(
               f"Company: {company_name}\nDescription: {post.get('description', '')}", 
               "extract-company-info", 
               "company-info-extractor"
           )
           company_size = company_info.get("size", 0)
       
       # Determine seniority
       seniority = "unknown"
       if post.get("description"):
           seniority_analysis = analyze_with_openrouter(post["description"], "classify", "seniority-classifier")
           seniority = seniority_analysis.get("seniority", "unknown")
       
       return {
           "company": entities.get("company", "Unknown"),
           "milestone": milestone,
           "location": entities.get("location", "Unknown"),
           "post_date": post["date"],
           "name": post.get("username", "Unknown"),
           "seniority": seniority,
           "company_size": company_size,
           "source": post["source"],
           "original_text": post["text"]
       }
   ```

---

## Analyzing Data with OpenRouter
Process posts to extract insights based on user prompt:

1. **Analyze User Prompt Intent**:
   ```python
   def analyze_prompt_intent(user_prompt):
       intent_analysis = analyze_with_openrouter(
           user_prompt,
           "analyze-intent",
           "intent-analyzer"
       )
       
       return {
           "keywords": intent_analysis.get("keywords", []),
           "industries": intent_analysis.get("industries", []),
           "company_stages": intent_analysis.get("company_stages", []),
           "milestones": intent_analysis.get("milestones", []),
           "locations": intent_analysis.get("locations", [])
       }
   ```

2. **Match Posts to User Intent**:
   ```python
   def match_post_to_intent(post_text, intent):
       match_score = analyze_with_openrouter(
           f"Post: {post_text}\nKeywords: {', '.join(intent['keywords'])}\n"
           f"Industries: {', '.join(intent['industries'])}\n"
           f"Milestones: {', '.join(intent['milestones'])}",
           "match-score",
           "intent-matcher"
       ).get("score", 0)
       
       return match_score
   ```

---

## Filtering and Scoring Leads
Refine leads using search parameters and assign scores.

1. **Filter Function**:
   ```python
   from datetime import datetime

   def filter_lead(lead, config):
       params = config['search_params']
       
       # Location filter
       if params['location'] and lead.get('location') and lead['location'] not in params['location']:
           return False
       
       # Age filter
       try:
           post_date = datetime.strptime(lead['post_date'], "%Y-%m-%d")
           if (datetime.now() - post_date).days > params['max_age_days']:
               return False
       except:
           pass  # Skip date filtering if format is unknown
       
       # Seniority filter
       if lead.get('seniority') and lead['seniority'] not in params['seniority_levels']:
           return False
       
       # Company size filter
       if lead.get('company_size') and not (params['company_size']['min'] <= lead['company_size'] <= params['company_size']['max']):
           return False
       
       return True
   ```

2. **Scoring Function**:
   ```python
   def score_lead(lead, config):
       score = 50  # Base score
       params = config['search_params']
       
       # Recency score
       try:
           age_days = (datetime.now() - datetime.strptime(lead['post_date'], "%Y-%m-%d")).days
           score += max(0, 30 - age_days)  # Fresher posts score higher
       except:
           pass
       
       # Seniority score
       seniority_scores = {"executive": 20, "senior": 15, "mid": 10, "entry": 5}
       score += seniority_scores.get(lead.get('seniority', "unknown"), 0)
       
       # Company size score (closer to target range midpoint = higher score)
       if 'company_size' in lead and lead['company_size'] > 0:
           midpoint = (params['company_size']['min'] + params['company_size']['max']) / 2
           score += max(0, 15 - abs(lead['company_size'] - midpoint) / 10)
       
       # Cap score at 100
       return min(100, score)
   ```

---

## Storing and Managing Leads
Save leads for later use:

1. **Export to CSV**:
   ```python
   import pandas as pd
   from datetime import datetime

   def save_leads_to_csv(leads, user_prompt):
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       filename = f"leads_{timestamp}.csv"
       
       df = pd.DataFrame(leads)
       df['search_prompt'] = user_prompt  # Add the original search prompt
       df.to_csv(filename, index=False)
       
       return filename
   ```

2. **CRM Integration (Optional)**:
   ```python
   def sync_to_crm(leads, crm_type="hubspot"):
       if crm_type == "hubspot" and "hubspot_api_key" in config:
           import hubspot
           client = hubspot.Client.create(api_key=config["hubspot_api_key"])
           
           for lead in leads:
               properties = {
                   "company": lead["company"],
                   "lead_source": f"LeadBot - {lead['milestone']}",
                   "notes": lead["original_text"],
                   "lead_score": lead["score"]
               }
               
               try:
                   client.crm.companies.basic_api.create(properties=properties)
               except Exception as e:
                   print(f"Error syncing to HubSpot: {e}")
       
       # Add more CRM integrations as needed
   ```

---

## Automating the Bot
Run the bot on a schedule:

1. **Using `schedule`**:
   ```python
   import schedule
   import time

   def run_scheduled_searches():
       # Load saved searches from database or file
       saved_searches = load_saved_searches()
       
       for search in saved_searches:
           try:
               prompt = search["prompt"]
               keywords = search["keywords"]
               leads = process_leads(prompt, keywords)
               
               if leads:
                   # Save to CSV
                   filename = save_leads_to_csv(leads, prompt)
                   
                   # Notify user if configured
                   if "email" in search:
                       send_email_notification(
                           search["email"], 
                           f"New leads for: {prompt}", 
                           f"Found {len(leads)} leads. See attachment.",
                           [filename]
                       )
           except Exception as e:
               print(f"Error in scheduled search '{prompt}': {e}")

   # Run every day at 9 AM
   schedule.every().day.at("09:00").do(run_scheduled_searches)
   
   def start_scheduler():
       while True:
           schedule.run_pending()
           time.sleep(60)
       
   # Run scheduler in a separate thread
   import threading
   scheduler_thread = threading.Thread(target=start_scheduler)
   scheduler_thread.daemon = True
   scheduler_thread.start()
   ```

2. **Email Notification Function**:
   ```python
   import smtplib
   from email.mime.multipart import MIMEMultipart
   from email.mime.text import MIMEText
   from email.mime.base import MIMEBase
   from email import encoders

   def send_email_notification(recipient, subject, body, attachments=None):
       try:
           msg = MIMEMultipart()
           msg['From'] = config.get("email_from", "leadbot@example.com")
           msg['To'] = recipient
           msg['Subject'] = subject
           
           msg.attach(MIMEText(body, 'plain'))
           
           # Add attachments
           if attachments:
               for file_path in attachments:
                   with open(file_path, "rb") as attachment:
                       part = MIMEBase("application", "octet-stream")
                       part.set_payload(attachment.read())
                   
                   encoders.encode_base64(part)
                   part.add_header(
                       "Content-Disposition",
                       f"attachment; filename={file_path.split('/')[-1]}",
                   )
                   msg.attach(part)
           
           # Connect to SMTP server
           server = smtplib.SMTP(
               config.get("smtp_server", "smtp.gmail.com"), 
               config.get("smtp_port", 587)
           )
           server.starttls()
           server.login(
               config.get("email_username"), 
               config.get("email_password")
           )
           server.send_message(msg)
           server.quit()
           
           return True
       except Exception as e:
           print(f"Email notification error: {e}")
           return False
   ```

---

## Testing and Troubleshooting
- **Test User Input**: Verify the bot correctly processes different user prompts.
- **API Checks**: Validate OpenRouter responses.
- **Front-end Testing**: Ensure the web interface works properly.
- **Data Quality**: Check if leads match the user's intent.

**Common Fixes**:
- **Rate Limits**: Add retries with exponential backoff:
  ```python
  import time
  
  def api_call_with_retry(func, max_retries=3):
      retries = 0
      while retries <= max_retries:
          try:
              return func()
          except Exception as e:
              if "rate limit" in str(e).lower():
                  wait_time = 2 ** retries
                  print(f"Rate limit hit. Retrying in {wait_time} seconds...")
                  time.sleep(wait_time)
                  retries += 1
              else:
                  raise
      raise Exception("Maximum retries exceeded")
  ```
- **NLP Errors**: Adjust prompts or add example-based templates.
- **Data Quality**: Implement validation for extracted entities.

---

## Best Practices
- **Compliance**: Follow data privacy laws and platform terms.
- **Efficiency**: Cache API results to save costs and improve performance:
  ```python
  import hashlib
  import json
  import os
  
  def cache_result(func):
      def wrapper(*args, **kwargs):
          # Create a unique key from function arguments
          key = hashlib.md5(f"{func.__name__}:{str(args)}:{str(kwargs)}".encode()).hexdigest()
          cache_file = f"cache/{key}.json"
          
          # Check if cached result exists and is recent
          if os.path.exists(cache_file):
              file_age = time.time() - os.path.getmtime(cache_file)
              if file_age < 3600:  # Cache valid for 1 hour
                  with open(cache_file, 'r') as f:
                      return json.load(f)
          
          # Call the function and cache the result
          result = func(*args, **kwargs)
          os.makedirs("cache", exist_ok=True)
          with open(cache_file, 'w') as f:
              json.dump(result, f)
          
          return result
      return wrapper
  ```
- **User Experience**: Provide feedback during processing and allow for refinement.
- **Data Security**: Encrypt stored credentials and sensitive lead information.

---

##