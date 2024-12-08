from flask import Blueprint, request, jsonify
from app.models.main import db
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash,generate_password_hash
import logging
from sqlalchemy import func
from app.models.user import BrokerCredentials
from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
import schedule
import time
import threading
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


payment = Blueprint('payment', __name__)


@payment.route('/make_payment', methods=['POST'])
def make_payment():
    data = request.get_json()
    username = data.get('username')
    payment_order_id = data.get('payment_order_id')
    payment_amount = data.get('payment_amount')
    payment_mode = data.get('payment_mode')
    num_of_users = data.get('num_of_users')
    renewal_period = data.get('renewal_period')
    payment_type = data.get('payment_type')

    # Validate required fields
    if not all([username, payment_order_id, payment_amount, payment_mode, payment_type]):
        return jsonify({"message": "Required fields are missing."}), 400

    # Validate payment_amount and num_of_users
    try:
        payment_amount = float(payment_amount)
        if num_of_users:
            num_of_users = int(num_of_users)
    except ValueError:
        return jsonify({"message": "Invalid payment amount or number of users."}), 400

    user = User.query.filter_by(username=username).first()

    # Check if user exists
    if not user:
        return jsonify({"message": "User not found."}), 404
            # Convert user.payment_amount to float if it’s a string
    if isinstance(user.payment_amount, str):
        try:
            user.payment_amount = float(user.payment_amount)
        except ValueError:
            return jsonify({"message": "Invalid stored payment amount."}), 500

    current_time_utc = datetime.now(timezone.utc)

    if payment_type == 'RENEW':
        if user.subscription_type == 'Active':
            user.subscription_end_date += timedelta(days=30)

        elif user.subscription_type == 'Expired':
            user.subscription_start_date = current_time_utc
            user.subscription_end_date = current_time_utc + timedelta(days=30)
            user.subscription_type = "Active"
        else:
            user.subscription_type = 'Active'
            user.subscription_start_date = current_time_utc
            user.subscription_end_date = current_time_utc + timedelta(days=30)
            user.is_on_trial = False

        user.payment_order_id = payment_order_id
        user.payment_amount += payment_amount 
        user.payment_mode = payment_mode
        user.renewal_period = renewal_period
        user.num_of_users = num_of_users

    elif payment_type == 'ADD USER':
        if user.subscription_type != 'Active':
            return jsonify({"message": "Cannot add users. User's subscription is not active."}), 400
        
        user.num_of_users += num_of_users
        user.payment_order_id = payment_order_id
        user.payment_mode = payment_mode
        user.payment_amount += payment_amount  

    else:
        return jsonify({"message": "Invalid payment type."}), 400

    db.session.commit()
    message = "Subscription Renewed Successfully" if payment_type == 'RENEW' else f"Number of users updated. Total users: {user.num_of_users}."
    return jsonify({
            "message": message,
            "subscription_end_date": user.subscription_end_date,
            "subscription_type": user.subscription_type,
            "num_of_users": user.num_of_users
        }), 200
    
    
    
# DATABASE_URI = 'postgresql://postgres:Makonis@localhost:5432/mti_payment'
from app.database.connection import Config

DATABASE_URI = Config.SQLALCHEMY_DATABASE_URI
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

def update_subscription_status_logic(session):

    print("Updating subscription statuses...")

    try:
        # Get all users from the database
        users = session.query(User).all()
        current_time_utc = datetime.now(timezone.utc)  # Current time in UTC
        
        for user in users:
            print(f"User ID: {user.id}, Start: {user.subscription_start_date}, End: {user.subscription_end_date}")
            print(f"Current UTC time: {current_time_utc}")

            # Ensure subscription_end_date is timezone-aware
            if user.subscription_end_date.tzinfo is None:
                print("message: subscription_end_date is not timezone-aware")
                continue  # Skip this user

            if user.is_on_trial:
                if current_time_utc > user.subscription_end_date:
                    # Trial period has ended
                    print(f"Trial ended for user {user.id}")
                    user.is_on_trial = False
                    user.subscription_type = 'Expired'
                    user.num_of_users = 0
                    session.commit()
            else:
                if current_time_utc > user.subscription_end_date:
                    # Subscription has expired
                    print(f"Subscription expired for user {user.id}")
                    user.subscription_type = 'Expired'
                    user.num_of_users = 0
                    session.commit()

        print("User subscription status updated successfully.")
        
    except Exception as e:
        session.rollback()
        print(f"Error occurred: {e}")

def update_subscription_status():

    session = Session()

    try:
        update_subscription_status_logic(session)
    finally:
        session.close()

schedule.every().day.at("23:59").do(update_subscription_status)

def subscription_scheduler():

    while True:
        schedule.run_pending()
        time.sleep(1)