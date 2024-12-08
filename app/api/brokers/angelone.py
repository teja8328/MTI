from pyotp import TOTP
from SmartApi.smartConnect import SmartConnect
from flask import jsonify, abort
from flask import Blueprint, jsonify, request, abort, Flask
import asyncio
from app.api.brokers import config
from flask import Flask, jsonify
import threading
import pyotp
import time
from datetime import datetime
from SmartApi import SmartConnect
from app.api.brokers.SmartWebsocketv2 import SmartWebSocketV2
from flask import Blueprint, jsonify, abort, request
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

# # Initialize dictionary to store data
sws = None
def retrieve_live_feed():
    global sws

    # Hardcoded tokens for NSE
    token_dict = {
        "NSE": ["99926000", "99926009", "99926037"],
        "BSE": ["99919000"]
    }

    # Mapping exchange types
    exchange_type_mapping = {
        "NSE": 1,
        "BSE": 3
    }

    # Prepare token lists based on exchange types
    new_tokens_list = []
    for exchange, tokens in token_dict.items():
        exchange_type = exchange_type_mapping.get(exchange)
        if exchange_type is not None:
            new_tokens_list.append({
                "exchangeType": exchange_type,
                "tokens": tokens
            })

    # Close the existing WebSocket connection, if it exists
    if sws:
        sws.close_connection()
        sws = None

    # Retrieve necessary authentication and configuration details
