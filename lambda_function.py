import time     # so we can sleep between calls
import decimal  # for incrementing the use count
import random   # for randomizing responses
import os       # to grab environment variables from Lambda
import base64   # encoding
import json     # banned numbers

from base64 import b64decode      # decode encrypted environment variables
from urllib import request, parse # to make API calls the old-fashioned way

import boto3    # accessing AWS
from boto3.session import Session
from boto3.dynamodb.conditions import Key # so we can save user info in Dynamo

# globals - these should all be saved as environment variables in Lambda
PARTICLE_URL = os.environ['PARTICLE_URL'] # ParticleCloud API URL
e1           = os.environ['ACCESS_TOKEN'] # ParticleCloud API Token
e2           = os.environ['TWILIO_SID']   # Twilio SID
e3           = os.environ['TWILIO_TOKEN'] # Twilio Token
TWILIO_URL   = os.environ['TWILIO_URL']   # Twilio API URL
TWILIO_NUM   = os.environ['TWILIO_NUM']   # Twilio Number
SUPPORT_NUM  = os.environ['SUPPORT_NUM']  # Support/Owner Number
SET_SECURE   = os.environ['SET_SECURE']   # Req passphrase?
PASSPHRASE   = os.environ['PASSPHRASE']   # The magic word
DYNAMO_ID    = os.environ['DYNAMO_ID']    # DynamoDB Table Name
BANNED_NUMS  = json.loads(os.environ.get("BANNED_NUMS", "[]"))
print("eSID: " + e2)

# using encryption helper for secret values
kms = boto3.client('kms')
ACCESS_TOKEN = kms.decrypt(CiphertextBlob=b64decode(e1))['Plaintext'].decode('utf-8')
TWILIO_SID   = kms.decrypt(CiphertextBlob=b64decode(e2))['Plaintext'].decode('utf-8')
TWILIO_TOKEN = kms.decrypt(CiphertextBlob=b64decode(e3))['Plaintext'].decode('utf-8')
print("SID: " + TWILIO_SID)

# create a DynamoDB session, load the user table
dynamodb     = boto3.resource('dynamodb', 'us-east-1')
users_table  = dynamodb.Table(DYNAMO_ID)

def number_lookup(user_num):
    if user_num == "+15555555555":
        return "AWS_Test", 1

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

        # if you want to get cute, store custom responses as a list of strings
        try:
            responses = dynamo_results['Items'][0]['responses']
        except KeyError as e:
            responses = ["Thanks for visiting!"]
            print("No custom responses for " + str(user_num))

        # increment the use_count in Dynamo
        use_count += 1
        users_table.update_item(
            Key={'fromNumber': user_num},
            UpdateExpression="set use_count = use_count+ :val",
            ExpressionAttributeValues={':val': decimal.Decimal(1)},
            ReturnValues="UPDATED_NEW"
            )
    return name, use_count, responses

def signal_door(payload):
    print("Hitting Relay API: " + str(payload))
    d = {'access_token': ACCESS_TOKEN, 'params': payload}
    data = parse.urlencode(d).encode()
    req  = request.Request(PARTICLE_URL, data=data)

    resp = request.urlopen(req)
    print("POST Response: " + str(resp.getcode()))
    return resp.getcode()

def send_message(txt, recip):
    populated_url = TWILIO_URL.format(TWILIO_SID)
    d = {"To": recip, "From": TWILIO_NUM, "Body": txt}
    data = parse.urlencode(d).encode()
    req = request.Request(populated_url)

    authentication = "{}:{}".format(TWILIO_SID, TWILIO_TOKEN)
    base64string = base64.b64encode(authentication.encode("utf-8"))
    req.add_header("Authorization", "Basic %s" % base64string.decode("ascii"))

    with request.urlopen(req, data) as f:
        print("Twilio returned {}".format(str(f.read().decode("utf-8"))))

def open_sesame(user_num, testing):
    print("Trying the door now")
    success_status = True

    # let the user know the door should be opening imminently
    if not testing:
        msg = "Message received, the door should open for about 5 seconds"
        send_message(msg, user_num)
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
    user_resp   = ""
    call_status = True
    testing     = False

    # parse the incoming SMS from Twilio
    try:
        message  = event['body']
        user_num = event['fromNumber']
    except KeyError as e:
        print("Didn't receive expected values from Twilio! Bombing out.")
        print(e)
        send_message("The doorbell robot just failed!", SUPPORT_NUM)
        return("Something went wrong")

    # try to look up their info
    print("*Commencing lookup function*")
    name, use_count, responses = number_lookup(user_num)
    if name == "AWS_Test":
        testing = True

    # log it to cloudwatch
    print("Number  : " + user_num)
    print("Name    : " + name)
    print("Message : " + message)

    # bad user, no cookie
    if user_num in BANNED_NUMS:
        print("***BANNED USER ATTEMPT***")
        msg = "Banned user " + str(name) + " tried to get in!\
            \n\nNumber: " + str(user_num)
        send_message(msg, SUPPORT_NUM)
        user_resp = "Sorry, you aren't allowed in."
        return user_resp

    # if the SET_SECURE bit is on, require a passphrase in SMS body to open
    if SET_SECURE == 'True':
        if PASSPHRASE not in message:
            print("***PASSPHRASE NOT PRESENT***")
            msg = str(name) + " tried to get in without the passphrase\
                \n\nNumber: " + str(user_num)
            send_message(msg, SUPPORT_NUM)
            user_resp = "Sorry, you didn't use the passphrase."
            return user_resp

    #function to talk to the particle device and open/close the door
    call_status = open_sesame(user_num, testing)

    if call_status:
        user_resp = random.choice(responses)+"\n\nUse Count: " + str(use_count)
        print("*Success*")
    else:
        #let the owner know that the robot appears to be failing
        send_message("The doorbell robot just failed!", SUPPORT_NUM)
        user_resp = "Unfortunately there was an error opening the door! \
            \n\nPlease contact " + str(SUPPORT_NUM)
        print("*Failure*")

    return user_resp
