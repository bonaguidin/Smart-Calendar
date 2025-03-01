from flask import Blueprint, request, jsonify, session, current_app
from datetime import datetime, timedelta
import jwt
import traceback
import logging
from models import User, UserPreference
from database import db
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def create_token(user_id, expires_in=86400):
    """
    Create JWT token for user authentication.
    
    Args:
        user_id: User ID to encode in token
        expires_in: Expiration time in seconds (default: 24 hours)
        
    Returns:
        str: JWT token
    """
    try:
        secret_key = current_app.config['SECRET_KEY']
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        return jwt.encode(payload, secret_key, algorithm='HS256')
    except Exception as e:
        logger.error(f"Error creating token: {str(e)}")
        return None

def token_required(f):
    """
    Decorator for routes that require authentication.
    Verifies JWT token in Authorization header.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
        if not token:
            return jsonify({'error': 'Missing authentication token'}), 401
            
        try:
            # Decode and verify token
            secret_key = current_app.config['SECRET_KEY']
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Get user from database
            user = User.query.filter_by(id=payload['user_id']).first()
            if not user:
                return jsonify({'error': 'Invalid authentication token'}), 401
                
            # Add user to request context
            kwargs['current_user'] = user
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401
            
        return f(*args, **kwargs)
    
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == data['username']) | 
            (User.email == data['email'])
        ).first()
        
        if existing_user:
            if existing_user.username == data['username']:
                return jsonify({'error': 'Username already exists'}), 409
            else:
                return jsonify({'error': 'Email already exists'}), 409
        
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            timezone=data.get('timezone', 'UTC'),
            location=data.get('location'),
            display_name=data.get('display_name')
        )
        
        # Create user preferences
        preferences = UserPreference(user=new_user)
        
        # Add to database
        db.session.add(new_user)
        db.session.add(preferences)
        db.session.commit()
        
        # Create token
        token = create_token(new_user.id)
        
        logger.info(f"New user registered: {new_user.username}")
        
        # Return success response
        return jsonify({
            'success': True,
            'token': token,
            'user': new_user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login an existing user."""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Get username and password
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        if not (username or email):
            return jsonify({'error': 'Username or email is required'}), 400
            
        # Find user by username or email
        user = None
        if username:
            user = User.query.filter_by(username=username).first()
        elif email:
            user = User.query.filter_by(email=email).first()
            
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Check password
        if not user.check_password(password):
            return jsonify({'error': 'Invalid password'}), 401
            
        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create token
        token = create_token(user.id)
        
        logger.info(f"User logged in: {user.username}")
        
        # Return success response
        return jsonify({
            'success': True,
            'token': token,
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get the current user's profile."""
    try:
        # Get user preferences
        preferences = current_user.preferences
        
        # Return user profile with preferences
        return jsonify({
            'user': current_user.to_dict(),
            'preferences': preferences.to_dict() if preferences else {}
        })
        
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update the current user's profile."""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Update user fields
        user_fields = ['display_name', 'timezone', 'location']
        for field in user_fields:
            if field in data:
                setattr(current_user, field, data[field])
                
        # Update preferences if provided
        if 'preferences' in data and data['preferences']:
            preferences = current_user.preferences
            if not preferences:
                preferences = UserPreference(user=current_user)
                db.session.add(preferences)
                
            pref_data = data['preferences']
            pref_fields = ['color_theme', 'default_view', 'notifications_enabled', 
                          'weather_enabled', 'traffic_enabled', 'default_task_color']
            
            for field in pref_fields:
                if field in pref_data:
                    setattr(preferences, field, pref_data[field])
        
        # Commit changes
        db.session.commit()
        
        logger.info(f"User profile updated: {current_user.username}")
        
        # Return updated profile
        return jsonify({
            'success': True,
            'user': current_user.to_dict(),
            'preferences': current_user.preferences.to_dict() if current_user.preferences else {}
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Profile update error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """Change the user's password."""
    try:
        # Get request data
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Check current password
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
            
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
            
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        logger.info(f"Password changed for user: {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': 'Password updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Password change error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Log out the current user."""
    try:
        # In a token-based auth system, we don't need to do anything on the server
        # The client should discard the token
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': str(e)}), 500 