# home/validators.py

import re
from django.core.exceptions import ValidationError

def validate_phone_number(value):
    # Regular expression for phone number validation (e.g., +1-800-123-4567)
    phone_regex = r'^\+?1?\d{9,15}$'  # Simple pattern for international numbers
    if not re.match(phone_regex, value):
        raise ValidationError("Enter a valid phone number (e.g., +1-800-123-4567).")
