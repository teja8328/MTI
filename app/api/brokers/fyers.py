from NorenRestApiPy.NorenApi import NorenApi
import requests
import hashlib
from urllib.parse import parse_qs, urlparse
from pyotp import TOTP
from flask import jsonify, abort
import json
from fyers_apiv3 import fyersModel
from fyers_api import accessToken
import pyotp
import threading
import time
import os
# from flask import Blueprint, jsonify, abort, request
from app.api.brokers import config
from fyers_apiv3.FyersWebsocket import data_ws

# # Initialize dictionary to store data
# FYERS_LIVE_FEED_JSON = {}

# def retrieve_live_feed_fyers():
#     def onmessage(message):
#         print("Response:", message)
 
#     def onerror(message):
#         print("Error:", message)
    
#     def onclose(message):
#         print("Connection closed:", message)
    
#     def onopen():
#         data_type = "SymbolUpdate"
#         symbols = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX","NSE:FINNIFTY-INDEX","BSE:SENSEX-INDEX"]
#         fyers.subscribe(symbols=symbols, data_type=data_type)
#         fyers.keep_running()
    
    
#     fyers = data_ws.FyersDataSocket(
#         access_token=config.fyers_access_token,
#         log_path="",
#         litemode=False,
#         write_to_file=False,
#         reconnect=True,
#         on_connect=onopen,
#         on_close=onclose,
#         on_error=onerror,
#         on_message=onmessage
#     )
    
#     # Start a new thread for WebSocket connection
#     threading.Thread(target=fyers.connect).start()
#     # Function to continuously print LIVE_FEED_JSON
#     def print_live_feed():
#         while True:
#             print(config.FYERS_LIVE_FEED_JSON)
#             time.sleep(60)  

#     # Start a new thread to continuously print LIVE_FEED_JSON
#     threading.Thread(target=print_live_feed).start()

# # Function to retrieve live feed data and return it
# def fyers_get_live_feed_data():
#     return config.FYERS_LIVE_FEED_JSON
# fyers_get_live_feed_blueprint = Blueprint('get_live_feed_fyers', __name__) 

# @fyers_get_live_feed_blueprint.route('/get_live_feed_fyers', methods=['GET'])
# def fyers_get_live_feed():
#     live_feed_data = fyers_get_live_feed_data()
#     print(live_feed_data)
#     return jsonify(live_feed_data)


async def execute(data):
    data = await handle_fyers_validation(data)
    return data
 
#fyers redirect url function
def get_redirect_uri():
    return f"https://www.google.co.in/"
 
 
