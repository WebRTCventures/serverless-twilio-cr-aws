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


def test_setup_handler(websocket_setup_event, dynamodb_table):
    """Test the WebSocket setup message handler"""
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        response = lambda_handler(websocket_setup_event, {})
        
        # Verify the response
        assert response['statusCode'] == 200
        
        # Verify the session was created in DynamoDB
        item = dynamodb_table.get_item(Key={'callSid': 'CA123456789abcdef123456789abcdef12'})
        assert 'Item' in item
        conversation = json.loads(item['Item']['conversation'])
        assert len(conversation) == 1
        assert conversation[0]['role'] == 'system'


@patch('src.websocket.app.ai_response')
def test_prompt_handler(mock_ai_response, websocket_prompt_event, dynamodb_table):
    """Test the WebSocket prompt message handler"""
    # Setup mock AI response
    mock_ai_response.return_value = "I'm doing well, thank you for asking!"
    
    # Setup initial session
    save_session('CA123456789abcdef123456789abcdef12', [{"role": "system", "content": "You are a helpful assistant."}])
    
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        response = lambda_handler(websocket_prompt_event, {})
        
        # Verify the response
        assert response['statusCode'] == 200
        
        # Verify the AI response was sent to the client
        mock_apigw.post_to_connection.assert_called_once()
        call_args = mock_apigw.post_to_connection.call_args[1]
        assert call_args['ConnectionId'] == 'test-connection-id'
        
        data = json.loads(call_args['Data'])
        assert data['type'] == 'text'
        assert data['token'] == "I'm doing well, thank you for asking!"
        assert data['last'] is True
        
        # Verify the conversation was updated in DynamoDB
        item = dynamodb_table.get_item(Key={'callSid': 'CA123456789abcdef123456789abcdef12'})
        assert 'Item' in item
        conversation = json.loads(item['Item']['conversation'])
        assert len(conversation) == 3  # system + user + assistant
        assert conversation[1]['role'] == 'user'
        assert conversation[1]['content'] == 'Hello, how are you?'
        assert conversation[2]['role'] == 'assistant'
        assert conversation[2]['content'] == "I'm doing well, thank you for asking!"


def test_interrupt_handler(websocket_interrupt_event):
    """Test the WebSocket interrupt message handler"""
    with patch('boto3.client') as mock_client:
        # Mock the API Gateway Management API client
        mock_apigw = MagicMock()
        mock_client.return_value = mock_apigw
        
        response = lambda_handler(websocket_interrupt_event, {})
        
        # Verify the response
        assert response['statusCode'] == 200


def test_get_session_new(dynamodb_table, env_vars):
    """Test getting a new session"""
    conversation = get_session('new-call-sid')
    assert len(conversation) == 1
    assert conversation[0]['role'] == 'system'


def test_get_session_existing(dynamodb_table, env_vars):
    """Test getting an existing session"""
    # Create a session
    test_conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    save_session('existing-call-sid', test_conversation)
    
    # Get the session
    conversation = get_session('existing-call-sid')
    assert len(conversation) == 3
    assert conversation[0]['role'] == 'system'
    assert conversation[1]['role'] == 'user'
    assert conversation[2]['role'] == 'assistant'


@patch('src.websocket.app.openai')
def test_ai_response(mock_openai_module, env_vars):
    """Test the AI response function"""
    # Setup mock OpenAI client
    mock_client = MagicMock()
    mock_openai_module.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="This is a test response"))]
    )
    
    # Test the function
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
    
    response = ai_response(messages)
    
    # Verify the response
    assert response == "This is a test response"
    mock_openai_module.chat.completions.create.assert_called_once_with(
        model='gpt-4o-mini',
        messages=messages
    )


@patch('src.websocket.app.openai')
def test_ai_response_error(mock_openai_module, env_vars):
    """Test the AI response function with an error"""
    # Setup mock OpenAI response to raise an exception
    mock_openai_module.chat.completions.create.side_effect = Exception("Test error")
    
    # Test the function
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
    
    response = ai_response(messages)
    
    # Verify the response
    assert "I'm sorry" in response