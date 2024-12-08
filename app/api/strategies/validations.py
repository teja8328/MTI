from flask import Blueprint, jsonify, request, abort, Flask
from app.models.main import db
from app.models.user import BrokerCredentials, User, Strategies , Portfolio, StrategyMultipliers
from .error_handlers import ERROR_HANDLER
from .routes import STRATEGIE_ROUTES
app = Flask(__name__)

# Multileg class for all Multi leg related operations 
class Strategies_class:

    def Store_broker_and_strategy_info(username):
        try:
            data = request.get_json()

            # Check if the user exists
            user = User.query.filter_by(username=username).first()
            if not user:
                response_data = ERROR_HANDLER.database_errors( "user", "User Does not exist")
                return jsonify(response_data), 500

            # Always create a new Strategies record
            strategy = Strategies(user_id=user.id)

            strategy_tag = data.get('strategy_tag')

            if len(data.get('broker_user_id')) == 0:
                response_data = ERROR_HANDLER.flask_api_errors("Store_broker_and_strategy_info",  f'Please map the Strategy Tag : { strategy_tag }, to atleast one trading account')
                return jsonify(response_data), 500

            # Initialize a dictionary to store multipliers for different broker_user_id
            broker_multipliers = {}

            # Iterate through broker_user_id and store corresponding multipliers
            for idx, broker_user_id in enumerate(data.get('broker_user_id')):
                multiplier = data.get('multiplier', [])[idx]
                broker_multipliers[broker_user_id] = multiplier

            strategy.strategy_tag = data.get('strategy_tag')
            strategy.alias = data.get('alias')
            strategy.max_profit = data.get('max_profit')
            strategy.max_loss = data.get('max_loss')
            strategy.broker_user_id = ','.join(map(str, data.get('broker_user_id', [])))
            strategy.broker = ','.join(map(str, data.get('broker', [])))

            # Check if strategy_tag is unique
            existing_strategy = Strategies.query.filter_by(strategy_tag=strategy.strategy_tag).first()
            existing_portfolio = Portfolio.query.filter_by(strategy=strategy.strategy_tag).all()

            if existing_strategy:
                if existing_portfolio:
                    for portfolio in existing_portfolio:
                        portfolio.strategy_accounts_id = ','.join(map(str, data.get('broker_user_id', [])))
                        portfolio.strategy_accounts = ','.join(map(str, data.get('broker', [])))
                else:
                    pass

                # Changing the strategy
                existing_strategy.alias = data.get('alias')
                existing_strategy.broker_user_id = ','.join(map(str, data.get('broker_user_id', [])))
                existing_strategy.broker = ','.join(map(str, data.get('broker', [])))

                db.session.add(existing_strategy)
                db.session.commit()

                # Update multipliers for existing strategy
                for broker_user_id, multiplier in broker_multipliers.items():
                    existing_strategy_multiplier = StrategyMultipliers.query.filter_by(strategy_id=existing_strategy.id, broker_user_id=broker_user_id).first()
                    if existing_strategy_multiplier:
                        existing_strategy_multiplier.multiplier = multiplier
                    else:
                        new_strategy_multiplier = StrategyMultipliers(strategy_id=existing_strategy.id, broker_user_id=broker_user_id, multiplier=multiplier)
                        db.session.add(new_strategy_multiplier)

                db.session.commit()
                return jsonify({'message': 'Strategy updated successfully'}), 200

            # Continue with the database interaction
            db.session.add(strategy)
            db.session.commit()

            # Store multipliers for new strategy
            for broker_user_id, multiplier in broker_multipliers.items():
                new_strategy_multiplier = StrategyMultipliers(strategy_id=strategy.id, broker_user_id=broker_user_id, multiplier=multiplier)
                db.session.add(new_strategy_multiplier)

            db.session.commit()

            return jsonify({'message': 'Strategy saved successfully'}), 200

        except Exception as e:
            response_data = ERROR_HANDLER.flask_api_errors("Store_broker_and_strategy_info", str(e))
            return jsonify(response_data), 500

    def update_max_profit_loss(username, strategy_tag):
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Get the strategy by strategy_tag
        strategy = Strategies.query.filter_by(strategy_tag=strategy_tag).first()
        
        if not strategy:
            return jsonify({'message': 'Strategy not found'}), 404

        try:
            # Extract max_profit, max_loss, and other times from the request
            max_profit = request.json.get('max_profit')
            max_loss = request.json.get('max_loss')
            open_time = request.json.get('open_time')
            close_time = request.json.get('close_time')
            square_off_time = request.json.get('square_off_time')
            from datetime import datetime
            # Convert times to datetime.time objects if provided
            if open_time:
                open_time = datetime.strptime(open_time, '%H:%M:%S').time()
            if close_time:
                close_time = datetime.strptime(close_time, '%H:%M:%S').time()
            if square_off_time:
                square_off_time = datetime.strptime(square_off_time, '%H:%M:%S').time()

            # Update the strategy's max_profit, max_loss, and times
            strategy.max_profit = max_profit
            strategy.max_loss = max_loss
            strategy.open_time = open_time
            strategy.close_time = close_time
            strategy.square_off_time = square_off_time

            # Commit changes to the database
            db.session.commit()
            
            response_data = {'message': f'Strategy data updated successfully for {strategy_tag} strategy'}
            return jsonify(response_data), 200
        
        except ValueError as ve:
            # Handle invalid time format errors
            return jsonify({'message': 'Invalid time format provided', 'error': str(ve)}), 400
        
        except Exception as e:
            # Handle any other exceptions and rollback the session
            db.session.rollback()
            return jsonify({'message': 'An error occurred while updating strategy data', 'error': str(e)}), 500

    def retrieve_strategy_info(username):
        try:
            # Check if the user exists
            user = User.query.filter_by(username=username).first()
            if not user:
                response_data = ERROR_HANDLER.database_errors("user", 'User not found')
                return jsonify(response_data), 404

            # Retrieve strategy information for the user
            strategies = Strategies.query.filter_by(user_id=user.id).all()

            # Prepare the response
            strategy_info = []
            for strategy in strategies:
                strategy_data = {
                    'strategy_tag': strategy.strategy_tag,
                    'alias': strategy.alias,
                    'max_profit': strategy.max_profit,
                    'max_loss': strategy.max_loss,
                    "profit_locking":strategy.profit_locking,
                    "reached_profit":strategy.reached_profit,
                    "locked_min_profit":strategy.locked_min_profit,
                    'open_time': strategy.open_time.strftime('%H:%M:%S') if strategy.open_time else "00:00:00",
                    'close_time': strategy.close_time.strftime('%H:%M:%S') if strategy.close_time else "00:00:00",
                    'square_off_time': strategy.square_off_time.strftime('%H:%M:%S') if strategy.square_off_time else "00:00:00",
                    'broker_user_id': strategy.broker_user_id.split(','),  # Convert back to a list
                    'broker': strategy.broker.split(','),  # Convert back to a list
                    'allowed_trades': strategy.allowed_trades,
                    'entry_order_retry':strategy.entry_order_retry, 
                    'entry_retry_count': strategy.entry_retry_count,
                    'exit_order_retry':strategy.exit_order_retry,
                    'entry_retry_wait':strategy.entry_retry_wait,
                    'exit_retry_count': strategy.exit_retry_count,
                    'exit_retry_wait':strategy.exit_retry_wait,
                    'exit_max_wait': strategy.exit_max_wait
                }
                # Retrieve multipliers for each broker_user_id
                multipliers = {}
                for broker_user_id in strategy_data['broker_user_id']:
                    multiplier_record = StrategyMultipliers.query.filter_by(strategy_id=strategy.id, broker_user_id=broker_user_id).first()
                    if multiplier_record:
                        multipliers[broker_user_id] = multiplier_record.multiplier
                    else:
                        multipliers[broker_user_id] = None
                
                strategy_data['multiplier'] = multipliers
                
                strategy_info.append(strategy_data)

            return jsonify({'strategies': strategy_info}), 200

        except Exception as e:
            response_data = ERROR_HANDLER.flask_api_errors("retrieve_strategy_info", str(e))
            return jsonify({'error': response_data['message']}), 500

    def delete_strategy_tag(username, strategy_tag):
        try:
            # Check if the user exists
            user = User.query.filter_by(username=username).first()
            if not user:
                return jsonify({'error': 'User not found'}), 404

            # Retrieve strategy information for the user
            strategy = Strategies.query.filter_by(user_id=user.id, strategy_tag=strategy_tag).first()
            if not strategy:
                response_data = ERROR_HANDLER.database_errors("strategies", 'Strategy not found')
                return jsonify(response_data['message']), 404

            # Retrieve and delete associated multipliers
            multipliers = StrategyMultipliers.query.filter_by(strategy_id=strategy.id).all()
            for multiplier in multipliers:
                db.session.delete(multiplier)

            # Delete the strategy
            db.session.delete(strategy)
            db.session.commit()

            return jsonify({'message': "Strategy Tag and Associated Multipliers Deleted Successfully"}), 200

        except Exception as e:
            response_data = ERROR_HANDLER.flask_api_errors("delete_strategy_tag", str(e))
            return jsonify({'error': response_data['message']}), 500

    def update_strategy_profit_locking(username,strategy_tag):
        data = request.get_json()
        user = User.query.filter_by(username=username).first()
        if not user:
            response_data = ERROR_HANDLER.flask_api_errors("user", 'User not found')
            return jsonify(response_data), 404
        
        if 'profit_locking' not in data:
            response_data = ERROR_HANDLER.flask_api_errors("update_strategy_profit_locking", 'Profit locking data not provided')
            return jsonify(response_data), 400

        try:
            profit_locking_data = [x for x in data['profit_locking'].split(',')]
            if len(profit_locking_data) != 4:
                raise ValueError("Invalid profit locking data format")
        except ValueError:
            response_data = ERROR_HANDLER.flask_api_errors("update_strategy_profit_locking", 'Invalid profit locking data format')
            return jsonify(response_data), 400

        credential = Strategies.query.filter_by(strategy_tag=strategy_tag).first()
        if not credential:
            response_data = ERROR_HANDLER.database_errors("strategies", 'Credential not found')
            return jsonify(response_data), 404

        credential.profit_locking = ','.join(map(str, profit_locking_data))
        db.session.commit()

                # Check if profit_locking is equal to ",,,"
        if credential.profit_locking == ",,,":
            # Set reached_profit and locked_min_profit to 0
            credential.reached_profit = 0
            credential.locked_min_profit = 0
            db.session.commit()

        return jsonify({'message': f'Profit locking updated successfully for {strategy_tag} Strategy'}), 200
    
    def update_strategy_profit_trail_values(username,strategy_tag):
        data = request.json  # Assuming JSON data is sent with the request
        
        existing_user = User.query.filter_by(username=username).first()
        if not existing_user:
            response_data = ERROR_HANDLER.database_errors("user", "User does not exist")
            return jsonify(response_data), 404

        strategy_info = Strategies.query.filter_by(strategy_tag=strategy_tag).first()
        print("strategy_info:",strategy_info)
        if not strategy_info:
            response_data = ERROR_HANDLER.database_errors("strategies", 'Strategy not found')
            return jsonify(response_data), 404

        # Query current reached_profit and locked_min_profit values
        reached_profit = data.get('reached_profit', strategy_info.reached_profit)
        locked_min_profit = data.get('locked_min_profit', strategy_info.locked_min_profit)

        # Update the reached_profit and locked_min_profit values
        strategy_info.reached_profit = reached_profit
        strategy_info.locked_min_profit = locked_min_profit

        db.session.commit()

        return jsonify({'message': 'Strategy profit trail values updated successfully'}), 200
    
    def update_wait_time(username, strategy_tag):
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'message': 'User not found'}), 404
        # Get the strategy by strategy_tag
        strategy = Strategies.query.filter_by(strategy_tag=strategy_tag).first()

        allowed_trades = request.json.get('allowed_trades')
        entry_order_retry = request.json.get('entry_order_retry')
        entry_retry_count = request.json.get('entry_retry_count')
        entry_retry_wait = request.json.get('entry_retry_wait')
        exit_order_retry = request.json.get('exit_order_retry')
        exit_retry_count = request.json.get('exit_retry_count')
        exit_retry_wait = request.json.get('exit_retry_wait')
        exit_max_wait = request.json.get('exit_max_wait')
        


        # Update the strategy's max_profit and max_loss
        strategy.allowed_trades = allowed_trades
        strategy.entry_order_retry = entry_order_retry
        strategy.entry_retry_count = entry_retry_count
        strategy.entry_retry_wait = entry_retry_wait
        strategy.exit_order_retry = exit_order_retry
        strategy.exit_retry_count = exit_retry_count
        strategy.exit_retry_wait = exit_retry_wait
        strategy.exit_max_wait = exit_max_wait
        

        # Commit changes to the database
        db.session.commit()
        response_data = {'message': f'Wait time updated successfully for {strategy_tag} strategy'}
        return jsonify(response_data), 200


