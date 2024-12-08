# app/routes/broker_integration.py
from flask import Blueprint, jsonify, request, abort, Flask
from app.models.main import db
from app.models.user import Portfolio , BrokerCredentials, Strategies, Portfolio_legs, ExecutedPortfolio,StrategyMultipliers,Performance, ExecutedEquityOrders
from werkzeug.security import generate_password_hash
from cryptography.fernet import Fernet, InvalidToken
from flask import Blueprint, jsonify, abort, request
from flask_restful import Api, Resource
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode, urlsafe_b64decode
import os
import json
from urllib.parse import urlparse, parse_qs
from flask import jsonify, abort
from pyotp import TOTP
import requests
import hashlib
import SmartApi
from NorenRestApiPy.NorenApi import NorenApi
from SmartApi.smartConnect import SmartConnect
import json
from werkzeug.security import check_password_hash,generate_password_hash
import requests
import time
import pyotp
import os
from urllib.parse import parse_qs, urlparse
import asyncio
import importlib.util
from app.api import brokers
from app.models.user import Portfolio
from app.models.user import User
import subprocess
import random
from flask_restful import Resource
import traceback
from app.api.brokers import config
from flask_mail import Mail, Message
from .error_handlers import ERROR_HANDLER
from .routes import USERSETTING_ROUTES
from app.api.brokers.pseudoAPI import PseudoAPI

BROKER_ANGELONE = 'angelone'
BROKER_FLATTRADE = 'flattrade'
BROKER_FYERS = 'fyers'
BROKER_FINVASIA = 'finvasia'

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'saich5252@gmail.com'
app.config['MAIL_PASSWORD'] = 'vfdesgvzxpbpnsko'
mail = Mail(app)

def generate_6otp():
    digits = "0123456789"
    otp = "".join(random.choice(digits) for _ in range(4))
    return otp

def validate_request_data(data):
    required_fields = ['mainUser', 'userId', 'password', 'apiKey', 'qrCode', 'broker']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise ValueError(f'Missing required fields: {", ".join(missing_fields)}')
    
key_file_path = 'fernet_key.json'

if os.path.exists(key_file_path):
    # Read the key from the file
    with open(key_file_path, 'r') as key_file:
        key_data = json.load(key_file)
        fernet_key = key_data['fernet_key']
else:
    # Generate a new key if the file doesn't exist
    fernet_key = Fernet.generate_key()
    # Store the key in the JSON file
    with open(key_file_path, 'w') as key_file:
        key_data = {'fernet_key': fernet_key.decode()}
        json.dump(key_data, key_file)

cipher_suite = Fernet(fernet_key)


def encrypt_data(data):
    encrypted_data = cipher_suite.encrypt(data.encode())
    app.logger.info(f"Encrypted data: {encrypted_data}")
    return urlsafe_b64encode(encrypted_data)

def decrypt_data(encrypted_data):
    try:
        decrypted_data = cipher_suite.decrypt(urlsafe_b64decode(encrypted_data))
        if decrypted_data is None:
            raise InvalidToken("Decryption failed. Decrypted data is None.")
        app.logger.info(f"Decrypted data: {decrypted_data}")
        return decrypted_data
    except InvalidToken as e:
        app.logger.error(f"Invalid Fernet token: {e}")
        # Log the encrypted data for further analysis
        app.logger.error(f"Encrypted data: {encrypted_data}")
        # Log the key for troubleshooting
        app.logger.error(f"Decryption key: {fernet_key}")
        # Handle the exception here, e.g., log it and return a specific response
        raise


