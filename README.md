# Menshen  

This app is designed to solve a personal annoyance - I live in an old New York apartment with a [typical 4-wire intercom](https://www.intercom-parts.com/apartment-stations/) and a shared front door at the street. I have a limited number of keys, so if I'm not in the apartment to buzz a guest/cleaning/delivery person inside, the only option is to give them my key.

This app solves my problem by allowing a user to send a message via SMS (passcodes optional) to a [Twilio](https://www.twilio.com/) number, which in turn sends a request to an Amazon API Gateway endpoint that triggers a Lambda function. The Lambda function communicates via REST API with a [Particle Core](https://www.particle.io/) in my apartment, which uses an ~~[attached relay](https://docs.particle.io/datasheets/particle-shields/#relay-shield)~~ that's wired to my intercom to buzz my building's front door open. As of 2021, the Core and original Relay Shield are no longer available; new hardware would be the [Photon](https://store.particle.io/products/photon?_pos=1&_sid=d0ce7703e&_ss=r) and [this 3rd Party Relay board](https://www.tindie.com/products/brlabelectronics/particle-photon-relay-shield-2-channel/).

This app was originally based on [this project](https://github.com/awslabs/lambda-apigateway-twilio-tutorial).  

## DISCLAIMERS
This is not a high security system. It only buzzes open my building's front door, not any individual apartments. Even using the Set-Secure option here is likely not very secure. Use at your own peril.

## Dependencies
Previously, I used [spyrk](https://github.com/Alidron/spyrk) and the [Twilio REST API](https://github.com/twilio/twilio-python/) Python library to communicate with the ParticleCloud API and Twilio API respectively. However, managing packages was a pain and with Python 2.x going EOL, I decided to drop external dependencies and use only what came in the base Lambda setup. Now, my API communications are just form-encoded calls using urllib.

### ParticleCloud
[ParticleCloud](https://docs.particle.io/reference/device-cloud/api/) tells my Core/Photon when to close/open the relay. I have the two wires that connect to the "Door" button on my intercom also running into one of the simple mechanical relays - when the relay is closed, it's the same effect as pushing the button (the building's front door gets buzzed open).

### Twilio
Twilio allows the Lambda to exchange SMS messages with the user (and me in the event of failures or unauthorized use). This is the most costly part of the whole setup (I think it runs me something like a nickel per use), but Twilio helpfully provides test credentials that I can freely use for API validation.

### Lambda
[Lambda](https://aws.amazon.com/lambda/) is a compute service that runs your code in response to events. Events are triggered or invoked by resources in your AWS environment or via API Gateway. Here our Lambda function is triggered by an API Gateway endpoint that Twilio hits after an SMS is received. The Lambda function is responsible for hitting the Particle Core and returning a response to Twilio. Secret values, including the API tokens for Twilio and ParticleCloud, are stored as encrypted environment variables in the Lambda function.

### Amazon API Gateway
[API Gateway](https://aws.amazon.com/api-gateway/) is a fully managed API as a service where you can create, publish, maintain, monitor, and secure APIs at any scale. In this app, I use API Gateway to create an endpoint for Twilio to make a GET request. API Gateway transforms Twilio's URL encoded request into a JSON object, so that Lambda can process it. Lastly, API Gateway takes the Lambda function's response (return value) and builds an XML object for Twilio.

### Amazon DynamoDB & Amazon S3
[DynamoDB](https://aws.amazon.com/dynamodb/) is Amazon's non-relational database service. This app leverages DynamoDB to store user data (and previously, environment variables).

## Test
I created a second Lambda function, lambda_test.py, to periodically test the APIs that I use and make sure they're still working. This is currently configured to run every 15 minutes and triggers a CloudWatch alarm if it fails, which in turn notifies me via SNS. Note that currently these tests fail more often than expected, despite the system typically still functioning during periods when the test throws errors.

## Build
I am currently using some [GitHub Actions](https://github.com/actions/setup-python) as a cobbled-together CI/CD to build, test, and deploy code to my Lambda functions; see .github/workflows for this code.

## TODO
+ Maybe move to [Serverless Application Model](https://github.com/awslabs/serverless-application-model)
+ More detailed documentation on wiring, setup, and initial configs
+ Add support for multiple phone numbers/relay devices