store_broker_and_strategy_info_blueprint = Blueprint('store_broker_and_strategy_info', __name__)
@store_broker_and_strategy_info_blueprint.route(STRATEGIE_ROUTES.get_routes("store_broker_and_strategy_info_blueprint"), methods=['POST'])
def store_broker_and_strategy_info(username):
    store_broker_and_strategy_info_response, status_code = Strategies_class.Store_broker_and_strategy_info(username=username)
    return store_broker_and_strategy_info_response, status_code
    

retrieve_strategy_info_blueprint = Blueprint('retrieve_strategy_info', __name__)
@retrieve_strategy_info_blueprint.route(STRATEGIE_ROUTES.get_routes("retrieve_strategy_info_blueprint"), methods=['GET'])
def retrieve_strategy_info(username):
    retrieve_strategy_info_response, status_code = Strategies_class.retrieve_strategy_info(username=username)
    return retrieve_strategy_info_response, status_code    


delete_strategy_tag_blueprint = Blueprint('delete_strategy_tag', __name__)
@delete_strategy_tag_blueprint.route(STRATEGIE_ROUTES.get_routes("delete_strategy_tag_blueprint"), methods=['DELETE'])
def delete_strategy_tag(username,strategy_tag):
    delete_strategy_tag_response, status_code = Strategies_class.delete_strategy_tag(username=username,strategy_tag=strategy_tag)
    return delete_strategy_tag_response, status_code  


