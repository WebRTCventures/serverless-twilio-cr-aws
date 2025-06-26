#!/bin/bash

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

# Deploy without guided mode
sam deploy

echo "Deployment complete!"
echo "Check the outputs for your API endpoints."