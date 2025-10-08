from flask import Flask, jsonify, request, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
import os
import decimal
from datetime import datetime
import uuid

load_dotenv()
app = Flask(__name__, static_folder='../frontend', static_url_path='/')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bank.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
db = SQLAlchemy(app)

# Models
class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    account_no = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    pin = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    balance = db.Column(db.Numeric(15,2), default=decimal.Decimal('0.00'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    txn_id = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # deposit, withdraw, transfer
    amount = db.Column(db.Numeric(15,2), nullable=False)
    details = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Utilities
def gen_account():
    # 12-digit account with low collision probability
    while True:
        acc = str(uuid.uuid4().int)[:12]
        if not Customer.query.filter_by(account_no=acc).first():
            return acc

def record_txn(txn_type, amount, details=''):
    txn = Transaction(txn_id=str(uuid.uuid4()), type=txn_type, amount=decimal.Decimal(amount), details=details)
    db.session.add(txn)
    db.session.commit()

# Serve frontend
@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_proxy(path):
    # serve any frontend file (index.html, dashboard.html, css, js)
    return send_from_directory(app.static_folder, path)

# API endpoints
@app.route('/api/customers', methods=['GET', 'POST'])
def customers():
    if request.method == 'GET':
        allc = Customer.query.order_by(Customer.created_at.desc()).all()
        result = []
        for c in allc:
            result.append({
                'account_no': c.account_no,
                'name': c.name,
                'email': c.email,
                'mobile': c.mobile,
                'type': c.type,
                'balance': float(c.balance or 0),
                'created_at': c.created_at.isoformat()
            })
        return jsonify(result)
    else:
        # create
        data = request.get_json() or {}
        name = data.get('name','').strip()
        email = data.get('email','').strip().lower()
        mobile = data.get('mobile','').strip()
        pin = data.get('pin','').strip()
        acct_type = data.get('type','').strip()

        # server-side validation (same rules)
        if not name: return jsonify({'message':'Name required'}), 400
        if not email or not email.endswith('@gmail.com'):
            return jsonify({'message':'Email must end with @gmail.com'}), 400
        if not mobile or not (len(mobile)==10 and mobile[0] in '6789' and mobile.isdigit()):
            return jsonify({'message':'Invalid mobile'}), 400
        if not pin or not (pin.isdigit() and len(pin)==4):
            return jsonify({'message':'PIN must be 4 digits'}), 400
        if acct_type not in ('Savings','Current'):
            return jsonify({'message':'Invalid account type'}), 400

        account_no = gen_account()
        newcust = Customer(account_no=account_no, name=name, email=email, mobile=mobile, pin=pin, type=acct_type, balance=decimal.Decimal('0.00'))
        db.session.add(newcust)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return jsonify({'message':'Email or mobile already exists'}), 400
        return jsonify({'account_no': account_no}), 201

@app.route('/api/customers/<account_no>', methods=['GET','DELETE'])
def customer_get_delete(account_no):
    cust = Customer.query.filter_by(account_no=account_no).first()
    if not cust:
        return jsonify({'message':'Customer not found'}), 404
    if request.method == 'GET':
        return jsonify({
            'account_no': cust.account_no, 'name':cust.name, 'email':cust.email,
            'mobile':cust.mobile, 'type':cust.type, 'balance': float(cust.balance)
        })
    else:
        db.session.delete(cust)
        db.session.commit()
        return jsonify({'message':'Deleted'})

@app.route('/api/customers/<account_no>/deposit', methods=['POST'])
def deposit(account_no):
    cust = Customer.query.filter_by(account_no=account_no).first()
    if not cust:
        return jsonify({'message':'Customer not found'}), 404
    data = request.get_json() or {}
    try:
        amt = decimal.Decimal(str(data.get('amount',0)))
    except Exception:
        return jsonify({'message':'Invalid amount'}), 400
    if amt <= 0: return jsonify({'message':'Amount must be positive'}), 400
    cust.balance = cust.balance + amt
    db.session.commit()
    record_txn('deposit', amt, f'Deposit to {account_no}')
    return jsonify({'balance': float(cust.balance)})

@app.route('/api/customers/<account_no>/withdraw', methods=['POST'])
def withdraw(account_no):
    cust = Customer.query.filter_by(account_no=account_no).first()
    if not cust:
        return jsonify({'message':'Customer not found'}), 404
    data = request.get_json() or {}
    try:
        amt = decimal.Decimal(str(data.get('amount',0)))
    except Exception:
        return jsonify({'message':'Invalid amount'}), 400
    if amt <= 0: return jsonify({'message':'Amount must be positive'}), 400
    if cust.balance < amt:
        return jsonify({'message':'Insufficient balance'}), 400
    cust.balance = cust.balance - amt
    db.session.commit()
    record_txn('withdraw', amt, f'Withdraw from {account_no}')
    return jsonify({'balance': float(cust.balance)})

@app.route('/api/transfer', methods=['POST'])
def transfer():
    data = request.get_json() or {}
    from_acc = data.get('from')
    to_acc = data.get('to')
    try:
        amount = decimal.Decimal(str(data.get('amount',0)))
    except Exception:
        return jsonify({'message':'Invalid amount'}), 400
    if not from_acc or not to_acc or from_acc == to_acc:
        return jsonify({'message':'Provide valid different from/to accounts'}), 400
    if amount <= 0:
        return jsonify({'message':'Amount must be positive'}), 400
    src = Customer.query.filter_by(account_no=from_acc).first()
    dst = Customer.query.filter_by(account_no=to_acc).first()
    if not src or not dst:
        return jsonify({'message':'One or both accounts not found'}), 404
    if src.balance < amount:
        return jsonify({'message':'Insufficient funds in source account'}), 400
    src.balance = src.balance - amount
    dst.balance = dst.balance + amount
    db.session.commit()
    record_txn('transfer', amount, f'From {from_acc} to {to_acc}')
    return jsonify({'message':'Transferred', 'from_balance': float(src.balance), 'to_balance': float(dst.balance)})

@app.route('/api/transactions', methods=['GET'])
def transactions():
    limit = int(request.args.get('limit', '50'))
    txns = Transaction.query.order_by(Transaction.timestamp.desc()).limit(limit).all()
    result = []
    for t in txns:
        result.append({
            'txn_id': t.txn_id,
            'type': t.type,
            'amount': float(t.amount),
            'details': t.details,
            'timestamp': t.timestamp.isoformat()
        })
    return jsonify(result)

# CLI helper to create DB
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print("Initialized database.")

if __name__ == '__main__':
    # create DB automatically if missing
    db.create_all()
    app.run(host='0.0.0.0', port=3000, debug=True)
