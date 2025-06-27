#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Print each command before executing
set -x

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

aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null || {
  echo "Creating S3 bucket: $BUCKET_NAME"
  aws s3 mb s3://$BUCKET_NAME --region $REGION
}

# Deploy with parameters
sam deploy

echo "Deployment complete!"
echo "Check the outputs for your API endpoints."
echo "TwiML Endpoint: Use the RestApiUrl output in your Twilio configuration"
echo "WebSocket Endpoint: The WebSocketUrl output is used internally by the TwiML endpoint"