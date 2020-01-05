# use test credentials to perform daily validation of Twilio and ParticleCloud
import os       # to grab environment variables from Lambda
import base64   # encoding
import boto3    # accessing AWS
import urllib   # http

from base64 import b64decode      # decode encrypted environment variables
from urllib import request, parse # to make API calls the old-fashioned way

TWILIO_TEST_URL    = os.environ['TWILIO_TEST_URL']    # Twilio API URL
TWILIO_TEST_FROM   = os.environ['TWILIO_TEST_FROM']   # Twilio API URL
TWILIO_TEST_SID    = os.environ['TWILIO_TEST_SID']    # Twilio API URL
TWILIO_TEST_TO     = os.environ['TWILIO_TEST_TO']     # Twilio API URL
TWILIO_TEST_TOKEN  = os.environ['TWILIO_TEST_TOKEN']  # Twilio API URL
PARTICLE_RELAY_URL = os.environ['PARTICLE_RELAY_URL'] # Twilio API URL
PARTICLE_INFO_URL  = os.environ['PARTICLE_INFO_URL']  # Twilio API URL
PARTICLE_TOKEN     = os.environ['PARTICLE_TOKEN']     # Twilio API URL

def lambda_handler(event, context):
    # if this stays true, we passed all tests
    test_result = True

    print("***COMMENCTING DAILY API TEST***\n")

    # test the Twilio API - sending SMS - using test (free) creds
    msg = "This is an API test!"
    twilio_status = _test_twilio_api(msg, TWILIO_TEST_TO)
    if twilio_status == 200 or twilio_status == 201:
        print('Twilio API succeeded!\n')
    else:
        print('Twilio API failed!\n')
        test_result = False

    # test the ParticleCloud API (talking to the robot)
    particle_status = _test_particle_api()
    if particle_status == 200:
        print('Particle API succeeded!\n')
    else:
        print('Particle API failed!\n')
        test_result = False

    if test_result:
        print("***TEST SUCCESS***")
        return {'statusCode': 200, 'body': 'TEST SUCCESS'}
    else:
        #TODO - SNS or other notification of failure
        print("***TEST FAILURE***")
        return {'statusCode': 400, 'body': 'TEST FAILURE'}


def _test_twilio_api(txt, recip):
    print("*Testing Twilio API*")
    populated_url = TWILIO_TEST_URL.format(TWILIO_TEST_SID)
    d    = {"To": recip, "From": TWILIO_TEST_FROM, "Body": txt}
    data = parse.urlencode(d).encode()
    req  = request.Request(populated_url)
    print('URL: ' + str(populated_url))

    authentication = "{}:{}".format(TWILIO_TEST_SID, TWILIO_TEST_TOKEN)
    base64string = base64.b64encode(authentication.encode("utf-8"))
    req.add_header("Authorization", "Basic %s" % base64string.decode("ascii"))

    try:
        with request.urlopen(req, data) as f:
            print('POST RESPONSE: ' + str(f.getcode()))
            print("Twilio returned {}".format(str(f.read().decode("utf-8"))))
            return f.getcode()
    except urllib.error.HTTPError as e:
        print('POST RESPONSE: ' + str(e.code))
        print('Twilio returned: ', e.read())
        return e.code


def _test_particle_api():
    print('*Testing Particle API*')
    d    = {'access_token': PARTICLE_TOKEN}
    data = parse.urlencode(d).encode()
    req  = request.Request(PARTICLE_INFO_URL, data=data, method='PUT')
    print('URL: ' + str(PARTICLE_INFO_URL))

    try:
        with request.urlopen(req, data) as f:
            print("PUT Response: " + str(f.getcode()))
            print("Particle returned {}".format(str(f.read().decode("utf-8"))))
            return f.getcode()
    except urllib.error.HTTPError as e:
        print('PUT RESPONSE: ' + str(e.code))
        print('Particle returned: ', e.read())
        return e.code
