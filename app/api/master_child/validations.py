import pandas as pd
from datetime import datetime,time 
import threading
from  time import sleep
from logzero import logger
import pyotp
import json
import urllib
import datetime as dt
from SmartApi import SmartConnect
from app.api.multileg import config
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from flask import Blueprint, jsonify, request, abort, Flask
from flask import Blueprint, jsonify, abort, request
from flask_restful import Api, Resource
import json
from datetime import datetime, time
from time import sleep
import logging
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime, time
from time import sleep
import logging
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.api.brokers import config
from urllib.parse import quote_plus

from sqlalchemy.orm import sessionmaker
from app.models.user import Portfolio , BrokerCredentials , Strategies , Portfolio_legs ,ExecutedPortfolio,ExecutedEquityOrders,MasterAccount,ChildAccount
from app.models.user import User
from app.models.main import db
from SmartApi import SmartConnect
from pyotp import TOTP
from fyers_apiv3.FyersWebsocket import order_ws
from fyers_apiv3 import fyersModel
from app.api.brokers import config
import re
from datetime import time
from datetime import datetime
import time
import pytz
from fyers_apiv3 import fyersModel
from datetime import datetime,time
import pytz
import pandas as pd
import urllib.request
import io
import json
import numpy as np
import datetime
from sqlalchemy import func
import re
import os
import csv
import requests
from datetime import datetime
import time
from datetime import datetime, time
from datetime import datetime, time
from app.models.user import ExecutedEquityOrders , StrategyMultipliers
from sqlalchemy.orm import joinedload
import urllib.request
import json
import datetime as dt
import pandas as pd
from sqlalchemy import Time
from sqlalchemy.exc import SQLAlchemyError
from collections import defaultdict

cached_df_fyers = None

