from app.models.main import db
from sqlalchemy import Time
from datetime import datetime, timezone, timedelta

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    broker_credentials = db.relationship('BrokerCredentials', backref='user', lazy=True)
    strategies = db.relationship('Strategies', backref='user', lazy=True)
    max_loss = db.Column(db.String(500),default="0")
    max_profit = db.Column(db.String(500),default="0")
    subscription_start_date = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    subscription_end_date = db.Column(db.DateTime(timezone=True))
    is_on_trial = db.Column(db.Boolean, default=True)
    num_of_users = db.Column(db.Integer, default=1)  
    subscription_type = db.Column(db.String(50), default='Free_Trial')  
    payment_order_id = db.Column(db.String(100), nullable=True)  
    payment_amount = db.Column(db.String(100), default="0") 
    payment_mode = db.Column(db.String(100), nullable=True) 
    renewal_period =  db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False) 
    login_datetime = db.Column(db.DateTime(timezone=True))
    logout_datetime = db.Column(db.DateTime(timezone=True))
    session_id = db.Column(db.String(36), nullable=True)
    
class Broker(db.Model):
    _tablename_ = 'brokers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)

import datetime
# Define BrokerCredentials model
class BrokerCredentials(db.Model):
    __tablename__ = 'broker_credentials'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(50), unique=False)
    broker = db.Column(db.String(500))
    broker_user_id = db.Column(db.String(500))
    password = db.Column(db.Text)
    api_key = db.Column(db.Text)
    qr_code = db.Column(db.Text)
    secret_key = db.Column(db.Text)
    client_id = db.Column(db.String(50))
    imei = db.Column(db.Text)
    vendor_code = db.Column(db.String(150))
    margin = db.Column(db.Text)
    enabled = db.Column(db.Boolean, default=True)
    display_name = db.Column(db.String(500))
    redirect_url = db.Column(db.String(500))
    max_loss = db.Column(db.String(500),default="0")
    max_profit = db.Column(db.String(500),default="0")
    profit_locking = db.Column(db.String(500), default=',,,')
    reached_profit = db.Column(db.Float, default=0)  
    locked_min_profit = db.Column(db.Float, default=0) 
    available_balance = db.Column(db.String(500), default="0.00")
    user_multiplier = db.Column(db.String(500),default="1")
    max_loss_per_trade = db.Column(db.String(500),default="0")
    utilized_margin = db.Column(db.String(500), default="0")
    max_open_trades = db.Column(db.String(500),default="1")
    exit_time = db.Column(Time, default=datetime.time(0, 0, 0))
    #strategies = db.relationship('Strategies', backref='broker_credentials', lazy=True,
                                # primaryjoin="BrokerCredentials.id == Strategies.broker_credentials_id")

# Define Strategies model
class Strategies(db.Model):
    __tablename__ = 'strategies'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alias = db.Column(db.String(50))
    strategy_tag = db.Column(db.String(50), unique=True, nullable=False)
    broker = db.Column(db.String(500))
    broker_user_id = db.Column(db.String(500))
    max_loss = db.Column(db.String(500),default="0")
    max_profit = db.Column(db.String(500),default="0")
    multipliers = db.relationship('StrategyMultipliers', backref='strategy', lazy=True, cascade="all, delete-orphan")
    profit_locking = db.Column(db.String(500), default=',,,')
    reached_profit = db.Column(db.Float, default=0)  
    locked_min_profit = db.Column(db.Float, default=0) 
    open_time = db.Column(Time, default=datetime.time(0, 0, 0))
    close_time = db.Column(Time, default=datetime.time(0, 0, 0))
    square_off_time = db.Column(Time, default=datetime.time(0, 0, 0))
    allowed_trades =  db.Column(db.String(100),default = "Both")
    entry_order_retry = db.Column(db.Boolean, default=False)
    entry_retry_count = db.Column(db.String(100),default = "0")
    entry_retry_wait = db.Column(db.String(500), default='0')
    exit_order_retry = db.Column(db.Boolean, default=False)
    exit_retry_count =db.Column(db.String(100),default = "0")
    exit_retry_wait = db.Column(db.String(500), default='0')
    exit_max_wait = db.Column(db.String(500), default='0')

    # Relationship with StrategyMultipliers
    # multipliers = db.relationship('StrategyMultipliers', backref='strategy', lazy=True)

class StrategyMultipliers(db.Model):
    __tablename__ = 'strategy_multipliers'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategies.id'), nullable=False)
    broker_user_id = db.Column(db.String(50), nullable=False)
    multiplier = db.Column(db.String(50))


from datetime import datetime
class Portfolio(db.Model):
    _tablename_ = 'portfolio'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    strategy = db.Column(db.String(500))
    strategy_accounts = db.Column(db.String(500))
    strategy_accounts_id = db.Column(db.String(500))
    variety = db.Column(db.String(50))
    order_type = db.Column(db.String(500))
    product_type = db.Column(db.String(500))
    duration = db.Column(db.String(500))
    exchange = db.Column(db.String(50))
    portfolio_name = db.Column(db.String(500), unique=False)
    remarks = db.Column(db.String(500))
    symbol = db.Column(db.String(500))
    enabled = db.Column(db.Boolean, default=False)
    start_time = db.Column(Time)
    end_time = db.Column(Time)
    square_off_time = db.Column(db.String(500))
    buy_trades_first = db.Column(db.Boolean, default=False)
    positional_portfolio = db.Column(db.Boolean, default=False)
    expiry_date = db.Column(db.String(500))
    max_lots = db.Column(db.String(10))

    

