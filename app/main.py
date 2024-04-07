# app/main.py
from flask import Flask, request, jsonify, g
from app.config import Config
from app.database import Database
import stripe
import logging
import json
from psycopg2 import IntegrityError

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
db = Database(app.config['DATABASE_URL'])

# Set Stripe's secret key
stripe.api_key = app.config['STRIPE_SECRET_KEY']


def create_checkout_session(customer_id) -> stripe.checkout.Session:
    customer = stripe.Customer.retrieve(customer_id)
    session = stripe.checkout.Session.create(
        customer=customer,
        payment_method_types=['card', 'us_bank_account'],
        mode='setup',
        success_url=app.config['SUCCESS_URL']
    )
    return session

def customer_exists_in_stripe(email: str) -> bool | dict:
    try:
        # Check for existing customer by email in Stripe
        existing_customers = stripe.Customer.list(email=email).data
        if existing_customers:
            return True
    except stripe.StripeError as e:
        logger.error("Failed to query Stripe for existing customer.", exc_info=True)
        return jsonify({'error': 'Failed to communicate with Stripe.'}), 500
    return False

def customer_exists_in_database(email: str, phone: str = None) -> bool | dict:
    # Check for existing customer in the database
    try:  
        with g.db_conn as conn:
            with conn.cursor() as cursor:
                if phone:
                    query = "SELECT 1 FROM public.customers WHERE email = %s OR phone = %s LIMIT 1"
                    cursor.execute(query, (email, phone))
                else:
                    query = "SELECT 1 FROM public.customers WHERE email = %s LIMIT 1"
                    cursor.execute(query, (email,))
                if cursor.fetchone():
                    return True
    except Exception as e:
        logger.error(f"Failed to communicate with database: {e}")
        return jsonify({'error': 'Failed to communicate with database.'}), 409
    return False
    
def create_customer(name: dict, email: str, phone: str) -> str:
    database_check = customer_exists_in_database(email, phone)
    if isinstance(database_check, dict):
        return database_check
    
    stripe_check = customer_exists_in_stripe(email)
    if isinstance(stripe_check, dict):
        return stripe_check

    try:
        customer = stripe.Customer.create(
            name=f"{name.get('First')}, {name.get('Last')}",
            email=email,
            phone=phone,
        )
        return customer.id
    except stripe.StripeError:
        logger.error("Failed to create Stripe customer.", exc_info=True)
        return jsonify({'error': 'Failed to create customer in Stripe.'}), 500
   
   
@app.route('/')
def hello_world():
    return 'Hello, World!'
 
