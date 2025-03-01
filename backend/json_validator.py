import json
from jsonschema import validate, FormatChecker
from jsonschema.exceptions import ValidationError
import re
import logging
from typing import Dict, Tuple, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JSONSanitizer:
    def extract_json(self, raw: str) -> dict:
        """
        Extract JSON from text efficiently using targeted regex patterns.
        
        Args:
            raw (str): Raw text potentially containing JSON
            
        Returns:
            dict: Extracted JSON object or empty dict
        """
        # Quick exit for empty input
        if not raw or len(raw.strip()) == 0:
            return {}
            
        try:
            # Try direct JSON parsing first (fastest path)
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
            
        # Remove markdown code blocks
        cleaned = re.sub(r'```(?:json)?\s*|\s*```', '', raw)
        
        try:
            # Try parsing the cleaned text
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # If that fails, try to find JSON between braces
            json_match = re.search(r'({[\s\S]*?})(?:\s*$|[^{])', cleaned)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
        
        # Fallback to an empty dictionary if all attempts fail
        return {}

    def validate_data(self, data: dict, schema: dict) -> bool:
        """
        Simple schema validation without excessive logging.
        
        Args:
            data (dict): Data to validate
            schema (dict): JSON schema to validate against
            
        Returns:
            bool: Whether the data is valid
        """
        try:
            validate(
                instance=data,
                schema=schema,
                format_checker=FormatChecker()
            )
            return True
        except ValidationError:
            return False

    def clean_and_validate(self, raw_text: str, schema: dict, context: Optional[dict] = None) -> dict:
        """
        Simplified version that extracts and validates JSON in one step.
        
        Args:
            raw_text (str): Raw text to process
            schema (dict): Schema to validate against
            context (dict, optional): Additional context
            
        Returns:
            dict: Validated data or error response
        """
        if context is None:
            context = {}
            
        try:
            # Extract JSON
            data = self.extract_json(raw_text)
            
            # Empty result check
            if not data:
                return {"error": "No valid JSON found"}
            
            # Validate data
            if self.validate_data(data, schema):
                return data
            else:
                return {"error": "Validation failed", "data": data}
                
        except Exception as e:
            return {"error": str(e)}

def test_json_sanitizer():
    """Comprehensive test suite for JSONSanitizer."""
    from schemas import TASK_SCHEMA, EDIT_SCHEMA
    
    test_cases = [
        # Task creation tests
        {
            "name": "Valid task creation",
            "input": '''
                {
                    "description": "Team meeting",
                    "start_date": "2025-02-01",
                    "end_date": "2025-02-01",
                    "color": "#2196F3"
                }
            ''',
            "schema": TASK_SCHEMA,
            "should_pass": True
        },
        # Edit operation tests
        {
            "name": "Valid edit operation",
            "input": '''
                {
                    "operations": [{
                        "field": "title",
                        "value": "Updated meeting",
                        "operation_type": "replace"
                    }]
                }
            ''',
            "schema": EDIT_SCHEMA,
            "should_pass": True
        },
        # Error cases
        {
            "name": "Invalid date format",
            "input": '{"description": "Test", "start_date": "invalid", "end_date": "2025-02-01"}',
            "schema": TASK_SCHEMA,
            "should_pass": False
        },
        {
            "name": "Missing required field",
            "input": '{"description": "Test"}',
            "schema": TASK_SCHEMA,
            "should_pass": False
        },
        {
            "name": "Invalid color format",
            "input": '{"description": "Test", "start_date": "2025-02-01", "end_date": "2025-02-01", "color": "blue"}',
            "schema": TASK_SCHEMA,
            "should_pass": False
        }
    ]
    
    for test in test_cases:
        logger.info(f"\nRunning test: {test['name']}")
        result = JSONSanitizer.clean_and_validate(
            test["input"],
            test["schema"],
            context={"test_name": test["name"]}
        )
        success = "error" not in result
        
        if success == test["should_pass"]:
            logger.info(f"✅ Test passed: {test['name']}")
        else:
            logger.error(f"❌ Test failed: {test['name']}")
            logger.error(f"Input: {test['input']}")
            logger.error(f"Result: {result}")

if __name__ == "__main__":
    test_json_sanitizer() 