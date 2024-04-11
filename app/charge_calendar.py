# app/charge_calendar.py
import stripe
import logging
from typing import List, Dict
from app.queries import Queries

queries = Queries()

logger = logging.getLogger(__name__)

def charge_customer(customer_id: str, amount: int, card_upcharge: int) -> bool:
    try:
        # Retrieve the customer object
        customer = stripe.Customer.retrieve(customer_id)
    except stripe.StripeError as e:
        logger.error("Failed to retrieve customer.", exc_info=True)
        return False

    # Check if a default payment method ID is set in invoice_settings
    default_payment_method_id = customer.invoice_settings.default_payment_method

    if default_payment_method_id:
        # Since a default payment method exists, retrieve its details
        payment_method = stripe.PaymentMethod.retrieve(default_payment_method_id)
        logger.debug("Default Payment Method Type: %s", payment_method.type)
    else:
        # If there is no default payment method set, there's no need for further API calls
        logger.debug("No default payment method set for this customer.")
        # Provide alert email to customer/staff to update payment method
        return False
    
    if payment_method.type == 'card':
        amount += card_upcharge
        
    try:
        stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            customer=customer_id,
            payment_method=default_payment_method_id,
            off_session=True,
            confirm=True
        )
        return True
    except stripe.StripeError as e:
        logger.error("Failed to charge customer.", exc_info=True)
        return False

def customers_from_type_code(type_code: str) -> List[Dict]:
    customer_data = queries.fetch_records(
        table_name='customers',
        fields=['customer_type'],
        values=[type_code],
        return_fields=['customer_id', 'email', 'phone', 'name']
    )
    if not customer_data:
        logger.error("Failed to retrieve customer data.")
        return []
    return customer_data

def fetch_charge_info(type_code: str) -> dict:
    charge_info_data = queries.fetch_records(
        table_name='charge_info',
        fields=['type_code'],
        values=[type_code],
        return_fields=['data']
    )
    if not charge_info_data:
        logger.error("Failed to retrieve charge info data.")
        return []
    elif len(charge_info_data) > 1:
        logger.error("Multiple charge info records found.")
        return []
    else:
        return charge_info_data[0]['data']
    
def process_charges(type_code: str) -> None:
    charge_info = fetch_charge_info(type_code)
    if not charge_info:
        logger.error("No charge info found.")
        return
    customers = customers_from_type_code(type_code)
    logger.debug("Customers found: %s", customers)
    if not customers:
        logger.info("No customers found.")
        return

    for customer in customers:
        customer: dict
        if not charge_customer(customer['customer_id'], charge_info['amount'], charge_info['card_upcharge']):
            logger.error(f"Failed to charge customer {customer['customer_id']}.")
