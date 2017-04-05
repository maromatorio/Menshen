
import boto3   # accessing AWS for DynamoDB session info
import time    # so we can sleep between Spark calls
import decimal # for incrementing the use_count
import random  # for randomizing responses

from boto3.session import Session
from boto3.dynamodb.conditions import Key # so we can save user info in Dynamo
from twilio.rest import TwilioRestClient  # Twilio client to process SMS
from spyrk import SparkCloud              # library to access the Spark

# create a DynamoDB session, pull out our secrets
dynamodb     = boto3.resource('dynamodb', 'us-east-1')
table_users  = dynamodb.Table('robot_users')
creds_dynamo = table_users.query(
    KeyConditionExpression=Key('fromNumber').eq('creds')
    )
TWILIO_SID   = creds_dynamo['Items'][0]['account_sid']   # Twilio SID
TWILIO_TOKEN = creds_dynamo['Items'][0]['auth_token']    # Twilio Token
TWILIO_NUM   = creds_dynamo['Items'][0]['twil_num']      # Twilio Number
ACCESS_TOKEN = creds_dynamo['Items'][0]['ACCESS_TOKEN']  # Spark Token
SET_SECURE   = creds_dynamo['Items'][0]['SetSecure']     # req passphrase?
PASSPHRASE   = creds_dynamo['Items'][0]['passphrase']    # the magic word

# create Twilio and Spark sessions using the above secrets
client = TwilioRestClient(TWILIO_SID, TWILIO_TOKEN)
spark  = SparkCloud(ACCESS_TOKEN)

def number_lookup(from_number):
    response_dynamo = table_users.query(
        KeyConditionExpression=Key('fromNumber').eq(from_number)
        )
    # new phone, who dis?
    if response_dynamo['Count'] == 0:
        table_users.put_item(Item={'fromNumber': from_number, 'use_count': 1, 'name': 'stranger'})
        name = "stranger"
        use_count = 1
    else:
        # yes, I manually enter the names
        try:
            name = response_dynamo['Items'][0]['name']
        except NameError:
            print("Error finding name")

        # how many times have they used the robot?
        try:
            use_count = response_dynamo['Items'][0]['use_count']
        except NameError:
            print("Error finding use_count")

        # increment the use_count in Dynamo
        use_count += 1
        table_users.update_item(
            Key={'fromNumber': from_number},
            UpdateExpression="set use_count = use_count+ :val",
            ExpressionAttributeValues={':val': decimal.Decimal(1)},
            ReturnValues="UPDATED_NEW"
            )
    return name, use_count

def open_sesame(from_num, name):
    print("Trying the door now.")
    txt_body = "The door should open for about 5 seconds, " + str(name)
    message = client.messages.create(
        body=txt_body,
        to=from_num,
        from_=TWILIO_NUM,
        )
    time.sleep(1)
    # open the door! for god's sake, open the door!
    spark.DoorbellCore.relay('R1', 'HIGH')
    # wait... wait for it....
    time.sleep(4)
    # ok now close the door
    spark.DoorbellCore.relay('R1', 'LOW')

def lambda_handler(event, context):
    twilio_resp = "none"

    # parse the SMS from Twilio
    message = event['body']
    from_number = event['fromNumber']

    # try to look up their info
    name, use_count = number_lookup(from_number)

    # log it to cloudwatch
    print("Number  : " + from_number)
    print("Name    : " + name)
    print("Message : " + message)

    # if the crappy SET_SECURE bit is on, require a simple passphrase to open
    if SET_SECURE == 'True':
        if PASSPHRASE not in message: # bad passphrase, do nothing
            print("***PASSPHRASE NOT PRESENT***")
            twilio_resp = "Sorry, you didn't use the passphrase."
            return twilio_resp

    #function to talk to the particle core and open the door
    open_sesame(from_number, name)

    twilio_resp = "Thanks for visiting!" + "\n\nUse Count: " +str(use_count)

    return twilio_resp
