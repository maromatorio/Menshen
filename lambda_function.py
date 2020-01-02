import boto3    # accessing AWS for DynamoDB session info
import time     # so we can sleep between Spark calls
import decimal  # for incrementing the use count
import random   # for randomizing responses
import requests # to hit the ParticleCloud API

from boto3.session import Session
from boto3.dynamodb.conditions import Key # so we can save user info in Dynamo
from twilio.rest import Client            # Twilio client to process SMS
from twilio.base.exceptions import TwilioRestException

# create a DynamoDB session, pull out our 'secrets'
# todo - testing/error handling
dynamodb = boto3.resource('dynamodb', 'us-east-1')
users_table  = dynamodb.Table('robot_users')
creds = users_table.query(
    KeyConditionExpression=Key('fromNumber').eq('creds')
    )['Items'][0]

# globals
TWILIO_SID   = creds['account_sid']   # Twilio SID
TWILIO_TOKEN = creds['auth_token']    # Twilio Token
TWILIO_NUM   = creds['twil_num']      # Twilio Number
ACCESS_TOKEN = creds['ACCESS_TOKEN']  # Particle Token
PARTICLE_URL = creds['PARTICLE_URL']  # Particle API URL
SUPPORT_NUM  = creds['sup_num']       # Support number
SET_SECURE   = creds['SetSecure']     # req passphrase?
PASSPHRASE   = creds['passphrase']    # the magic word
#DEVICE_NAME  = creds['DEVICE_NAME']   # Particle Core Name

# create a Twilio session using the above secrets
# todo - testing/error handling for session creation
client = Client(TWILIO_SID, TWILIO_TOKEN)

def number_lookup(user_num):
    dynamo_results = users_table.query(
        KeyConditionExpression=Key('fromNumber').eq(user_num)
        )

    # new phone, who dis?
    if dynamo_results['Count'] == 0:
        new_entry = {'fromNumber': user_num,
            'use_count': 1,
            'name': 'Stranger'
            }
        users_table.put_item(Item=new_entry)
        name = "Stranger"
        use_count = 1
    else:
        try:
            name = dynamo_results['Items'][0]['name']
        except NameError as e:
            print("Error finding name for " + str(user_num))
            #print(e)

        # how many times have they used the robot?
        try:
            use_count = dynamo_results['Items'][0]['use_count']
        except NameError as e:
            print("Error finding use_count for " + str(user_num))

        # increment the use_count in Dynamo
        use_count += 1
        users_table.update_item(
            Key={'fromNumber': user_num},
            UpdateExpression="set use_count = use_count+ :val",
            ExpressionAttributeValues={':val': decimal.Decimal(1)},
            ReturnValues="UPDATED_NEW"
            )
    return name, use_count

def signal_door(payload):
    print("Hitting Relay API: " + str(payload))
    data = {
        'access_token': ACCESS_TOKEN,
        'params': payload
        }
    response = requests.post(PARTICLE_URL, data=data)
    print("POST Response: " + str(response.status_code))
    return response.status_code

def send_message(txt, recip):
    try:
        message = client.messages.create(
            body=txt,
            to=recip,
            from_=TWILIO_NUM,
            )
    except TwilioRestException as e:
        print(e)
    return message

def open_sesame(user_num):
    print("Trying the door now")
    success_status = True

    # let the user know the door should be opening imminently
    m = send_message("The door should open for about 5 seconds", user_num)
    time.sleep(1)

    # open the door! for god's sake, open the door!
    r = signal_door('R1,HIGH')
    if r != 200:
        success_status = False

    # wait... wait for it....
    time.sleep(4)

    # ok now close the door
    r = signal_door('R1,LOW')
    if r != 200:
        success_status = False

    return success_status

def lambda_handler(event, context):
    user_resp   = "none"
    call_status = True

    # parse the SMS from Twilio
    message  = event['body']
    user_num = event['fromNumber']

    # try to look up their info
    name, use_count = number_lookup(user_num)

    # log it to cloudwatch
    print("Number  : " + user_num)
    print("Name    : " + name)
    print("Message : " + message)

    # if the crappy SET_SECURE bit is on, require a simple passphrase to open
    if SET_SECURE == 'True':
        if PASSPHRASE not in message:
            print("***PASSPHRASE NOT PRESENT***")
            msg = str(name) + " tried to get in without the passphrase\
                \n\nNumber: " + str(user_num)
            m = send_message(msg, SUPPORT_NUM)
            user_resp = "Sorry, you didn't use the passphrase."
            return user_resp

    #function to talk to the particle device and open the door
    call_status = open_sesame(user_num)

    if call_status:
        user_resp = "Thanks for visiting!" + "\n\nUse Count: " + str(use_count)
        print("Success")
    else:
        #let the owner know that the robot appears to be failing
        m = send_message("The doorbell robot just failed!", SUPPORT_NUM)
        user_resp = "Unfortunately there was an error opening the door! \
            \n\nPlease contact " + str(SUPPORT_NUM)

    return user_resp
