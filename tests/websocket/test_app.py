import json
import os
import pytest
import boto3
from unittest.mock import patch, MagicMock

# Import the lambda handler
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.websocket.app import lambda_handler, get_session, save_session, ai_response


class TestWebSocketHandlers:
    """Tests for WebSocket event handlers"""
    
    def test_connect_handler(self, websocket_connect_event):
        """Test the WebSocket $connect handler"""
        response = lambda_handler(websocket_connect_event, {})
        assert response['statusCode'] == 200
    
    def test_disconnect_handler(self, websocket_disconnect_event):
        """Test the WebSocket $disconnect handler"""
        response = lambda_handler(websocket_disconnect_event, {})
        assert response['statusCode'] == 200
    
    def test_setup_handler(self, websocket_setup_event, mock_aws_clients):
        """Test the WebSocket setup message handler"""
        with patch('boto3.client') as mock_client:
            mock_apigw = MagicMock()
            mock_client.return_value = mock_apigw
            
            response = lambda_handler(websocket_setup_event, {})
            assert response['statusCode'] == 200
            mock_aws_clients['table'].put_item.assert_called_once()
    
    @patch('src.websocket.app.ai_response')
    def test_prompt_handler(self, mock_ai_response, websocket_prompt_event, mock_aws_clients):
        """Test the WebSocket prompt message handler"""
        mock_ai_response.return_value = "I'm doing well, thank you for asking!"
        
        with patch('boto3.client') as mock_client:
            mock_apigw = MagicMock()
            mock_client.return_value = mock_apigw
            
            response = lambda_handler(websocket_prompt_event, {})
            assert response['statusCode'] == 200
            
            mock_ai_response.assert_called_once()
            call_kwargs = mock_ai_response.call_args.kwargs
            assert call_kwargs.get('connection_id') == 'test-connection-id'
            assert call_kwargs.get('client') is not None
            mock_aws_clients['table'].put_item.assert_called()
    
    def test_interrupt_handler(self, websocket_interrupt_event):
        """Test the WebSocket interrupt message handler"""
        with patch('boto3.client') as mock_client:
            mock_apigw = MagicMock()
            mock_client.return_value = mock_apigw
            
            response = lambda_handler(websocket_interrupt_event, {})
            assert response['statusCode'] == 200


class TestSessionManagement:
    """Tests for session management functions"""
    
    def test_get_session_new(self, mock_aws_clients, env_vars):
        """Test getting a new session"""
        mock_aws_clients['table'].get_item.return_value = {}
        
        conversation = get_session('new-call-sid')
        assert len(conversation) == 1
        assert conversation[0]['role'] == 'system'
    
    def test_get_session_existing(self, mock_aws_clients, env_vars):
        """Test getting an existing session"""
        conversation = get_session('existing-call-sid')
        assert len(conversation) == 3
        assert conversation[0]['role'] == 'system'
        assert conversation[1]['role'] == 'user'
        assert conversation[2]['role'] == 'assistant'


class TestAIResponse:
    """Tests for AI response function"""
    
    def test_ai_response(self, mock_aws_clients, env_vars):
        """Test the AI response function"""
        mock_client = MagicMock()
        connection_id = "test-connection-id"
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ]
        
        response = ai_response(messages=messages, connection_id=connection_id, client=mock_client)
        
        assert "This is a test response" in response
        mock_aws_clients['bedrock'].converse_stream.assert_called_once()
        
        call_kwargs = mock_aws_clients['bedrock'].converse_stream.call_args.kwargs
        assert "amazon.nova" in call_kwargs['modelId']
        assert 'messages' in call_kwargs
        assert 'system' in call_kwargs
        assert 'inferenceConfig' in call_kwargs
    
    def test_ai_response_error(self, mock_aws_clients, env_vars):
        """Test the AI response function with an error"""
        mock_aws_clients['bedrock'].converse_stream.side_effect = Exception("Test error")
        
        mock_client = MagicMock()
        connection_id = "test-connection-id"
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ]
        
        response = ai_response(messages=messages, connection_id=connection_id, client=mock_client)
        
        assert "I'm sorry" in response
        
        mock_client.post_to_connection.assert_called_once()
        call_kwargs = mock_client.post_to_connection.call_args.kwargs
        assert call_kwargs['ConnectionId'] == connection_id
        data = json.loads(call_kwargs['Data'])
        assert data['last'] is True
        assert "I'm sorry" in data['token']