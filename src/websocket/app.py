import json
import boto3
import os
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Handle WebSocket events
    """
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
        
        if route_key == '$connect':
            logger.info(f"Client connected: {connection_id}")
            return {
                'statusCode': 200,
                'headers': headers
            }
            
        elif route_key == '$disconnect':
            logger.info(f"Client disconnected: {connection_id}")
            return {
                'statusCode': 200,
                'headers': headers
            }
            
        elif route_key == 'message':
            body = {}
            if event.get('body'):
                try:
                    body = json.loads(event.get('body'))
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse body as JSON: {event.get('body')}")
            
            logger.info(f"Message received: {body}")
            
            # Get API Gateway management client
            domain = event['requestContext']['domainName']
            stage = event['requestContext']['stage']
            endpoint = f"https://{domain}/{stage}"
            client = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint)
            
            # Send response back to client
            message = {
                'type': 'response',
                'message': f"Received: {body.get('message', '')}",
                'timestamp': datetime.utcnow().isoformat()
            }
            
            try:
                client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message)
                )
            except Exception as e:
                logger.error(f"Error sending message to client: {str(e)}")
            
            return {
                'statusCode': 200,
                'headers': headers
            }
        
        elif route_key == '$default':
            logger.info(f"Default route hit with body: {event.get('body', '{}')}")
            return {
                'statusCode': 200,
                'headers': headers
            }
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500, 
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
        
    return {
        'statusCode': 200,
        'headers': headers
    }