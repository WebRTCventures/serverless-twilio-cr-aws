import json
import os
import pytest
import boto3
import botocore.session
from moto import mock_dynamodb
from unittest.mock import patch, MagicMock

# Set default region for boto3
boto3.setup_default_session(region_name='us-east-1')


@pytest.fixture
def env_vars(monkeypatch):
    """Set required environment variables for tests"""
    monkeypatch.setenv('SESSIONS_TABLE', 'TwilioSessions')
    monkeypatch.setenv('BEDROCK_MODEL_ID', 'amazon.nova-text-pro-v1')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test-access-key')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test-secret-key')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


@pytest.fixture(autouse=True)
def mock_aws_clients(monkeypatch):
    """Mock AWS clients to avoid real AWS calls during tests"""
    # Create mocks
    mock_bedrock = MagicMock()
    mock_table = MagicMock()
    
    # Setup mock streaming response
    mock_event = MagicMock()
    mock_chunk = MagicMock()
    mock_bytes = MagicMock()
    
    # Create mock event for converse_stream
    mock_event = MagicMock()
    mock_event.chunk = MagicMock()
    mock_event.chunk.message = MagicMock()
    mock_event.chunk.message.content = "This is a test response"
    
    # Mock the converse_stream response
    mock_bedrock.converse_stream.return_value = [mock_event]
    
    # Setup mock DynamoDB responses
    mock_table.get_item.return_value = {
        'Item': {
            'callSid': 'test-call-sid',
            'conversation': json.dumps([
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ])
        }
    }
    
    # Import the app module
    import src.websocket.app
    
    # Replace the global variables with mocks
    src.websocket.app.bedrock_runtime = mock_bedrock
    src.websocket.app.table = mock_table
    
    # Create a patch for boto3.client to return our mock for any new client creation
    def mock_boto3_client(service_name, *args, **kwargs):
        if service_name == 'bedrock-runtime':
            return mock_bedrock
        elif service_name == 'apigatewaymanagementapi':
            return MagicMock()
        else:
            # For any other service, return a basic mock
            return MagicMock()
    
    # Apply the patch
    monkeypatch.setattr(boto3, 'client', mock_boto3_client)
    
    return {
        'bedrock': mock_bedrock,
        'table': mock_table
    }

@pytest.fixture
def dynamodb_table(env_vars):
    """Create a mock DynamoDB table for testing"""
    with mock_dynamodb():
        # Create the DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='TwilioSessions',
            KeySchema=[
                {'AttributeName': 'callSid', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'callSid', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield table
        
        # Clean up
        table.delete()


@pytest.fixture
def websocket_connect_event():
    """Create a mock WebSocket $connect event"""
    return {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'routeKey': '$connect',
            'domainName': 'test-domain.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        }
    }


@pytest.fixture
def websocket_disconnect_event():
    """Create a mock WebSocket $disconnect event"""
    return {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'routeKey': '$disconnect',
            'domainName': 'test-domain.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        }
    }


@pytest.fixture
def websocket_setup_event():
    """Create a mock WebSocket setup message event based on Twilio Conversation Relay format"""
    return {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'routeKey': '$default',
            'domainName': 'test-domain.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        },
        'body': json.dumps({
            'type': 'setup',
            'callSid': 'CA123456789abcdef123456789abcdef12',
            'accountSid': 'AC123456789abcdef123456789abcdef12',
            'from': '+15551234567',
            'to': '+15557654321'
        })
    }


@pytest.fixture
def websocket_prompt_event():
    """Create a mock WebSocket prompt message event based on Twilio Conversation Relay format"""
    return {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'routeKey': '$default',
            'domainName': 'test-domain.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        },
        'body': json.dumps({
            'type': 'prompt',
            'callSid': 'CA123456789abcdef123456789abcdef12',
            'voicePrompt': 'Hello, how are you?',
            'confidence': 0.95,
            'promptDuration': 1.5
        })
    }


@pytest.fixture
def websocket_interrupt_event():
    """Create a mock WebSocket interrupt message event based on Twilio Conversation Relay format"""
    return {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'routeKey': '$default',
            'domainName': 'test-domain.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        },
        'body': json.dumps({
            'type': 'interrupt',
            'callSid': 'CA123456789abcdef123456789abcdef12'
        })
    }