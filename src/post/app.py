import json
from datetime import datetime

# Initialize any static resources outside the handler
# for Lambda optimization

def lambda_handler(event, context):
    """
    Handle POST requests to /setup endpoint
    
    Parameters:
    - event: API Gateway event
    - context: Lambda context
    
    Returns:
    - API Gateway response object
    """
    body = json.loads(event.get('body', '{}'))
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Setup request received',
            'data': body,
            'timestamp': datetime.utcnow().isoformat()
        })
    }