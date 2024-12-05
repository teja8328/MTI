from NorenRestApiPy.NorenApi import NorenApi
import requests
import hashlib
from urllib.parse import parse_qs, urlparse
from pyotp import TOTP
from flask import jsonify, abort
import pyotp

async def execute(data):
    data = await handle_finvasia_validation(data)
    return data

class ShoonyaApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, host='https://api.shoonya.com/NorenWClientTP/', 
                          websocket='wss://api.shoonya.com/NorenWSTP/')
        global api
        api = self

async def handle_finvasia_validation(data):
    api = ShoonyaApiPy()

    # Set up authentication variables
    qrCode = data['qrCode']
    otp = pyotp.TOTP(qrCode).now()
    userId = data['userId']
    password = data['password']
    factor2 = otp
    vendor_code = f'{userId}_U'
    apiKey = data['apiKey']
    imei = data['imei']

    # Perform login
    ret = api.login(userid=userId, password=password, twoFA=factor2, vendor_code=vendor_code, api_secret=apiKey, imei=imei)
    
    # Prepare JSON response
    if ret:
        # API limits
        limits = api.get_limits()

        data = {"data" : {"name": ret["uname"],'availablecash':limits["cash"]}}

        response_data = {
            'status': 'success',
            'message': 'Login successful',
            'limits': limits,
            'api_response': ret,  # Include the API response in the JSON
            'data':data
        }
        return jsonify(response_data), 200
    else:
        response_data = {
            'status': 'error',
            'message': 'Login failed',
            'api_response': ret  # Include the API response in the JSON
        }
        return jsonify(response_data), 500