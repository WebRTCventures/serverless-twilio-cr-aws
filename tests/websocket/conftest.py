import json
import os
import pytest
import boto3
import botocore.session
from moto import mock_dynamodb

# Set default region for boto3
boto3.setup_default_session(region_name='us-east-1')


@pytest.fixture
def env_vars(monkeypatch):
    """Set required environment variables for tests"""
    monkeypatch.setenv('SESSIONS_TABLE', 'TwilioSessions')
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-4o-mini')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-api-key')
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test-access-key')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test-secret-key')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')


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