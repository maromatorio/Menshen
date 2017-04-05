# Menshen  

[Menshen](https://en.wikipedia.org/wiki/Menshen), or door gods, are divine guardians of doors and gates in Chinese folk religions, used to protect against evil influences or to encourage the entrance of positive ones. This app is designed to solve a personal annoyance - I live an old New York brownstone with a [typical 4-wire intercom](http://www.intercom-parts.com/IR204-Intercom.html) and a high-security lock on the common front door. I have a very limited number of keys, so if I'm not in the apartment to buzz a guest/cleaning/delivery person inside, the only option is to give them my key.  

This app solves my problem by allowing a user to send a message (passcodes optional) via SMS to my [Twilio](https://www.twilio.com/) number, which in turn sends a request to an Amazon API Gateway endpoint that triggers a Lambda function. The Lambda function communicates via REST API with a [Particle Core](https://www.particle.io/) in my apartment, which uses an [attached relay](https://docs.particle.io/datasheets/particle-shields/#relay-shield) that's wired to my intercom to buzz my building's front door open.

Most of my work is based on [this project](https://github.com/awslabs/lambda-apigateway-twilio-tutorial).  

## Spyrk
I use [spyrk](https://github.com/Alidron/spyrk) to connect to the Particle Core and tell it when to close/open the relay. Closing the relay is the same

## Twilio
My Lambda uses the [Twilio REST API](https://github.com/twilio/twilio-python/) Python library to send a message.

## AWS
### Lambda
[Lambda](https://aws.amazon.com/lambda/) is a compute service that runs your code in response to events. Events are triggered or invoked by resources in your AWS environment or via API Gateway. Here our Lambda function is triggered by an API Gateway endpoint that Twilio hits after an SMS is received. The Lambda function is responsible for hitting the Particle Core and returning a response to Twilio.

### Amazon API Gateway
[API Gateway](https://aws.amazon.com/api-gateway/) is a fully managed API as a service where you can create, publish, maintain, monitor, and secure APIs at any scale. In this app, I use API Gateway to create an endpoint for Twilio to make a GET request. API Gateway transforms Twilio's URL encoded request into a JSON object, so that Lambda can process it. Lastly, API Gateway takes Lambda's response and builds an XML object for Twilio.

### Amazon DynamoDB & Amazon S3
[DynamoDB](https://aws.amazon.com/dynamodb/) is Amazon's non-relational database service. This app leverages DynamoDB to store user data and creds (at least for now).

## TODO
+ Move to [Serverless Application Model](https://github.com/awslabs/serverless-application-model)
+ Consider some actual security
+ Additional validation, better error handling
+ Alternate function to do customized messages?
+ Look into asking new users for their name (appropriately sanitized)
+ Figure out proper dependency handling (e.g., staying up to date on Twilio REST API)
