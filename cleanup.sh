#!/bin/bash

echo "Cleaning up resources..."
sam delete --stack-name serverless-twilio-cr-aws --no-prompts

echo "Removing deployment bucket..."
aws s3 rb s3://serverless-twilio-cr-aws-deployment --force

echo "Cleanup complete!"