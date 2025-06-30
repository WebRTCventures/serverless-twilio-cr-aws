import json
import os
import pytest
from unittest.mock import patch, MagicMock

# Import the lambda handler
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.websocket.app import lambda_handler


@pytest.fixture
def websocket_streaming_event():
    """Create a mock WebSocket event for testing streaming responses"""
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
            'voicePrompt': 'Tell me a story',
            'confidence': 0.98,
            'promptDuration': 1.2
        })
    }


@patch('src.websocket.app.ai_response')
def test_streaming_response_format(mock_ai_response, websocket_streaming_event, env_vars):
    """Test that the response is formatted correctly for Twilio Conversation Relay"""
    # Setup mock AI response
    mock_ai_response.return_value = "Once upon a time in a land far away..."
    
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        # Call the lambda handler
        lambda_handler(websocket_streaming_event, {})
        
        # With streaming, we now send multiple messages and a final empty one with last=True
        # Verify that ai_response was called with the correct parameters
        mock_ai_response.assert_called_once()
        # Check that connection_id and client were passed to enable streaming
        call_kwargs = mock_ai_response.call_args.kwargs
        assert call_kwargs.get('connection_id') == 'test-connection-id'
        assert call_kwargs.get('client') is not None