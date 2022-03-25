import time     # so we can sleep between calls
import decimal  # for incrementing the use count
import random   # for randomizing responses
import os       # to grab environment variables from Lambda
import base64   # encoding
import json     # banned numbers
import urllib   # http stuff

from base64 import b64decode      # decode encrypted environment variables
from urllib import request, parse # to make API calls the old-fashioned way

import boto3    # accessing AWS
from boto3.session import Session
from boto3.dynamodb.conditions import Key # so we can save user info in Dynamo

# globals - these should all be saved as environment variables in Lambda
PARTICLE_URL = os.environ['PARTICLE_URL'] # ParticleCloud API URL
e1           = os.environ['ACCESS_TOKEN'] # ParticleCloud API Token (Encrypted)
e2           = os.environ['TWILIO_SID']   # Twilio SID (Encrypted)
e3           = os.environ['TWILIO_TOKEN'] # Twilio Token (Encrypted)
TWILIO_URL   = os.environ['TWILIO_URL']   # Twilio API URL
TWILIO_NUM   = os.environ['TWILIO_NUM']   # Twilio Number
SUPPORT_NUM  = os.environ['SUPPORT_NUM']  # Support/Owner Phone Number
SET_SECURE   = os.environ['SET_SECURE']   # Req passphrase?
PASSPHRASE   = os.environ['PASSPHRASE']   # The magic word
DYNAMO_ID    = os.environ['DYNAMO_ID']    # DynamoDB Table Name
REGION       = 'us-east-1'                # hardcoding region (for now)
BANNED_NUMS  = json.loads(os.environ.get("BANNED_NUMS", "[]"))

# use kms to decrypt secret values
kms = boto3.client('kms')
ACCESS_TOKEN = kms.decrypt(CiphertextBlob=b64decode(e1))['Plaintext'].decode('utf-8')
TWILIO_SID   = kms.decrypt(CiphertextBlob=b64decode(e2))['Plaintext'].decode('utf-8')
TWILIO_TOKEN = kms.decrypt(CiphertextBlob=b64decode(e3))['Plaintext'].decode('utf-8')

# create a DynamoDB session and load the user table
dynamodb     = boto3.resource('dynamodb', REGION)
users_table  = dynamodb.Table(DYNAMO_ID)

def number_lookup(user_num):
    """Takes the calling phone number and attempts a lookup in DynamoDB
    
    Parameters
    ----------
    user_num : str
        The sending phone number, extracted from the Twilio call
    
    Returns
    -------
    name : str
        the user's name, if known (default is "Stranger")
    use_count : int
        how many times this number has used the service
    responses : list
        potential replies as a list of strings (default "Thanks for visiting!")
    """
    if user_num == "+15555555555":
        # if it's from the test number, do not pass go
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
        responses = ["Looks like it's your first time. Thanks for visiting!"]
    else:
        usr_result = dynamo_results['Items'][0]
        try:
            name = usr_result['name']
        except NameError as e:
            print("Error finding name for " + str(user_num))
            #print(e)

        # how many times have they used the robot service?
        try:
            use_count = usr_result['use_count']
            use_count += 1
            users_table.update_item(
                Key={'fromNumber': user_num},
                UpdateExpression="set use_count = use_count+ :val",
                ExpressionAttributeValues={':val': decimal.Decimal(1)},
                ReturnValues="UPDATED_NEW"
                )
        except NameError as e:
            print("Error finding use_count for " + str(user_num))
            use_count = "unknown"

        # if you want to get cute, store custom responses as a list of strings
        try:
            responses = usr_result['responses']
        except KeyError as e:
            responses = ["Thanks for visiting!"]

    return name, use_count, responses

def signal_door(payload):
    """Constructs an API call to the Particle device attached to the intercom
    
    Parameters
    ----------
    payload : str
        The API parameters, formatted as "pin,state" (e.g., "r1,HIGH" to open)
    """
    print("Hitting Relay API: " + str(payload))
    d = {'access_token': ACCESS_TOKEN, 'params': payload}
    data = parse.urlencode(d).encode()
    req  = request.Request(PARTICLE_URL, data=data)

    resp = request.urlopen(req)
    print("POST Response: " + str(resp.getcode()))
    return resp.getcode()

    try:
        resp = request.urlopen(req)
        print("POST Response: " + str(resp.getcode()))
        return resp.getcode()
    except urllib.error.HTTPError as e:
        print('POST RESPONSE: ' + str(e.code))
        print('Particle returned: ', e.read())
        return e.code

