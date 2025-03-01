import unittest
from datetime import datetime, timedelta
import pytz
from timezone_handler import TimezoneHandler

class TestTimezoneHandler(unittest.TestCase):
    def setUp(self):
        self.tz_handler = TimezoneHandler()
        self.chicago_tz = pytz.timezone('America/Chicago')

    def test_dst_transition_spring(self):
        # Test DST spring forward (2024)
        march_10_2024 = datetime(2024, 3, 10, tzinfo=self.chicago_tz)
        self.assertTrue(self.tz_handler.is_dst_transition_day(march_10_2024))
        
        # Test day before transition
        march_9_2024 = datetime(2024, 3, 9, tzinfo=self.chicago_tz)
        self.assertFalse(self.tz_handler.is_dst_transition_day(march_9_2024))

    def test_dst_transition_fall(self):
        # Test DST fall back (2024)
        nov_3_2024 = datetime(2024, 11, 3, tzinfo=self.chicago_tz)
        self.assertTrue(self.tz_handler.is_dst_transition_day(nov_3_2024))
        
        # Test day after transition
        nov_4_2024 = datetime(2024, 11, 4, tzinfo=self.chicago_tz)
        self.assertFalse(self.tz_handler.is_dst_transition_day(nov_4_2024))

    def test_task_migration(self):
        original_task = {
            'title': 'Test Task',
            'startDate': '2024-01-29',
            'endDate': '2024-01-31'
        }
        
        migrated_task = self.tz_handler.migrate_task(original_task)
        
        self.assertIn('timezone', migrated_task)
        self.assertIn('utc_offset', migrated_task)
        self.assertEqual(migrated_task['timezone'], 'America/Chicago')

    def test_duration_calculation(self):
        # Test duration across DST transition
        start = datetime(2024, 3, 9, 12, 0, tzinfo=self.chicago_tz)
        end = datetime(2024, 3, 11, 12, 0, tzinfo=self.chicago_tz)
        
        duration = self.tz_handler.calculate_duration(start, end)
        self.assertEqual(duration.total_seconds(), 48 * 3600 - 3600)  # 47 hours due to DST

if __name__ == '__main__':
    unittest.main() 