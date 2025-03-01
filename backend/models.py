from database import db
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
import logging

# Configure logging
logger = logging.getLogger(__name__)

class User(db.Model):
    """User profile model for authentication and personalization."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100))
    timezone = db.Column(db.String(50), default='UTC')
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    preferences = db.relationship('UserPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def __init__(self, username, email, password, timezone='UTC', location=None, display_name=None):
        self.username = username
        self.email = email
        self.set_password(password)
        self.timezone = timezone
        self.location = location
        self.display_name = display_name or username
        
    def set_password(self, password):
        """Hash password for storage."""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def get_timezone(self):
        """Get pytz timezone object."""
        try:
            return pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {self.timezone} for user {self.id}, falling back to UTC")
            return pytz.UTC
            
    def to_dict(self):
        """Convert user to dictionary for API responses."""
        return {
            'id': self.uuid,
            'username': self.username,
            'email': self.email,
            'display_name': self.display_name,
            'timezone': self.timezone,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        
    def __repr__(self):
        return f'<User {self.username}>'

class UserPreference(db.Model):
    """User preferences for calendar and notification settings."""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    color_theme = db.Column(db.String(20), default='light')
    default_view = db.Column(db.String(20), default='month')
    notifications_enabled = db.Column(db.Boolean, default=True)
    weather_enabled = db.Column(db.Boolean, default=True)
    traffic_enabled = db.Column(db.Boolean, default=True)
    default_task_color = db.Column(db.String(7), default='#2196F3')
    
    def to_dict(self):
        return {
            'color_theme': self.color_theme,
            'default_view': self.default_view,
            'notifications_enabled': self.notifications_enabled,
            'weather_enabled': self.weather_enabled,
            'traffic_enabled': self.traffic_enabled,
            'default_task_color': self.default_task_color
        }
        
    def __repr__(self):
        return f'<UserPreference user_id={self.user_id}>'

class Task(db.Model):
    """Task model for calendar events and to-dos."""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    group_id = db.Column(db.String(36))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    color = db.Column(db.String(7), default='#2196F3')
    location = db.Column(db.String(200))
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # For recurring tasks
    recurrence_pattern = db.Column(db.String(100))
    recurrence_end_date = db.Column(db.Date)
    
    # Additional properties for multi-day events
    is_part_of_multi_day = db.Column(db.Boolean, default=False)
    day_number = db.Column(db.Integer, default=1)
    total_days = db.Column(db.Integer, default=1)
    
    # Weather and traffic data (optional)
    weather_forecast = db.Column(db.JSON)
    traffic_estimate = db.Column(db.JSON)
    
    def to_dict(self):
        """Convert task to dictionary for API responses."""
        return {
            'id': self.uuid,
            'group_id': self.group_id,
            'title': self.title,
            'description': self.description,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'startTime': self.start_time.isoformat() if self.start_time else None,
            'endTime': self.end_time.isoformat() if self.end_time else None,
            'color': self.color,
            'location': self.location,
            'isCompleted': self.is_completed,
            'recurrence': self.recurrence_pattern,
            'recurrenceEnd': self.recurrence_end_date.isoformat() if self.recurrence_end_date else None,
            'isPartOfMultiDay': self.is_part_of_multi_day,
            'dayNumber': self.day_number,
            'totalDays': self.total_days,
            'weatherForecast': self.weather_forecast,
            'trafficEstimate': self.traffic_estimate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
    def __repr__(self):
        return f'<Task {self.title}>' 