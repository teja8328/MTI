# app/__init__.py
from flask import Flask
from app.models.main import db
from flask_mail import Mail, Message
from app.user_validation.registration import registration
from app.user_validation.login import login_blueprint
from app.user_validation.login import app_logout_blueprint



from app.api.user_settings.broker_integration import validation_blueprint
from app.api.user_settings.broker_integration import delete_broker_account_blueprint
from app.api.user_settings.broker_integration import update_password_blueprint
from app.api.user_settings.broker_integration import get_startegy_account_blueprint
from app.api.user_settings.broker_integration import logout_blueprint
from app.api.user_settings.broker_integration import update_user_data_blueprint
from app.api.user_settings.broker_integration import update_user_profit_locking_blueprint
from app.api.user_settings.broker_integration import update_user_profit_trail_values_blueprint
from app.api.user_settings.broker_integration import square_off_maxloss_per_trade_blueprint
from app.api.user_settings.broker_integration import square_off_equity_maxloss_per_trade_level_blueprint
from app.api.user_settings.broker_integration  import update_pseudo_balance_blueprint
from app.api.user_settings.broker_integration import update_displayname_blueprint

from app.api.payment.validations import payment
from app.api.admin.validations import admin
from app.api.admin.validations import broker_list
from app.api.admin.validations import user_list


from app.database.connection import Config
from app.api.strategies.validations import store_broker_and_strategy_info_blueprint
from app.api.strategies.validations import retrieve_strategy_info_blueprint
from app.api.strategies.validations import delete_strategy_tag_blueprint
from app.api.strategies.validations import update_max_profit_loss_blueprint
from app.api.strategies.validations import update_strategy_profit_locking_blueprint
from app.api.strategies.validations import update_strategy_profit_trail_values_blueprint

from app.api.strategies.validations import update_wait_time_blueprint


from app.api.multileg.validations import angelone_placeorder_blueprint



from app.api.multileg.validations import store_portfolio_blueprint
from app.api.multileg.validations import get_portfolio_blueprint
from app.api.multileg.validations import delete_portfolio_blueprint
from app.api.multileg.validations import fyers_websocket_blueprint

from app.api.multileg.validations import fyers_place_order_blueprint
from app.api.multileg.validations import edit_portfolio_blueprint
from app.api.brokers.angelone import get_live_feed_blueprint
from app.api.multileg.validations import get_price_details_blueprint
from app.api.multileg.validations import delete_portfolio_legs_blueprint
from app.api.multileg.validations import get_expiry_list_blueprint

from app.api.order_book.validations import order_book_blueprint
from app.api.order_book.validations import pseudo_limit_order_status_blueprint



from app.api.multileg.validations import logout_broker_accounts_blueprint
from app.api.multileg.validations import fyers_square_off_strategy_blueprint
from app.user_validation.login import change_password_blueprint
from app.api.multileg.validations import get_executed_portfolios_blueprint
from app.api.multileg.validations import angelone_square_off_strategy_blueprint
from app.api.optionchain.optionchain import get_option_chain_blueprint
from app.api.multileg.validations import flatrade_place_order_blueprint
from app.api.equity.validations import fyers_equity_symbols_blueprint
from app.api.trading_tools.validations import square_off_angelone_loggedIn_blueprint
from app.api.user_settings.broker_integration import forgot_password_blueprint
from app.api.equity.validations import fyers_place_equity_order_blueprint
from app.api.user_settings.broker_integration import verify_otp_blueprint
from app.api.user_settings.broker_integration import change_user_password_blueprint
from app.api.trading_tools.validations import square_off_fyers_loggedIn_blueprint
from app.api.multileg.validations import flattrade_square_off_strategy_blueprint
from app.api.equity.validations import get_equity_price_details_blueprint
from app.api.trading_tools.validations import square_off_flattrade_loggedIn_blueprint
from app.api.equity.validations import angelone_equity_symbols_blueprint
from app.api.equity.validations import get_angelone_equity_price_details_blueprint
from app.api.equity.validations import angelone_place_equity_order_blueprint
from app.api.equity.validations import flattrade_equity_place_order_blueprint



from app.api.multileg.validations import enable_portfolio_blueprint
from app.api.multileg.validations import enable_all_portfolio_blueprint
from app.api.multileg.validations import delete_all_enabled_portfolios_blueprint
from app.api.multileg.validations import delete_all_portfolio_blueprint
from app.api.order_book.validations import cancel_portfolio_orders_blueprint
from app.api.order_book.validations import modify_portfolio_orders_blueprint
from app.api.order_book.validations import execute_at_market_orders_blueprint



