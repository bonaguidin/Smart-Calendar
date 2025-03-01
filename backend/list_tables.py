"""
Script to list tables in the smart_calendar database.
"""
from flask import Flask
from database import db, init_db
from dotenv import load_dotenv
from sqlalchemy import inspect

# Load environment variables
load_dotenv()

# Create a small Flask app
app = Flask(__name__)

# Initialize database with app context
init_db(app)

# Print database tables
with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    print("\n=== Tables in smart_calendar database ===")
    if not tables:
        print("No tables found.")
    else:
        for table in tables:
            print(f"- {table}")
            columns = inspector.get_columns(table)
            for column in columns:
                print(f"  | {column['name']} ({column['type']})")
    print("========================================\n") 