# Retrieve necessary authentication and configuration details
    AUTH_TOKEN = "Bearer eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6IlM3NjQ3NzQiLCJyb2xlcyI6MCwidXNlcnR5cGUiOiJVU0VSIiwidG9rZW4iOiJleUpoYkdjaU9pSlNVekkxTmlJc0luUjVjQ0k2SWtwWFZDSjkuZXlKMWMyVnlYM1I1Y0dVaU9pSmpiR2xsYm5RaUxDSjBiMnRsYmw5MGVYQmxJam9pZEhKaFpHVmZZV05qWlhOelgzUnZhMlZ1SWl3aVoyMWZhV1FpT2pFeExDSnpiM1Z5WTJVaU9pSXpJaXdpWkdWMmFXTmxYMmxrSWpvaU9ETXlabU5rWlRBdE5qUTNNaTB6TURkbUxXSmpZalV0Tm1NeE5qQXlaVEF6TlRWbElpd2lhMmxrSWpvaWRISmhaR1ZmYTJWNVgzWXhJaXdpYjIxdVpXMWhibUZuWlhKcFpDSTZNVEVzSW5CeWIyUjFZM1J6SWpwN0ltUmxiV0YwSWpwN0luTjBZWFIxY3lJNkltRmpkR2wyWlNKOWZTd2lhWE56SWpvaWRISmhaR1ZmYkc5bmFXNWZjMlZ5ZG1salpTSXNJbk4xWWlJNklsTTNOalEzTnpRaUxDSmxlSEFpT2pFM016TTBOVGsxTWpjc0ltNWlaaUk2TVRjek16TTNNamswTnl3aWFXRjBJam94TnpNek16Y3lPVFEzTENKcWRHa2lPaUkxWldZeU1HUXpaaTB6T0RjNExUUXdORFV0T1RWbE55MWtNamhqWVRZeU9EUmxOV1FpTENKVWIydGxiaUk2SWlKOS5XUjE4eUdMYzZmdzJtcUZIY1hCdFJTaFlRbUNzX2NfRW55RnVyUHZvUnMyRkh4Q2J2R3lzR1VfblVIUXlUdU8yU0FfbFR2Q3ZWTExIWkxtTzJ5bGtsUjUyNFh0SzhRQWhrT2xydExHSHB3UFV3emxmSlhPR2FqeDAyRTdmRTBzZVpkRFNKVU9jangxbFdVWEFmN2czeTl2b3B5NU1BTGFIdXZDc2pKVURGVjQiLCJBUEktS0VZIjoiekc4czlMbnMiLCJpYXQiOjE3MzMzNzMxMjcsImV4cCI6MTczMzQ1OTUyN30.It9TXlJQS8n990LhRB6raE7nPVoUzVyga_Z9hnE8azW4b4sFx4a9QDnv5eKGYOOmG3CCEAf4FKtF841YtC6lDQ"
    API_KEY = "zG8s9Lns"
    CLIENT_CODE = "S764774"
    FEED_TOKEN = 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VybmFtZSI6IlM3NjQ3NzQiLCJpYXQiOjE3MzMzNzMxMjcsImV4cCI6MTczMzQ1OTUyN30.uIlZO2HF_uqCqHx23RSLVT2HfWIQP_hSnkZQMdaxnWNTuu-yLdBWgL8G2384nOCIw0ElAOsmk3Ev-S1nHcG0AQ'

    # Initialize the WebSocket connection parameters
    correlation_id = "abc123"
    mode = 3

    # Initialize SmartWebSocketV2 instance
    sws = SmartWebSocketV2(AUTH_TOKEN, API_KEY, CLIENT_CODE, FEED_TOKEN, max_retry_attempt=100,
                        retry_strategy=2, retry_delay=30, retry_duration=300)

    # Define callback functions
    def on_data(wsapp, message):
        # Log the received message
        # print("Received message:", message)
        
        # Extract the token, last_traded_price, and closed_price from the message
        token = message.get('token')
        last_traded_price = message.get('last_traded_price')
        closed_price = message.get('closed_price')

        # Validate presence of token and prices
        if token and last_traded_price is not None and closed_price is not None:
            # Format the prices (dividing by 100 to adjust for price scale)
            formatted_ltp = "{:.2f}".format(last_traded_price / 100)
            formatted_cp = "{:.2f}".format(closed_price / 100)
            
            # Save the values into the LIVE_FEED_JSON dictionary
            config.LIVE_FEED_JSON[token] = {
                "last_traded_price": formatted_ltp,
                "closed_price": formatted_cp
            }
            
            # Log the updated dictionary for debugging
            # print(f"Updated LIVE_FEED_JSON: {config.LIVE_FEED_JSON}")
        else:
            print("Missing data in the received message. Check for errors.")

    def on_control_message(wsapp, message):
        print(f"Control Message: {message}")

    def on_open(wsapp):
        print("WebSocket connection opened")
        sws.subscribe(correlation_id, mode, new_tokens_list)

    def on_error(wsapp, error):
        print(f"WebSocket error: {error}")

    def on_close(wsapp):
        print("WebSocket connection closed")
        time.sleep(5)
        connect_websocket()

    # Assign the callbacks
    sws.on_open = on_open
    sws.on_data = on_data
    sws.on_error = on_error
    sws.on_close = on_close
    sws.on_control_message = on_control_message

    # Connect to WebSocket in a separate thread
    def connect_websocket():
        try:
            sws.connect()
        except Exception as e:
            print(f"Error connecting to WebSocket: {e}")
            time.sleep(5)
            connect_websocket()

    websocket_thread = threading.Thread(target=connect_websocket)
    websocket_thread.start()

    # Log a success message
    print("Angelone WebSocket initialized and tokens subscribed.")

def continuously_print_live_feed():
    """Function to print the live feed continuously."""
    while True:
        print("Current LIVE_FEED_JSON:")
        # print(config.LIVE_FEED_JSON)  # Print the current live feed data
        time.sleep(5)  # Delay for 5 seconds before printing again


def get_live_feed_data():
     return config.LIVE_FEED_JSON

# Flask blueprint
get_live_feed_blueprint = Blueprint('get_live_feed', __name__)

@get_live_feed_blueprint.route('/get_live_feed', methods=['GET'])
def get_live_feed():
     live_feed_data = get_live_feed_data()
#     print(live_feed_data)
     return jsonify(live_feed_data)


# from fyers_apiv3.FyersWebsocket import data_ws
# from flask import Blueprint, jsonify, abort, request
# from fyers_apiv3 import fyersModel
# # import config
# import time
# import threading

