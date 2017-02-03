
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
        table_users.put_item(Item={'fromNumber': from_number, 'use_count': 1})
        name = "stranger"
        use_count = 1
    else:
        # yes, I manually enter the names
        name      = response_dynamo['Items'][0]['name']
        # how many times have they used the robot?
        use_count = response_dynamo['Items'][0]['use_count']
        # increment the use_count in Dynamo
        use_count += 1
        table_users.update_item(
            Key={'fromNumber': from_number},
            UpdateExpression="set use_count = use_count+ :val",
            ExpressionAttributeValues={':val': decimal.Decimal(1)},
            ReturnValues="UPDATED_NEW"
            )
    return name, use_count

def open_sesame():
    print("Trying the door now.")
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

    # if the SET_SECURE bit is on, require a passphrase to open
    if SET_SECURE == 'True':
        if PASSPHRASE not in message: # bad passphrase, do nothing
            print("***PASSPHRASE NOT PRESENT***")
            twilio_resp = "Sorry, you didn't use the passphrase."
            return twilio_resp

    open_sesame()

    if name == 'Anderson':
        Ando = [
            "God dammit Anderson, what do you want now?",
            "Who invited this douche?",
            "Great, there goes the neighborhood.",
            "Arturo is going to be mad jealous.",
            "Fucking Anderson is here again?",
            "Quick, hide the minorities!"
        ]
        twilio_resp = random.choice(Ando)

    elif name == 'Allison':
        Allison = [
            "Welcome home, queen!",
            "Hey there good lookin'",
            "Did you forget your key?"
        ]
        twilio_resp = random.choice(Allison)

    elif name == 'Serg':
        Serg = [
            "YASSSSSSSSSSSS!",
            "What up neighbor?",
            "Welcome home buddy!"
        ]
        twilio_resp = random.choice(Serg)

    else:
        twilio_resp = "The door should open for about 5 seconds, " + str(name)

    twilio_resp = twilio_resp + "\n\nUse Count: " +str(use_count)
    return twilio_resp
