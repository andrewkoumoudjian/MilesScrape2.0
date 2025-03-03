import os
import logging
from datetime import datetime, timedelta
import threading
import schedule
import time
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from werkzeug.utils import secure_filename

from modules.auth import User
from modules.social_media import SocialMediaManager
from modules.nlp import OpenRouterClient
from modules.leads import LeadProcessor
from modules.storage import LeadStorage
from utils.email import send_lead_notification

from config import active_config as config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# Initialize components
social_media = SocialMediaManager()
nlp_client = OpenRouterClient()
lead_processor = LeadProcessor(nlp_client=nlp_client)
storage = LeadStorage()

# Helper functions
def get_score_color(score):
    """Return a color based on the score"""
    if score >= 80:
        return "#28a745"  # Green
    elif score >= 60:
        return "#17a2b8"  # Blue
    elif score >= 40:
        return "#ffc107"  # Yellow
    else:
        return "#dc3545"  # Red

def run_scheduled_searches():
    """Run all scheduled searches"""
    from firebase_admin import firestore
    db = firestore.client()
    
    # Get all scheduled searches
    searches_ref = db.collection('saved_searches')
    query = searches_ref.where('is_scheduled', '==', True)
    searches = list(query.stream())
    
    logger.info(f"Running {len(searches)} scheduled searches")
    
    for search_doc in searches:
        search_id = search_doc.id
        search_data = search_doc.to_dict()
        
        try:
            # Get user
            user_id = search_data.get('user_id')
            user = User.get_by_id(user_id) if user_id else None
            
            # Extract search parameters
            user_prompt = search_data.get('user_prompt', '')
            search_params = search_data.get('search_params', {})
            
            # Run the search
            leads = process_search(user_prompt, search_params)
            
            if leads:
                # Save to CSV
                csv_url = storage.save_leads_to_csv(leads, user_prompt)
                
                # Save to Firestore
                lead_ids = storage.save_leads_to_firestore(leads, user_id, search_id)
                
                # Update search with new lead count and last run
                db.collection('saved_searches').document(search_id).update({
                    'last_run': datetime.now(),
                    'lead_count': len(leads)
                })
                
                # Send email notification if user exists
                if user and hasattr(user, 'email'):
                    send_lead_notification(user.email, len(leads), user_prompt, csv_url)
                    
                logger.info(f"Scheduled search {search_id} completed with {len(leads)} leads")
            else:
                logger.info(f"Scheduled search {search_id} completed with no leads")
                
        except Exception as e:
            logger.error(f"Error running scheduled search {search_id}: {str(e)}")


def process_search(user_prompt, search_params):
    """Process a search and return leads"""
    try:
        # Extract keywords from user prompt
        keywords_analysis = nlp_client.extract_keywords(user_prompt)
        keywords = keywords_analysis.get('keywords', ['funding', 'startup', 'series'])
        
        # Create search query for social media
        search_query = " OR ".join(keywords)
        
        # Search social media
        logger.info(f"Searching social media for: {search_query}")
        posts = social_media.search_all_platforms(search_query)
        
        # Process posts into leads
        logger.info(f"Found {len(posts)} posts, processing...")
        leads = lead_processor.process_posts(posts, user_prompt, search_params)
        
        logger.info(f"Processed {len(leads)} leads")
        return leads
        
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        return []


# Routes
@app.route('/')
def index():
    """Homepage with search form"""
    from flask_wtf import FlaskForm
    from wtforms import StringField, TextAreaField, IntegerField, SelectMultipleField, BooleanField
    from wtforms.validators import DataRequired, Optional
    
    class SearchForm(FlaskForm):
        pass  # Just for CSRF protection
        
    form = SearchForm()
    return render_template('index.html', form=form)


@app.route('/search', methods=['POST'])
def search():
    """Process search form and display results"""
    # Get form data
    user_prompt = request.form.get('prompt', '')
    
    # Build search parameters
    search_params = {
        "location": request.form.get('locations', '').split(','),
        "max_age_days": int(request.form.get('max_age_days', 30)),
        "seniority_levels": request.form.getlist('seniority_levels'),
        "company_size": {
            "min": int(request.form.get('min_size', 50)),
            "max": int(request.form.get('max_size', 500))
        }
    }
    
    # Process search
    leads = process_search(user_prompt, search_params)
    
    # Extract all milestone types for filtering
    all_milestones = list(set(lead.get('milestone_type', '') for lead in leads if lead.get('milestone_type')))
    
    # Save to CSV
    csv_url = storage.save_leads_to_csv(leads, user_prompt)
    
    # Create a search record
    user_id = current_user.id if current_user.is_authenticated else None
    search_id = storage.save_search_results(search_params, user_prompt, len(leads), user_id)
    
    # Save search if requested
    if current_user.is_authenticated and request.form.get('save_search'):
        current_user.save_search(user_prompt, [k for k in search_params])
        flash('Search saved for daily updates', 'success')
    
    # Save leads to Firestore
    storage.save_leads_to_firestore(leads, user_id, search_id)
    
    return render_template(
        'results.html', 
        leads=leads, 
        search_query=user_prompt,
        search_id=search_id,
        csv_url=csv_url,
        all_milestones=all_milestones,
        get_score_color=get_score_color
    )