class MasterChild:

    def create_master_child_accounts(username):
        data = request.json
        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            user_id = existing_user.id
        else:
            response_data = {'message': 'User does not exist'}
            return jsonify(response_data), 200

        master_data = data.get('masterAccount')
        child_accounts_data = data.get('childAccounts')

        # Validate master account data
        if not master_data or not all([
            master_data.get('name'), master_data.get('broker'), master_data.get('broker_user_id')
        ]):
            return jsonify({'message': 'Missing required master account data'}), 400

        name = master_data.get('name')
        broker = master_data.get('broker')
        broker_user_id = master_data.get('broker_user_id')
        copy_start_time = master_data.get('copyStartTime')
        copy_end_time = master_data.get('copyEndTime')
        copy_placement = master_data.get('copyPlacement')
        copy_cancellation = master_data.get('copyCancellation')
        copy_modification = master_data.get('copyModification')
        parallel_order_execution = master_data.get('parallelOrderExecution')
        auto_split_frozen_qty = master_data.get('autoSplitFrozenQty')

        try:
            master_account = MasterAccount.query.filter_by(
                name=name, broker=broker, broker_user_id=broker_user_id
            ).first()

            if master_account:
                # Update existing master account
                master_account.copy_start_time = copy_start_time
                master_account.copy_end_time = copy_end_time
                master_account.copy_placement = copy_placement
                master_account.copy_cancellation = copy_cancellation
                master_account.copy_modification = copy_modification
                master_account.parallel_order_execution = parallel_order_execution
                master_account.auto_split_frozen_qty = auto_split_frozen_qty
            else:
                # Create a new master account
                master_account = MasterAccount(
                    name=name, broker=broker, broker_user_id=broker_user_id,
                    copy_start_time=copy_start_time, copy_end_time=copy_end_time,
                    copy_placement=copy_placement, copy_cancellation=copy_cancellation,
                    copy_modification=copy_modification, parallel_order_execution=parallel_order_execution,
                    auto_split_frozen_qty=auto_split_frozen_qty,user_id = user_id
                )
                db.session.add(master_account)

            created_or_updated_child_accounts = []

            if child_accounts_data:
                for account_data in child_accounts_data:
                    child_name = account_data.get('name')
                    multiplier = account_data.get('multiplier')
                    child_broker = account_data.get('broker')
                    child_broker_user_id = account_data.get('broker_user_id')
                    live = account_data.get('live')

                    # Validate child account data
                    if not all([child_name, multiplier, child_broker, child_broker_user_id]):
                        return jsonify({'message': 'Missing data for one or more child accounts'}), 400

                    existing_child_account = ChildAccount.query.filter_by(broker_user_id=child_broker_user_id).first()

                    if existing_child_account:
                        existing_child_account.multiplier = multiplier
                        existing_child_account.live = live
                        existing_child_account.name = child_name
                        created_or_updated_child_accounts.append(existing_child_account)
                    else:
                        new_child_account = ChildAccount(
                            name=child_name, multiplier=multiplier, broker=child_broker,
                            broker_user_id=child_broker_user_id, live=live, master_account=master_account
                        )
                        db.session.add(new_child_account)
                        created_or_updated_child_accounts.append(new_child_account)

            db.session.commit()
            return jsonify({
                'message': 'Master and child accounts created or updated successfully',
                'created_master_account': master_account.name,
                'created_or_updated_child_accounts': [account.name for account in created_or_updated_child_accounts]
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'message': 'Failed to create or update accounts', 'details': str(e)}), 500

    def fetch_master_child_accounts(username):
        
        existing_user = User.query.filter_by(username=username).first()


        try:
            master_accounts = MasterAccount.query.filter_by(user_id=existing_user.id).all()
            results = []

            for master in master_accounts:
                master_dict = {
                    "id": master.id,
                    "name": master.name,
                    # "multiplier": master.multiplier,
                    "broker": master.broker,
                    "broker_user_id": master.broker_user_id,
                    "copy_start_time": master.copy_start_time.strftime('%H:%M:%S') if master.copy_start_time else None,
                    "copy_end_time": master.copy_end_time.strftime('%H:%M:%S') if master.copy_end_time else None,
                    "copy_placement": master.copy_placement,
                    "copy_cancellation": master.copy_cancellation,
                    "copy_modification": master.copy_modification,
                    "parallel_order_execution": master.parallel_order_execution,
                    "auto_split_frozen_qty": master.auto_split_frozen_qty,
                    "child_accounts": []
                }

                child_accounts = master.child_accounts
                for child in child_accounts:
                    child_dict = {
                        "id": child.id,
                        "name": child.name,
                        "broker": child.broker,
                        "broker_user_id": child.broker_user_id,
                        "multiplier": child.multiplier,
                        "live": child.live
                    }
                    master_dict["child_accounts"].append(child_dict)

                results.append(master_dict)

            return jsonify(results), 200
        except Exception as e:
            return jsonify({'message': 'Failed to retrieve accounts', 'details': str(e)}), 500

    def delete_master_child_accounts(username, broker_user_id):
        existing_user = User.query.filter_by(username=username).first()

        if not existing_user:
            return jsonify({'message': "User does not exist"}), 404

        try:
            # Find the master account based on broker_user_id
            master_account = MasterAccount.query.filter_by(broker_user_id=broker_user_id).first()
            
            if not master_account:
                return jsonify({'message': "Master account does not exist"}), 404

            # Delete all child accounts associated with this master account
            child_accounts = ChildAccount.query.filter_by(master_account_id=master_account.id).all()
            for child_account in child_accounts:
                db.session.delete(child_account)

            # Delete the master account
            db.session.delete(master_account)

            db.session.commit()
            return jsonify({
                'message': f'Master account with broker_user_id {broker_user_id} deleted successfully'
            }), 200

        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({'message': 'Failed to delete accounts', 'details': str(e)}), 500

    def angelone_symbols(username, broker_user_id):
        data = request.json
        
        if 'exchange' not in data:
            return jsonify({"error": "Exchange not provided"}), 400
        
        exchange = data['exchange']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            try:
                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
            except KeyError:
                return jsonify({"error": "Broker ID not found"}), 500   
        
            # URL of the JSON data
            json_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            
            try:
                # Fetch data from the URL
                response = urllib.request.urlopen(json_url)
                # Load JSON data
                data = json.load(response)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
            
            nse_symbols = []
            bse_symbols = []
            nfo_symbols = []

            for instrument in data:
                symbol = instrument.get('symbol')
                exch_seg = instrument.get('exch_seg')
                if symbol:  # Check if symbol is not empty or None
                    if exchange == 'NSE' and exch_seg == 'NSE':
                        nse_symbols.append(symbol)
                    elif exchange == 'BSE' and exch_seg == 'BSE':
                        bse_symbols.append(symbol)
                    elif exchange == 'NFO' and exch_seg == 'NFO':
                        nfo_symbols.append(symbol)

            # Create dataframes for NSE, BSE, and NFO symbols
            nse_df = pd.DataFrame(nse_symbols, columns=['Symbol'])
            bse_df = pd.DataFrame(bse_symbols, columns=['Symbol'])
            nfo_df = pd.DataFrame(nfo_symbols, columns=['Symbol'])

            response_data = {
                "angelone_nse_symbols_data": nse_df.to_dict(orient='records'),
                "angelone_bse_symbols_data": bse_df.to_dict(orient='records'),
                "angelone_nfo_symbols_data": nfo_df.to_dict(orient='records')
            }
            return jsonify(response_data), 200
        
        return jsonify({"error": "User not found"}), 404

    def delete_child_account(username,broker_user_id):
        existing_user = User.query.filter_by(username=username).first()

        if not existing_user:
            return jsonify({"message": "User not found"}), 404
        try:
            child_account = ChildAccount.query.filter_by(broker_user_id=broker_user_id).first()

            if not child_account:
                return jsonify({'message': 'Child account not found'}), 404

            db.session.delete(child_account)
            db.session.commit()
            return jsonify({'message': 'Child account deleted successfully'}), 200

        except Exception as e:
            logging.error(f"Error deleting child account: {str(e)}")
            db.session.rollback()
            return jsonify({'message': 'Failed to delete child account', 'details': str(e)}), 500

    def place_master_child_order(username, master_account_id,child_broker_user_id=None):
            import datetime
            current_time_str = datetime.datetime.now().strftime('%H%M%S')
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                return jsonify({"message": "User not found"}), 404
    
            master_account = MasterAccount.query.filter_by(id=master_account_id).options(joinedload(MasterAccount.child_accounts)).first()
            if not master_account:
                return jsonify({'message': 'Master account not found'}), 404
            master_account_id = master_account.id
            data = request.json
            symbol = data.get('symbol')
            exchange = data.get('exchange')
            ordertype = data.get('ordertype')
            transactiontype = data.get('transactiontype')
            quantity = data.get('quantity')
            producttype = data.get('producttype')
            duration = data.get('duration')
            price = data.get('price') if ordertype == 'LIMIT' else 0
    
            # if not all([symbol, exchange, ordertype, transactiontype, quantity]):
            #     return jsonify({"message": "Invalid order parameters"}), 400
    
            config.order_place_response = []
    
            def angle_one_login(broker_user_id):
                if broker_user_id not in config.SMART_API_OBJ_angelone:
                    api_obj = SmartConnect(api_key=config.apikey)
                    data = api_obj.generateSession(config.username, config.pwd, pyotp.TOTP(config.token).now())
                    config.AUTH_TOKEN = data['data']['jwtToken']
                    refreshToken = data['data']['refreshToken']
                    config.FEED_TOKEN = api_obj.getfeedToken()
                    api_obj.getProfile(refreshToken)
                    config.SMART_API_OBJ_angelone[broker_user_id] = api_obj
    
            def angle_one_place_order(broker_user_id, order_params):
                response = config.SMART_API_OBJ_angelone[broker_user_id].placeOrder(order_params)
                return response
        
            def flattrade_place_order(broker_user_id, order_params):
                print("")
                response = config.flattrade_api[broker_user_id].place_order(**order_params)
                return response
        
            def fyers_place_order(broker_user_id, data):
                print("fyers_place_order")
                response = config.OBJ_fyers[broker_user_id].place_order(data=data)
                return response
    
            # Add login and order placement functions for other brokers as needed
            def some_other_broker_login(broker_user_id):
                # Implement login logic for another broker
                pass
    
            def some_other_broker_place_limit_order(broker_user_id, order_params):
                # Implement order placement logic for another broker
                pass
    
            def generic_login(broker, broker_user_id):
                if broker == 'angelone':
                    angle_one_login(broker_user_id)
                elif broker == 'flattrade':
                    config.flattrade_api.get(broker_user_id)  
                elif broker == 'fyers':
                    config.OBJ_fyers.get(broker_user_id)
                # Add additional login functions for other brokers here
    
            def generic_place_order(broker, broker_user_id, order_params, data):
                if broker == 'angelone':
                    return angle_one_place_order(broker_user_id, order_params)
                elif broker == 'flattrade':
                    return flattrade_place_order(broker_user_id, order_params)
                elif broker == 'fyers':
                    return fyers_place_order(broker_user_id, data)
                # Add additional order placement functions for other brokers here
            
            if exchange=="NFO" or exchange == "NSE":
                def process_order(username,account, symbol, quantity,master_id):
                    existing_user = User.query.filter_by(username=username).first()
        
                    if not existing_user:
                        response_data = {'message': "User Does not exist"}
                        return jsonify(response_data), 500
        
                    user_id = existing_user.id
                    account_details = MasterAccount.query.filter_by(user_id=user_id).first()
                    print("master_account_details:",account_details)
    
                    broker = account.broker
                    broker_user_id = account.broker_user_id
                    multiplier = getattr(account, 'multiplier', 1)
                    print("multiplier:",multiplier)
    
                    generic_login(broker, broker_user_id)
    
                    if broker == 'angelone':
                        token = fetch_token(symbol, exchange)
                        if token is None:
                            return {'message': "Instrument not found"}, 500
                        angel_one_total_quantity = quantity * multiplier
                        print("angelone_quantity:",angel_one_total_quantity)


                        master_id_str = f"{current_time_str}{master_id}"

                        if exchange == "NFO" :
                            order_params = {
                                "variety": "NORMAL",  
                                "tradingsymbol": symbol,
                                "symboltoken": token,
                                "transactiontype": transactiontype,  
                                "exchange": exchange,
                                "ordertype": ordertype,
                                "producttype": producttype,
                                "duration": duration,
                                "price": price,
                                "quantity": angel_one_total_quantity,
                                "ordertag": master_id_str
                            }
                        else:
                            order_params = {
                                "variety": "NORMAL",  
                                "tradingsymbol": symbol,
                                "symboltoken": token,
                                "transactiontype": transactiontype,  
                                "exchange": exchange,
                                "ordertype": ordertype,
                                "producttype": 'DELIVERY' if producttype == 'NORMAL' else 'INTRADAY',
                                "duration": duration,
                                "price": price,
                                "quantity": angel_one_total_quantity,
                                "ordertag": master_id_str
                            }
    
                        order_id = generic_place_order(broker, broker_user_id, order_params, data=None)
                        if not order_id:
                            return {'message': "Order placement failed"}, 500
    
                        print("Order placed:", order_id)
                        api_obj = config.SMART_API_OBJ_angelone[broker_user_id]
                        config.all_angelone_details[broker_user_id] = {
                            "orderbook": api_obj.orderBook(),
                            "positions": api_obj.position(),
                            "holdings": api_obj.holding(),
                            "all_holdings": api_obj.allholding()
                        }

                        status = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['orderstatus']
                        order_status = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['status']
                        orderid = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['orderid']
                        if order_status=='rejected':
                            rejection_reason =(broker_user_id ,config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['text'])
                            return rejection_reason, 400  
                   
                        elif order_status == "complete" or order_status=="open":
                            #avg_price = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['averageprice']
                            if order_status == "complete":
                                avg_price = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['averageprice']
                            else:  # order_status == "OPEN"
                                limit_price_value = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['price']
                            if transactiontype=="BUY":
                                executed_master_child_positions = ExecutedPortfolio(user_id=user_id,broker_user_id=broker_user_id,
                                                transaction_type=transactiontype,
                                                trading_symbol=symbol,
                                                exchange=exchange,product_type=producttype,
                                                netqty=angel_one_total_quantity,order_id = orderid,
                                                symbol_token=token, broker=broker,
                                                variety="NORMAL",duration=duration,buy_price= avg_price if order_status == "complete" else limit_price_value,
                                                order_type=ordertype,status=status,master_account_id= master_account_id)
                            else:
                                executed_master_child_positions = ExecutedPortfolio(user_id=user_id,broker_user_id=broker_user_id,
                                transaction_type=transactiontype,order_id= orderid,
                                trading_symbol=symbol,
                                exchange=exchange,product_type=producttype,
                                netqty=angel_one_total_quantity,
                                symbol_token=token,broker=broker,
                                variety="NORMAL",duration=duration,sell_price=avg_price if order_status == "complete" else limit_price_value,
                                order_type=ordertype,status=status,master_account_id=master_account_id)
                            
    
                            db.session.add(executed_master_child_positions)
                            db.session.commit()
                            message={'message': f'Order placed successfully for {broker_user_id}'}
                            return message, 200  # Return with a 200 status code for success
                        else:
                            message={'message': "Unknown order status"}
                            return message, 500  
                    
                    elif broker == 'flattrade':
                        token = fetch_token(symbol, exchange)
                    
                        print("token:", token)
                        if token is None:
                            response_data = {'message': "Instrument not found"}
                            return jsonify(response_data), 500
                        flattrade_total_quantity = quantity * multiplier

                        def symbol_converter(symbol):
                            angleone_symbol = symbol
                            pattern_option = r"([A-Z]+)(\d{2}[A-Z]{3}\d{2})(\d+)([PE|CE])"
                            pattern_futures = r"([A-Z]+)(\d{2}[A-Z]{3}\d{2})FUT"
                            match_option = re.search(pattern_option, angleone_symbol)
                            if match_option:
                                index_name = match_option.group(1)
                                expiry_date = match_option.group(2)
                                strike_price = match_option.group(3)
                                option_type = match_option.group(4)[0]  # Remove 'E' from option type
                                flattrade_symbol = f"{index_name}{expiry_date}{option_type}{strike_price}"
                                return flattrade_symbol
                            else:
                                match_futures = re.search(pattern_futures, angleone_symbol)
                                if match_futures:
                                    index_name = match_futures.group(1)
                                    expiry_date = match_futures.group(2)
                                    flattrade_symbol = f"{index_name}{expiry_date}F"
                                    return flattrade_symbol
                                else:
                                    return jsonify({"message": "Invalid angleone symbol format"})

                        master_id_str=str(master_id)
                        master_id_str = f"{current_time_str}{master_id_str}"

                        if exchange == "NFO":  
                            converted_symbol = symbol_converter(symbol)
    
                        if exchange == "NFO":    
                            order_params = {
                                "buy_or_sell": 'B' if transactiontype == 'BUY' else 'S',
                                "product_type": 'I' if producttype == 'INTRADAY' else "M",
                                "exchange": exchange,
                                "tradingsymbol": converted_symbol,
                                "quantity": flattrade_total_quantity,
                                "discloseqty": 0,
                                "price_type" : 'MKT' if ordertype == 'MARKET' else 'LMT' if ordertype == 'LIMIT' else 'UNKNOWN',
                                "price": price,
                                "trigger_price": None,
                                "retention": duration,
                                "remarks": master_id_str  # Example strategy tag, adjust as needed
                            }
                        elif exchange == "NSE":
                            order_params = {
                            "buy_or_sell": 'B' if transactiontype == 'BUY' else 'S',
                            "product_type": 'I' if producttype == 'INTRADAY' else 'C',
                            "exchange": exchange,
                            "tradingsymbol": symbol,
                            "quantity": flattrade_total_quantity,
                            "discloseqty": 0,
                            "price_type" : 'MKT' if ordertype == 'MARKET' else 'LMT' if ordertype == 'LIMIT' else 'UNKNOWN',
                            "price": price,
                            "trigger_price": None,
                            "retention": duration,
                            "remarks": master_id_str  # Example strategy tag, adjust as needed
                            }
                    
                    
                        order_id = generic_place_order(broker, broker_user_id, order_params, data=None)
                        order_book = config.flattrade_api[broker_user_id].get_order_book()
                        print("Order Book :",order_book)
                        positions = config.flattrade_api[broker_user_id].get_positions()
                        holdings = config.flattrade_api[broker_user_id].get_holdings()
                        config.all_flattrade_details[broker_user_id] = {"orderbook": order_book, "positions": positions, "holdings": holdings}
                        print(config.all_flattrade_details[broker_user_id])
                        order_status = config.all_flattrade_details[broker_user_id]["orderbook"][0]['status']
                        #avg_price=0 if order_status=="REJECTED" else config.all_flattrade_details[broker_user_id]["orderbook"][0]['avgprc']
                        orderid=config.all_flattrade_details[broker_user_id]["orderbook"][0]['norenordno']
                        # product_type = config.all_flattrade_details[broker_user_id]["orderbook"][0]['prctyp']
                    
                
                        if order_status == "REJECTED":
                            rejection_reason = config.all_flattrade_details[broker_user_id]["orderbook"][0]['rejreason']
                            rejection_reason_with_id = [broker_user_id, rejection_reason, 400]
                            return rejection_reason_with_id, 400  # Return with a 400 status code for rejection
                    
                        elif order_status == "COMPLETE" or order_status == "OPEN":
                            #avg_price=config.all_flattrade_details[broker_user_id]["orderbook"][0]['avgprc']

                            if order_status == "COMPLETE" or order_status == "OPEN":
                                if order_status == "COMPLETE":
                                    avg_price = config.all_flattrade_details[broker_user_id]["orderbook"][0]['avgprc']
                                else:  # order_status == "OPEN"
                                    limit_price_value = config.all_flattrade_details[broker_user_id]["orderbook"][0]['rprc']

                                
                                if transactiontype == "BUY":
                                    executed_master_child_positions = ExecutedPortfolio(
                                        user_id=user_id,
                                        master_account_id=master_account_id,
                                        broker_user_id=broker_user_id,
                                        order_id=orderid,
                                        transaction_type=transactiontype,
                                        duration=duration,
                                        buy_price=avg_price if order_status == "COMPLETE" else limit_price_value,
                                        trading_symbol=converted_symbol,
                                        status=order_status,
                                        order_type=ordertype,
                                        exchange=exchange,
                                        product_type=producttype,
                                        broker=broker,
                                        netqty=flattrade_total_quantity,
                                        symbol_token=token
                                    )
                                else:

                                    executed_master_child_positions = ExecutedPortfolio(
                                        user_id=user_id,
                                        master_account_id=master_account_id,
                                        broker_user_id=broker_user_id,
                                        order_id=orderid,
                                        transaction_type=transactiontype,
                                        duration=duration,
                                        sell_price=avg_price if order_status == "COMPLETE" else limit_price_value,
                                        trading_symbol=symbol,
                                        status=order_status,
                                        order_type=ordertype,
                                        exchange=exchange,
                                        product_type=producttype,
                                        broker=broker,
                                        netqty=flattrade_total_quantity,
                                        symbol_token=token
                                    )
                            
                            db.session.add(executed_master_child_positions)
                            db.session.commit()
                            message={'message': f'Order placed successfully for {broker_user_id}'}
                            return message, 200  # Return with a 200 status code for success
                        else:
                            message={'message': "Unknown order status"}
                            return message, 500
                    
                    elif broker == 'fyers':
                        def fetch_fyers_data():
                            global cached_df_fyers
                            if cached_df_fyers is not None:
                                return cached_df_fyers
            
                            fyers_csv_url = "https://public.fyers.in/sym_details/NSE_FO.csv"
                            try:
                                with urllib.request.urlopen(fyers_csv_url) as response:
                                    fyers_csv_data = response.read().decode('utf-8')
                                df_fyers = pd.read_csv(io.StringIO(fyers_csv_data))
                                df_fyers.columns = ['Fytoken', 'Symbol Details', 'Exchange Instrument type', 'Minimum lot size', 'Tick size',
                                                    'Empty', 'ISIN', 'Trading Session', 'Last update date', 'Expiry date', 'Symbol ticker',
                                                    'Exchange', 'Segment', 'Scrip code', 'Underlying scrip code', 'Strike price', 'Option type',
                                                    'Underlying FyToken', 'EMPTY', 's1', 's2']
                                cached_df_fyers = df_fyers
                                return df_fyers
                            except Exception as e:
                                raise Exception(f"Error fetching or processing CSV data: {e}")
            
                        def convert_symbol(symbol):
                            print("Entering convert_symbol")
                            if symbol.endswith("CE") or symbol.endswith("PE"):
                                month_map = {"jan": "1", "feb": "2", "mar": "3", "apr": "4", "may": "5",
                                            "jun": "6", "jul": "7", "aug": "8", "sep": "9", "oct": "10",
                                            "nov": "11", "dec": "12"}
                                match = re.search(r"^(?P<index>\w+)(?P<expiry_date>\d{2})(?P<month>\w{3})(?P<year>\d{2})(?P<strike_price>\d+)(?P<option_type>PE|CE)", symbol, flags=re.IGNORECASE)
                                if not match:
                                    return jsonify({"message" : "No match Found !"})
                                month_number = month_map.get(match.group('month').lower())
                                if not month_number:
                                    return jsonify({"message" : "No month number !"})
                                fyers_symbol = match.group('index') + match.group('year') + month_number + match.group('expiry_date') + match.group('strike_price') + match.group('option_type')
                                fyers_symbol = "NSE:" + fyers_symbol
                                return fyers_symbol
                            elif exchange == "NSE":
                                print("NSE:" + symbol)
                                return symbol
                            else:
                                match = re.search(r"^(?P<index>\w+)(?P<expiry_date>\d{2})(?P<month>\w{3})(?P<year>\d{2})(?P<option_type>FUT)", symbol, flags=re.IGNORECASE)
                                fyers_symbol = match.group('index') + match.group('year') + match.group('month') + match.group('option_type')
                                fyers_symbol = "NSE:" + fyers_symbol
                                return fyers_symbol
            
                        def check_symbol_in_fyers(symbol, df_fyers):
                            return df_fyers[df_fyers['Expiry date'] == symbol]
            
                        def process_broker_symbol(symbol):
                            print("Entering process_broker_symbol")
                            df_fyers = fetch_fyers_data()
                            if df_fyers is None:
                                print("Fyers data not found in process_broker_symbol")
                                return jsonify({"message": "Error processing symbol."})
            
                            fyers_symbol = convert_symbol(symbol)
                            print("process_broker_symbol")
                            if fyers_symbol:
                                fyers_symbol_data = check_symbol_in_fyers(fyers_symbol, df_fyers)
                                print("true")
                                if not fyers_symbol_data.empty:
                                    return fyers_symbol
                                else:
                                    match = re.search(r"^(?P<index>\w+)(?P<expiry_date>\d{2})(?P<month>\w{3})(?P<year>\d{2})(?P<strike_price>\d+)(?P<option_type>PE|CE)", symbol, flags=re.IGNORECASE)
                                    if match:
                                        alternative_fyers_symbol = match.group('index') + match.group('year') + match.group('month') + match.group('strike_price') + match.group('option_type')
                                        alternative_fyers_symbol = "NSE:" + alternative_fyers_symbol
                                        alternative_fyers_symbol_data = check_symbol_in_fyers(alternative_fyers_symbol, df_fyers)
                                        if not alternative_fyers_symbol_data.empty:
                                            return alternative_fyers_symbol
                                        else:
                                            return jsonify({"message" : "Fyers symbol not available in both formats."})
                            else:
                                return jsonify({"message": "Unable to convert symbol."})
                        
                        def process_symbol(symbol, broker_user_id):
                            print("Entering process_symbol")
                            broker_name = BrokerCredentials.query.filter_by(broker_user_id=broker_user_id).first()
                            if broker_name.broker == "fyers":
                                print("process_symbol for fyers")
                                result = process_broker_symbol(symbol)
                                return result
                            else:
                                return jsonify({"message": "Broker not supported."})
                        
                        if exchange == "NFO":
                            converted_symbol = process_symbol(symbol, broker_user_id)
                        elif exchange == "NSE":
                            converted_symbol = "NSE:" + symbol
                        else:
                            converted_symbol = process_symbol(symbol, broker_user_id)
                            
                        order_type_map = {"MARKET": 2, "LIMIT": 1}
                        type = order_type_map.get(ordertype, 2)
                        print("type:",type)
                    
                        limitPrice = None
                    
                        if type == 1:
                            limitPrice = price if price else 0
                            print("limitPrice:",limitPrice)
                        master_id_str=str(master_id)
                        fyers_total_quantity = int(quantity) * int(multiplier)


                        master_id_str = f"{current_time_str}{master_id_str}"
    
                        if exchange == "NFO":
                            data={
                                    "symbol":converted_symbol,
                                        "qty":(fyers_total_quantity),
                                        "type":(type),
                                        "side":1 if transactiontype == 'BUY' else -1,
                                        "productType":"INTRADAY" if producttype=="INTRADAY" else "MARGIN",
                                        "limitPrice":float(limitPrice) if ordertype=="LIMIT" else 0,
                                        "stopPrice":0,
                                        "validity":duration,
                                        "disclosedQty":0,
                                        "offlineOrder":False,
                                        "orderTag":master_id_str
                                    }
                        elif exchange == "NSE":
                            data={
                                "symbol":converted_symbol,
                                    "qty":int(fyers_total_quantity),
                                    "type":type,
                                    "side":1 if transactiontype == 'BUY' else -1,
                                    "productType":'INTRADAY' if producttype=='INTRADAY'else "CNC",
                                    "limitPrice":float(limitPrice) if ordertype=="LIMIT" else 0,
                                    "stopPrice":0,
                                    "validity":duration,
                                    "disclosedQty":0,
                                    "offlineOrder":False,
                                    "orderTag":master_id_str
                                }
                            
                        fyers_order_response = generic_place_order(broker, broker_user_id, data=data,order_params=None)
                        print("fyers_order_response:", fyers_order_response)
    
                        order_book = config.OBJ_fyers[broker_user_id].orderbook()
                        positions = config.OBJ_fyers[broker_user_id].positions()
                        holdings = config.OBJ_fyers[broker_user_id].holdings()
                        config.fyers_orders_book[broker_user_id] = {"orderbook": order_book, "positions": positions, "holdings": holdings}
                        print(config.fyers_orders_book[broker_user_id])
                    
                        order_status = config.fyers_orders_book[broker_user_id]["orderbook"]['orderBook'][-1]['status']
                        order_results = config.fyers_orders_book[broker_user_id]["orderbook"]['orderBook'][-1]
                        order_type = config.fyers_orders_book[broker_user_id]["orderbook"]['orderBook'][-1]['type']
                        if order_status == 5:
                            rejection_reason = config.fyers_orders_book[broker_user_id]["orderbook"]['orderBook'][-1]['message']
                            rejection_reason_with_id = [broker_user_id, rejection_reason]
                            return rejection_reason_with_id, 400
                        
                        elif order_status == 2:
                                order_id = f"{data['symbol']}-{data['productType']}"
                                
                                if order_type == 1 or order_status == 2:
                                    if order_status == 2:
                                        avg_price = order_results['tradedPrice']
                                    else:  
                                        limit_price_value = order_results['limitPrice']

        
                                if transactiontype=="BUY":
                                    executed_master_child_positions = ExecutedPortfolio(user_id=user_id, trading_symbol=order_id,
                                                                                                product_type=order_results['productType'],broker_user_id=broker_user_id,
                                                                                                transaction_type=transactiontype, netqty= order_results['qty'],
                                                                                                order_id =order_results['id'],master_account_id= master_account_id,
                                                                                                buy_price=avg_price if order_status == 2 else limit_price_value,broker = broker)
                                else:
                                    executed_master_child_positions = ExecutedPortfolio(user_id=user_id, trading_symbol=order_results['symbol'],
                                                                                                product_type=order_results['productType'],broker_user_id=broker_user_id,
                                                                                                transaction_type=transactiontype, netqty= order_results['qty'],
                                                                                                order_id =order_results['id'],sell_price=avg_price if order_status == 2 else limit_price_value,
                                                                                                master_account_id=master_account_id,broker= broker)
    
                                # config.fyers_order_place_response.append(order_id)
                                db.session.add(executed_master_child_positions)  # Add executed portfolio to database
                                db.session.commit()
                                message={'message': f'Order placed successfully for {broker_user_id}'}
                                return message, 200  
                        else:
                            return {'message': "Unknown order status"}, 500
    
                        # except Exception as e:
                        #         print("Error:", str(e))  # Log any exceptions
                        #         return jsonify({'messages': str(e)}), 500
            
            if child_broker_user_id:
                # Find the specific child account
                selected_child_account = next(
                    (child for child in master_account.child_accounts if child.broker_user_id == child_broker_user_id), None)
                print("selected_child_account:", selected_child_account)

                if not selected_child_account:
                    return jsonify({"message": "Child account not found"}), 404

                # Process the order for the selected child account
                child_order_response = process_order(username, selected_child_account, symbol, quantity, master_account_id)
                if child_order_response:
                    return jsonify({"child_order_responses": child_order_response}), 200

                return jsonify({'message': f'Order placed successfully in {child_broker_user_id} child account'}), 200
            else:
                # If no child_broker_user_id and copy_placement is False, process order for the master account
                if not master_account.copy_placement:
                    broker_id = master_account.broker_user_id
                    master_order_response = process_order(username, master_account, symbol, quantity, master_account_id)
                    if master_order_response:
                        return jsonify({"master_order_responses": master_order_response}), 200

                    return jsonify({'message': f'Order placed successfully in {broker_id} master account'}), 200

            # Place orders in both master and child accounts
    
            master_order_response = process_order(username,master_account, symbol, quantity,master_account_id)
            print("Response :",master_order_response)
            if not master_order_response:
                return jsonify(master_order_response), 500
            child_order_responses = []
            for child_account in master_account.child_accounts:
                child_order_response = process_order(username,child_account, symbol, quantity,master_account_id)
                if not child_order_response:
                    return jsonify(child_order_response), 500
                child_order_responses.append(child_order_response)
            combined_response = {
            'child_order_responses': child_order_responses,'master_order_response': master_order_response}
    
            return jsonify(combined_response), 200
 
    def square_off_master_child(username, master_account_id,child_broker_user_id=None):
        try:
            # Fetch existing user
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                response_data = {'message': "User does not exist"}
                return jsonify(response_data), 404
            
            user_id = existing_user.id
            
            # Fetch all executed master-child positions for the given master_account_id
            executed_master_child_positions = ExecutedPortfolio.query.filter_by(user_id=user_id, master_account_id=master_account_id).all()

            # Filter positions if child_broker_user_id is provided
            if child_broker_user_id:
                executed_master_child_positions_filtered = [pos for pos in executed_master_child_positions if pos.broker_user_id == child_broker_user_id]
            else:
                executed_master_child_positions_filtered = executed_master_child_positions

            # Group positions by broker and broker_user_id
            position_groups = defaultdict(list)
            for position in executed_master_child_positions_filtered:
                if not position.square_off:
                    broker = position.broker
                    broker_user_id = position.broker_user_id
                    position_groups[(broker, broker_user_id)].append(position)

            response_data_list = []
            
            # Process positions for each group
            for (broker, broker_user_id), positions in position_groups.items():
                try: 
                    if broker == "flattrade":
                        flattrade = config.flattrade_api[broker_user_id]
                        for position in positions:
                            if position.exchange == 'NFO':
                                flattrade_square_off = flattrade.place_order(
                                    buy_or_sell="S" if position.transaction_type == "BUY" else "B",
                                    product_type='I' if position.product_type == 'INTRADAY' else 'M',
                                    exchange=position.exchange,
                                    tradingsymbol=position.trading_symbol,
                                    quantity=position.netqty,
                                    discloseqty=0,
                                    price_type = 'MKT',
                                    price=0,
                                    trigger_price=None,
                                    retention=position.duration,
                                    remarks = position.master_account_id
                                )
                            else:
                                flattrade_square_off = flattrade.place_order(
                                    buy_or_sell="S" if position.transaction_type == "BUY" else "B",
                                    product_type='I' if position.product_type == 'INTRADAY' else 'C',
                                    exchange=position.exchange,
                                    tradingsymbol=position.trading_symbol,
                                    quantity=position.netqty,
                                    discloseqty=0,
                                    price_type = 'MKT',
                                    price=0,
                                    trigger_price=None,
                                    retention=position.duration,
                                    remarks = position.master_account_id
                                )
                            print("flattrade_square_off:",flattrade_square_off)
                            order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                            holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                            positions_info = config.flattrade_api[broker_user_id].get_positions()

                            config.all_flattrade_details[broker_user_id] = {
                                'orderbook': order_book_send,
                                "holdings": holdings_info,
                                "positions": positions_info
                            }
                            # avg_price=config.all_flattrade_details[broker_user_id]["orderbook"][0]['avgprc']
                            if flattrade_square_off['stat'] == 'Ok':
                                position.square_off = True
                                avg_price=config.all_flattrade_details[broker_user_id]["orderbook"][0]['avgprc']
                                if position.transaction_type=="BUY":
                                   position.sell_price=avg_price
                                else:
                                   position.buy_price=avg_price
                                
                                db.session.commit()
                                response_data = {'message': f'Square off successfully for {broker_user_id}', 'Square_off': flattrade_square_off}
                                response_data_list.append(response_data)
                                
                            elif flattrade_square_off['stat'] != 'Ok':
                                response_data = {'message': f'Square off failed for {broker_user_id}', 'Square_off': flattrade_square_off}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message': f'No open positions found for {broker_user_id}'}
                                response_data_list.append(response_data)
                    
                    elif broker == "fyers":
                        fyers = config.OBJ_fyers[broker_user_id]
                        for position in positions:
                            data = {
                                "segment": [10],
                                'id': position.trading_symbol,
                                "side": [config.fyers_data['Side'][position.transaction_type]]
                            }
                            square_off = fyers.exit_positions(data)
                            
                            fyers_order=config.OBJ_fyers[broker_user_id].orderbook()
                            fyers_position=config.OBJ_fyers[broker_user_id].positions()
                            fyers_holdings=config.OBJ_fyers[broker_user_id].holdings()
                            config.fyers_orders_book[broker_user_id] = {"orderbook" : fyers_order,"positions" : fyers_position, "holdings" : fyers_holdings}
                            order_results = config.fyers_orders_book[broker_user_id]["orderbook"]['orderBook'][-1]['tradedPrice']
                            
                            if square_off['s'] == 'ok':
                                position.square_off = True
                                if position.transaction_type=="BUY":
                                    position.sell_price=order_results
                                else:
                                    position.buy_price=order_results
                                db.session.commit()
                                response_data = {'message': f'Square off successfully for {broker_user_id}', 'Square_off': square_off}
                                response_data_list.append(response_data)
                                
                            elif square_off['s'] != 'ok':
                                response_data = {'message': f'Square off failed for {broker_user_id}', 'Square_off': square_off}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message': f'No open positions found for {broker_user_id}'}
                                response_data_list.append(response_data)
                    
                    elif broker == "angelone":
                        angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                        for position in positions:
                            if position.exchange == 'NFO':
                                data = {
                                    "variety": position.variety,
                                    "orderTag": position.master_account_id,
                                    "tradingsymbol": position.trading_symbol,
                                    "symboltoken": position.symbol_token,
                                    "exchange": position.exchange,
                                    "quantity": int(position.netqty),
                                    "producttype": position.product_type,
                                    "transactiontype": "SELL" if position.transaction_type == "BUY" else "BUY",
                                    "price": 0,
                                    "duration": position.duration,
                                    "ordertype": "MARKET"
                                }
                            else:
                                data = {
                                    "variety": position.variety,
                                    "orderTag": position.master_account_id,
                                    "tradingsymbol": position.trading_symbol,
                                    "symboltoken": position.symbol_token,
                                    "exchange": position.exchange,
                                    "quantity": int(position.netqty),
                                    "producttype": 'DELIVERY' if position.producttype == 'NORMAL' else 'INTRADAY',
                                    "transactiontype": "SELL" if position.transaction_type == "BUY" else "BUY",
                                    "price": 0,
                                    "duration": position.duration,
                                    "ordertype": "MARKET"
                                }
                            
                            angelone_square_off = angelone.placeOrderFullResponse(data)
                            
                            order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                            positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                            holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                            all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                            config.all_angelone_details[broker_user_id] = {"orderbook" : order,"positions" : positions,"holdings" : holdings,"all_holdings" : all_holdings}
                                    
                            if angelone_square_off['message'] == 'SUCCESS':
                                response_data = {'message': f'Square off successfully for {broker_user_id}','Square_off':angelone_square_off}
                                response_data_list.append(response_data)
                                position.square_off = True
                                if position.transaction_type=="BUY":
                                    position.sell_price=order['data'][::-1][0]['averageprice']
                                else:
                                    position.buy_price=order['data'][::-1][0]['averageprice']
                                db.session.commit()
                                
                            elif angelone_square_off['message'] != 'SUCCESS':
                            
                                response_data = {'message': f'Square off failed for {broker_user_id}', 'Square_off': angelone_square_off}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message': f'No open positions found for {broker_user_id}'}
                                response_data_list.append(response_data)
                
                except KeyError:
                    response_data = {'message': "Broker user ID not found for position ID: {}".format(position.id)}
                    response_data_list.append(response_data)
                    continue
            
            # Return response data list containing responses for each position
            return jsonify(response_data_list), 200
        
        except Exception as e:
            response_data = {'message': "An error occurred: {}".format(str(e))}
            return jsonify(response_data), 500

    def fetching_master_child_positions(username,master_account_id_data):
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            response_data = {'message': "User does not exist"}
            return jsonify(response_data), 404
        all_master_child_positions = {}
        
        for masterchild_id in master_account_id_data:
            master_account_id = masterchild_id['master_account_id']
            broker_names = masterchild_id['broker_names']
            broker_user_ids = masterchild_id['broker_user_ids']
            list_accounts = []

            for broker_user_id, broker_name in zip(broker_user_ids, broker_names):
                executed_portfolio = ExecutedPortfolio.query.filter_by(
                    master_account_id=master_account_id, broker_user_id=broker_user_id
                ).all()
                
                if not executed_portfolio:
                    list_accounts.append({broker_user_id: []})
                    continue
                
                symbols_list = [portfolio.trading_symbol for portfolio in executed_portfolio]
                token_list = [portfolio.symbol_token for portfolio in executed_portfolio]

                if broker_name == "flattrade":
                    flattrade_positions = config.all_flattrade_details[broker_user_id]["positions"]
                    combined_positions = [position for position in flattrade_positions if position['tsym'] in symbols_list and position['token'] in token_list]
                    list_accounts.append({broker_user_id: combined_positions})

                elif broker_name == "fyers":
                    fyers_positions = config.fyers_orders_book[broker_user_id]['netPositions']['netPositions']
                    combined_positions = [position for position in fyers_positions if position['id'] in symbols_list]
                    list_accounts.append({broker_user_id: combined_positions})

                elif broker_name == "angelone":
                    angelone_positions = config.all_angelone_details[broker_user_id]['positions']['data']
                    combined_positions = [position for position in angelone_positions if position['tradingsymbol'] in symbols_list and position['symboltoken'] in token_list]
                    list_accounts.append({broker_user_id: combined_positions})
            
            all_master_child_positions[master_account_id] = list_accounts

        return jsonify(all_master_child_positions), 200

    def cancel_mc_orders(username, master_account_id, order_ids, child_broker_user_id=None):
        try:
            # Fetch existing user
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                response_data = {'message': "User does not exist"}
                return jsonify(response_data), 404
            
            user_id = existing_user.id
            
            # Fetch all executed master-child positions for the given master_account_id
            executed_master_child_positions = ExecutedPortfolio.query.filter_by(user_id=user_id, master_account_id=master_account_id).all()

            # Filter positions if child_broker_user_id is provided
            if child_broker_user_id:
                executed_master_child_positions_filtered = [pos for pos in executed_master_child_positions if pos.broker_user_id == child_broker_user_id]
            else:
                executed_master_child_positions_filtered = executed_master_child_positions

            # Further filter positions based on order_ids
            if order_ids:
                executed_master_child_positions_filtered = [pos for pos in executed_master_child_positions_filtered if pos.order_id in order_ids]

            # Group positions by broker and broker_user_id
            position_groups = defaultdict(list)
            for position in executed_master_child_positions_filtered:
                if not position.square_off and position.status.upper() == 'OPEN':
                    broker = position.broker
                    broker_user_id = position.broker_user_id
                    order_id = position.order_id
                    position_groups[(broker, broker_user_id)].append(position)

            response_data_list = []
            
            # Process positions for each group
            for (broker, broker_user_id), positions in position_groups.items():
                try:
                    if broker == "flattrade":
                        flattrade = config.flattrade_api[broker_user_id]
                        for position in positions:
                            flattrade_cancel_order = flattrade.cancel_order(orderno=position.order_id)
                            
                            order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                            positions_info = config.flattrade_api[broker_user_id].get_positions()
                            holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                            
                            config.all_flattrade_details[broker_user_id] = {
                                'orderbook': order_book_send,
                                "holdings": holdings_info,
                                "positions": positions_info
                            }

                            if flattrade_cancel_order['stat'] == 'Ok':
                                position.square_off = True
                                position.status = 'CANCELLED'
                                db.session.commit()
                                response_data = {'message': f'order cancelled successfully for {broker_user_id}', 'order_cancelled': flattrade_cancel_order}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message': f'order cancelling failed for {broker_user_id}'}
                                response_data_list.append(response_data)
                                
                    elif broker == "angelone":
                        try:
                            angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                        except KeyError:
                            response_data = {"error": "Broker user ID not found"}
                            return jsonify(response_data), 500
                        
                        for position in positions:
                            orderid = position.order_id    
                            variety = position.variety    
                            angelone_cancel_order = angelone.cancelOrder(orderid, variety)

                            #angelone_cancel_order = angelone.cancelOrder(data)
                            print(angelone_cancel_order)
                            
                            order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                            positions_info = config.SMART_API_OBJ_angelone[broker_user_id].position()
                            holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                            all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                            config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions_info, "holdings": holdings, "all_holdings": all_holdings}

                            if angelone_cancel_order['message'] == 'SUCCESS':
                                position.square_off = True
                                position.status = 'CANCELLED'
                                db.session.commit()
                                response_data = {'message': f'order cancelled successfully for {broker_user_id}', 'order_cancelled': angelone_cancel_order}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message': f'order cancelling failed for {broker_user_id}'}
                                response_data_list.append(response_data)

                    elif broker == "fyers":
                        try:
                            fyers = config.OBJ_fyers[broker_user_id]
                            print(fyers)
                        except KeyError:
                            response_data = {"error": "Broker user ID not found"}
                            return jsonify(response_data), 500
                        
                        for position in positions:
                            data = {
                                'id': position.order_id
                            }
                            square_off = fyers.cancel_order(data=data)
                            print(square_off)
                            
                            fyers_order = config.OBJ_fyers[broker_user_id].orderbook()
                            fyers_position = config.OBJ_fyers[broker_user_id].positions()
                            fyers_holdings = config.OBJ_fyers[broker_user_id].holdings()
                            config.fyers_orders_book[broker_user_id] = {"orderbook": fyers_order, "positions": fyers_position, "holdings": fyers_holdings}

                            if square_off['s'] == 'ok':
                                position.square_off = True
                                position.status = 'CANCELLED'
                                db.session.commit()
                                response_data = {'message': f'order cancelled successfully for {broker_user_id}', 'order_cancelled': square_off}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message':f'order cancelling failed {broker_user_id}'}
                                response_data_list.append(response_data)
                                    
                except KeyError:
                    response_data = {'message': "Broker user ID not found"}
                    response_data_list.append(response_data)
                    continue
            
            # Return response data list containing responses for each position
            return jsonify(response_data_list), 200
        
        except Exception as e:
            response_data = {'message': "An error occurred: {}".format(str(e))}
            return jsonify(response_data), 500
        
    def modify_mc_orders(username, master_account_id, order_ids, child_broker_user_id=None):
        try:
            # Fetch existing user
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                response_data = {'message': "User does not exist"}
                return jsonify(response_data), 404
            
            data = request.json
            new_price = data.get('new_price')
            new_quantity = data.get('new_quantity')
            
            user_id = existing_user.id
            
            # Fetch all executed master-child positions for the given master_account_id
            executed_master_child_positions = ExecutedPortfolio.query.filter_by(user_id=user_id, master_account_id=master_account_id).all()

            # Filter positions if child_broker_user_id is provided
            if child_broker_user_id:
                executed_master_child_positions_filtered = [pos for pos in executed_master_child_positions if pos.broker_user_id == child_broker_user_id]
            else:
                executed_master_child_positions_filtered = executed_master_child_positions

            # Further filter positions based on order_ids
            if order_ids:
                executed_master_child_positions_filtered = [pos for pos in executed_master_child_positions_filtered if pos.order_id in order_ids]

            # Group positions by broker and broker_user_id
            position_groups = defaultdict(list)
            for position in executed_master_child_positions_filtered:
                if not position.square_off and position.status.upper() == 'OPEN':
                    broker = position.broker
                    broker_user_id = position.broker_user_id
                    order_id = position.order_id
                    exchange = position.exchange
                    trading_symbol = position.trading_symbol
                    order_type = position.order_type
                    netqty = position.netqty
                    price = position.price
                    position_groups[(broker, broker_user_id)].append(position)

            response_data_list = []
            
            # Process positions for each group
            for (broker, broker_user_id), positions in position_groups.items():
                try:
                    if broker == "flattrade":
                        flattrade = config.flattrade_api[broker_user_id]
                        for position in positions:
                            flattrade_modify_order = flattrade.modify_order(exchange=exchange, tradingsymbol=trading_symbol, orderno=order_id,
                                   newquantity=new_quantity if new_quantity else netqty, newprice_type=order_type, newprice=new_price if new_price else price)
                            
                            order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                            positions_info = config.flattrade_api[broker_user_id].get_positions()
                            holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                            
                            config.all_flattrade_details[broker_user_id] = {
                                'orderbook': order_book_send,
                                "holdings": holdings_info,
                                "positions": positions_info
                            }
                            orderid=config.all_flattrade_details[broker_user_id]["orderbook"][0]['norenordno']
                            if flattrade_modify_order['stat'] == 'Ok':
                                position.order_id = orderid
                                if new_price:
                                    position.buy_price = new_price
                                if new_quantity:
                                    position.netqty = new_quantity
                                db.session.commit()
                                response_data = {'message': f'order Modified successfully for {broker_user_id}', 'order_modified': flattrade_modify_order}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message': f'order Modifying failed for {broker_user_id}'}
                                response_data_list.append(response_data)

                    elif broker == "angelone":
                        try:
                            angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                        except KeyError:
                            response_data = {"error": "Broker user ID not found"}
                            return jsonify(response_data), 500
                        
                        for position in positions:
                            orderid = position.order_id    
                            variety = position.variety    
                            ordertype = position.order_type
                            producttype = position.product_type
                            duration = position.duration
                            tradingsymbol= position.trading_symbol
                            symbol_token = position.symbol_token
                            exchange = position.exchange
                            netqty = position.netqty
                            price  = position.price
                            
                            data = {
                                "variety": variety,
                                "orderid": orderid,
                                "ordertype": ordertype,
                                "producttype": producttype,
                                "duration": duration,
                                "price": new_price if new_price else price,
                                "quantity": new_quantity if new_quantity else netqty,
                                "tradingsymbol": tradingsymbol,
                                "symboltoken": symbol_token,
                                "exchange": exchange
                            }
                            angelone_modify_order = angelone.modifyOrder(data)
                            print(angelone_modify_order)
                            
                            order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                            positions_info = config.SMART_API_OBJ_angelone[broker_user_id].position()
                            holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                            all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                            config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions_info, "holdings": holdings, "all_holdings": all_holdings}
                            orderid = config.all_angelone_details[broker_user_id]['orderbook']['data'][::-1][0]['orderid']
                            if angelone_modify_order['message'] == 'SUCCESS':
                                
                                position.order_id = orderid
                                if new_price:
                                    position.buy_price = new_price
                                if new_quantity:
                                    position.netqty = new_quantity
                                db.session.commit()
                                response_data = {'message': f'order Modified successfully for {broker_user_id}', 'order_modified': angelone_modify_order}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message': f'order Modifying failed for {broker_user_id}'}
                                response_data_list.append(response_data)

                    elif broker == "fyers":
                        try:
                            fyers = config.OBJ_fyers[broker_user_id]
                            print(fyers)
                        except KeyError:
                            response_data = {"error": "Broker user ID not found"}
                            return jsonify(response_data), 500

                        for position in positions:
                            orderId = position.order_id
                            data = {
                                "id": orderId,
                                "type": 1 if position.order_type=='LIMIT' else None,
                                "limitPrice": new_price if new_price else price,
                                "qty":new_quantity if new_quantity else netqty
                            }
                            fyers_modify_order = fyers.modify_order(data=data)
                            print(fyers_modify_order)
                            
                            fyers_order = config.OBJ_fyers[broker_user_id].orderbook()
                            fyers_position = config.OBJ_fyers[broker_user_id].positions()
                            fyers_holdings = config.OBJ_fyers[broker_user_id].holdings()
                            config.fyers_orders_book[broker_user_id] = {"orderbook": fyers_order, "positions": fyers_position, "holdings": fyers_holdings}
                            order_results = config.fyers_orders_book[broker_user_id]["orderbook"]['orderBook'][-1]
                            if fyers_modify_order['s'] == 'ok':
                                position.order_id = order_results['id']
                                if new_price:
                                    position.buy_price = new_price
                                if new_quantity:
                                    position.netqty = new_quantity
                                db.session.commit()
                                response_data = {'message': f'order Modified successfully for {broker_user_id}', 'order_modified': fyers_modify_order}
                                response_data_list.append(response_data)
                            else:
                                response_data = {'message':f'order Modifying failed for {broker_user_id}'}
                                response_data_list.append(response_data)      
                                    
                except KeyError:
                    response_data = {'message': "Broker user ID not found"}
                    response_data_list.append(response_data)
                    continue
            
            # Return response data list containing responses for each position
            return jsonify(response_data_list), 200
        
        except Exception as e:
            response_data = {'message': "An error occurred: {}".format(str(e))}
            return jsonify(response_data), 500

