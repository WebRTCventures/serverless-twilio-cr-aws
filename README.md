# Serverless Twilio Conversation Relay with AWS

This project implements a serverless backend for Twilio Conversation Relay, allowing you to create voice assistants powered by Amazon Bedrock models.

This project creates:
- REST API with POST endpoint at `/twiml` that returns TwiML for Twilio
- WebSocket API that handles real-time communication with Twilio Conversation Relay
- DynamoDB table for storing conversation sessions

## Architecture

- **API Gateway**: Handles HTTP and WebSocket requests
- **Lambda Functions**: Python 3.12 runtime for request processing
- **DynamoDB**: Stores conversation sessions
- **Amazon Bedrock**: Provides AI responses with streaming capability
- **SAM**: Infrastructure as Code for AWS deployment

## Prerequisites

- AWS CLI configured with appropriate permissions
- SAM CLI installed
- Python 3.12
- AWS account with Amazon Bedrock access
- Twilio account with a phone number configured for Voice

## Deploy

```bash
# Make the deployment script executable
chmod +x deploy.sh

# One-step deployment (uses default Bedrock model or BEDROCK_MODEL_ID env var)
./deploy.sh
```

## Configure Twilio

1. Log in to your Twilio account
2. Navigate to Phone Numbers > Manage > Active Numbers
3. Select the phone number you want to use
4. Under "Voice & Fax" section, set the following:
   - When a call comes in: Webhook
   - URL: Your TwiML endpoint URL (from the SAM deployment outputs)
   - HTTP Method: POST
5. Save your changes

## Test the Voice Assistant

1. Call your Twilio phone number
2. You should hear the welcome greeting
3. Start speaking and the assistant will respond

## Monitoring and Debugging

- Check CloudWatch Logs for both Lambda functions
- Examine DynamoDB for stored conversation sessions
- Use the AWS Lambda console to test functions with sample events

## Troubleshooting

If you encounter issues:

1. Check CloudWatch logs for both Lambda functions
2. Verify the TwiML endpoint URL is correctly configured in Twilio
3. Ensure your AWS account has access to the Amazon Bedrock model you're using
4. Check that the WebSocket URL in the TwiML response matches your API Gateway WebSocket URL
5. Verify Lambda permissions are correctly set up for DynamoDB access
6. Check that the integration URI format is correct in the SAM template

## Customization Options

- Change the welcome greeting by modifying the `WELCOME_GREETING` variable in the POST function
- Modify the system prompt by updating the `SYSTEM_PROMPT` variable in the WebSocket function
- Change the Bedrock model by updating the `BedrockModelId` parameter during deployment
- Adjust the TTL for conversation sessions (default is 24 hours)

## Lambda Optimization

This project uses Lambda optimization techniques:
- Initializes clients outside the handler function
- Uses DynamoDB for persistent session storage
- Implements proper error handling with detailed logging
- Configures appropriate timeout and memory settings

## Features

- Streaming responses for more natural conversation flow
- Implement conversation history management (deletion, export)
- Add support for multiple languages
- Implement authentication for the TwiML endpoint
- Add unit tests with proper mocking of AWS services

## Clean Up

```bash
# Make the cleanup script executable
chmod +x cleanup.sh

# Run the cleanup script
./cleanup.sh

# Or use SAM directly
sam delete --stack-name serverless-twilio-cr-aws --no-prompts
```