import boto3   # accessing AWS for DynamoDB session info
import time    # so we can sleep between Spark calls
import decimal # for incrementing the use count
import random  # for randomizing responses

from boto3.session import Session
from boto3.dynamodb.conditions import Key # so we can save user info in Dynamo
from twilio.rest import TwilioRestClient  # Twilio client to process SMS
from spyrk import SparkCloud              # library to access the Spark

# create a DynamoDB session, pull out our secrets
# todo - testing/error handling for object creation
dynamodb     = boto3.resource('dynamodb', 'us-east-1')
users_table  = dynamodb.Table('robot_users')
creds_dynamo = users_table.query(
    KeyConditionExpression=Key('fromNumber').eq('creds')
    )
# globals
TWILIO_SID   = creds_dynamo['Items'][0]['account_sid']   # Twilio SID
TWILIO_TOKEN = creds_dynamo['Items'][0]['auth_token']    # Twilio Token
TWILIO_NUM   = creds_dynamo['Items'][0]['twil_num']      # Twilio Number
ACCESS_TOKEN = creds_dynamo['Items'][0]['ACCESS_TOKEN']  # Particle Token
SUPPORT_NUM  = creds_dynamo['Items'][0]['sup_num']       # Support number
SET_SECURE   = creds_dynamo['Items'][0]['SetSecure']     # req passphrase?
PASSPHRASE   = creds_dynamo['Items'][0]['passphrase']    # the magic word

# create Twilio and Spark sessions using the above secrets
client = TwilioRestClient(TWILIO_SID, TWILIO_TOKEN)
spark  = SparkCloud(ACCESS_TOKEN)

def number_lookup(from_num):
    response_dynamo = users_table.query(
        KeyConditionExpression=Key('fromNumber').eq(from_num)
        )
    # new phone, who dis?
    if response_dynamo['Count'] == 0:
        new_entry = {'fromNumber': from_num, 'use_count': 1, 'name': 'stranger'}
        users_table.put_item(Item=new_entry)
        name = "A stranger"
        use_count = 1
    else:
        # yes, I manually enter the names
        try:
            name = response_dynamo['Items'][0]['name']
        except NameError as e:
            print("Error finding name for " + str(from_num))

        # how many times have they used the robot?
        try:
            use_count = response_dynamo['Items'][0]['use_count']
        except NameError as e:
            print("Error finding use_count for " + str(from_num))

        # increment the use_count in Dynamo
        use_count += 1
        users_table.update_item(
            Key={'fromNumber': from_num},
            UpdateExpression="set use_count = use_count+ :val",
            ExpressionAttributeValues={':val': decimal.Decimal(1)},
            ReturnValues="UPDATED_NEW"
            )
    return name, use_count

def open_sesame(from_num, name):
    print("Trying the door now")
    txt_body = "The door should open for about 5 seconds, " + str(name)
    message = client.messages.create(
        body=txt_body,
        to=from_num,
        from_=TWILIO_NUM,
        )
    success_status = True
    time.sleep(1)
    try:
        # open the door! for god's sake, open the door!
        spark.DoorbellCore.relay('R1', 'HIGH')
    except AttributeError as error:
        print("Error setting the relay to High state!")
        #print error
        success_status = False

    # wait... wait for it....
    time.sleep(4)
    try:
        # ok now close the door
        spark.DoorbellCore.relay('R1', 'LOW')
    except AttributeError as error:
        print("Error setting the relay to Low state to close door!")
        success_status = False
        #print error

    return success_status

def lambda_handler(event, context):
    twilio_resp = "none"
    call_status = "none"

    # parse the SMS from Twilio
    message = event['body']
    from_num = event['fromNumber']

    # try to look up their info
    name, use_count = number_lookup(from_num)

    # log it to cloudwatch
    print("Number  : " + from_num)
    print("Name    : " + name)
    print("Message : " + message)

    # if the crappy SET_SECURE bit is on, require a simple passphrase to open
    if SET_SECURE == 'True':
        if PASSPHRASE not in message: # bad passphrase, do nothing
            print("***PASSPHRASE NOT PRESENT***")
            errmessage = client.messages.create(
                body= str(name) + " tried to get in without the passphrase",
                to=SUPPORT_NUM,
                from_=TWILIO_NUM,
            )
            twilio_resp = "Sorry, you didn't use the passphrase."
            return twilio_resp

    #function to talk to the particle core and open the door
    call_status = open_sesame(from_num, name)

    if call_status:
        twilio_resp = "Thanks for visiting!" + "\n\nUse Count: " + str(use_count)
    else:
        #let the owner know that the robot appears to be failing
        errmessage = client.messages.create(
            body="The doorbell robot just failed!",
            to=SUPPORT_NUM,
            from_=TWILIO_NUM,
        )
        twilio_resp = "Unfortunately there was an error opening the door! \n\n"
        twilio_resp = twilio_resp + "Please contact " + str(SUPPORT_NUM)

    return twilio_resp
