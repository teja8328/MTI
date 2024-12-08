# app/routes/registration.py
from flask import Blueprint, request, jsonify
from app.models.main import db
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash,generate_password_hash
import logging
from sqlalchemy import func
from app.models.user import BrokerCredentials
from datetime import datetime, timezone, timedelta

registration = Blueprint('registration', __name__)
@registration.route('/data', methods=['POST'])
def handle_form_data():
    data = request.json

    # Validate data fields
    required_fields = ['name', 'email', 'mobile', 'username', 'password']
    if not all(field in data for field in required_fields):
        response_data = {
            'message': 'Missing required fields',
            'data': data
        }
        return jsonify(response_data), 400  # 400 Bad Request

    # Check if mobile number already exists in the incoming data
    if User.query.filter_by(mobile=data['mobile']).first():
        response_data = {
            'message': 'Mobile number already exists',
            'field': 'mobile',
            'data': data
        }
        return jsonify(response_data), 409  # 409 Conflict

    try:
        hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')

        existing_user_mail = User.query.filter(func.lower(User.email) == func.lower(data['email'])).first()
        existing_user_name = User.query.filter(func.lower(User.username) == func.lower(data['username'])).first()

        if existing_user_mail and existing_user_name:
            response_data = {
                'message': 'User already exists',
                'field': '',
                'data': data
            }
            return jsonify(response_data), 409  # 409 Conflict

        elif existing_user_mail:
            response_data = {
                'message': 'Email already exists',
                'field': 'email',
                'data': data
            }
            return jsonify(response_data), 409  # 409 Conflict

        elif existing_user_name:
            response_data = {
                'message': 'Username already taken',
                'field': 'username',
                'data': data
            }
            return jsonify(response_data), 409  # 409 Conflict

        # Create and add a new user
        current_time_utc = datetime.now(timezone.utc)
        new_user = User(
            name=data['name'],
            email=data['email'],
            mobile=data['mobile'],
            username=data['username'],
            password=hashed_password,
            subscription_start_date=current_time_utc,
            subscription_end_date=current_time_utc + timedelta(days=7),
            is_on_trial=True,
            num_of_users=1,
            subscription_type='Free_Trial'
        )

        db.session.add(new_user)
        db.session.commit()

        pseudo_account = BrokerCredentials(
            user_id=new_user.id,
            username=data['username'],                                 
            broker="pseudo_account",
            broker_user_id="PSEUDO123",
            #password="123",
            available_balance="100000",
            max_loss = "0",
            max_profit ="0",
            user_multiplier = "1",
            profit_locking = ",,,",
            reached_profit ="0",
            locked_min_profit ="0",
            max_loss_per_trade= "0",
            utilized_margin="0",
            max_open_trades = "0",
            exit_time ="00:00:00"
        )
        db.session.add(pseudo_account)
        db.session.commit()

        response_data = {
            'message': 'User created successfully',
            'data': data
        }
        return jsonify(response_data), 201  # 201 Created

    except IntegrityError as e:
        db.session.rollback()
        logging.error(f'IntegrityError: {str(e)}')
        response_data = {
            'message': 'IntegrityError occurred',
            'data': data
        }
        return jsonify(response_data), 500  # 500 Internal Server Error
    finally:
        db.session.close()