@app.route('/search/<search_id>')
def view_search(search_id):
    """View results of a saved search"""
    from firebase_admin import firestore
    db = firestore.client()
    
    # Get search data
    search_doc = db.collection('searches').document(search_id).get()
    if not search_doc.exists:
        flash('Search not found', 'danger')
        return redirect(url_for('dashboard'))
        
    search_data = search_doc.to_dict()
    user_prompt = search_data.get('user_prompt', '')
    
    # Get leads for this search
    leads = storage.get_leads_for_search(search_id)
    
    # Get CSV URL if it exists
    csv_url = search_data.get('csv_url', None)
    
    # Extract all milestone types for filtering
    all_milestones = list(set(lead.get('milestone_type', '') for lead in leads if lead.get('milestone_type')))
    
    return render_template(
        'results.html',
        leads=leads,
        search_query=user_prompt,
        search_id=search_id,
        csv_url=csv_url,
        all_milestones=all_milestones,
        get_score_color=get_score_color
    )


@app.route('/search/<search_id>/run')
@login_required
def run_search(search_id):
    """Re-run a saved search"""
    from firebase_admin import firestore
    db = firestore.client()
    
    # Get search data
    search_doc = db.collection('searches').document(search_id).get()
    if not search_doc.exists:
        flash('Search not found', 'danger')
        return redirect(url_for('dashboard'))
        
    search_data = search_doc.to_dict()
    user_prompt = search_data.get('user_prompt', '')
    search_params = search_data.get('search_params', {})
    
    # Run the search
    leads = process_search(user_prompt, search_params)
    
    if leads:
        # Save to CSV
        csv_url = storage.save_leads_to_csv(leads, user_prompt)
        
        # Save to Firestore
        lead_ids = storage.save_leads_to_firestore(leads, current_user.id, search_id)
        
        # Update search with new lead count and last run
        db.collection('searches').document(search_id).update({
            'last_run': datetime.now(),
            'lead_count': len(leads),
            'csv_url': csv_url
        })
        
        flash(f'Found {len(leads)} new leads', 'success')
    else:
        flash('No new leads found', 'info')
    
    return redirect(url_for('view_search', search_id=search_id))


@app.route('/search/<search_id>/delete', methods=['POST'])
@login_required
def delete_search(search_id):
    """Delete a saved search"""
    from firebase_admin import firestore
    db = firestore.client()
    
    # Get search data
    search_doc = db.collection('searches').document(search_id).get()
    if not search_doc.exists:
        flash('Search not found', 'danger')
        return redirect(url_for('dashboard'))
        
    search_data = search_doc.to_dict()
    
    # Check if user owns this search
    if search_data.get('user_id') != current_user.id:
        flash('You do not have permission to delete this search', 'danger')
        return redirect(url_for('dashboard'))
    
    # Delete search
    db.collection('searches').document(search_id).delete()
    
    flash('Search deleted', 'success')
    return redirect(url_for('dashboard'))


@app.route('/lead/<lead_id>/save', methods=['POST'])
@login_required
def save_lead(lead_id):
    """Save a lead to user's saved leads"""
    from firebase_admin import firestore
    db = firestore.client()
    
    # Get lead data
    lead_doc = db.collection('leads').document(lead_id).get()
    if not lead_doc.exists:
        flash('Lead not found', 'danger')
        return redirect(url_for('dashboard'))
        
    lead_data = lead_doc.to_dict()
    
    # Save lead
    current_user.save_lead(lead_data)
    
    flash('Lead saved', 'success')
    
    # Redirect back to referring page
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/saved-leads')
@login_required
def saved_leads():
    """View user's saved leads"""
    leads = current_user.get_saved_leads()
    
    # Extract all milestone types for filtering
    all_milestones = list(set(lead.get('milestone_type', '') for lead in leads if lead.get('milestone_type')))
    
    return render_template(
        'saved_leads.html',
        leads=leads,
        all_milestones=all_milestones,
        get_score_color=get_score_color
    )


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Get saved searches
    saved_searches = current_user.get_saved_searches()
    
    # Get total leads count
    total_leads = len(current_user.get_saved_leads())
    
    # Calculate next scheduled run time
    next_scheduled_time = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0).strftime('%Y-%m-%d %H:%M')
    
    return render_template(
        'dashboard.html',
        saved_searches=saved_searches,
        total_leads=total_leads,
        next_scheduled_time=next_scheduled_time
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    from flask_wtf import FlaskForm
    
    class LoginForm(FlaskForm):
        pass  # Just for CSRF protection
        
    form = LoginForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.verify_password(email, password)
        if user:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Login successful', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    from flask_wtf import FlaskForm
    
    class RegisterForm(FlaskForm):
        pass  # Just for CSRF protection
        
    form = RegisterForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html', form=form)
        
        # Check if email already exists
        if User.get_by_email(email):
            flash('Email already registered', 'danger')
            return render_template('register.html', form=form)
        
        # Create user
        user = User.create(email, username, password)
        if user:
            login_user(user)
            flash('Registration successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Registration failed', 'danger')
    
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Handle CSRF errors"""
    flash('CSRF token expired or invalid. Please try again.', 'danger')
    return redirect(url_for('index'))


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(e)}")
    return render_template('500.html'), 500


def start_scheduler():
    """Start the scheduler for running saved searches"""
    if config.SCHEDULER_ENABLED:
        # Schedule to run every day at 9 AM
        schedule.every().day.at("09:00").do(run_scheduled_searches)
        
        # Also run once at startup for testing
        if os.environ.get('RUN_SCHEDULER_AT_STARTUP', 'False') == 'True':
            schedule.run_all()
        
        logger.info("Scheduler started")
        
        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == '__main__':
    # Start scheduler in a separate thread
    if config.SCHEDULER_ENABLED:
        scheduler_thread = threading.Thread(target=start_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))