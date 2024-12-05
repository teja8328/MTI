from NorenRestApiPy.NorenApi import NorenApi
import requests
import hashlib
from urllib.parse import parse_qs, urlparse
from pyotp import TOTP
from flask import jsonify, abort
import json
from fyers_api import fyersModel
from fyers_api import accessToken
import pyotp
import os
from app.api.brokers import config
 
async def execute(data):
    data = await handle_fyers_validation(data)
    return data
 
#fyers redirect url function
def get_redirect_uri():
    return f"http://127.0.0.1:{5000}"
 
 
async def handle_fyers_validation(data):
    client_id = data['client_id']
    APP_ID = client_id.split('-')[0]
    APP_TYPE = client_id.split('-')[1]
    secretKey = data['secretKey']
    userId = data['userId']
    qrCode = data['qrCode']
    password = data['password']
    REDIRECT_URI = data['REDIRECT_URI']
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
    session = accessToken.SessionModel(client_id=client_id, secret_key=secretKey, redirect_uri=REDIRECT_URI,
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
        verify_totp_result = verify_totp(request_key=request_key, totp=pyotp.TOTP(qrCode).now())
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
    print(res_pin)
    ses.headers.update({
        'authorization': f"Bearer {res_pin['data']['access_token']}"
    })
    authParam = {"fyers_id": userId, "app_id": APP_ID, "redirect_uri": REDIRECT_URI, "appType": APP_TYPE,
                 "code_challenge": "", "state": "None", "scope": "", "nonce": "", "response_type": "code",
                 "create_cookie": True}
    authres = ses.post('https://api.fyers.in/api/v2/token', json=authParam).json()
    print(authres)
    url = authres['Url']
    print(url)
    parsed = urlparse(url)
    auth_code = parse_qs(parsed.query)['auth_code'][0]
    print(auth_code)
    session.set_token(auth_code)
    response = session.generate_token()
    print(response)
    access_token = response["access_token"]
    if access_token:
        try:
            fyers = fyersModel.FyersModel(client_id=data['client_id'], token=access_token, log_path=os.getcwd())
            profile_info = fyers.get_profile()
           
            # Extracting specific fields from profile_info
            extracted_profile_info = {
                "fy_id": profile_info['data']['fy_id'],
                "name": profile_info['data']['name'],
                "email_id": profile_info['data']['email_id'],
                "mobile_number": profile_info['data']['mobile_number']
            }
 
            config.SMART_API_OBJ_fyers = fyers
 
            if config.SMART_API_OBJ_fyers :
                print("Without Login")
                pass
 
            funds_info = fyers.funds()
            order_book = fyers.orderbook()
            positions_info = fyers.positions()
            holdings_info = fyers.holdings()
           
            # Extracting specific fund limit information
            total_balance_info = next(
                (fund_limit for fund_limit in funds_info.get('fund_limit', []) if fund_limit['id'] == 1),
                None
            )
           
            extracted_profile_info['availablecash'] = total_balance_info["equityAmount"]
               
            response_data = {"data" :{"data": extracted_profile_info, "total_balance_info": total_balance_info,"Order Book" : order_book,"Positions" : positions_info,"Holdings_info" : holdings_info}}
            return jsonify(response_data)
       
        except Exception as e:
            response_data = {"error": str(e)}
            return jsonify(response_data)
    else:
        response_data = {"error": "Authentication failed"}
        return jsonify(response_data)