# from app.api.equity.validations import angelone_equity_square_off_loggedIn_blueprint

# from app.api.websocket.validations import websocket_fyers_blueprint

# from app.api.equity.validations import flattrade_equity_square_off_loggedIn_blueprint
# from app.api.equity.validations import fyers_equity_square_off_loggedIn_blueprint

from app.api.multileg.validations import get_future_expiry_list_blueprint
from app.api.multileg.validations import fyers_futures_place_order_blueprint
from app.api.multileg.validations import angleone_future_place_order_blueprint
from app.api.multileg.validations import flatrade_future_place_order_blueprint

from app.api.equity.validations import fyers_equity_square_off_loggedIn_blueprint
from app.api.equity.validations import angelone_equity_square_off_loggedIn_blueprint
from app.api.equity.validations import flattrade_equity_square_off_loggedIn_blueprint
 
from app.api.equity.validations import flattrade_equity_strategy_square_off_blueprint
from app.api.equity.validations import angelone_equity_strategy_square_off_blueprint
from app.api.equity.validations import fyers_equity_strategy_square_off_blueprint
from app.api.equity.validations import pseudo_equity_place_order_blueprint
from app.api.equity.validations import pseudo_equity_square_off_blueprint
from app.api.equity.validations import pseudo_equity_strategy_square_off_blueprint

from app.api.multileg.validations import angelone_ltp_websocket_blueprint
from app.api.multileg.validations import get_ltp_blueprint
from app.api.multileg.validations import fyers_websocket_ltp_blueprint
from app.api.multileg.validations import get_fyers_ltp_blueprint
from app.api.multileg.validations import fetching_portfoliolevel_positions_blueprint
from app.api.multileg.validations import square_off_portfolio_level_blueprint
from app.api.multileg.validations import flatrade_websocket_blueprint
from app.api.multileg.validations import get_flattrade_ltp_blueprint
from app.api.multileg.validations import fetching_strategy_tag_positions_blueprint
from app.api.multileg.validations import websocket_ltp_blueprint
from app.api.multileg.validations import all_ltp_data_blueprint
from app.api.multileg.validations import update_portfolio_leg_profit_trail_values_blueprint
from app.api.multileg.validations import square_off_portfolio_leg_level_blueprint
from app.api.multileg.validations import Get_theta_gamma_vega_values_blueprint
from app.api.multileg.validations import add_portfolio_performance_blueprint
from app.api.multileg.validations import get_portfolio_performance_blueprint

from app.api.multileg.validations import Get_latest_blueprint
 



from app.api.master_child.validations import create_master_child_accounts_blueprint
from app.api.master_child.validations import fetch_master_child_accounts_blueprint
from app.api.master_child.validations import delete_master_child_accounts_blueprint
from app.api.master_child.validations import angelone_symbols_blueprint
from app.api.master_child.validations import delete_child_account_blueprint
from app.api.master_child.validations import place_master_child_order_blueprint
from app.api.master_child.validations import square_off_master_child_blueprint
from app.api.master_child.validations import fetching_master_child_positions_blueprint
from app.api.master_child.validations import cancel_mc_orders_blueprint
from app.api.master_child.validations import modify_mc_orders_blueprint

from app.api.multileg.validations import pseudo_placeorderblueprint
from app.api.multileg.validations import pseudo_squareoff_user_blueprint
from app.api.multileg.validations import pseudo_squareoff_strategy_blueprint



from flask_socketio import SocketIO, disconnect
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask import request

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'saich5252@gmail.com'
app.config['MAIL_PASSWORD'] = 'vfdesgvzxpbpnsko'
mail = Mail(app)

# Use the Config class for configuration
app.config.from_object(Config)

# Add CORS support for all origins
CORS(app, origins='*')

# Use the db instance created in models.py
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

jwt = JWTManager(app)

# socketio = SocketIO(app, cors_allowed_origins = '*')

from app.api.brokers import config

from app.models.main import db
from app.models.user import User

import time
from threading import Timer

from flask import Flask, request, session, current_app
from flask_socketio import SocketIO, disconnect
from app.models.main import db
from app.models.user import User
from app.api.brokers import config
import time
from threading import Timer
from app.api.brokers.config import active_connections
from datetime import datetime, timezone, timedelta
# # Initialize Flask app and SocketIO
# app = Flask(_name_)
# socketio = SocketIO(app, cors_allowed_origins="*")

# # Dictionary to store pending disconnections and session information
# pending_disconnections = {}

