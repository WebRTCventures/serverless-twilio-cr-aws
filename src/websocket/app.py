import json
import boto3
import os
import logging
import time
from openai import OpenAI
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
SYSTEM_PROMPT = "You are a helpful assistant. This conversation is being translated to voice, so answer carefully. When you respond, please spell out all numbers, for example twenty not 20. Do not include emojis in your responses. Do not include bullet points, asterisks, or special symbols."

# Initialize OpenAI client outside the handler for Lambda optimization
openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'TwilioSessions'))

def ai_response(messages):
    """Get a response from OpenAI API"""
    try:
        completion = openai.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error getting AI response: {str(e)}")
        return "I'm sorry, I'm having trouble processing your request right now."

def get_session(call_sid):
    """Get conversation session from DynamoDB"""
    try:
        response = table.get_item(Key={'callSid': call_sid})
        if 'Item' in response:
            return json.loads(response['Item']['conversation'])
        return [{"role": "system", "content": SYSTEM_PROMPT}]
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        return [{"role": "system", "content": SYSTEM_PROMPT}]

def save_session(call_sid, conversation):
    """Save conversation session to DynamoDB"""
    try:
        table.put_item(
            Item={
                'callSid': call_sid,
                'conversation': json.dumps(conversation),
                'ttl': int(time.time()) + 86400  # 24 hour TTL
            }
        )
    except Exception as e:
        logger.error(f"Error saving session: {str(e)}")

def lambda_handler(event, context):
    """Handle WebSocket events for Twilio Conversation Relay"""
    # Log the full event for debugging
    logger.info(f"Event received: {json.dumps(event)}")
    
    # Define headers for all responses
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    
    try:
        # Extract connection ID and route key
        connection_id = event['requestContext']['connectionId']
        route_key = event['requestContext']['routeKey']
        
        logger.info(f"Processing {route_key} for connection {connection_id}")
        
        # Get API Gateway management client
        domain = event['requestContext']['domainName']
        stage = event['requestContext']['stage']
        endpoint = f"https://{domain}/{stage}"
        client = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint)
        
        if route_key == '$connect':
            logger.info(f"Client connected: {connection_id}")
            return {'statusCode': 200, 'headers': headers}
            
        elif route_key == '$disconnect':
            logger.info(f"Client disconnected: {connection_id}")
            return {'statusCode': 200, 'headers': headers}
            
        elif route_key == '$default':
            # Process the message from Twilio Conversation Relay
            if event.get('body'):
                try:
                    message = json.loads(event.get('body'))
                    logger.info(f"Message received: {message}")
                    
                    if message.get("type") == "setup":
                        call_sid = message.get("callSid")
                        logger.info(f"Setup for call: {call_sid}")
                        # Initialize session in DynamoDB
                        save_session(call_sid, [{"role": "system", "content": SYSTEM_PROMPT}])
                        
                    elif message.get("type") == "prompt":
                        call_sid = message.get("callSid")
                        voice_prompt = message.get("voicePrompt")
                        
                        if not call_sid:
                            logger.error("No callSid provided in prompt message")
                            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No callSid provided'})}
                        
                        if not voice_prompt:
                            logger.warning(f"Empty voice prompt received for {call_sid}")
                            voice_prompt = "I didn't catch that. Could you please repeat?"
                            
                        logger.info(f"Processing prompt for {call_sid}: {voice_prompt}")
                        
                        # Get conversation history
                        conversation = get_session(call_sid)
                        
                        # Add user message
                        conversation.append({"role": "user", "content": voice_prompt})
                        
                        # Get AI response
                        response = ai_response(conversation)
                        
                        # Add assistant response to conversation
                        conversation.append({"role": "assistant", "content": response})
                        
                        # Save updated conversation
                        save_session(call_sid, conversation)
                        
                        # Send response back to client
                        try:
                            client.post_to_connection(
                                ConnectionId=connection_id,
                                Data=json.dumps({
                                    "type": "text",
                                    "token": response,
                                    "last": True
                                })
                            )
                            logger.info(f"Sent response: {response}")
                        except Exception as e:
                            logger.error(f"Error sending message to client: {str(e)}")
                    
                    elif message.get("type") == "interrupt":
                        logger.info("Handling interruption.")
                        # Handle interruption logic here if needed
                        
                    else:
                        logger.warning(f"Unknown message type: {message.get('type')}")
                        
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse body as JSON: {event.get('body')}")
            
            return {'statusCode': 200, 'headers': headers}
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500, 
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
        
    return {'statusCode': 200, 'headers': headers}