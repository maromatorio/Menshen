# Menshen  

This app uses [Twilio](https://www.twilio.com/) to ping a [Particle Core](https://www.particle.io/) with an attached relay, buzzing the building's front door open. A user sends a message (passcodes optional) using SMS to a Twilio phone number which sends a request to an Amazon API Gateway endpoint that triggers a Lambda function. This app uses AWS Lambda, API Gateway, and DynamoDB. Most of my work is based on [this project](https://github.com/awslabs/lambda-apigateway-twilio-tutorial).  

### AWS Lambda

[Lambda](https://aws.amazon.com/lambda/) is a compute service that runs your code in response to events. Events are triggered or invoked by resources in your AWS environment or via API Gateway. Here our Lambda function is triggered by an API Gateway endpoint that Twilio hits after an SMS is received. The Lambda function is responsible for hitting the Particle Core and returning a response to Twilio.

### Amazon API Gateway
[API Gateway](https://aws.amazon.com/api-gateway/) is a fully managed API as a service where you can create, publish, maintain, monitor, and secure APIs at any scale. In this app, we use API Gateway to create an endpoint for Twilio to make a GET request. API Gateway transforms Twilio's URL encoded request into a JSON object, so that Lambda can process it. Lastly, API Gateway takes Lambda's response and builds an XML object for Twilio.

### Amazon DynamoDB & Amazon S3
[DynamoDB](https://aws.amazon.com/dynamodb/) is Amazon's non-relational database service. This app leverages DynamoDB to store user data.
