import json
import os
import pytest
import boto3
from unittest.mock import patch, MagicMock

# Import the lambda handler
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.websocket.app import lambda_handler, get_session, save_session, ai_response


def test_connect_handler(websocket_connect_event):
    """Test the WebSocket $connect handler"""
    response = lambda_handler(websocket_connect_event, {})
    assert response['statusCode'] == 200


def test_disconnect_handler(websocket_disconnect_event):
    """Test the WebSocket $disconnect handler"""
    response = lambda_handler(websocket_disconnect_event, {})
    assert response['statusCode'] == 200


def test_setup_handler(websocket_setup_event, mock_aws_clients):
    """Test the WebSocket setup message handler"""
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        response = lambda_handler(websocket_setup_event, {})
        
        # Verify the response
        assert response['statusCode'] == 200
        
        # Verify save_session was called with the correct parameters
        mock_aws_clients['table'].put_item.assert_called_once()


@patch('src.websocket.app.ai_response')
def test_prompt_handler(mock_ai_response, websocket_prompt_event, mock_aws_clients):
    """Test the WebSocket prompt message handler"""
    # Setup mock AI response
    mock_ai_response.return_value = "I'm doing well, thank you for asking!"
    
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        response = lambda_handler(websocket_prompt_event, {})
        
        # Verify the response
        assert response['statusCode'] == 200
        
        # Verify that ai_response was called with the correct parameters
        mock_ai_response.assert_called_once()
        # Check that connection_id and client were passed to enable streaming
        call_kwargs = mock_ai_response.call_args.kwargs
        assert call_kwargs.get('connection_id') == 'test-connection-id'
        assert call_kwargs.get('client') is not None
        
        # Verify save_session was called
        mock_aws_clients['table'].put_item.assert_called()


def test_interrupt_handler(websocket_interrupt_event):
    """Test the WebSocket interrupt message handler"""
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        response = lambda_handler(websocket_interrupt_event, {})
        
        # Verify the response
        assert response['statusCode'] == 200


def test_get_session_new(mock_aws_clients, env_vars):
    """Test getting a new session"""
    # Configure mock to return empty response for new session
    mock_aws_clients['table'].get_item.return_value = {}
    
    conversation = get_session('new-call-sid')
    assert len(conversation) == 1
    assert conversation[0]['role'] == 'system'


def test_get_session_existing(mock_aws_clients, env_vars):
    """Test getting an existing session"""
    # The mock is already configured to return a session with 3 messages
    conversation = get_session('existing-call-sid')
    assert len(conversation) == 3
    assert conversation[0]['role'] == 'system'
    assert conversation[1]['role'] == 'user'
    assert conversation[2]['role'] == 'assistant'


def test_ai_response(mock_aws_clients, env_vars):
    """Test the AI response function"""
    # The mock_aws_clients fixture already sets up the mock response
    
    # Create mock client and connection_id
    mock_client = MagicMock()
    connection_id = "test-connection-id"
    
    # Test the function
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
    
    response = ai_response(messages=messages, connection_id=connection_id, client=mock_client)
    
    # Verify the response
    assert "This is a test response" in response
    mock_aws_clients['bedrock'].converse_stream.assert_called_once()
    
    # Verify the model ID and parameters
    call_kwargs = mock_aws_clients['bedrock'].converse_stream.call_args.kwargs
    assert "amazon.nova" in call_kwargs['modelId']
    assert 'messages' in call_kwargs
    assert 'system' in call_kwargs


def test_ai_response_error(mock_aws_clients, env_vars):
    """Test the AI response function with an error"""
    # Setup mock Bedrock response to raise an exception
    mock_aws_clients['bedrock'].converse_stream.side_effect = Exception("Test error")
    
    # Create mock client and connection_id
    mock_client = MagicMock()
    connection_id = "test-connection-id"
    
    # Test the function
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
    
    response = ai_response(messages=messages, connection_id=connection_id, client=mock_client)
    
    # Verify the response
    assert "I'm sorry" in response
    
    # Verify that an error message was sent to the client
    mock_client.post_to_connection.assert_called_once()
    call_kwargs = mock_client.post_to_connection.call_args.kwargs
    assert call_kwargs['ConnectionId'] == connection_id
    data = json.loads(call_kwargs['Data'])
    assert data['last'] is True
    assert "I'm sorry" in data['token']