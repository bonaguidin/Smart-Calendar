import pytz
from datetime import datetime, timedelta
from typing import Dict, Optional, Union, List
import logging

class TimezoneHandler:
    """Handles timezone conversions and standardization for the calendar system."""
    
    def __init__(self, default_tz: str = "America/Chicago"):
        self.default_tz = pytz.timezone(default_tz)
        self.utc = pytz.UTC
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Configure logging for timezone operations."""
        logger = logging.getLogger('TimezoneHandler')
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def localize_datetime(self, dt: datetime) -> datetime:
        """Localize naive datetime to default timezone."""
        if dt.tzinfo is None:
            return self.default_tz.localize(dt)
        return dt.astimezone(self.default_tz)

    def to_utc(self, dt: datetime) -> datetime:
        """Convert datetime to UTC."""
        localized = self.localize_datetime(dt)
        return localized.astimezone(pytz.UTC)

    def parse_date_string(self, date_str: str) -> datetime:
        """Parse date string with timezone awareness."""
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return self.default_tz.localize(dt)
        except ValueError as e:
            self.logger.error(f"Error parsing date string: {e}")
            raise

    def format_date_for_storage(self, dt: datetime) -> str:
        """Format datetime for database storage with timezone info."""
        utc_dt = self.to_utc(dt)
        return utc_dt.isoformat()

    def format_date_for_display(self, dt: datetime) -> str:
        """Format datetime for display in local timezone."""
        local_dt = self.localize_datetime(dt)
        return local_dt.strftime('%Y-%m-%d %H:%M %Z')

    def calculate_duration(self, start_dt: datetime, end_dt: datetime) -> timedelta:
        """Calculate duration considering timezone differences."""
        start_utc = self.to_utc(start_dt)
        end_utc = self.to_utc(end_dt)
        return end_utc - start_utc

    def migrate_task(self, task: Dict) -> Dict:
        """Migrate existing task to include timezone information."""
        try:
            # Convert dates to timezone-aware format
            start_date = self.parse_date_string(task['startDate'])
            end_date = self.parse_date_string(task.get('endDate', task['startDate']))

            migrated_task = {
                **task,
                'startDate': self.format_date_for_storage(start_date),
                'endDate': self.format_date_for_storage(end_date),
                'timezone': str(self.default_tz),
                'utc_offset': self.default_tz.utcoffset(datetime.now()).total_seconds() / 3600
            }

            self.logger.info(f"Migrated task: {task['title']}")
            return migrated_task
        except Exception as e:
            self.logger.error(f"Error migrating task: {e}")
            raise

    def is_dst_transition_day(self, date: datetime) -> bool:
        """Check if date is during DST transition."""
        try:
            # Check day before and after for timezone transitions
            day_before = date - timedelta(days=1)
            day_after = date + timedelta(days=1)
            
            offset1 = self.default_tz.utcoffset(day_before)
            offset2 = self.default_tz.utcoffset(date)
            offset3 = self.default_tz.utcoffset(day_after)
            
            return offset1 != offset2 or offset2 != offset3
        except Exception as e:
            self.logger.error(f"Error checking DST transition: {e}")
            return False 