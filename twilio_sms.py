"""
twilio_sms.py
Reusable Twilio SMS sending function for AI Reception Bot.
Set your Twilio credentials below.
"""
from twilio.rest import Client
import logging
import os

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def send_sms(mobile, message):
    """
    Send an SMS using Twilio.
    Args:
        mobile (str): Recipient's phone number in E.164 format (e.g., '+919876543210')
        message (str): Message body
    """
    # ===========================================
    # 🔑 SET YOUR TWILIO CREDENTIALS HERE
    # ===========================================
    # Option 1: Set environment variables (recommended)
    # export TWILIO_ACCOUNT_SID="your_account_sid"
    # export TWILIO_AUTH_TOKEN="your_auth_token"  
    # export TWILIO_PHONE_NUMBER="+1234567890"
    #
    # Option 2: Replace the values below directly
    # ===========================================
    
    # Read credentials strictly from environment variables (no insecure fallbacks)
    account_sid = os.getenv('TWILIO_ACCOUNT_SID', '').strip()
    auth_token = os.getenv('TWILIO_AUTH_TOKEN', '').strip()
    twilio_number = os.getenv('TWILIO_PHONE_NUMBER', '').strip()

    # No hardcoded fallback: require env vars only
    print(f"🔑 Using Twilio credentials: Account SID: {account_sid[:10]}..., Phone: {twilio_number}")

    # Validate presence
    missing = []
    if not account_sid:
        missing.append('TWILIO_ACCOUNT_SID')
    if not auth_token:
        missing.append('TWILIO_AUTH_TOKEN')
    if not twilio_number:
        missing.append('TWILIO_PHONE_NUMBER')
    if missing:
        logging.error(f"❌ Missing Twilio config: {', '.join(missing)}")
        print(f"❌ Missing Twilio config: {', '.join(missing)}")
        print("Set them as environment variables. Example (PowerShell):")
        print("$env:TWILIO_ACCOUNT_SID='ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'")
        print("$env:TWILIO_AUTH_TOKEN='your_auth_token'")
        print("$env:TWILIO_PHONE_NUMBER='+1XXXXXXXXXX'")
        return

    # Check if using API Key SID (starts with 'SK') vs Account SID (starts with 'AC')
    if account_sid.startswith('SK'):
        # Using API Key approach - need API Key Secret
        api_key_secret = os.getenv('TWILIO_API_KEY_SECRET', '').strip()
        if not api_key_secret:
            msg = (
                "❌ Using API Key SID but missing TWILIO_API_KEY_SECRET.\n"
                "Set both:\n"
                "  $env:TWILIO_ACCOUNT_SID='ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'\n"
                "  $env:TWILIO_AUTH_TOKEN='your_auth_token'\n"
                "OR for API Keys:\n"
                "  $env:TWILIO_ACCOUNT_SID='SK850f222f54353de699399000afc3fc02'\n"
                "  $env:TWILIO_API_KEY_SECRET='your_api_key_secret'\n"
            )
            logging.error(msg)
            print(msg)
            return
        # Use API Key authentication
        client = Client(account_sid, api_key_secret, account_sid)
    else:
        # Use regular Account SID + Auth Token
        client = Client(account_sid, auth_token)

        # Basic format check for E.164 on from number
    if not twilio_number.startswith('+'):
        logging.warning(f"⚠️ TWILIO_PHONE_NUMBER should be in E.164 format, current: {twilio_number}")
    try:
        sms = client.messages.create(
            body=message,
            from_=twilio_number,
            to=mobile
        )
        logging.info(f"SMS sent to {mobile}: {sms.sid}")
        print(f"[TWILIO SMS to {mobile}]: {message}")
        return True
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Failed to send SMS: {error_msg}")
        
        # Handle specific Twilio trial account restrictions
        if "21608" in error_msg and "unverified" in error_msg.lower():
            print(f"[TWILIO SMS ERROR]: Trial account restriction - {mobile} needs verification")
            print(f"💡 To fix this:")
            print(f"   1. Go to: https://twilio.com/user/account/phone-numbers/verified")
            print(f"   2. Add and verify {mobile}")
            print(f"   3. Or upgrade to a paid Twilio account")
        else:
            print(f"[TWILIO SMS ERROR]: {error_msg}")
        
        return False
