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
        
        # Verify the response format
        mock_apigw.post_to_connection.assert_called_once()
        call_args = mock_apigw.post_to_connection.call_args[1]
        
        # Check that the response is in the correct format
        data = json.loads(call_args['Data'])
        assert 'type' in data
        assert data['type'] == 'text'
        assert 'token' in data
        assert data['token'] == "Once upon a time in a land far away..."
        assert 'last' in data
        assert data['last'] is True


@patch('src.websocket.app.get_session')
@patch('src.websocket.app.save_session')
@patch('src.websocket.app.ai_response')
def test_empty_prompt_handling(mock_ai_response, mock_save_session, mock_get_session, websocket_streaming_event, env_vars):
    """Test handling of empty voice prompts"""
    # Modify the event to have an empty prompt
    event_data = json.loads(websocket_streaming_event['body'])
    event_data['voicePrompt'] = ''
    websocket_streaming_event['body'] = json.dumps(event_data)
    
    # Setup mock session
    mock_get_session.return_value = [{"role": "system", "content": "You are a helpful assistant."}]
    
    # Setup mock AI response
    mock_ai_response.return_value = "I didn't catch that. Could you please repeat?"
    
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        # Call the lambda handler
        response = lambda_handler(websocket_streaming_event, {})
        
        # Verify the response
        assert response['statusCode'] == 200
        
        # With our updated code, we now handle empty prompts by using a default message
        # So save_session should be called
        mock_apigw.post_to_connection.assert_called_once()
        call_args = mock_apigw.post_to_connection.call_args[1]
        data = json.loads(call_args['Data'])
        assert data['token'] == "I didn't catch that. Could you please repeat?"