# @socketio.on('connect')
# def handle_connect():
#     session_id = request.args.get('session_id')
#     print("session_id:",session_id)

#     username = request.args.get('username')  # Pass the user_id as a parameter
#     print("username:", username)

#     if not session_id or not username:
#         print("Unauthenticated user tried to connect.")
#         return disconnect()

#     # If session_id already exists in active_connections, disconnect the previous connection
#     if session_id in active_connections:
#         previous_sid = active_connections[session_id]
#         if previous_sid != request.sid:
#             print(f"Disconnecting previous WebSocket connection for session_id {session_id}")
#             disconnect()

#     # Register the new WebSocket connection
#     active_connections[session_id] = request.sid
#     print(f"Session {session_id} connected with SID {request.sid}")

#     try:
#         # Look for a user with the given user_id and session_id=None
#         user = User.query.filter_by(username=username, session_id=None).first()

#         if user:
#             # Assign the session_id to the found user
#             user.session_id = session_id
#             user.logout_datetime = None
#             db.session.commit()
#             print(f"Assigned session_id {session_id} to User ID {username}")
#         else:
#             print(f"No user found with Username {username} and session_id=None")
#             # Optionally, handle cases where the user is not found
#     except Exception as e:
#         db.session.rollback()
#         print(f"Error saving session_id {session_id} to the database for Username {username}: {e}")

# # Route for socket disconnection
# @socketio.on('disconnect')
# def handle_disconnect():
#     sid = request.sid
#     for session_id, conn_sid in list(active_connections.items()):
#         if conn_sid == sid:
#             active_connections.pop(session_id)
#             print(f"Session {session_id} disconnected.")
#             # Optionally, remove from the database if needed
#             user = User.query.filter_by(session_id=session_id).first()
#             if user:
#                 # db.session.delete(user)
#                 user.session_id = None
#                 user.logout_datetime = datetime.now(timezone.utc)
#                 db.session.commit()
#             break
                

# Register blueprints
app.register_blueprint(registration)
app.register_blueprint(login_blueprint)
app.register_blueprint(validation_blueprint)
app.register_blueprint(delete_broker_account_blueprint)
app.register_blueprint(update_password_blueprint)
app.register_blueprint(get_startegy_account_blueprint)
app.register_blueprint(logout_blueprint)
app.register_blueprint(store_broker_and_strategy_info_blueprint)
app.register_blueprint(retrieve_strategy_info_blueprint)
app.register_blueprint(delete_strategy_tag_blueprint)
app.register_blueprint(angelone_placeorder_blueprint)


app.register_blueprint(store_portfolio_blueprint)
app.register_blueprint(get_portfolio_blueprint)

app.register_blueprint(delete_portfolio_blueprint)
app.register_blueprint(fyers_websocket_blueprint)

app.register_blueprint(fyers_place_order_blueprint)
app.register_blueprint(edit_portfolio_blueprint)
app.register_blueprint(get_live_feed_blueprint)
app.register_blueprint(get_price_details_blueprint)
app.register_blueprint(delete_portfolio_legs_blueprint)
app.register_blueprint(get_expiry_list_blueprint)
app.register_blueprint(order_book_blueprint)
app.register_blueprint(logout_broker_accounts_blueprint)
app.register_blueprint(fyers_square_off_strategy_blueprint)
app.register_blueprint(change_password_blueprint)
app.register_blueprint(pseudo_equity_place_order_blueprint)
app.register_blueprint(get_executed_portfolios_blueprint)
app.register_blueprint(angelone_square_off_strategy_blueprint)
app.register_blueprint(get_option_chain_blueprint)
app.register_blueprint(flatrade_place_order_blueprint)
app.register_blueprint(fyers_equity_symbols_blueprint)
app.register_blueprint(square_off_angelone_loggedIn_blueprint)
app.register_blueprint(forgot_password_blueprint)
app.register_blueprint(fyers_place_equity_order_blueprint)
app.register_blueprint(verify_otp_blueprint)
app.register_blueprint(change_user_password_blueprint)
app.register_blueprint(square_off_fyers_loggedIn_blueprint)
app.register_blueprint(flattrade_square_off_strategy_blueprint)
app.register_blueprint(get_equity_price_details_blueprint)
app.register_blueprint(square_off_flattrade_loggedIn_blueprint)
app.register_blueprint(angelone_equity_symbols_blueprint)
app.register_blueprint(pseudo_equity_square_off_blueprint)
app.register_blueprint(pseudo_equity_strategy_square_off_blueprint)
app.register_blueprint(get_angelone_equity_price_details_blueprint)
app.register_blueprint(angelone_place_equity_order_blueprint)