def fetch_token(symbol, exchange):
    try:
        # Fetch the JSON data from the URL
        instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        with urllib.request.urlopen(instrument_url) as response:
            instrument_list = json.loads(response.read())

        # Find the token for the given trading symbol and exchange
        for item in instrument_list:
            if item["symbol"] == symbol and item["exch_seg"] == exchange:
                return item["token"]
        
        # If the trading symbol is not found, return None
        return None

    except Exception as e:
        # Handle any errors that might occur during the process
        print("Error fetching token:", e)
        return None


create_master_child_accounts_blueprint = Blueprint('create_master_child_accounts_blueprint', __name__)
@create_master_child_accounts_blueprint.route('/create_master_child_accounts/<string:username>', methods=['POST'])
def create_master_child_accounts(username):
    create_master_child_accounts_response,status_code = MasterChild.create_master_child_accounts(username=username)
    return create_master_child_accounts_response,status_code

fetch_master_child_accounts_blueprint = Blueprint('fetch_master_child_accounts_blueprint', __name__)
@fetch_master_child_accounts_blueprint.route('/fetch_master_child_accounts/<string:username>', methods=['GET'])
def fetch_master_child_accounts(username):
    fetch_master_child_accounts_response,status_code = MasterChild.fetch_master_child_accounts(username=username)
    return fetch_master_child_accounts_response,status_code

