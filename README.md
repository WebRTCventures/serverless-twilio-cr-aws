# Serverless Twilio CR AWS

This project creates:
- REST API with POST endpoint at `/setup`
- WebSocket API with connection management and message handling

## Architecture

- **API Gateway**: Handles HTTP and WebSocket requests
- **Lambda Functions**: Python 3.12 runtime for request processing
- **SAM**: Infrastructure as Code for AWS deployment

## Deploy

```bash
# One-step deployment
./deploy.sh
```

## Test REST API

```bash
curl -X POST https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/Prod/setup \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "message": "hello"}'
```

## Test WebSocket

Using wscat:
```bash
npm install -g wscat
wscat -c wss://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod
> {"action": "message", "message": "Hello WebSocket!"}
```

## Troubleshooting WebSocket

If you encounter 500 errors when connecting to the WebSocket:

1. Check CloudWatch logs for both API Gateway and the WebSocket Lambda function
2. Verify the WebSocket URL format is correct (should be `wss://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod`)
3. Make sure your message includes the `action` field set to `message`
4. Verify Lambda permissions are correctly set up for API Gateway to invoke the function
5. Check that the integration URI format is correct in the SAM template
6. Ensure the deployment and stage resources are properly linked

## Lambda Optimization

This project uses Lambda optimization techniques:
- Dynamic client initialization using event context
- Error handling with detailed logging
- Prioritizes reliability over cold start time

## Future Improvements

- Add unit tests with proper mocking of AWS services
- Add integration tests using SAM local

## Clean Up

```bash
sam delete --stack-name serverless-twilio-cr-aws --no-prompts
```