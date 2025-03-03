from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

# Initialize Firebase Admin SDK for Firestore if not already initialized
if not firebase_admin._apps:
    # Use default credentials when deployed to Google Cloud
    if os.environ.get('GAE_ENV', '').startswith('standard'):
        cred = credentials.ApplicationDefault()
    # Use service account file for local development or non-Google Cloud environments
    else:
        service_account_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account.json')
        cred = credentials.Certificate(service_account_path)

    firebase_admin.initialize_app(cred, {
        'projectId': os.environ.get('GOOGLE_CLOUD_PROJECT', 'leadbot-project')
    })

db = firestore.client()

class User(UserMixin):
    def __init__(self, user_id, email, username, created_at=None, last_login=None):
        self.id = user_id
        self.email = email
        self.username = username
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login or datetime.utcnow()

    @staticmethod
    def get_by_id(user_id):
        user_doc = db.collection('users').document(user_id).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return User(
                user_id=user_id,
                email=user_data.get('email'),
                username=user_data.get('username'),
                created_at=user_data.get('created_at'),
                last_login=user_data.get('last_login')
            )
        return None
        
    @staticmethod
    def get_by_email(email):
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1)
        users = list(query.stream())
        if users:
            user_id = users[0].id
            user_data = users[0].to_dict()
            return User(
                user_id=user_id,
                email=user_data.get('email'),
                username=user_data.get('username'),
                created_at=user_data.get('created_at'),
                last_login=user_data.get('last_login')
            )
        return None

    @staticmethod
    def create(email, username, password):
        # Check if user already exists
        if User.get_by_email(email):
            return None
            
        # Create new user document
        new_user_ref = db.collection('users').document()
        new_user = {
            'email': email,
            'username': username,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.utcnow(),
            'last_login': datetime.utcnow()
        }
        
        new_user_ref.set(new_user)
        return User(
            user_id=new_user_ref.id,
            email=email,
            username=username,
            created_at=new_user['created_at'],
            last_login=new_user['last_login']
        )

    @staticmethod
    def verify_password(email, password):
        user = User.get_by_email(email)
        if user is None:
            return None
            
        user_doc = db.collection('users').document(user.id).get()
        user_data = user_doc.to_dict()
        
        if check_password_hash(user_data['password_hash'], password):
            # Update last login time
            db.collection('users').document(user.id).update({
                'last_login': datetime.utcnow()
            })
            return user
            
        return None

    def save_search(self, prompt, keywords):
        """Save a search configuration for the user"""
        search_data = {
            'user_id': self.id,
            'prompt': prompt,
            'keywords': keywords,
            'created_at': datetime.utcnow(),
            'is_scheduled': True
        }
        db.collection('saved_searches').add(search_data)
        
    def get_saved_searches(self):
        """Get all saved searches for the user"""
        searches_ref = db.collection('saved_searches')
        query = searches_ref.where('user_id', '==', self.id)
        searches = list(query.stream())
        return [{**search.to_dict(), 'id': search.id} for search in searches]
        
    def save_lead(self, lead_data):
        """Save a lead to the user's saved leads"""
        lead_data['user_id'] = self.id
        lead_data['saved_at'] = datetime.utcnow()
        db.collection('saved_leads').add(lead_data)
        
    def get_saved_leads(self):
        """Get all saved leads for the user"""
        leads_ref = db.collection('saved_leads')
        query = leads_ref.where('user_id', '==', self.id)
        leads = list(query.stream())
        return [{**lead.to_dict(), 'id': lead.id} for lead in leads]