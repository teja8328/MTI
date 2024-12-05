from NorenRestApiPy.NorenApi import NorenApi
import requests
import hashlib
from urllib.parse import parse_qs, urlparse
from pyotp import TOTP
from flask import jsonify, abort
from app.api.brokers import config
import json


async def execute(data, config):
    data = await handle_flattrade_validation(data, config)
    return data


class FlatTradedApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, host='https://piconnect.flattrade.in/PiConnectTP/',
                          websocket='wss://piconnect.flattrade.in/PiConnectWSTp/')
        
# FlatTrade validation logic
async def handle_flattrade_validation(data, config):
    userName = data["userId"]
    pswrd = data['password']
    apikey = data['apiKey']
    qrcode = data['qrCode']

    try:
        secretKey = data['secretKey']
    except KeyError:
        secretKey = ""

    header_json = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; win64; x64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/53.36",
        "Referer": "https://auth.flattrade.in/"
    }

    ses_url = 'https://authapi.flattrade.in/auth/session'
    
    if userName not in config.flattrade_sessions:
        ses = requests.Session()
        config.flattrade_sessions[userName] = ses
    else:
        ses = config.flattrade_sessions[userName]

    try:
        res_pin = config.flattrade_sessions[userName].post(ses_url, headers=header_json)
        sid = res_pin.text

        totp_value = TOTP(qrcode).now()
    except Exception as e:
        error_message = f"Error message: {e}"
        print(error_message)
        if "Incorrect padding" in str(e):
            return jsonify({'message': f'Invalid QR Code: {userName}', 'error': error_message}), 500
            # user_settings_errors(code='USFTIQR',description='Invalid QR Code')
        elif "Non-base32 digit found" in str(e):
            return jsonify({'message': f'Invalid QR Code: {userName}', 'error': error_message}), 500
            # user_settings_errors(code='USFTIQR',description='Invalid QR Code')
        else:
            user_settings_errors(code='',description='')
        

    url2 = 'https://authapi.flattrade.in/ftauth'
    password_encrypted = hashlib.sha256(pswrd.encode()).hexdigest()
    payload = {
        "UserName": userName,
        "password": password_encrypted,
        "PAN_DOB": totp_value,
        "App": "",
        "CientID": "",
        "key": "",
        "APIkey": apikey,
        "Sid": sid
    }

    res2 = config.flattrade_sessions[userName].post(url2, json=payload)
    if res2.status_code != 200:
        return jsonify({'message': f'Error validating user: {userName}'}), 500

    reqcode_res = res2.json()

    if reqcode_res['emsg'] == 'Invalid API key':
        return jsonify({'message': f'Invalid API key or User ID: {userName}'}), 500
    elif reqcode_res['emsg'] == 'Invalid Input : Invalid Password':
        return jsonify({'message': f'Invalid Password: {userName}'}), 500
        
    parsed = urlparse(reqcode_res['RedirectURL'])
    parsed_query = parse_qs(parsed.query)
    if 'code' in parsed_query:
        req_code = parsed_query['code'][0]
    else:
        return jsonify({'message': f'Invalid Password or QR Code: {userName}'}), 500

    api_url = "https://auth.flattrade.in/?app_key=" + apikey
    api_secret = apikey + req_code + secretKey
    api_secret = hashlib.sha256(api_secret.encode()).hexdigest()
    payload_token = {"api_key": apikey, "request_code": req_code, "api_secret": api_secret}
    url3 = 'https://authapi.flattrade.in/trade/apitoken'
    res3 = ses.post(url3, json=payload_token)

    if res3.status_code == 200:
        token = res3.json()['token']
        if token == '':
            return jsonify({'message': f'Invalid Secret Key: {userName}'}), 500
        else:
            if userName not in config.flattrade_api:
                api = FlatTradedApiPy()
                config.flattrade_api[userName] = api
            else:
                api = config.flattrade_api[userName]

            # Use the session globally for all requests
            api.session = config.flattrade_sessions[userName]

            # Now you can call the methods of api
            ret = api.set_session(userid=userName, password=pswrd, usertoken=token)

            details = api.get_limits()
                # user = api.get_order_book()
                # print("user",user)
                # rel = api.searchscrip(exchange='NFO', searchtext='BANKNIFTY 27 MAR CE')
                # print("rel:", rel)
                
                # option_contracts = api.get_option_chain('NFO', 'BANKNIFTY27MAR24C47000', '47000', '5')
                # print("option_contracts:", option_contracts)
                
                # flattrade_order = api.place_order(buy_or_sell='B', product_type='C',
                #     exchange='NFO', tradingsymbol='BANKNIFTY27MAR24C47000', 
                #     quantity=15, discloseqty=0,price_type='LMT', price=0, trigger_price=0,
                #     retention='DAY', remarks='testing21324')

                # print("flattrade_order:", flattrade_order)
                    
                # exch  = 'NFO'
                # token = '66691'
                # bannknifty = api.get_quotes(exchange=exch, token=token)
                # print("bannknifty:", bannknifty)

                # details['availablecash'] = details['cash']
                # del details['cash']
                # details['name'] = details['prfname']
                # del details['prfname']

            response_data= ({'message': 'Validation successful', 'data': details})
            return jsonify (response_data), 200
    else:
        response_data = {'message': 'Authentication failed', 'data': f'{res2.text}'}
        return jsonify(response_data), 500