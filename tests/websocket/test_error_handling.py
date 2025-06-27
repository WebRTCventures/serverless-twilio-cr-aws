import json
import os
import pytest
from unittest.mock import patch, MagicMock

# Import the lambda handler
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.websocket.app import lambda_handler


@pytest.fixture
def invalid_json_event():
    """Create a mock WebSocket event with invalid JSON"""
    return {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'routeKey': '$default',
            'domainName': 'test-domain.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        },
        'body': '{invalid json'
    }


@pytest.fixture
def missing_callsid_event():
    """Create a mock WebSocket event with missing callSid"""
    return {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'routeKey': '$default',
            'domainName': 'test-domain.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        },
        'body': json.dumps({
            'type': 'prompt',
            'voicePrompt': 'Hello, how are you?'
        })
    }


def test_invalid_json_handling(invalid_json_event, env_vars):
    """Test handling of invalid JSON in the request body"""
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        # Call the lambda handler
        response = lambda_handler(invalid_json_event, {})
        
        # Verify the response
        assert response['statusCode'] == 200
        
        # The function should handle the error gracefully
        mock_apigw.post_to_connection.assert_not_called()


def test_missing_callsid_handling(missing_callsid_event, env_vars):
    """Test handling of missing callSid in prompt messages"""
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        # Mock AI response
        with patch('src.websocket.app.ai_response') as mock_ai_response:
            mock_ai_response.return_value = "Hello there!"
            
            # Call the lambda handler
            response = lambda_handler(missing_callsid_event, {})
            
            # Verify the response - should now be 200 as we use connection ID as fallback
            assert response['statusCode'] == 200
            
            # Verify that post_to_connection was called
            mock_apigw.post_to_connection.assert_called_once()
            
            # Verify connection ID was used as the key
            call_args = mock_apigw.post_to_connection.call_args[1]
            assert call_args['ConnectionId'] == 'test-connection-id'


@patch('boto3.client')
def test_api_gateway_error_handling(mock_client, env_vars):
    """Test handling of API Gateway errors"""
    # Create a mock event
    event = {
        'requestContext': {
            'connectionId': 'test-connection-id',
            'routeKey': '$default',
            'domainName': 'test-domain.execute-api.us-east-1.amazonaws.com',
            'stage': 'prod'
        },
        'body': json.dumps({
            'type': 'prompt',
            'callSid': 'CA123456789abcdef123456789abcdef12',
            'voicePrompt': 'Hello'
        })
    }
    
    # Setup mock to raise an exception
    mock_apigw = MagicMock()
    mock_client.return_value = mock_apigw
    mock_apigw.post_to_connection.side_effect = Exception("Connection error")
    
    # Mock the AI response and session functions
    with patch('src.websocket.app.ai_response') as mock_ai_response:
        with patch('src.websocket.app.get_session') as mock_get_session:
            with patch('src.websocket.app.save_session') as mock_save_session:
                # Setup mocks
                mock_ai_response.return_value = "Hello there!"
                mock_get_session.return_value = [{"role": "system", "content": "You are a helpful assistant."}]
                
                # Call the lambda handler
                response = lambda_handler(event, {})
                
                # Verify the response
                assert response['statusCode'] == 200
                
                # Verify that the session was still updated despite the API Gateway error
                mock_save_session.assert_called_once()