class Portfolio_legs(db.Model):
     _tablename_ = 'portfoliolegs'
     id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
     Portfolio_id = db.Column(db.Integer)
     portfolio_name = db.Column(db.String(500), unique=False)
     transaction_type = db.Column(db.String(500))
     option_type = db.Column(db.String(500))
     lots = db.Column(db.String(500))
     expiry_date = db.Column(db.String(500))
     strike = db.Column(db.String(500))
     quantity = db.Column(db.String(500))
     target = db.Column(db.String(500), default="None")
     tgt_value = db.Column(db.String(500))
     trail_tgt = db.Column(db.String(500))
     stop_loss = db.Column(db.String(500), default="None")
     sl_value = db.Column(db.String(500))
     trail_sl = db.Column(db.String(500))
     limit_price = db.Column(db.String(500))
     start_time = db.Column(db.String(500))
     wait_sec = db.Column(db.String(500))
     wait_action = db.Column(db.String(500))



class ExecutedPortfolio(db.Model):
     __tablename__ = "executedportfolios"
     id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
     user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
     strategy_tag = db.Column(db.String(100))
     portfolio_name =  db.Column(db.String(100), unique=False)
     order_id =  db.Column(db.String(100),unique=False)
     broker_user_id = db.Column(db.String(500))
     portfolio_Status = db.Column(db.Boolean, default=True)
     transaction_type = db.Column(db.String(100))
     trading_symbol = db.Column(db.String(100))
     exchange = db.Column(db.String(100))
     product_type = db.Column(db.String(100))
     netqty = db.Column(db.String(100))
     symbol_token = db.Column(db.String(100))
     variety = db.Column(db.String(100))
     duration = db.Column(db.String(100))
     price = db.Column(db.String(100))
     order_type = db.Column(db.String(100))
     status = db.Column(db.String(100))
     square_off = db.Column(db.Boolean, default=False)
     portfolio_leg_id = db.Column(db.Integer)
     reached_profit = db.Column(db.Float, default=0)  
     locked_min_profit = db.Column(db.Float, default=0)
     buy_price = db.Column(db.String(100))
     sell_price = db.Column(db.String(100))
     master_account_id = db.Column(db.Integer, db.ForeignKey('master_accounts.id'))
     broker = db.Column(db.String)
     placed_time = db.Column(db.String)
     sell_order_id =  db.Column(db.String(100),unique=False)
     squared_off_time = db.Column(db.String)
     buy_qty = db.Column(db.String(100))
     sell_qty =db.Column(db.String(100))
     trailed_sl = db.Column(db.Float, default=0)
     margin_req = db.Column(db.String(500), default="0")
     wait_sec = db.Column(db.String(500))
     wait_action = db.Column(db.String(500))
    

class ExecutedEquityOrders(db.Model):
     __tablename__="executedequityorders"
     id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
     order_id =  db.Column(db.String(100),unique=False)
     sell_order_id =  db.Column(db.String(100),unique=False)
     user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
     trading_symbol =db.Column(db.String(100))
     broker = db.Column(db.String(500))
     broker_user_id=db.Column(db.String(500))
     quantity = db.Column(db.String(500))
     transaction_type = db.Column(db.String(100))
     product_type = db.Column(db.String(100))
     strategy_tag = db.Column(db.String(100))
     buy_price = db.Column(db.String(100))
     sell_price = db.Column(db.String(100))
     symbol_token = db.Column(db.String(100))
     placed_time = db.Column(db.String(100))
     squared_off_time = db.Column(db.String(100))
     square_off = db.Column(db.Boolean, default=False)
     buy_qty = db.Column(db.String(100))
     sell_qty =db.Column(db.String(100))
     margin_req = db.Column(db.String(500), default="0")
     status = db.Column(db.String(100))
     order_type = db.Column(db.String(100))
     
     


class MasterAccount(db.Model):
    __tablename__ = 'master_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    broker = db.Column(db.String, nullable=False)
    broker_user_id = db.Column(db.String, unique=True, nullable=False)
    copy_start_time = db.Column(Time)
    copy_end_time = db.Column(Time)
    copy_placement = db.Column(db.Boolean, default=True)
    copy_cancellation = db.Column(db.Boolean, default=True)
    copy_modification = db.Column(db.Boolean, default=True)
    parallel_order_execution = db.Column(db.Boolean, default=True)
    auto_split_frozen_qty = db.Column(db.Boolean, default=True)
    
    # Relationship with ChildAccount
    child_accounts = db.relationship('ChildAccount', back_populates='master_account', cascade="all, delete-orphan")

class ChildAccount(db.Model):
    __tablename__ = 'child_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    broker = db.Column(db.String, nullable=False)
    broker_user_id = db.Column(db.String, unique=True, nullable=False)
    multiplier = db.Column(db.Integer, nullable=False, default=1)
    live = db.Column(db.Boolean, default=True)
    master_account_id = db.Column(db.Integer, db.ForeignKey('master_accounts.id'))
    
    # Relationship with MasterAccount
    master_account = db.relationship('MasterAccount', back_populates='child_accounts')



class Performance(db.Model):
    __tablename__ = 'portfolio_performance'
    id = db.Column(db.Integer, primary_key=True)
    portfolio_name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    broker_user_id = db.Column(db.String(100), nullable=False)
    max_pl = db.Column(db.Numeric, nullable=False)
    min_pl = db.Column(db.Numeric, nullable=False)
    max_pl_time = db.Column(db.Time, nullable=False)
    min_pl_time = db.Column(db.Time, nullable=False)
    product_type = db.Column(db.String(50))
    square_off = db.Column(db.Boolean, default=False)