# LIVE_FEED_JSON = {}
# # Replace the sample access token with your actual access token obtained from Fyers
# access_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3MzE5MDQ1MDEsImV4cCI6MTczMTk3NjIwMSwibmJmIjoxNzMxOTA0NTAxLCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbk9zUDFIbkt5c255cXlmZGkxVkpqTGlBbzBwZ1dNWjNGOVp6bEVyRDRsakQ4dncyLV9aS0RxUXJoRXNMODZKb0FYU25PYy0zejBQeWxLaXdnTVg4NzlLOW5jbGk5WmhYZzhMVDROaE1lMXZsQzVCTT0iLCJkaXNwbGF5X25hbWUiOiJTQUkgR0FORVNIIEtBTlVQQVJUSEkiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiIwYTgzNjI0ZmEwYjA1ZmViODJmNDBlMDdiY2Y3MmYxYWEwMGY1ODFhMTIxOTNkNWM3Y2ZlZTI2YiIsImZ5X2lkIjoiWVMxNzE5NSIsImFwcFR5cGUiOjEwMCwicG9hX2ZsYWciOiJOIn0.JEk_DcZdr935tREqXXJj86lpfYDRrsE21oDR_nQ8vK0',

# def retrieve_fyers_live_feed(access_token):
#     def onmessage(message):
#         global LIVE_FEED_JSON
#         config.symbols_list.append(message['symbol'])
#         if message['symbol'] in list(set(config.symbols_list)):
#             config.LIVE_FEED_JSON.update({ message['symbol'] : message })
#         else:
#             config.LIVE_FEED_JSON = { message['symbol'] : message }
        
#     def onerror(message):
#         print("Error:", message)

#     def onclose(message):
#         print("Connection closed:", message)

#     def onopen():
#         data_type = "SymbolUpdate"
#         symbols = ["NSE:NIFTY50-INDEX" , "NSE:NIFTYBANK-INDEX","NSE:FINNIFTY-INDEX","BSE:SENSEX-INDEX"]
#         fyers.subscribe(symbols=symbols, data_type=data_type)
#         fyers.keep_running()

#     fyers = data_ws.FyersDataSocket(
#         access_token=access_token,
#         log_path="",
#         litemode=False,
#         write_to_file=False,
#         reconnect=True,
#         on_connect=onopen,
#         on_close=onclose,
#         on_error=onerror,
#         on_message=onmessage
#     )

#     threading.Thread(target=fyers.connect).start()

# def print_fyers_live_feed():
#     global LIVE_FEED_JSON
#     while True:
#         # print('LIVE_FEED_JSON:', config.LIVE_FEED_JSON)
#         time.sleep(2)

# def get_live_feed_data():
#     global LIVE_FEED_JSON
#     return config.LIVE_FEED_JSON

# get_live_feed_blueprint = Blueprint('get_live_feed', __name__)

# @get_live_feed_blueprint.route('/get_live_feed', methods=['GET'])
# def get_live_feed():
#     time.sleep(3)
#     live_feed_data = get_live_feed_data()
#     return jsonify(live_feed_data)

app = Flask(__name__)
app.register_blueprint(get_live_feed_blueprint)


import requests.exceptions

async def execute(data):
    data = await handle_angelone_validation(data)
    return data
 

async def execute(data):
    data = await handle_angelone_validation(data)
    return data
 