delete_master_child_accounts_blueprint = Blueprint('delete_master_child_accounts_blueprint', __name__)

@delete_master_child_accounts_blueprint.route('/delete_master_child_accounts/<string:username>/<string:broker_user_id>', methods=['DELETE'])
def delete_master_child_accounts(username,broker_user_id):
    delete_master_child_accounts_response,status_code = MasterChild.delete_master_child_accounts(username=username,broker_user_id=broker_user_id)
    return delete_master_child_accounts_response,status_code

angelone_symbols_blueprint = Blueprint('angelone_symbols_blueprint', __name__)
@angelone_symbols_blueprint.route('/angelone_symbols/<string:username>/<string:broker_user_id>', methods=['POST'])
def angelone_symbols(username,broker_user_id):
    angelone_symbols_response = MasterChild.angelone_symbols(username=username,broker_user_id=broker_user_id)
    return angelone_symbols_response

delete_child_account_blueprint = Blueprint('delete_child_account_blueprint', __name__)
@delete_child_account_blueprint.route('/delete_child_account/<string:username>/<string:broker_user_id>', methods=['DELETE'])
def delete_child_account(username,broker_user_id):
    delete_child_account_response,status_code = MasterChild.delete_child_account(username=username,broker_user_id=broker_user_id)
    return delete_child_account_response,status_code


