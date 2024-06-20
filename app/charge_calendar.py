# app/charge_calendar.py
import stripe
import logging
from typing import List, Dict
from app.queries import Queries
import json
import datetime

queries = Queries()

logger = logging.getLogger(__name__)


def charge_customer(customer_id: str, amount: int, card_upcharge: int) -> Dict[str, any]:
    response = {
        'customer_id': customer_id,
        'amount_charged': 0,
        'charge_type': '',
        'status': '',
        'reason': ''
    }
    try:
        # Retrieve the customer object
        customer = stripe.Customer.retrieve(customer_id)
        response['amount_charged'] = amount
    except stripe.InvalidRequestError as e:
        response['status'] = 'failure'
        response['reason'] = 'Customer does not exist in Stripe'
        return response
    except stripe.StripeError as e:
        response['status'] = 'failure'
        response['reason'] = 'Unrecognized Stripe error'
        return response
    
    if hasattr(customer, 'deleted') and customer.deleted:
        response['status'] = 'failure'
        response['reason'] = 'Customer has been deleted in Stripe'
        return response

    # Check and set default payment method if not exists
    default_payment_method_id = customer.invoice_settings.default_payment_method
    if not default_payment_method_id:
        # Retrieve and set the first available payment method
        payment_methods = stripe.PaymentMethod.list(customer=customer_id)
        if payment_methods.data:
            first_payment_method = payment_methods.data[0]
            stripe.Customer.modify(customer_id, invoice_settings={'default_payment_method': first_payment_method.id})
            default_payment_method_id = first_payment_method.id
        else:
            response['status'] = 'failure'
            response['reason'] = 'No payment methods on file'
            return response

    try:
        # Retrieve and charge using the default payment method
        payment_method = stripe.PaymentMethod.retrieve(default_payment_method_id)
        response['charge_type'] = payment_method.type
        if payment_method.type == 'card':
            amount += card_upcharge  # Adjust for card upcharge

        # Execute the charge
        stripe.PaymentIntent.create(amount=amount, currency='usd', customer=customer_id, payment_method=default_payment_method_id, off_session=True, confirm=True)
        response['status'] = 'success'
        response['amount_charged'] = amount
    except stripe.StripeError as e:
        response['status'] = 'failure'
        response['reason'] = 'Stripe error during charging'
    return response

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
        return_fields=['label', 'data']
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
    customers = customers_from_type_code(type_code)
    results = []
    stats = {'total_customers': len(customers), 'charged_customers': 0}

    for customer in customers:
        result = charge_customer(customer['customer_id'], charge_info['amount'], charge_info['card_upcharge'])
        if result['status'] == 'success':
            stats['charged_customers'] += 1     
        results.append(result)

    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    json_filename = f'charge_report_{current_time}.json'
    stats_filename = f'stats_{current_time}.txt'
    
    # Write JSON report
    with open(json_filename, 'w') as file:
        json.dump(results, file, indent=4)

    # Write stats file
    with open(stats_filename, 'w') as file:
        file.write(f"Total Stripe Customers: {stats['total_customers']}\n")
        file.write(f"Customers Charged: {stats['charged_customers']}\n")
