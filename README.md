# Menshen  

[Menshen](https://en.wikipedia.org/wiki/Menshen), or door gods, are divine guardians of doors and gates in Chinese folk religions, used to protect against evil influences or to encourage the entrance of positive ones. This app is designed to solve a personal annoyance - I live an old New York brownstone with a [typical 4-wire intercom](http://www.intercom-parts.com/IR204-Intercom.html) and a common front door. I have a limited number of keys, so if I'm not in the apartment to buzz a guest/cleaning/delivery person inside, the only option is to give them my key.  

This app solves my problem by allowing a user to send a message via SMS (passcodes optional) to my [Twilio](https://www.twilio.com/) number, which in turn sends a request to an Amazon API Gateway endpoint that triggers a Lambda function. The Lambda function communicates via REST API with a [Particle Core](https://www.particle.io/) in my apartment, which uses an [attached relay](https://docs.particle.io/datasheets/particle-shields/#relay-shield) that's wired to my intercom to buzz my building's front door open.

This app was originally based on [this project](https://github.com/awslabs/lambda-apigateway-twilio-tutorial).  

## Dependencies
Previously, I used [spyrk](https://github.com/Alidron/spyrk) and the [Twilio REST API](https://github.com/twilio/twilio-python/) Python library to communicate with the ParticleCloud API and Twilio API respectively. However, managing dependencies was getting more difficult and with Python 2.x going EOL shortly, I decided to drop all external dependencies and use only what came in the base Lambda setup, so all my API communications are just form-encoded calls using urllib.

### ParticleCloud
[ParticleCloud](https://docs.particle.io/reference/device-cloud/api/) tells my Core/Photon when to close/open the relay. I have the two wires that connect to the "Door" button on my intercom also running into one of the simple mechanical relays - when the relay is closed, it's the same effect as pushing the button (the building's front door gets buzzed open).

### Twilio
Twilio allows the Lambda to receive (and send) SMS messages to the user (and me in the event of failures or unauthorized use).

### Lambda
[Lambda](https://aws.amazon.com/lambda/) is a compute service that runs your code in response to events. Events are triggered or invoked by resources in your AWS environment or via API Gateway. Here our Lambda function is triggered by an API Gateway endpoint that Twilio hits after an SMS is received. The Lambda function is responsible for hitting the Particle Core and returning a response to Twilio. Secret values, including the API tokens for Twilio and ParticleCloud, are stored as encrypted environment variables in the Lambda function.

### Amazon API Gateway
[API Gateway](https://aws.amazon.com/api-gateway/) is a fully managed API as a service where you can create, publish, maintain, monitor, and secure APIs at any scale. In this app, I use API Gateway to create an endpoint for Twilio to make a GET request. API Gateway transforms Twilio's URL encoded request into a JSON object, so that Lambda can process it. Lastly, API Gateway takes the Lambda function's response (return value) and builds an XML object for Twilio.

### Amazon DynamoDB & Amazon S3
[DynamoDB](https://aws.amazon.com/dynamodb/) is Amazon's non-relational database service. This app leverages DynamoDB to store user data.

## TODO
+ Move to [Serverless Application Model](https://github.com/awslabs/serverless-application-model)
+ Additional validation, better error/exception handling