place_master_child_order_blueprint = Blueprint('place_master_child_order_blueprint', __name__)
@place_master_child_order_blueprint.route('/place_master_child_order/<string:username>/<int:master_account_id>', methods=['POST'])
def place_master_child_order(username, master_account_id):
    # Get the child_broker_user_id from query parameters
    child_broker_user_id = request.args.get('child_broker_user_id')
    place_master_child_order_response, status_code = MasterChild.place_master_child_order(
        username=username,
        master_account_id=master_account_id,
        child_broker_user_id=child_broker_user_id
    )
    return place_master_child_order_response, status_code

square_off_master_child_blueprint = Blueprint('square_off_master_child_blueprint', __name__)

@square_off_master_child_blueprint.route('/square_off_master_child/<string:username>/<int:master_account_id>', methods=['POST'])
def square_off_master_child(username, master_account_id):
    child_broker_user_id = request.args.get('child_broker_user_id')
    square_off_master_child_response, status_code = MasterChild.square_off_master_child(username=username,
                                                                                        master_account_id=master_account_id,
                                                                                        child_broker_user_id=child_broker_user_id)
    return square_off_master_child_response, status_code

fetching_master_child_positions_blueprint = Blueprint('fetching_master_child_positions_blueprint', __name__)

@fetching_master_child_positions_blueprint.route('/fetching_master_child_positions/<string:username>', methods=['POST'])
def fetching_master_child_positions_route(username):
    master_account_id_data = request.json.get('master_account_id_data', [])
    fetching_master_child_positions_response, status_code = MasterChild.fetching_master_child_positions(username,master_account_id_data)
    return fetching_master_child_positions_response, status_code

