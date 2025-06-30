import json
import os

# Initialize any static resources outside the handler
# for Lambda optimization
WELCOME_GREETING = "Hi! I am a voice assistant powered by Twilio and Open A I . Ask me anything!"

def lambda_handler(event, context):
    """
    Handle POST requests to /twiml endpoint
    
    Parameters:
    - event: API Gateway event
    - context: Lambda context
    
    Returns:
    - TwiML response for Twilio to connect to the WebSocket
    """
    # Get the WebSocket URL from environment variable or construct it
    stage = os.environ.get('STAGE', 'prod')
    domain = os.environ.get('DOMAIN_NAME')
    
    # Construct WebSocket URL
    ws_url = f"wss://{domain}/{stage}"
    
    # Create TwiML response
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Connect>
        <ConversationRelay url="{ws_url}" welcomeGreeting="{WELCOME_GREETING}" />
      </Connect>
    </Response>"""
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/xml'
        },
        'body': xml_response
    }