import json
import boto3
import os
import logging
import time
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
SYSTEM_PROMPT = "You are a helpful assistant. This conversation is being translated to voice, so answer carefully. When you respond, please spell out all numbers, for example twenty not 20. Do not include emojis in your responses. Do not include bullet points, asterisks, or special symbols."

# Initialize Bedrock client outside the handler for Lambda optimization
bedrock_runtime = boto3.client('bedrock-runtime')

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'TwilioSessions'))

def ai_response(messages, connection_id, client):
    """Stream response from Amazon Bedrock to the client using converse_stream"""
    model_id = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-text-pro-v1")
    try:
        # Convert messages to Amazon Nova format
        formatted_messages = []
        system_content = None
        
        # Extract system message and format other messages
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                formatted_messages.append({"role": "user", "content": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                formatted_messages.append({"role": "assistant", "content": [{"text": msg["content"]}]})
        
        # Format system message as list for Nova API
        system_message = None
        if system_content:
            system_message = [{"text": system_content}]
        
        # Configure inference parameters
        inference_config = {
            "temperature": 0.7,
            "maxTokens": 1024
        }
        
        response = bedrock_runtime.converse_stream(
            modelId=model_id,
            messages=formatted_messages,
            system=system_message,
            inferenceConfig=inference_config
        )
        
        full_response = ""
        
        # Process each chunk from the stream
        for chunk in response["stream"]:
            if "contentBlockDelta" in chunk:
                content_text = chunk["contentBlockDelta"]["delta"]["text"]
                if content_text:
                    full_response += content_text
                    # Send the chunk to the client
                    client.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps({
                            "type": "text",
                            "token": content_text,
                            "last": False
                        })
                    )
        
        # Send final message with last=True
        client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({
                "type": "text",
                "token": "",  # Empty token for final message
                "last": True
            })
        )
        
        return full_response
    except Exception as e:
        logger.error(f"Error in streaming response: {str(e)}")
        # Send error message to client
        try:
            client.post_to_connection(
                ConnectionId=connection_id,
                Data=json.dumps({
                    "type": "text",
                    "token": "I'm sorry, I'm having trouble processing your request right now.",
                    "last": True
                })
            )
        except Exception as post_error:
            logger.error(f"Error sending error message to client: {str(post_error)}")
        
        return "I'm sorry, I'm having trouble processing your request right now."

def get_session(connection_id):
    """Get conversation session from DynamoDB"""
    try:
        response = table.get_item(Key={'connection_id': connection_id})
        if 'Item' in response:
            return json.loads(response['Item']['conversation'])
        return [{"role": "system", "content": SYSTEM_PROMPT}]
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        return [{"role": "system", "content": SYSTEM_PROMPT}]

def save_session(connection_id, conversation):
    """Save conversation session to DynamoDB"""
    try:
        table.put_item(
            Item={
                'connection_id': connection_id,
                'conversation': json.dumps(conversation),
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S UTC')
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
        client = boto3.client('apigatewaymanagementapi', 
                            endpoint_url=endpoint,
                            region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        
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
                        logger.info(f"Setup for call: {connection_id}")
                        # Initialize session in DynamoDB
                        save_session(connection_id, [{"role": "system", "content": SYSTEM_PROMPT}])
                        
                    elif message.get("type") == "prompt":
                        voice_prompt = message.get("voicePrompt")
                            
                        logger.info(f"Processing prompt for {connection_id}: {voice_prompt}")
                        
                        # Get conversation history
                        conversation = get_session(connection_id)
                        
                        # Add user message
                        conversation.append({"role": "user", "content": voice_prompt})
                        
                        # Get AI response with streaming
                        response = ai_response(messages=conversation, connection_id=connection_id, client=client)
                        
                        # Add assistant response to conversation
                        conversation.append({"role": "assistant", "content": response})
                        
                        # Save updated conversation
                        save_session(connection_id, conversation)
                        
                        logger.info(f"Sent streaming response completed")
                    elif message.get("type") == "interrupt":
                        logger.info("Handling interruption.")
                        # Handle interruption logic here if needed
                    
                    else:
                        logger.warning(f"Unknown message type: {message.get('type')}")
                        
                except Exception as e:
                    logger.error(f"Error in streaming response process: {str(e)}")
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