#!/bin/bash

echo "Installing dependencies..."

# Install dependencies for WebSocket function
echo "Installing WebSocket function dependencies..."
cd src/websocket
pip install -r requirements.txt
cd ../..

echo "Building SAM application..."
sam build

echo "Deploying SAM application..."

# Create S3 bucket if it doesn't exist
BUCKET_NAME="serverless-twilio-cr-aws-deployment"
REGION="us-east-1"

aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null
if [ $? -ne 0 ]; then
  echo "Creating S3 bucket: $BUCKET_NAME"
  aws s3 mb s3://$BUCKET_NAME --region $REGION
fi

# Prompt for OpenAI API Key if not set
if [ -z "$OPENAI_API_KEY" ]; then
  read -sp "Enter your OpenAI API Key: " OPENAI_API_KEY
  echo ""
fi

# Deploy with parameters
sam deploy --parameter-overrides OpenAIApiKey=$OPENAI_API_KEY

echo "Deployment complete!"
echo "Check the outputs for your API endpoints."
echo "TwiML Endpoint: Use the RestApiUrl output in your Twilio configuration"
echo "WebSocket Endpoint: The WebSocketUrl output is used internally by the TwiML endpoint"