app.register_blueprint(enable_portfolio_blueprint)
app.register_blueprint(enable_all_portfolio_blueprint)
app.register_blueprint(delete_all_enabled_portfolios_blueprint)
app.register_blueprint(delete_all_portfolio_blueprint)

app.register_blueprint(flattrade_equity_place_order_blueprint)
# app.register_blueprint(angelone_equity_square_off_loggedIn_blueprint)

# app.register_blueprint(websocket_fyers_blueprint)
# app.register_blueprint(flattrade_equity_square_off_loggedIn_blueprint)

# app.register_blueprint(fyers_equity_square_off_loggedIn_blueprint)
app.register_blueprint(get_future_expiry_list_blueprint)
app.register_blueprint(fyers_futures_place_order_blueprint)
app.register_blueprint(angleone_future_place_order_blueprint)
app.register_blueprint(flatrade_future_place_order_blueprint)

app.register_blueprint(fyers_equity_square_off_loggedIn_blueprint)
app.register_blueprint(angelone_equity_square_off_loggedIn_blueprint)
app.register_blueprint(flattrade_equity_square_off_loggedIn_blueprint)
app.register_blueprint(flattrade_equity_strategy_square_off_blueprint)
app.register_blueprint(angelone_equity_strategy_square_off_blueprint)
app.register_blueprint(fyers_equity_strategy_square_off_blueprint)

app.register_blueprint(angelone_ltp_websocket_blueprint)
app.register_blueprint(get_ltp_blueprint)
app.register_blueprint(fyers_websocket_ltp_blueprint)
app.register_blueprint(get_fyers_ltp_blueprint)
app.register_blueprint(fetching_portfoliolevel_positions_blueprint)
app.register_blueprint(square_off_portfolio_level_blueprint)
app.register_blueprint(flatrade_websocket_blueprint)
app.register_blueprint(get_flattrade_ltp_blueprint)
app.register_blueprint(fetching_strategy_tag_positions_blueprint)
app.register_blueprint(update_max_profit_loss_blueprint)
app.register_blueprint(update_user_data_blueprint)

app.register_blueprint(websocket_ltp_blueprint)
app.register_blueprint(all_ltp_data_blueprint)
app.register_blueprint(update_user_profit_trail_values_blueprint)
app.register_blueprint(update_user_profit_locking_blueprint)
app.register_blueprint(update_portfolio_leg_profit_trail_values_blueprint)

app.register_blueprint(update_strategy_profit_locking_blueprint)
app.register_blueprint(update_strategy_profit_trail_values_blueprint)
app.register_blueprint(square_off_portfolio_leg_level_blueprint)
app.register_blueprint(create_master_child_accounts_blueprint)
app.register_blueprint(fetch_master_child_accounts_blueprint)
app.register_blueprint(delete_master_child_accounts_blueprint)
app.register_blueprint(angelone_symbols_blueprint)
app.register_blueprint(delete_child_account_blueprint)
app.register_blueprint(place_master_child_order_blueprint)
app.register_blueprint(square_off_master_child_blueprint)
app.register_blueprint(fetching_master_child_positions_blueprint)
app.register_blueprint(Get_theta_gamma_vega_values_blueprint)
app.register_blueprint(add_portfolio_performance_blueprint)
app.register_blueprint(get_portfolio_performance_blueprint)
app.register_blueprint(Get_latest_blueprint)
app.register_blueprint(cancel_mc_orders_blueprint)
app.register_blueprint(cancel_portfolio_orders_blueprint)

app.register_blueprint(modify_mc_orders_blueprint)
app.register_blueprint(pseudo_placeorderblueprint)
app.register_blueprint(pseudo_squareoff_strategy_blueprint)
app.register_blueprint(pseudo_squareoff_user_blueprint)
app.register_blueprint(update_pseudo_balance_blueprint)
app.register_blueprint(square_off_maxloss_per_trade_blueprint)
app.register_blueprint(square_off_equity_maxloss_per_trade_level_blueprint)
app.register_blueprint(payment)
app.register_blueprint(update_wait_time_blueprint)
app.register_blueprint(admin)
app.register_blueprint(broker_list)
app.register_blueprint(user_list)
app.register_blueprint(update_displayname_blueprint)
app.register_blueprint(pseudo_limit_order_status_blueprint)
app.register_blueprint(modify_portfolio_orders_blueprint)
app.register_blueprint(execute_at_market_orders_blueprint)
app.register_blueprint(app_logout_blueprint)



