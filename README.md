# Serverless Twilio Conversation Relay with AWS

A serverless backend for Twilio Conversation Relay using Amazon Bedrock for AI voice assistants.

## Components
- REST API (`/twiml`) - Returns TwiML for Twilio
- WebSocket API - Handles real-time communication
- DynamoDB - Stores conversation sessions
- Amazon Bedrock - Provides AI responses with streaming

## Prerequisites
- AWS CLI with appropriate permissions
- SAM CLI
- Python 3.12
- AWS account with Amazon Bedrock access
- Twilio account with a phone number

## Quick Start

```bash
chmod +x deploy.sh
./deploy.sh
```

## Configure Twilio
1. Log in to Twilio account
2. Navigate to Phone Numbers > Active Numbers
3. Set webhook URL to your TwiML endpoint (from deployment outputs)
4. Set HTTP Method to POST

## Testing
Call your Twilio number and start speaking with the assistant.

## Customization
- `WELCOME_GREETING` in POST function
- `SYSTEM_PROMPT` in WebSocket function
- `BedrockModelId` parameter during deployment in template.yml
- `BUCKET_NAME` in `deploy.sh`

## Clean Up
```bash
chmod +x cleanup.sh
./cleanup.sh
```