update_max_profit_loss_blueprint = Blueprint('update_max_profit_loss_blueprint', __name__)
@update_max_profit_loss_blueprint.route(STRATEGIE_ROUTES.get_routes("update_max_profit_loss_blueprint"), methods=['POST'])
def update_max_profit_loss(username,strategy_tag):
    update_max_profit_loss_response, status_code = Strategies_class.update_max_profit_loss(username=username,strategy_tag=strategy_tag)
    return update_max_profit_loss_response, status_code  

update_strategy_profit_locking_blueprint = Blueprint('update_strategy_profit_locking_blueprint', __name__)
@update_strategy_profit_locking_blueprint.route(STRATEGIE_ROUTES.get_routes("update_strategy_profit_locking_blueprint"), methods=['POST'])
def update_strategy_profit_locking(username,strategy_tag):
    update_strategy_profit_locking_response, status_code = Strategies_class.update_strategy_profit_locking(username=username,strategy_tag=strategy_tag)
    return update_strategy_profit_locking_response, status_code 


update_strategy_profit_trail_values_blueprint = Blueprint('update_profit_trail_values', __name__)
@update_strategy_profit_trail_values_blueprint.route(STRATEGIE_ROUTES.get_routes("update_strategy_profit_trail_values_blueprint"), methods=['POST'])
def update_strategy_profit_trail_values(username,strategy_tag):
    update_strategy_profit_trail_values_response, status_code = Strategies_class.update_strategy_profit_trail_values(username,strategy_tag)
    return update_strategy_profit_trail_values_response, status_code

update_wait_time_blueprint = Blueprint('update_wait_time_blueprint', __name__)
@update_wait_time_blueprint.route(STRATEGIE_ROUTES.get_routes("update_wait_time_blueprint"), methods=['POST'])
def update_wait_time(username,strategy_tag):
    update_wait_time_response, status_code = Strategies_class.update_wait_time(username=username,strategy_tag=strategy_tag)
    return update_wait_time_response, status_code
    
    