async def handle_fyers_validation(data):
    client_id = data['client_id']
    config.fyers_clientID = client_id
    APP_ID = client_id.split('-')[0]
    APP_TYPE = client_id.split('-')[1]
    secretKey = data['secretKey']
    userId = data['userId']
    qrCode = data['qrCode']
    password = data['password']
    # REDIRECT_URI = data['redirectAPI']
    REDIRECT_URI = get_redirect_uri()
    client_id = f'{APP_ID}-{APP_TYPE}'
    APP_ID_TYPE = "2"
    BASE_URL = "https://api-t2.fyers.in/vagator/v2"
    BASE_URL_2 = "https://api.fyers.in/api/v2"
    URL_SEND_LOGIN_OTP = BASE_URL + "/send_login_otp"
    URL_VERIFY_TOTP = BASE_URL + "/verify_otp"
    URL_VERIFY_PIN = BASE_URL + "/verify_pin"
    URL_TOKEN = BASE_URL_2 + "/token"
    URL_VALIDATE_AUTH_CODE = BASE_URL_2 + "/validate-authcode"
    SUCCESS = 1
    ERROR = -1
    def send_login_otp(fy_id, app_id):
        try:
            result_string = requests.post(url=URL_SEND_LOGIN_OTP, json={"fy_id": fy_id, "app_id": app_id})
            if result_string.status_code != 200:
                return [ERROR, result_string.text]
            result = json.loads(result_string.text)
            request_key = result["request_key"]
            return [SUCCESS, request_key]
        except Exception as e:
            return [ERROR, e]
    def verify_totp(request_key, totp):
        try:
            result_string = requests.post(url=URL_VERIFY_TOTP, json={"request_key": request_key, "otp": totp})
            if result_string.status_code != 200:
                return [ERROR, result_string.text]
            result = json.loads(result_string.text)
            request_key = result["request_key"]
            return [SUCCESS, request_key]
        except Exception as e:
            return [ERROR, e]
   
    if config.OBJ_fyers == {} or userId not in config.OBJ_fyers.keys():
        session = fyersModel.SessionModel(client_id=client_id, secret_key=secretKey, redirect_uri=REDIRECT_URI,
                                        response_type='code', grant_type='authorization_code')
        urlToActivate = session.generate_authcode()
        print(f'URL to activate APP:  {urlToActivate}')
        send_otp_result = send_login_otp(fy_id=userId, app_id=APP_ID_TYPE)
        if send_otp_result[0] != SUCCESS:
            print(f"send_login_otp failure - {send_otp_result[1]}")
            return None
        print("send_login_otp success")
        for i in range(1, 3):
            request_key = send_otp_result[1]
            try:
                verify_totp_result = verify_totp(request_key=request_key, totp=pyotp.TOTP(qrCode).now())
            except:
                response_data = {"error": "Invalid QR_Code"}
                return jsonify(response_data), 500
           
            if verify_totp_result[0] != SUCCESS:
                print(f"verify_totp_result failure - {verify_totp_result[1]}")
            else:
                print(f"verify_totp_result success {verify_totp_result}")
                break
        request_key_2 = verify_totp_result[1]
        ses = requests.Session()
        payload_pin = {"request_key": f"{request_key_2}", "identity_type": "pin", "identifier": f"{password}",
                    "recaptcha_token": ""}
        res_pin = ses.post('https://api-t2.fyers.in/vagator/v2/verify_pin', json=payload_pin).json()
        try:    
            print(res_pin['data'])
        except:
            response_data = {"error": "Invalid Pin or QR_Code"}
            return jsonify(response_data), 500
 
        ses.headers.update({
            'authorization': f"Bearer {res_pin['data']['access_token']}"
        })
        authParam = {"fyers_id": userId, "app_id": APP_ID, "redirect_uri": REDIRECT_URI, "appType": APP_TYPE,
                    "code_challenge": "", "state": "None", "scope": "", "nonce": "", "response_type": "code",
                    "create_cookie": True}
        authres = ses.post('https://api.fyers.in/api/v2/token', json=authParam).json()
        print(authres,"\n\n\n")
        try:
            url = authres['Url']
        except:
            response_data = {"error": "Invalid RedirectApi or Cliend_id"}
            return jsonify(response_data), 500
        parsed = urlparse(url)
        auth_code = parse_qs(parsed.query)['auth_code'][0]
        print(auth_code)
        session.set_token(auth_code)
        response = session.generate_token()
        print(response)
        try:
            access_token = response["access_token"]
        except:
            response_data = {"error": "Invalid SecretKey"}
            return jsonify(response_data), 500
       
        config.fyers_access_token[userId] = access_token
       
    else:
        fyers = config.OBJ_fyers[userId]
        access_token = config.fyers_access_token[userId]
 
    if access_token:
        try:
            if config.OBJ_fyers != {} and userId in config.OBJ_fyers.keys():
                print("Without Login")
                fyers = config.OBJ_fyers[userId]
                profile_info = fyers.get_profile()
                pass
            elif APP_ID not in config.OBJ_fyers:
                fyers = fyersModel.FyersModel(client_id=data['client_id'], token=access_token, log_path=os.getcwd())
                print('fyers:', fyers)
                profile_info = fyers.get_profile()
            else:
                fyers = fyersModel.FyersModel(client_id=data['client_id'], token=access_token, log_path=os.getcwd())
                print('fyers:', fyers)
                profile_info = fyers.get_profile()
           
            # Extracting specific fields from profile_info
            extracted_profile_info = {
                "fy_id": profile_info['data']['fy_id'],
                "name": profile_info['data']['name'],
                "email_id": profile_info['data']['email_id'],
                "mobile_number": profile_info['data']['mobile_number']
            }
 
            data = {
                        "symbols":"NSE:NIFTY50-INDEX,NSE:NIFTYBANK-INDEX,NSE:FINNIFTY-INDEX,BSE:SENSEX-INDEX"
                    }  
 
            print("Before Adding :",config.OBJ_fyers)
            config.OBJ_fyers[userId] = fyers
            print("After Adding :",config.OBJ_fyers)
 
            funds_info = fyers.funds()
            order_book = fyers.orderbook()
           
            positions_info = fyers.positions()
            holdings_info = fyers.holdings()
            index_data = fyers.quotes(data=data)
            print(order_book)
 
            # Extracting specific fund limit information
            total_balance_info = next(
                (fund_limit for fund_limit in funds_info.get('fund_limit', []) if fund_limit['id'] == 1),
                None
            )
           
            extracted_profile_info['availablecash'] = total_balance_info["equityAmount"]
               
           
            response_data = {"data" :{"data": extracted_profile_info, "total_balance_info": total_balance_info,"Order_Book" : order_book,"Positions" : positions_info,"Holdings_info" : holdings_info,'Index_data': index_data}}
            return jsonify(response_data)
       
        except Exception as e:
            print(config.OBJ_fyers)
            response_data = {"error": str(e)}
            return jsonify(response_data), 500
    else:
        response_data = {"error": "Authentication failed"}
        return jsonify(response_data), 500