cancel_mc_orders_blueprint = Blueprint('cancel_mc_orders_child_blueprint', __name__)

@cancel_mc_orders_blueprint.route('/cancel_mc_orders/<string:username>/<int:master_account_id>', methods=['POST'])
def cancel_mc_orders(username, master_account_id):
    child_broker_user_id = request.args.get('child_broker_user_id')
    order_ids = request.json.get('order_ids', [])
    cancel_mc_orders_response, status_code = MasterChild.cancel_mc_orders(username=username,
                                                                         master_account_id=master_account_id,
                                                                         order_ids=order_ids,
                                                                         child_broker_user_id=child_broker_user_id)
    return cancel_mc_orders_response, status_code

modify_mc_orders_blueprint = Blueprint('modify_mc_orders_blueprint', __name__)

@modify_mc_orders_blueprint.route('/modify_mc_orders/<string:username>/<int:master_account_id>', methods=['POST'])
def modify_mc_orders(username, master_account_id):
    child_broker_user_id = request.args.get('child_broker_user_id')
    order_ids = request.json.get('order_ids', [])
    modify_mc_orders_response, status_code = MasterChild.modify_mc_orders(username=username,
                                                                         master_account_id=master_account_id,
                                                                         order_ids=order_ids,
                                                                         child_broker_user_id=child_broker_user_id)
    return modify_mc_orders_response, status_code