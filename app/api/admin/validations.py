from flask import abort, request, jsonify,Blueprint
from app.models.user import Broker,User,BrokerCredentials
from app.models.main import db

admin = Blueprint('admin', __name__)

@admin.route('/admin/add_broker', methods=['POST'])
def add_brokers():
    
    data = request.get_json()
    username = data.get('username')
    
    # Check if the current user is an admin
    user = User.query.filter_by(username=username).first()
    if not user or not user.is_admin:
        return jsonify({"message": "User not found or not authorized."}), 404
    
    # Check if 'brokers' field is provided and is a list of broker names
    broker_names = data.get('brokers')
    if not broker_names or not isinstance(broker_names, list):
        return jsonify({"error": "'brokers' must be a list of broker names."}), 400

    added_brokers = []
    existing_brokers = []
    
    # Add each broker name in the list
    try:
        for broker_name in broker_names:
            if not broker_name:
                continue  
            
            # Check if the broker already exists
            existing_broker = Broker.query.filter_by(name=broker_name).first()
            if existing_broker:
                existing_brokers.append(broker_name)
                continue  # Skip adding this broker since it already exists

            # Create new broker object
            broker = Broker(name=broker_name)
            db.session.add(broker)
            added_brokers.append(broker_name)
        
        # Commit changes to the database
        db.session.commit()

        # Return success response
        return jsonify({
            'message': 'Brokers Added successfully.',
            'added_brokers': added_brokers,
            'existing_brokers': existing_brokers
        }), 201

    except Exception as e:
        # Handle any database or server errors
        db.session.rollback()  # Rollback in case of error
        return jsonify({'error': str(e)}), 500  # Internal server error

    
    
broker_list = Blueprint('broker_list', __name__)

@broker_list.route('/broker_list', methods=['GET'])
def get_brokers():
    try:
        # Fetch all brokers from the database
        brokers = Broker.query.all()
        
        # If no brokers are found, return an empty list
        if not brokers:
            return jsonify({'message': 'No brokers found', 'brokers': []}), 200
        
        # Convert the broker objects to a list of dictionaries
        brokers_list = [{'id': broker.id, 'name': broker.name} for broker in brokers]
        
        # Return the list of brokers
        return jsonify({'brokers': brokers_list}), 200

    except Exception as e:
        return jsonify({'message': 'Failed to fetch brokers'}), 500
    
    
user_list = Blueprint('user_list', __name__)

@user_list.route('/user_list', methods=['GET'])
def get_users_list():
    try:
        # Retrieve JSON data from the request
        data = request.get_json()
        username = data.get('username')
        
        # Check if the current user is an admin
        user = User.query.filter_by(username=username).first()
        if not user or not user.is_admin:
            return jsonify({"message": "User not found or not authorized."}), 404
        
        # Fetch all users from the database
        users = User.query.all()
        
        # If no users are found, return an empty list
        if not users:
            return jsonify({'message': 'No users found', 'users': []}), 200
        
        # Convert user objects to a list of dictionaries
        users_list = [
            {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'mobile': user.mobile,
                'subscription_start_date': user.subscription_start_date,
                'is_on_trial': user.is_on_trial,
                'subscription_end_date': user.subscription_end_date,
                'num_of_users': user.num_of_users,
                'subscription_type': user.subscription_type,
                'payment_order_id': user.payment_order_id,
                'payment_amount': user.payment_amount,
                'payment_mode': user.payment_mode,
                'renewal_period': user.renewal_period
            } for user in users
        ]
        
        # Return the list of users
        return jsonify({'users': users_list}), 200
    
    except Exception as e:
        # Handle exceptions and return an error message
        return jsonify({'message': 'Failed to fetch users', 'error': str(e)}), 500