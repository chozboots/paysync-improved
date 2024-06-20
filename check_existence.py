# app/check_customers.py
import stripe
import logging
from typing import List, Dict
from app.queries import Queries

queries = Queries()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_customers_from_db() -> List[Dict[str, str]]:
    """
    Fetch customers from the database.
    
    Returns:
        List[Dict[str, str]]: List of customers with their customer_id.
    """
    return queries.fetch_records(
        table_name='customers',
        fields=[],
        values=[],
        return_fields=['customer_id']
    )

def check_customer_exists_in_stripe(customer_id: str) -> bool:
    """
    Check if a customer exists in Stripe.
    
    Args:
        customer_id (str): The customer ID to check.
        
    Returns:
        bool: True if the customer exists in Stripe, False otherwise.
    """
    try:
        stripe.Customer.retrieve(customer_id)
        return True
    except stripe.error.InvalidRequestError:
        return False
    except stripe.StripeError as e:
        logger.error(f"Stripe error when checking customer {customer_id}: {e.user_message}")
        return False

def main():
    """
    Main function to check if all customers in the database exist in Stripe.
    """
    customers = get_customers_from_db()
    if not customers:
        logger.error("No customers found in the database.")
        return

    non_existing_customers = []
    
    for customer in customers:
        customer_id = customer.get('customer_id')
        if not customer_id:
            logger.error("Customer record without customer_id found.")
            continue
        
        if not check_customer_exists_in_stripe(customer_id):
            non_existing_customers.append(customer_id)
    
    logger.info(f"Total customers checked: {len(customers)}")
    logger.info(f"Non-existing customers in Stripe: {len(non_existing_customers)}")
    
    if non_existing_customers:
        logger.info("List of non-existing customer IDs:")
        for customer_id in non_existing_customers:
            logger.info(customer_id)
    else:
        logger.info("All customers exist in Stripe.")

if __name__ == "__main__":
    main()
