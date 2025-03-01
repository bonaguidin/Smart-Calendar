# Schema Definition File 
TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "start_date": {"type": "string", "format": "date"},
        "end_date": {"type": "string", "format": "date"},
        "color": {"type": "string", "pattern": "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"},
        "recurrence": {"type": ["string", "null"]},
        "recurrence_end": {"type": ["string", "null"], "format": "date"},
        "group_id": {"type": "string"}
    },
    "required": ["description", "start_date", "end_date"]
}

EDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "operations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"enum": ["title", "dates", "color", "description", "recurrence"]},
                    "value": {"type": ["string", "null"]},
                    "operation_type": {"enum": ["replace", "relative_shift", "recurrence_update"]}
                },
                "required": ["field", "value"]
            }
        }
    },
    "required": ["operations"]
}