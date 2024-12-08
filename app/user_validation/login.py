# app/routes/login.py
from flask import Blueprint, request, jsonify
from app.models.user import User
import jwt
from sqlalchemy import func
import secrets
from werkzeug.security import check_password_hash, generate_password_hash
import logging
from app.user_validation.error_handlers import login_errors
from app.models.main import db
from flask_jwt_extended import create_access_token
import uuid
import logging
from datetime import datetime, timezone, timedelta


active_connections = {}

login_blueprint  = Blueprint('login', __name__)

@login_blueprint.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        data = request.json

        entered_username = data.get('username')
        password = data.get('password')

        if not entered_username or not password:
            response_data = {
                'message': 'Username and password are required',
            }
            return jsonify(response_data), 400  # 400 Bad Request

        existing_user = User.query.filter(User.username == entered_username).first()

        if existing_user:
            # Check if there's already an active session
            if existing_user.session_id:
                response_data = {
                    'message': 'You already have an active session. Please log out first to log in again.',
                    'subscription_end_date': existing_user.subscription_end_date,
                    'subscription_type': existing_user.subscription_type,
                    'username': entered_username
                }
                logging.warning(f'User {entered_username} attempted to log in with an active session.')
                return jsonify(response_data), 401  # 401 Unauthorized

            # Check if the password is correct
            if check_password_hash(existing_user.password, password):
                # Set the token expiration time to 1 day
                expires = timedelta(minutes=1440)

                # Create only the access token with username in the payload
                user_payload = {
                    "username": existing_user.username  # Only include username
                }
                access_token = create_access_token(identity=user_payload, expires_delta=expires)

                # Generate a unique session ID
                session_id = str(uuid.uuid4())  # Generates a random UUID

                # Update login datetime and session ID in the database
                existing_user.login_datetime = datetime.now(timezone.utc)  # Store current UTC time
                existing_user.session_id = session_id
                existing_user.logout_datetime = None  # Add the session ID
                db.session.commit()  # Commit the changes to the database

                # Response with the access token, user details, and session ID
                response_data = {
                    'message': 'Login Successful',
                    'username': existing_user.username,
                    'access_token': access_token,
                    'subscription_end_date': existing_user.subscription_end_date,
                    'subscription_type': existing_user.subscription_type,
                    'num_of_users': existing_user.num_of_users,
                    'session_id': session_id
                }

                return jsonify(response_data), 200
            else:
                response_data = {
                    'message': 'Invalid Password',
                    'field': 'password',
                    'username': entered_username
                }
                logging.warning(f'Invalid password for user {entered_username}')
                return jsonify(response_data), 401  # 401 Unauthorized
        else:
            response_data = {
                'message': 'Invalid Username',
                'field': 'username',
                'username': entered_username
            }
            logging.warning(f'Invalid username: {entered_username}')
            return jsonify(response_data), 401  # 401 Unauthorized



change_password_blueprint  = Blueprint('change_password', __name__)
 
@change_password_blueprint.route('/change_password/<string:username>', methods=['POST'])
def change_password(username):
    if request.method == 'POST':
        data = request.json
 
        old_password = data['old_password']
        new_password = data['password']
 
        existing_user = User.query.filter_by(username=username).first()
 
        if check_password_hash(existing_user.password,old_password):
            pass
        else:
            response_data = {
                "message" : "Incorrect Old password !"
            }
            return jsonify(response_data), 401
 
 
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
 
        if existing_user:
            existing_user.password = hashed_password
            db.session.add(existing_user)
            db.session.commit()
 
            response_data = {
                "message" : f"Password Changed Successfully for user : {username}"
            }
            return jsonify(response_data), 200
        else:
            response_data = {
                "message" : "Problem changing the password"
            }
            return jsonify(response_data), 401


app_logout_blueprint  = Blueprint('app_logout', __name__)

@app_logout_blueprint.route('/app_logout', methods=['POST'])
def app_logout():
    data = request.json
    session_id = data.get('session_id')  # Get session_id from the session
    if not session_id:
        return jsonify({'message': 'Session not found'}), 400

    existing_user = User.query.filter(User.session_id == session_id).first()
    if existing_user and existing_user.session_id:
        # Clear session ID from the database
        existing_user.session_id = None
        existing_user.logout_datetime = datetime.now(timezone.utc)
        db.session.commit()

        # # Disconnect WebSocket associated with the session
        # if session_id in active_connections:
        #     sid = active_connections.pop(session_id, None)
        #     socketio.disconnect(sid)
        
        # return jsonify({'message': 'Logout successful'}), 200
    else:
        return jsonify({'message': 'Invalid session or already logged out'}), 400







            