# Class for all the broker integration related operations
class Broker_Integration:
    
    async def Account_validation(data):
        try:
            
            validate_request_data(data)
    
            broker = data['broker']
            username = data['mainUser']  # Assuming 'mainUser' contains the username

            if broker == "pseudo_account":
                existing_user = User.query.filter_by(username=username).first()
                
                exisiting_account = BrokerCredentials.query.filter_by(user_id=existing_user.id, broker="pseudo_account",broker_user_id=data['userId']).first()

                print("exisiting_account:",exisiting_account)
            
                if exisiting_account:
                    available_balance = exisiting_account.available_balance
                   
                else:
                    available_balance = "1000000.00"
                    pseudo_credentials = BrokerCredentials(user_id=existing_user.id,username=existing_user.username,broker="pseudo_account",display_name=data['display_name'],broker_user_id=data['userId'],max_profit="0",max_loss="0",profit_locking=",,,,",available_balance=available_balance, enabled=True)
                    
                    db.session.add(pseudo_credentials)
                    db.session.commit()

                response_data = {'message': f'Validation Successful: {username}', 'data': {"data":{"name":"pseudo","availableMargin":available_balance,"broker":"pseudo_account"}}}
                return jsonify(response_data), 200
    
            # Check if a record with the same broker_user_id already exists
            existing_record = BrokerCredentials.query.filter_by(broker_user_id=data['userId']).first()
        
            module_path = f"./app/api/brokers/{broker}.py"

            if existing_record:
                if broker == 'angelone':
                    existing_record.enabled = True
                    db.session.commit()
                    spec = importlib.util.spec_from_file_location(broker, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    response = await module.execute(data)
                    
    
                elif broker == 'fyers':
                    existing_record.enabled = True
                    db.session.commit()
                    spec = importlib.util.spec_from_file_location(broker, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    response = await module.execute(data)
    
                elif broker == 'finvasia':
                    existing_record.enabled = True
                    db.session.commit()
                    spec = importlib.util.spec_from_file_location(broker, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    response = await module.execute(data)
        
                elif broker == 'flattrade':
                    existing_record.enabled = True
                    db.session.commit()
                    spec = importlib.util.spec_from_file_location(broker, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Assuming `config` is obtained or initialized before this block
                    response = await module.execute(data, config)
                else:
                    abort(400, description='Invalid broker mentioned')
    
                if response:
                    # Update any necessary information in the existing record
                    existing_record.broker = broker
                    existing_record.display_name = data['display_name']
                    existing_record.max_profit = data['max_profit']
                    existing_record.max_loss = data['max_loss']
    
                    db.session.commit()
    
                return response
            
    
            # Continue with the validation process for a new record
            if broker == 'angelone':
                spec = importlib.util.spec_from_file_location(broker, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                response = await module.execute(data)
                
            elif broker == 'flattrade':
                # existing_record.enabled = True
                db.session.commit()
                spec = importlib.util.spec_from_file_location(broker, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Assuming `config` is obtained or initialized before this block
                response = await module.execute(data, config)

            elif broker == 'fyers':
                spec = importlib.util.spec_from_file_location(broker, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                response = await module.execute(data)
               
            elif broker == 'finvasia':
                spec = importlib.util.spec_from_file_location(broker, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                response = await module.execute(data)
            else:
                abort(400, description='Invalid broker mentioned')
                
            try:
                response_code = response.status
            except:
                response_code = response[1]

            print(response_code)
            if response_code == 200 or response_code == '200 OK':
                # If it doesn't exist, save data to BrokerCredentials model
                
                user = User.query.filter_by(username=username).first()
                if not user:
                    return jsonify({"error": "User not found."}), 404

                print("user:", user, "\n\n\n\n\n\n\n\n")

                current_broker_count = len([
                    bc for bc in user.broker_credentials if bc.broker != 'pseudo_account'
                ])
                
                # Check subscription limits
                if user.num_of_users ==0:
                    return jsonify({"message": "Subscription Expired.Renew your Subscription Plan"}), 403
                
                elif user.is_on_trial and current_broker_count >= user.num_of_users:
                    return jsonify({"message": "Your trial subscription plan does not allow adding more broker accounts."}), 403
                elif not user.is_on_trial and current_broker_count >= user.num_of_users:
                    return jsonify({"message": "You have reached the limit for adding Deemat accounts on your current plan."}), 403
    
                if user:
                    # Encrypt sensitive information using Fernet
                    encrypted_password = encrypt_data(data['password'])
                    encrypted_api_key = encrypt_data(data.get('apiKey')) if data.get('apiKey') is not None else None
                    encrypted_qr_code = encrypt_data(data['qrCode'])
                    encrypted_secret_key = encrypt_data(data['secretKey']) if data.get('secretKey') is not None else None
                    encrypted_imei = encrypt_data(data['imei'])  if data.get('imei') is not None else None
                    print(response)
    
                    broker_credentials = BrokerCredentials(
                        user=user,
                        broker=broker,
                        broker_user_id=data['userId'],
                        display_name = data['display_name'],
                        max_profit = data['max_profit'],
                        max_loss = data['max_loss'],
                        client_id = data['client_id'] if 'client_id' in data else None,
                        vendor_code = data['vendor_code'] if 'vendor_code' in data else None,
                        # redirect_url = data['REDIRECT_URI'] if 'REDIRECT_URI' in data else None,
                        username=username,  # Use the provided username
                        password=encrypted_password.decode(),
                        api_key=encrypted_api_key.decode() if encrypted_api_key else None,
                        qr_code=encrypted_qr_code.decode(),
                        secret_key=encrypted_secret_key.decode() if encrypted_secret_key else None,
                        imei=encrypted_imei.decode() if encrypted_imei else None,
                        enabled = True
                    )
    
                    db.session.add(broker_credentials)
                    db.session.commit()
            # time.sleep(3)
            return response
    
        except ValueError as ve:
            response_data = {'message': 'Invalid request data', 'error': str(ve)}
            return jsonify(response_data), 400

    def get_startegy_account(username):
        try:
            # Query the database to find the user with the provided username
            user = User.query.filter_by(username=username).first()
            if not user:
                response_data = ERROR_HANDLER.database_errors("user", 'User not found')
                return jsonify({'error': response_data['message']}), 404

            # Find all enabled broker credentials for the user in the database
            enabled_credentials = BrokerCredentials.query.filter_by(user_id=user.id, enabled=True).all()
            if not enabled_credentials:
                response_data = ERROR_HANDLER.database_errors("broker_credentials", 'No enabled broker credentials found for the user')
                return jsonify({'message': response_data['message'], 'Login enabled': False}), 404

            # Prepare response data
            response_data = {
                'message': 'Login successful',
                'data': []
            }

            for credential in enabled_credentials:
                # Find all strategy multipliers associated with the credential's broker user ID
                multipliers = StrategyMultipliers.query.filter_by(broker_user_id=credential.broker_user_id).all()

                # Prepare strategy tags and associated multipliers
                strategy_tags = {}
                for multiplier in multipliers:
                    strategy_tags[multiplier.strategy.strategy_tag] = multiplier.multiplier

                response_data['data'].append({
                    'broker': credential.broker,
                    'broker_id': credential.broker_user_id,
                    'display_name': credential.display_name,
                    'Login enabled': credential.enabled,
                    "available balance": credential.available_balance,
                    'multiplier': strategy_tags
                })

            return jsonify(response_data), 200

        except Exception as e:
            response_data = ERROR_HANDLER.flask_api_errors("get_strategy_account", str(e))
            return jsonify(response_data), 500

    def delete_broker_account(username, broker_user_id, broker):
        try:
            # Check if a record with the specified broker_user_id exists in BrokerCredentials
            existing_record = BrokerCredentials.query.filter_by(broker_user_id=broker_user_id, username=username).first()

            if not existing_record:
                response_data = ERROR_HANDLER.database_errors("broker_credentials", 'Broker credentials not found')
                return jsonify(response_data), 404

            # Find related strategies
            related_strategies = Strategies.query.filter(
                Strategies.broker_user_id.contains(broker_user_id),
                Strategies.broker.contains(broker)
            ).all()

            for strategy in related_strategies:
                broker_user_ids = strategy.broker_user_id.split(',')
                brokers = strategy.broker.split(',')

                if ',' not in strategy.broker_user_id and ',' not in strategy.broker:
                    # Strategy has a single broker_user_id and broker
                    db.session.delete(strategy)
                else:
                    # Strategy has multiple broker_user_ids and brokers
                    broker_user_ids = [bid.strip() for bid in broker_user_ids if bid.strip() != broker_user_id.strip()]
                    brokers = [br.strip() for br in brokers if br.strip() != broker.strip()]

                    strategy.broker_user_id = ','.join(broker_user_ids)
                    strategy.broker = ','.join(brokers)

                # Delete related strategy multipliers
                StrategyMultipliers.query.filter_by(strategy_id=strategy.id, broker_user_id=broker_user_id).delete()

            # Finally, delete the broker credentials
            db.session.delete(existing_record)
            db.session.commit()

            response_data = {'message': 'Account Deleted Successfully'}
            return jsonify(response_data), 200

        except SQLAlchemyError as e:
            logging.error(f"Database error occurred: {e}")
            response = ERROR_HANDLER.flask_api_errors("delete_broker_account", str(e))
            response_data = {'message': 'Internal Server Error', 'error': response['message']}
            return jsonify(response_data), 500

        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            response = ERROR_HANDLER.flask_api_errors("delete_broker_account", str(e))
            response_data = {'message': 'Internal Server Error', 'error': response['message']}
            return jsonify(response_data), 500

    def update_password(data,username,broker_user_id):
        try:
            new_password = data.get('newPassword')

            # Check if a record with the specified broker_user_id and username exists
            existing_record = BrokerCredentials.query.filter_by(broker_user_id=broker_user_id, username=username).first()

            if existing_record:
                # Encrypt the new password using the same encryption method
                encrypted_password = encrypt_data(new_password)

                # Update the password in the existing record
                existing_record.password = encrypted_password.decode()

                db.session.commit()

                response_data = {'message': 'Password updated successfully'}
                return jsonify(response_data), 200
            else:
                response_data = ERROR_HANDLER.database_errors("broker_credentials", 'Broker credentials not found')
                return jsonify(response_data), 404

        except ValueError as ve:
            response = ERROR_HANDLER.flask_api_errors(str(ve))
            response_data = {'message': 'Invalid request data', 'error': response['message']}
            return jsonify(response_data), 400

        except Exception as e:
            response = ERROR_HANDLER.flask_api_errors(str(e))
            response_data = {'message': 'Internal Server Error', 'error': response['message']}
            return jsonify(response_data), 500

    def logout(username,broker_user_id):
        logout_account = BrokerCredentials.query.filter_by(username=username,broker_user_id=broker_user_id).first()

        if logout_account:
            logout_account.enabled = False
            db.session.commit()

            response_data = {'message': 'Logout successfully'}
            return jsonify(response_data), 200
        else:
            response_data = ERROR_HANDLER.database_errors("broker_credentials", 'Invalid Details')
            return jsonify(response_data), 500

    def forgot_password(username):
            application_user = User.query.filter_by(username=username).first()
    
            if application_user:
                otp = generate_6otp()
                application_user.otp = otp
                db.session.commit()
                msg = Message('Account Verification', sender='saich5252@gmail.com', recipients=[application_user.email])
                msg.body = f'Hi { application_user.name },\n\n OTP for resetting your password { otp }.'
                mail.send(msg)
                response_data = {'message': f'OTP generated successfully please check your email {application_user.email}'}
                return jsonify(response_data), 200
            else:
                response_data = {'message': "User with email does not exist !"}
                response_data = ERROR_HANDLER.database_errors("user", "User with email does not exist !")
                return jsonify(response_data), 500

    def verify_otp(username):
            data = request.json
    
            entered_otp = data['otp']
    
            application_user = User.query.filter_by(username=username).first()
    
            if application_user.otp == entered_otp:
                response_data = {'message': 'Please change your Password !!'}
                return jsonify(response_data), 200
            else:
                response_data = ERROR_HANDLER.database_errors("user", 'Ivalid Otp please verify again !!')
                return jsonify(response_data), 500
        
    def change_passowrd(username):
            data = request.json
    
            password = data['password']
            confirm_password = data['confirm_password']
    
            application_user = User.query.filter_by(username=username).first()
    
            if check_password_hash(application_user.password,password):
                response_data = ERROR_HANDLER.database_errors("user", 'You have entered the same old password !!')
                return jsonify(response_data), 200
            else:
                if password == confirm_password:
                    print("Not Same")
                    application_user.password = generate_password_hash(password, method='pbkdf2:sha256')
                    db.session.commit()
                    response_data = {'message': 'Password Changed Successfully !!'}
                    return jsonify(response_data), 200
                else:
                    response_data = ERROR_HANDLER.database_errors("user", 'Passwords Does not match !!')
                    return jsonify(response_data), 200

    def update_user_data(username, broker_user_id):
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Get the user profile by username and broker_user_id
        user_profile = BrokerCredentials.query.filter_by(username=username, broker_user_id=broker_user_id).first()
        
        if not user_profile:
            return jsonify({'message': 'User profile not found'}), 404

        try:
            # Extract max_profit, max_loss, and other fields from the request
            user_max_profit = request.json.get('max_profit')
            user_max_loss = request.json.get('max_loss')
            user_multiplier = request.json.get('user_multiplier')
            max_loss_per_trade = request.json.get('max_loss_per_trade')
            max_open_trades = request.json.get('max_open_trades')
            exit_time = request.json.get('exit_time')

            # Convert exit_time to a datetime.time object if it's provided
            from datetime import datetime
            if exit_time:
                exit_time = datetime.strptime(exit_time, '%H:%M:%S').time()

            # Update the user profile fields
            user_profile.max_profit = user_max_profit
            user_profile.max_loss = user_max_loss
            user_profile.user_multiplier = user_multiplier
            user_profile.max_loss_per_trade = max_loss_per_trade
            user_profile.max_open_trades = max_open_trades
            user_profile.exit_time = exit_time
            
            # Commit changes to the database
            db.session.commit()
            
            response_data = {'message': f'User data updated successfully for {broker_user_id}'}
            return jsonify(response_data), 200
        
        except ValueError as ve:
            # Handle incorrect data formats, such as time conversion errors
            return jsonify({'message': 'Invalid data format provided', 'error': str(ve)}), 400
        
        except Exception as e:
            # Catch any other exceptions and roll back the session
            db.session.rollback()
            return jsonify({'message': 'An error occurred while updating user data', 'error': str(e)}), 500

    def update_user_profit_locking(username, broker_user_id):
        data = request.get_json()
        user = User.query.filter_by(username=username).first()
        if not user:
            response_data = ERROR_HANDLER.database_errors("user", 'User not found')
            return jsonify(response_data), 404
        
        if 'profit_locking' not in data:
            response_data = ERROR_HANDLER.flask_api_errors("update_user_profit_locking", 'Profit locking data not provided')
            return jsonify(response_data), 400

        try:
            profit_locking_data = [x for x in data['profit_locking'].split(',')]
            if len(profit_locking_data) != 4:
                raise ValueError("Invalid profit locking data format")
        except ValueError:
            response_data = ERROR_HANDLER.flask_api_errors("update_user_profit_locking", 'Invalid profit locking data format')
            return jsonify(response_data), 400

        credential = BrokerCredentials.query.filter_by(username=username, broker_user_id=broker_user_id).first()
        if not credential:
            response_data = ERROR_HANDLER.database_errors("broker_credentials", 'Credential not found')
            return jsonify(response_data), 404

        # Update profit_locking
        credential.profit_locking = ','.join(map(str, profit_locking_data))
        db.session.commit()

        # Check if profit_locking is equal to ",,,"
        if credential.profit_locking == ",,,":
            # Set reached_profit and locked_min_profit to 0
            credential.reached_profit = 0
            credential.locked_min_profit = 0
            db.session.commit()

        return jsonify({'message': f'Profit locking updated successfully for {broker_user_id}'}), 200

    def update_user_profit_trail_values(username,broker_user_id):
        data = request.json  # Assuming JSON data is sent with the request
        
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
            return jsonify(response_data), 404

        broker_id = BrokerCredentials.query.filter_by(username=username, broker_user_id=broker_user_id).first()
        print("broker_id:",broker_id)
        if not broker_id:
            response_data = ERROR_HANDLER.database_errors("broker_credentails", 'Broker ID not found')
            return jsonify(response_data), 404

        # Query current reached_profit and locked_min_profit values
        reached_profit = data.get('reached_profit', broker_id.reached_profit)
        locked_min_profit = data.get('locked_min_profit', broker_id.locked_min_profit)

        # Update the reached_profit and locked_min_profit values
        broker_id.reached_profit = reached_profit
        broker_id.locked_min_profit = locked_min_profit

        db.session.commit()

        return jsonify({'message': 'profit trail values updated successfully'}), 200
    
    def update_pseudo_balance(username, broker_user_id):
        user = User.query.filter_by(username=username).first()
        if not user:
            response_data = ERROR_HANDLER.flask_api_errors("user", 'User not found')
            return jsonify(response_data), 404
        
        user_profile = BrokerCredentials.query.filter_by(username=username,broker_user_id=broker_user_id).first()

        available_balance = request.json.get('available_balance')


        # Update the strategy's max_profit and max_loss
        user_profile.available_balance = available_balance

        # Commit changes to the database
        db.session.commit()
        response_data = {'message': f'Available Balance updated successfully for {broker_user_id}'}
        return jsonify(response_data), 200

    def update_displayname(username, broker_user_id):
        user = User.query.filter_by(username=username).first()
        if not user:
            response_data = ERROR_HANDLER.flask_api_errors("user", 'User not found')
            return jsonify(response_data), 404
        
        user_profile = BrokerCredentials.query.filter_by(username=username,broker_user_id=broker_user_id).first()

        display_name = request.json.get('display_name')


        # Update the strategy's max_profit and max_loss
        user_profile.display_name = display_name

        # Commit changes to the database
        db.session.commit()
        response_data = {'message': f'Display name updated successfully for {broker_user_id}'}
        return jsonify(response_data), 200
    
    def square_off_maxloss_per_trade(username, trading_symbol, broker_type, broker_user_id):
            try:
                # Fetch existing user
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
                    return jsonify(response_data), 404
            
                user_id = existing_user.id
    
                # Fetch the specific executed portfolio leg
                executed_portfolio_details = ExecutedPortfolio.query.filter_by(user_id=user_id, trading_symbol=trading_symbol).first()
                print("executed_portfolio_details:", executed_portfolio_details)
                if not executed_portfolio_details:
                    response_data = ERROR_HANDLER.database_errors("executed_portfolio", "No open positions found for the specified portfolio leg.")
                    return jsonify(response_data), 200
            
                try:
                    if broker_type == "flattrade":
                        try:
                            flattrade = config.flattrade_api[broker_user_id]
                        except KeyError:
                            response_data = ERROR_HANDLER.broker_api_errors("flattrade", "Broker user ID not found")
                            return jsonify(response_data), 500
    
                        if not executed_portfolio_details.square_off:
                            for executedPortfolio in executed_portfolio_details:
                                flattrade_square_off = flattrade.place_order(
                                    buy_or_sell="S" if executedPortfolio.transaction_type == "BUY" else "B",
                                    product_type="I" if executedPortfolio.product_type == "MIS" else "M",
                                    exchange=executedPortfolio.exchange,
                                    tradingsymbol=executedPortfolio.trading_symbol,
                                    quantity=executedPortfolio.netqty,
                                    discloseqty=0,
                                    price_type='MKT',
                                    price=0,
                                    trigger_price=None,
                                    retention='DAY',
                                    remarks=executedPortfolio.strategy_tag
                                )
                            
                                order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                                positions_info = config.flattrade_api[broker_user_id].get_positions()
                                holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                                print("\n\n\n\n")
                                print("order_book_send:", order_book_send)
                                config.all_flattrade_details[broker_user_id] = {
                                    'order': order_book_send,
                                    "holdings": holdings_info,
                                    "positions": positions_info
                                }
        
                                if flattrade_square_off['stat'] == 'Ok':
                                    executedPortfolio.square_off = True
                                    last_avgprc = order_book_send[0]['avgprc']
                                    print("sell_price:",last_avgprc)
                                    executedPortfolio.sell_price = last_avgprc
                                    db.session.commit()
                                    response_data = {'message': 'Max loss per trade square off successfully', 'Square_off': flattrade_square_off}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = {'message': 'Square off failed. No open positions found.'}
                                    return jsonify(response_data), 200
    
                    elif broker_type == "fyers":
                        try:
                            fyers = config.OBJ_fyers[broker_user_id]
                            print(fyers)
                        except KeyError:
                            response_data = ERROR_HANDLER.broker_api_errors("fyers", "Broker user ID not found")
                            return jsonify(response_data), 500
                    
                        if not executed_portfolio_details.square_off:
                            for executedPortfolio in executed_portfolio_details:
                                data = {
                                    "orderTag": executedPortfolio.strategy_tag,
                                    "segment": [10],
                                    'id': executedPortfolio.order_id,
                                    "side": [config.fyers_data['Side'][executedPortfolio.transaction_type]]
                                }
                                square_off = fyers.exit_positions(data)
                                print(square_off)
                            
                                fyers_order = config.OBJ_fyers[broker_user_id].orderbook()
                                fyers_position = config.OBJ_fyers[broker_user_id].positions()
                                fyers_holdings = config.OBJ_fyers[broker_user_id].holdings()
                                config.fyers_orders_book[broker_user_id] = {"orderbook": fyers_order, "positions": fyers_position, "holdings": fyers_holdings}
        
                                if square_off['s'] == 'ok':
                                    executedPortfolio.square_off = True
                                    if executedPortfolio.transaction_type=="BUY":
                                        executedPortfolio.sell_price=square_off['tradedPrice']
                                    else:
                                        executedPortfolio.buy_price=square_off['tradedPrice']
                                    db.session.commit()
                                    response_data = {'message': 'Max loss per trade square off successfully', 'Square_off': square_off}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = ERROR_HANDLER.flask_api_errors("square_off_maxloss_per_trade", 'Square off failed. No open positions found.')
                                    return jsonify(response_data), 200
    
                    elif broker_type == "angelone":
                            try:
                                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                            except KeyError:
                                response_data = ERROR_HANDLER.broker_api_errors("angelone", "Broker user ID not found")
                                return jsonify(response_data), 500
                            if not executed_portfolio_details.square_off:
                                for executedPortfolio in executed_portfolio_details:
                                    data = {
                                        "variety": executedPortfolio.variety,
                                        "orderTag": executedPortfolio.strategy_tag,
                                        "tradingsymbol": executedPortfolio.trading_symbol,
                                        "symboltoken": executedPortfolio.symbol_token,
                                        "exchange": executedPortfolio.exchange,
                                        "quantity": int(executedPortfolio.netqty),
                                        "producttype": "INTRADAY" if executedPortfolio.product_type == "MIS" else "CARRYFORWARD",
                                        "transactiontype": "SELL" if executedPortfolio.transaction_type == "BUY" else "BUY",
                                        "price": executedPortfolio.price,
                                        "duration": executedPortfolio.duration,
                                        "ordertype": "MARKET"
                                    }
                                    angelone_square_off = angelone.placeOrderFullResponse(data)
                                    print(angelone_square_off)
                                    order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                                    positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                                    holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                                    all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                                    config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions, "holdings": holdings, "all_holdings": all_holdings}
                                    if angelone_square_off['message'] == 'SUCCESS':
                                        executedPortfolio.square_off = True
                                        if executedPortfolio.transaction_type=="BUY":
                                            executedPortfolio.sell_price=order['data'][::-1][0]['averageprice']
                                        else:
                                            executedPortfolio.buy_price=order['data'][::-1][0]['averageprice']
                                        db.session.commit()
                                        response_data = {'message': 'Portfolio leg manual square off successfully', 'Square_off': angelone_square_off}
                                        return jsonify(response_data), 200
                                    else:
                                        response_data = ERROR_HANDLER.database_errors("executed_portfolio", 'Square off failed. No open positions found.')
                                        return jsonify(response_data), 200
                
                    elif broker_type == "pseudo_account":
                        data = {"broker_user_id" : broker_user_id, "username" : username, "broker_type" : broker_type, "trading_symbol" : trading_symbol, "exchange" : "NFO"}

                        pseudo_api = PseudoAPI(data=data)

                        square_off_response = pseudo_api.square_off()

                        # response_data = {'message': square_off_response, "trading_symbol":trading_symbol}

                        response_message = f"{square_off_response} for {trading_symbol}"
    
                        response_data = {
                            'message': response_message
                        }
                        return jsonify(response_data), 200
                
                except KeyError:
                    response_data = ERROR_HANDLER.flask_api_errors("square_off_maxloss_per_trade", "Broker user ID not found.")
                    return jsonify(response_data), 500
                
            except KeyError:
                response_data = ERROR_HANDLER.flask_api_errors("square_off_maxloss_per_trade", "Broker user ID not found.")
                return jsonify(response_data), 500
            
    def square_off_equity_maxloss_per_trade(username, trading_symbol, broker_type, broker_user_id):
            try:
                # Fetch existing user
                existing_user = User.query.filter_by(username=username).first()
                if not existing_user:
                    response_data = {'message': "User does not exist"}
                    return jsonify(response_data), 404
            
                user_id = existing_user.id
    
                # Fetch the specific executed portfolio leg
                executed_portfolio_details = ExecutedEquityOrders.query.filter_by(user_id=user_id, trading_symbol=trading_symbol).first()
                print("executed_portfolio_details:", executed_portfolio_details)
                if not executed_portfolio_details:
                    response_data = {'message': "No open positions found for the specified stock symbol."}
                    return jsonify(response_data), 200
            
                try:
                    if broker_type == "flattrade":
                        try:
                            flattrade = config.flattrade_api[broker_user_id]
                        except KeyError:
                            response_data = ERROR_HANDLER.broker_api_errors("flattrade", "Broker user ID not found")
                            return jsonify(response_data), 500
    
                        if not executed_portfolio_details.square_off:
                            for executedPortfolio in executed_portfolio_details:
                                flattrade_square_off = flattrade.place_order(
                                    buy_or_sell="S" if executedPortfolio.transaction_type == "BUY" else "B",
                                    product_type="I" if executedPortfolio.product_type == "MIS" else "C",
                                    exchange="NSE",
                                    tradingsymbol=executedPortfolio.trading_symbol,
                                    quantity=executedPortfolio.quantity,
                                    discloseqty=0,
                                    price_type='MKT',
                                    price=0,
                                    trigger_price=None,
                                    retention='DAY',
                                    remarks=executedPortfolio.strategy_tag
                                )
                            
                                order_book_send = config.flattrade_api[broker_user_id].get_order_book()
                                positions_info = config.flattrade_api[broker_user_id].get_positions()
                                holdings_info  = config.flattrade_api[broker_user_id].get_holdings()
                                print("\n\n\n\n")
                                print("order_book_send:", order_book_send)
                                config.all_flattrade_details[broker_user_id] = {
                                    'order': order_book_send,
                                    "holdings": holdings_info,
                                    "positions": positions_info
                                }
        
                                if flattrade_square_off['stat'] == 'Ok':
                                    executedPortfolio.square_off = True
                                    last_avgprc = order_book_send[0]['avgprc']
                                    print("sell_price:",last_avgprc)
                                    executedPortfolio.sell_price = last_avgprc
                                    db.session.commit()
                                    response_data = {'message': 'Max loss per trade square off successfully', 'Square_off': flattrade_square_off}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = {'message': 'Square off failed. No open positions found.'}
                                    return jsonify(response_data), 200
    
                    elif broker_type == "fyers":
                        try:
                            fyers = config.OBJ_fyers[broker_user_id]
                            print(fyers)
                        except KeyError:
                            response_data = ERROR_HANDLER.broker_api_errors("fyers", "Broker user ID not found")
                            return jsonify(response_data), 500
                    
                        if not executed_portfolio_details.square_off:
                            for executedPortfolio in executed_portfolio_details:
                                symbol = executedPortfolio.trading_symbol
                                product_type = "CNC" if executedPortfolio.product_type == 'NRML' else "INTRADAY"
                                symbol_id=symbol +'-'+ product_type
                                data = {
                                    "id":symbol_id
                                }
                                square_off = fyers.exit_positions(data=data)
                                print(square_off)
                            
                                fyers_order = config.OBJ_fyers[broker_user_id].orderbook()
                                fyers_position = config.OBJ_fyers[broker_user_id].positions()
                                fyers_holdings = config.OBJ_fyers[broker_user_id].holdings()
                                config.fyers_orders_book[broker_user_id] = {"orderbook": fyers_order, "positions": fyers_position, "holdings": fyers_holdings}
        
                                if square_off['s'] == 'ok':
                                    executedPortfolio.square_off = True
                                    if executedPortfolio.transaction_type=="BUY":
                                       executedPortfolio.sell_price=square_off['tradedPrice']
                                    else:
                                       executedPortfolio.buy_price=square_off['tradedPrice']
                                    db.session.commit()
                                    response_data = {'message': 'Maxloss per trade manual square off successfully', 'Square_off': square_off}
                                    return jsonify(response_data), 200
                                else:
                                    response_data = ERROR_HANDLER.flask_api_errors("square_off_equity_maxloss_per_trade", 'Square off failed. No open positions found.')
                                    return jsonify(response_data), 200
    
                    elif broker_type == "angelone":
                            try:
                                angelone = config.SMART_API_OBJ_angelone[broker_user_id]
                            except KeyError:
                                response_data = {"message": "Broker user ID not found"} ###
                                return jsonify(response_data), 500
                            if not executed_portfolio_details.square_off:
                                for executedPortfolio in executed_portfolio_details:
                                    data = {
                                        "variety": "NORMAL",
                                        "orderTag": executedPortfolio.strategy_tag,
                                        "tradingsymbol": executedPortfolio.trading_symbol,
                                        "symboltoken": executedPortfolio.symbol_token,
                                        "exchange": "NSE",
                                        "quantity": int(executedPortfolio.netqty),
                                        "producttype": "INTRADAY" if executedPortfolio.product_type == "MIS" else "DELIVERY",
                                        "transactiontype": "SELL" if executedPortfolio.transaction_type == "BUY" else "BUY",
                                        "price": 0,
                                        "duration": "DAY",
                                        "ordertype": "MARKET"
                                    }
                                    angelone_square_off = angelone.placeOrderFullResponse(data)
                                    print(angelone_square_off)
                                    order = config.SMART_API_OBJ_angelone[broker_user_id].orderBook()
                                    positions = config.SMART_API_OBJ_angelone[broker_user_id].position()
                                    holdings = config.SMART_API_OBJ_angelone[broker_user_id].holding()
                                    all_holdings = config.SMART_API_OBJ_angelone[broker_user_id].allholding()
                                    config.all_angelone_details[broker_user_id] = {"orderbook": order, "positions": positions, "holdings": holdings, "all_holdings": all_holdings}
                                    if angelone_square_off['message'] == 'SUCCESS':
                                        executedPortfolio.square_off = True
                                        if executedPortfolio.transaction_type=="BUY":
                                            executedPortfolio.sell_price=order['data'][::-1][0]['averageprice']
                                        else:
                                            executedPortfolio.buy_price=order['data'][::-1][0]['averageprice']
                                        db.session.commit()
                                        response_data = {'message': 'Maxloss per trade square off successfully', 'Square_off': angelone_square_off}
                                        return jsonify(response_data), 200
                                    else:
                                        response_data = ERROR_HANDLER.database_errors("executed_portfolio", 'Square off failed. No open positions found.')
                                        return jsonify(response_data), 200
                
                    elif broker_type == "pseudo_account":
                        # Ensure broker_user_id is available in data
                        data = request.json
                        broker_user_id = data['broker_user_id']
                        print("broker_user_id:", broker_user_id, "\n\\n\n\n\n")
                        trading_symbol = data['trading_symbol']
                        broker_type = data['broker_type']
                        existing_equity_orders = ExecutedEquityOrders.query.filter_by(
                            user_id=user_id,
                            broker_user_id=broker_user_id,
                            trading_symbol=trading_symbol,
                            square_off=False
                        ).all()
                    
                        print(existing_equity_orders, "\n\n\n\n\n\n")  # Debugging line
                        
                        sell_order_id = random.randint(10**14, 10**15 - 1)
                        from datetime import datetime
                        
                        for equity_order in existing_equity_orders:
                            token = equity_order.symbol_token
                            sell_price = config.angelone_live_ltp[token]
                            equity_order.sell_price = sell_price
                            equity_order.squared_off_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            equity_order.square_off = True
                            equity_order.sell_qty = equity_order.buy_qty
                            equity_order.sell_order_id = sell_order_id
                            db.session.commit()

                        return jsonify({'message': "Equity Square Off Successful (Max loss per trade level) !!"}), 200


                
                except KeyError:
                    response_data = ERROR_HANDLER.flask_api_errors("square_off_equity_maxloss_per_trade", "Broker user ID not found.")
                    return jsonify(response_data), 500
            except KeyError:
                response_data = ERROR_HANDLER.flask_api_errors("square_off_equity_maxloss_per_trade", "Broker user ID not found.")
                return jsonify(response_data), 500

# Flask Function for DataValidation for All accounts
validation_blueprint = Blueprint('validation', __name__)
@validation_blueprint.route(USERSETTING_ROUTES.get_routes("validation_blueprint"), methods=['POST'])
async def handle_account_validation():
    data = request.json
    response = Broker_Integration.Account_validation(data=data)
    return await response

# Flask Api Function for getting the account details
api = Api(validation_blueprint)
class UserDataResource(Resource):
    def get(self, username):
        try:
            user = User.query.filter_by(username=username).first()

            if not user:
                abort(404, description=f'User with username {username} not found')

            broker_credentials = BrokerCredentials.query.filter_by(user=user).all()
            print("\n\n\n\n\n\n\n\n\n\n\n\n\n")
            print(f"Fetched broker credentials: {[cred.available_balance for cred in broker_credentials]}")

            response_data = {
                'username': user.username,
                'broker_credentials': []
            }

            for credential in broker_credentials:
                try:
                    decrypted_api_key = decrypt_data(credential.api_key) if credential.api_key else ""
                    decrypted_imei = decrypt_data(credential.imei) if credential.imei else ""
                    decrypted_secret_key = decrypt_data(credential.secret_key) if credential.secret_key else ""
                    decrypted_qr_code = decrypt_data(credential.qr_code) if credential.qr_code else ""
                    decrypted_password = decrypt_data(credential.password) if credential.password else ""

                except Exception as decryption_error:
                    # Log the decryption error
                    app.logger.error(f"Decryption error for user {username}: {decryption_error}")
                    traceback.print_exc()

                    # Continue to the next credential
                    continue

                broker_data = {
                    'broker': credential.broker,
                    'broker_user_id': credential.broker_user_id,
                    'display_name': credential.display_name,
                    'client_id': credential.client_id,
                    "max_profit": credential.max_profit,
                    "max_loss": credential.max_loss,
                    "profit_locking": credential.profit_locking,
                    "reached_profit": credential.reached_profit,
                    "locked_min_profit": credential.locked_min_profit,
                    "user_multiplier": credential.user_multiplier,
                    "max_loss_per_trade":credential.max_loss_per_trade,
                    "max_open_trades":credential.max_open_trades,
                    'exit_time': credential.exit_time.strftime('%H:%M:%S') if credential.exit_time else "00:00:00",
                    "utilized_margin":credential.utilized_margin,
                    #'redirect_url': credential.redirect_url,
                    'vendor_code': credential.vendor_code,
                    'api_key': decrypted_api_key.decode() if decrypted_api_key else "",
                    'qr_code': decrypted_qr_code.decode() if decrypted_qr_code else "",
                    'secret_key': decrypted_secret_key.decode() if decrypted_secret_key else "",
                    'password': decrypted_password.decode() if decrypted_password else "",
                    'imei': decrypted_imei.decode() if decrypted_imei else "",
                    'available_balance': credential.available_balance 
                }


                response_data['broker_credentials'].append(broker_data)
                print(response_data)
            return jsonify(response_data)

        except Exception as e:
            # Log the error
            app.logger.error(f"An error occurred: {e}\n{traceback.format_exc()}")

            # Return an error response
            return {'message': 'Internal Server Error'}, 500
api.add_resource(UserDataResource, '/get_user_data/<username>')



# Flask Function for Deleting all the broker accounts
delete_broker_account_blueprint = Blueprint('delete_broker_account', __name__)
@delete_broker_account_blueprint.route(USERSETTING_ROUTES.get_routes("delete_broker_account_blueprint"), methods=['DELETE'])
def delete_credentials(username,broker_user_id, broker):
    delete_broker_account_response, status_code = Broker_Integration.delete_broker_account(username=username,
                                                                                           broker_user_id=broker_user_id, broker=broker)
    return delete_broker_account_response, status_code


# Flask Function for Updating password for all the broker accounts
update_password_blueprint = Blueprint('update_password_blueprint', __name__)
@update_password_blueprint.route(USERSETTING_ROUTES.get_routes("update_password_blueprint"), methods=['PATCH'])
def update_password(username, broker_user_id):
    data = request.json
    update_password_response, status_code = Broker_Integration.update_password(username=username,broker_user_id=broker_user_id,data=data)
    return update_password_response, status_code


# Flask function for Logging out the functions
logout_blueprint = Blueprint('logout', __name__)
@logout_blueprint.route(USERSETTING_ROUTES.get_routes("logout_blueprint"), methods=['POST'])
def logout(username,broker_user_id):
    logout_response, status_code = Broker_Integration.logout(username=username,broker_user_id=broker_user_id)
    return logout_response, status_code


forgot_password_blueprint = Blueprint('forgot_password', __name__)
@forgot_password_blueprint.route(USERSETTING_ROUTES.get_routes("forgot_password_blueprint"), methods=['POST'])
def forgot_password(username):
    forgot_password_response, status_code = Broker_Integration.forgot_password(username=username)
    return forgot_password_response, status_code

verify_otp_blueprint = Blueprint('verify_otp', __name__)
@verify_otp_blueprint.route(USERSETTING_ROUTES.get_routes("verify_otp_blueprint"), methods=['POST'])
def verify_otp(username):
    verify_otp_response, status_code = Broker_Integration.verify_otp(username=username)
    return verify_otp_response, status_code
 
change_user_password_blueprint = Blueprint('change_user_password', __name__)
@change_user_password_blueprint.route(USERSETTING_ROUTES.get_routes("change_user_password_blueprint"), methods=['POST'])
def change_password(username):
    change_password_response, status_code = Broker_Integration.change_passowrd(username=username)
    return change_password_response, status_code

get_startegy_account_blueprint = Blueprint('get_startegy_account', __name__)    
@get_startegy_account_blueprint.route(USERSETTING_ROUTES.get_routes("get_startegy_account_blueprint"), methods=['POST'])
def get_startegy_account(username):
    get_strategy_account_response, status_code = Broker_Integration.get_startegy_account(username=username)
    return get_strategy_account_response, status_code

update_user_data_blueprint = Blueprint('update_user_data_loss_blueprint', __name__)
@update_user_data_blueprint.route(USERSETTING_ROUTES.get_routes("update_user_data_blueprint"), methods=['POST'])
def update_user_data(username,broker_user_id):
    update_user_data_response, status_code = Broker_Integration.update_user_data(username=username,broker_user_id=broker_user_id)
    return update_user_data_response, status_code 

update_user_profit_locking_blueprint = Blueprint('update_user_profit_locking_blueprint', __name__)
@update_user_profit_locking_blueprint.route(USERSETTING_ROUTES.get_routes("update_user_profit_locking_blueprint"), methods=['POST'])
def update_user_profit_locking(username,broker_user_id):
    update_user_profit_locking_response, status_code = Broker_Integration.update_user_profit_locking(username=username,broker_user_id=broker_user_id)
    return update_user_profit_locking_response, status_code 

update_user_profit_trail_values_blueprint = Blueprint('update_user_profit_trail_values', __name__)
@update_user_profit_trail_values_blueprint.route(USERSETTING_ROUTES.get_routes("update_user_profit_trail_values_blueprint"), methods=['POST'])
def update_user_profit_trail_values(username,broker_user_id):
    update_user_profit_trail_valuesresponse, status_code = Broker_Integration.update_user_profit_trail_values(username,broker_user_id)
    return update_user_profit_trail_valuesresponse, status_code

update_pseudo_balance_blueprint = Blueprint('update_pseudo_balance_blueprint', __name__)
@update_pseudo_balance_blueprint.route(USERSETTING_ROUTES.get_routes("update_pseudo_balance_blueprint"), methods=['POST'])
def update_pseudo_balance(username,broker_user_id):
    update_pseudo_balance_response, status_code = Broker_Integration.update_pseudo_balance(username=username,broker_user_id=broker_user_id)
    return update_pseudo_balance_response, status_code 

update_displayname_blueprint = Blueprint('update_displayname_blueprint', __name__)
@update_displayname_blueprint.route(USERSETTING_ROUTES.get_routes("update_displayname_blueprint"), methods=['POST'])
def update_displayname(username,broker_user_id):
    update_displayname_response, status_code = Broker_Integration.update_displayname(username=username,broker_user_id=broker_user_id)
    return update_displayname_response, status_code   

square_off_maxloss_per_trade_blueprint = Blueprint('square_off_maxloss_per_trade_blueprint', __name__)
@square_off_maxloss_per_trade_blueprint.route(USERSETTING_ROUTES.get_routes("square_off_maxloss_per_trade_blueprint"), methods=['POST'])
def square_off_portfolio_leg_level(username, trading_symbol,broker_type, broker_user_id):
    square_off_maxloss_per_trade_response, status_code = Broker_Integration.square_off_maxloss_per_trade(username, trading_symbol, broker_type, broker_user_id)
    return square_off_maxloss_per_trade_response, status_code

square_off_equity_maxloss_per_trade_level_blueprint = Blueprint('square_off_equity_maxloss_per_trade_level_blueprint', __name__)
@square_off_equity_maxloss_per_trade_level_blueprint.route(USERSETTING_ROUTES.get_routes('square_off_equity_maxloss_per_trade_level_blueprint'), methods=['POST'])
def square_off_equity_maxloss_per_trade(username, trading_symbol,broker_type, broker_user_id):
    square_off_equity_maxloss_per_trade_response, status_code = Broker_Integration.square_off_equity_maxloss_per_trade(username, trading_symbol, broker_type, broker_user_id)
    return square_off_equity_maxloss_per_trade_response, status_code