def send_message(txt, recip):
    """Sends an SMS message via Twilio API call
    
    Parameters
    ----------
    txt : str
        The text to be sent via SMS
    recip : str
        The phone number receiving our message
    """
    populated_url = TWILIO_URL.format(TWILIO_SID)
    d = {"To": recip, "From": TWILIO_NUM, "Body": txt}
    data = parse.urlencode(d).encode()
    req = request.Request(populated_url)

    authentication = "{}:{}".format(TWILIO_SID, TWILIO_TOKEN)
    base64string = base64.b64encode(authentication.encode("utf-8"))
    req.add_header("Authorization", "Basic %s" % base64string.decode("ascii"))

    try:
        with request.urlopen(req, data) as f:
            print("Twilio returned {}".format(str(f.read().decode("utf-8"))))
            return f.getcode()
    except urllib.error.HTTPError as e:
        print('POST RESPONSE: ' + str(e.code))
        print('Twilio returned: ', e.read())
        return e.code

def open_sesame(user_num, testing):
    """Runs the cycle to open the door
    
    Parameters
    ----------
    user_num : str
        The phone number of the user, to receive confirmation
    testing : boolean
        This bit, when true, indicates this call is a test of the system
    """
    print("Trying the door now")
    success_status = True

    # let the user know the door should be opening imminently
    if not testing:
        msg = "Message received, the door should open for about 5 seconds"
        code = send_message(msg, user_num)
        time.sleep(1)

    # open the door! for god's sake, open the door!
    r = signal_door('R1,HIGH')
    if r != 200:
        success_status = False

    # wait... wait for it....
    time.sleep(4)

    # now close the door
    r = signal_door('R1,LOW')
    if r != 200:
        success_status = False

    return success_status

def lambda_handler(event, context):
    """Main function for our Lambda - parses the received message
    
    Parameters
    ----------
    event : dict
        The TwiML (XML) values of the incoming SMS from Twilio

    Returns
    -------
    user_resp : str
        The body of the SMS sent in response, at the conclusion of processing
    """
    user_resp    = ""
    call_status  = True
    testing      = False

    # parse the incoming SMS from Twilio
    try:
        message  = event['body']
        user_num = event['fromNumber']
        rec_num  = event['toNumber']
    except KeyError as e:
        print("Didn't receive expected values from Twilio! Bombing out.")
        print(e)
        send_message("The doorbell robot just failed!", SUPPORT_NUM)
        return("Apologies, something went wrong. Technology is hard!")

    # try to look up their info; if it's the test number set the bit to true
    print("*Commencing lookup function*")
    name, use_count, responses = number_lookup(user_num)
    if name == "AWS_Test":
        testing = True

    # log the details to cloudwatch
    print("Number  : " + user_num)
    print("Receive : " + rec_num)
    print("Name    : " + name)
    print("Message : " + message)

    # we all need to be able to set boundaries
    if user_num in BANNED_NUMS:
        print("***BANNED USER ATTEMPT***")
        msg = "Banned user " + str(name) + " tried to get in!\
            \n\nNumber: " + str(user_num)
        code = send_message(msg, SUPPORT_NUM)
        user_resp = "Sorry, you aren't allowed in. This has been reported."
        return user_resp

    # if the SET_SECURE bit is on, require a passphrase in SMS body to open
    if SET_SECURE == 'True':
        if PASSPHRASE not in message:
            print("***REQUIRED PASSPHRASE NOT PRESENT***")
            msg = str(name) + " tried to get in without the passphrase\
                \n\nNumber: " + str(user_num)
            code = send_message(msg, SUPPORT_NUM)
            user_resp = "Sorry, you didn't use the passphrase."
            return user_resp

    # if you've made it this far, let's get that door buzzing
    call_status = open_sesame(user_num, testing)

    if call_status:
        # everything appears to have worked, send a success response
        user_resp = random.choice(responses)+"\n\nUse Count: " + str(use_count)
        print("*Success*")
    else:
        # let the owner know that the robot appears to be failing
        code = send_message("The doorbell robot just failed!", SUPPORT_NUM)
        user_resp = "Unfortunately there was an error opening the door! \
            \n\nPlease contact " + str(SUPPORT_NUM)
        print("*Failure*")

    return user_resp