async def handle_angelone_validation(data):
    userName = data["userId"]
    pswrd = data.get('password')
    apikey = data.get('apiKey')
    qrcode = data.get('qrCode')
    config.CLIENT_CODE = userName
    config.PASSWORD = pswrd
    config.API_KEY = apikey
    config.TOKEN = qrcode
   
    if not all([userName, pswrd, apikey, qrcode]):
        return jsonify({'message': 'Missing required fields'}), 400
 
    try:
        totp = TOTP(qrcode).now()
    except Exception as e:
        return jsonify({'message': f'Invalid QR Code: {userName}', 'error': str(e)}), 500
   
    try:
        obj = config.SMART_API_OBJ_angelone
        if not obj:
            print("Without Login")
            obj = SmartConnect(api_key=apikey)
            print('obj:', obj)
            config.SMART_API_OBJ_angelone[userName] = obj
            
        elif userName not in config.SMART_API_OBJ_angelone.keys():
            obj = SmartConnect(api_key=apikey)
            print('obj:', obj)
            config.SMART_API_OBJ_angelone[userName] = obj
        else:
            obj = config.SMART_API_OBJ_angelone[userName]

    except Exception as e:
        config.SMART_API_OBJ_angelone.pop(userName)
        return jsonify({'message': f'Invalid API Key: {userName}', 'error': str(e)}), 500
 
    try:
        if config.angel_one_data == {}:
            data = obj.generateSession(userName, pswrd, totp)
            config.angel_one_data[userName] = data
        elif userName not in config.angel_one_data.keys():
            data = obj.generateSession(userName, pswrd, totp)
            config.angel_one_data[userName] = data
        else:
            data = config.angel_one_data[userName]
 
        if not data['status']:
            config.angel_one_data.pop(userName)
            config.SMART_API_OBJ_angelone.pop(userName)
            error_message = data["message"].replace("Invalid totp", "Invalid QR Code or User ID")
            return jsonify({'message': f'{error_message} : {userName}', 'data': data}), 400
           
        refreshToken = data['data']['refreshToken']
        auth_token = data['data']['jwtToken']
        feedToken = obj.getfeedToken()
        config.AUTH_TOKEN = auth_token
        config.FEED_TOKEN = feedToken
        userProfile = obj.getProfile(refreshToken)
        blnc = obj.rmsLimit()
        print('\n\n\n\n')
        print(config.SMART_API_OBJ_angelone)
        # orderbook = obj.orderBook()
        # nifty_ltp = obj.ltpData('NSE', 'NIFTY', '26000')
        # bank_nifty_ltp = obj.ltpData('NSE', 'BANKNIFTY', '26009')
        # fin_nifty_ltp = obj.ltpData('NSE', 'Nifty Fin Service', '99926037')
        # sensex_ltp = obj.ltpData('BSE', 'SENSEX', '99919000')
       
        userProfile['data']['availablecash'] = float(blnc['data']['availablecash'])
        userProfile['data']['Net'] = float(blnc['data']['net'])
     
        response_data = {'message': f'Validation Successful: {userName}', 'data': userProfile}
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({'message': f'Error validating account: {userName}', 'error': str(e)}), 500
        


import asyncio


async def log_out_session(broker_user_id):
    try:
        obj = config.SMART_API_OBJ_angelone.get(broker_user_id)
        print("obj:", obj)
        if obj:
            obj.terminateSession(broker_user_id)
            return None  
        else:
            return f"No active session found for user: {broker_user_id}"
    except Exception as e:
        return str(e)  

logout_angelone_blueprint = Blueprint('logout_angelone', __name__)

@logout_angelone_blueprint.route('/logout_angelone/<string:broker_user_id>', methods=['POST'])
async def logout(broker_user_id):
    try:
        result = await log_out_session(broker_user_id)  
        if result is None:
            return jsonify({'message': 'Logout Successful'}), 200  
        else:
            return jsonify({'message': result}), 404  
    except Exception as e:
        return jsonify({'message': 'Logout failed', 'error': str(e)}), 500 
 
# import csv
# import json
# import pyotp
# from .SmartApi import SmartConnect, SmartWebSocketOrderUpdate
 
 
# def server(feed_token,auth_token,userName,api_key):
#     print("Hello")
#     class MyWebSocketOrderUpdate(SmartWebSocketOrderUpdate):
#         def on_message(self, ws, message):
#             try:
#                 # Print the received message
#                 print(f"Received message: {message}")
 
#                 # Parse the JSON string into a dictionary
#                 message_dict = json.loads(message)
 
#                 order_data_value = message_dict.get("orderData", None)
 
#                 if order_data_value is not None:
#                     # Handle the case where "orderData" is a string
#                     if isinstance(order_data_value, str):
#                         order_data = json.loads(order_data_value)
#                     else:
#                         order_data = order_data_value
                   
#                     with open('ordercopy2.csv', 'a', newline='') as data_file:
#                         csv_writer = csv.writer(data_file)
 
#                         # Check if the CSV file is empty and write the header
#                         if data_file.tell() == 0:
#                             csv_writer.writerow(order_data.keys())
 
#                         # Write the data
#                         csv_writer.writerow(order_data.values())
#             except json.JSONDecodeError as e:
#                 print(f"No order placed")
 
#     client = MyWebSocketOrderUpdate(auth_token=auth_token, api_key=api_key, client_code=userName, feed_token=feed_token)
#     client.connect()