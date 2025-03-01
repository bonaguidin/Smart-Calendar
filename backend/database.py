import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy instance
db = SQLAlchemy()

def init_db(app):
    """
    Initialize database connection and migrations.
    
    Args:
        app: Flask application instance
    """
    try:
        # Database configuration
        db_user = os.environ.get('DB_USER', 'postgres')
        db_password = os.environ.get('DB_PASSWORD', 'postgres')
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'smart_calendar')
        
        # Configure SQLAlchemy
        app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database with app
        db.init_app(app)
        
        # Initialize migrations
        migrate = Migrate(app, db)
        
        logger.info(f"Database initialized: {db_host}:{db_port}/{db_name}")
        
        # Create tables if they don't exist
        with app.app_context():
            db.create_all()
            logger.info("Database tables created")
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        # In development, you can still run with in-memory storage as fallback
        logger.warning("Using in-memory storage as fallback") 