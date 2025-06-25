# home/validators.py
import re
from django.core.exceptions import ValidationError

def validate_phone_number(phone_number):
    if not phone_number:  # Skip validation if empty or None
        return
    pattern = r'^\+?\d{1,4}?[-.\s]?\(?\d{1,4}?\)?[-.\s]?\d{1,9}[-.\s]?\d{1,9}(?:\s*(?:ext\.?|x|#)\s*\d{1,5})?$'
    if not re.match(pattern, phone_number):
        raise ValidationError('Enter a valid phone number (e.g., +1-800-123-4567 or +1-800-123-4567 x123).')