@app.route('/submit-application', methods=['POST'])
def submit_application():
    data: dict = request.json
    email = data.get('email')
    phone = data.get('phone')
    name = data.get('name', {})
    address = data.get('address', {})
    metadata = data.get('metadata', {})

    if not email or not phone:
        return jsonify({'error': 'Both email and phone number are required.'}), 400

    if not all(key in name for key in ['First', 'Last']):
        return jsonify({'error': 'Name must include First and Last fields.'}), 400
    if not all(key in address for key in ['State', 'City', 'Address1', 'Zip']):
        return jsonify({'error': 'Address must include State, City, Address1, and Zip fields.'}), 400
    
    stripe_check = customer_exists_in_stripe(email)
    if not isinstance(stripe_check, bool):
        return stripe_check
    database_check = customer_exists_in_database(email, phone)
    if not isinstance(database_check, bool):
        return database_check
    if stripe_check is True or database_check is True:
        return jsonify({'error': 'Customer already exists.'}), 409

    response = create_customer(name, email, phone)
    if not isinstance(response, str):
        return response
    customer_id = response
    
    try:
        with g.db_conn as conn:
            with conn.cursor() as cursor:
                query = """
                INSERT INTO public.customers (customer_id, email, phone, name, address, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (customer_id, email, phone, json.dumps(name), json.dumps(address), json.dumps(metadata)))
                conn.commit()
                return jsonify({'message': 'Application submitted successfully.', 'id': customer_id}), 201
    except IntegrityError as e:
        conn.rollback()
        stripe.Customer.delete(customer_id)
        return jsonify({'error': 'An error occurred. Please try again later.'}), 409
    
@app.route('/add-payment', methods=['POST'])
def add_payment():
    data: dict = request.json
    customer_id = data.get('customer_id')
    try:
        session = create_checkout_session(customer_id)
    except stripe.StripeError as e:
        logger.error("Failed to create checkout session.", exc_info=True)
        return jsonify({'error': 'Failed to create checkout session.'}), 500
    logger.debug('Checkout session created.')
    return jsonify({'message': 'Your update payment link is ready.', 'id': customer_id, 'link': session.url})

@app.route('/customer-payment-methods', methods=['POST'])
def customer_payment_methods():
    data: dict = request.json
    customer_id = data.get('customer_id')

    if not customer_id:
        return jsonify({'error': 'Customer ID is required.'}), 400

    try:
        customer = stripe.Customer.retrieve(customer_id)
        payment_methods = stripe.PaymentMethod.list(customer=customer_id)

        # Extract default payment method ID from the customer object
        invoice_settings: dict = customer.get('invoice_settings', {})
        default_payment_method_id = invoice_settings.get('default_payment_method')

        # Prepare the list of payment method IDs and indicate which one is the default
        payment_methods_info = []
        for pm in payment_methods.data:
            payment_methods_info.append({
                'id': pm.id,
                'is_default': pm.id == default_payment_method_id
            })

        return jsonify({'payment_methods': payment_methods_info}), 200
    except stripe.StripeError as e:
        logger.error("Failed to retrieve payment methods from Stripe.", exc_info=True)
        return jsonify({'error': 'Failed to retrieve payment methods from Stripe.'}), 500
    
@app.route('/set-default-payment-method', methods=['POST'])
def set_default_payment_method():
    data: dict = request.json
    customer_id = data.get('customer_id')
    payment_method_id = data.get('payment_method_id')

    if not customer_id:
        return jsonify({'error': 'Customer ID is required.'}), 400
    if not payment_method_id:
        return jsonify({'error': 'Payment method ID is required.'}), 400

    try:
        # Retrieve the customer to check the current default payment method
        customer = stripe.Customer.retrieve(customer_id)
        invoice_settings: dict = customer.get('invoice_settings', {})
        current_default_payment_method_id = invoice_settings.get('default_payment_method')

        # Check if the provided payment method ID is already the default
        if payment_method_id == current_default_payment_method_id:
            return jsonify({'message': 'The provided payment method is already the default.'}), 200

        # Attempt to update the default payment method
        stripe.Customer.modify(customer_id, 
                               invoice_settings={'default_payment_method': payment_method_id})

        return jsonify({'message': 'Default payment method updated successfully.'}), 200
    except stripe.InvalidRequestError as e:
        # Handle scenarios like invalid customer ID or payment method ID
        return jsonify({'error': str(e)}), 400
    except stripe.StripeError as e:
        logger.error("Stripe API call failed.", exc_info=True)
        return jsonify({'error': 'Failed to update the default payment method.'}), 500
    
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.debug("Received webhook.")
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, app.config["WEBHOOK_SIGNING_SECRET"]
        )
    except ValueError as e:
        logger.error(f'Invalid payload: {e}')
        return 'Invalid payload', 400
    except stripe.SignatureVerificationError as e:
        logger.error(f'Invalid signature: {e}')
        return 'Invalid signature', 400
    except Exception as e:
        logger.error(f'Unhandled exception: {e}')
        return 'Internal server error', 500
    
    # Add event handling logic here


@app.before_request
def before_request():
    # Acquire a connection
    g.db_conn = db.connection_pool.getconn()

@app.teardown_request
def teardown_request(exception=None):
    # Put back into the pool
    db_conn = getattr(g, 'db_conn', None)
    if db_conn is not None:
        db.connection_pool.putconn(db_conn, close=True)


if __name__ == "__main__":
    app.run(debug=True)
    