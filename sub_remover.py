import stripe
from dotenv import load_dotenv
import os
import logging

load_dotenv()
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, filename='subscription_removal_report.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

def cancel_all_subscriptions(customer_id):
    try:
        total_removed = 0

        # Cancel each scheduled subscription
        scheduled_subscriptions = stripe.SubscriptionSchedule.list(customer=customer_id)
        for scheduled_subscription in scheduled_subscriptions.auto_paging_iter():
            if stripe.SubscriptionSchedule.retrieve(scheduled_subscription.id).status == 'canceled':
                logging.info(f"Subscription schedule {scheduled_subscription.id} is already canceled.")
                
            elif stripe.SubscriptionSchedule.retrieve(scheduled_subscription.id).status == 'not_started':
                logging.info(f"Subscription schedule {scheduled_subscription.id} has not started yet.")
                stripe.SubscriptionSchedule.cancel(scheduled_subscription.id)
                total_removed += 1
                
            elif stripe.SubscriptionSchedule.retrieve(scheduled_subscription.id).status == 'active':
                logging.info(f"Subscription schedule {scheduled_subscription.id} is active. Cancelling now.")
                stripe.SubscriptionSchedule.cancel(scheduled_subscription.id)
                total_removed += 1
                
            try:
                stripe.SubscriptionSchedule.cancel(scheduled_subscription.id)
                total_removed += 1
            except:
                logging.error(f"Failed to cancel subscription schedule {scheduled_subscription.id}.")
            
        # Cancel each active subscription
        subscriptions = stripe.Subscription.list(customer=customer_id, status='all')
        for subscription in subscriptions.auto_paging_iter():
            stripe.Subscription.delete(subscription.id)
            total_removed += 1
            
        try:
            stripe.Subscription.delete(subscription.id)
            total_removed += 1
        except:
            logging.error(f"Failed to cancel subscription {subscription.id}.")
                
        if total_removed > 0:
            logging.info(f"All subscriptions (active and scheduled) cancelled for customer {customer_id}. Total removed: {total_removed}")
            return total_removed
        else:
            logging.info(f"No subscriptions found for customer {customer_id} to remove.")
            return 0
    except stripe.StripeError as e:
        # Handle Stripe API errors
        logging.error(f"Stripe API error occurred for customer {customer_id}: {e}")
        return 0
    except Exception as e:
        # Handle other errors
        logging.error(f"An error occurred for customer {customer_id}: {e}")
        return 0

def remove_subscriptions_from_all_customers():
    total_customers = 0
    total_subscriptions_removed = 0

    try:
        # Fetch all customers
        customers = stripe.Customer.list()

        # Cancel all subscriptions for each customer
        for customer in customers.auto_paging_iter():
            subs_removed = cancel_all_subscriptions(customer.id)
            total_customers += 1
            total_subscriptions_removed += subs_removed

        logging.info(f"Processed {total_customers} customers in total.")
        logging.info(f"Total subscriptions removed from all customers: {total_subscriptions_removed}")

        # Write the summary to a text file
        with open('summary_report.txt', 'w') as file:
            file.write(f"Total customers processed: {total_customers}\n")
            file.write(f"Total subscriptions removed: {total_subscriptions_removed}\n")
    except stripe.StripeError as e:
        # Handle Stripe API errors
        logging.error(f"Stripe API error occurred while processing all customers: {e}")
    except Exception as e:
        # Handle other errors
        logging.error(f"An error occurred while processing all customers: {e}")

# Example usage
remove_subscriptions_from_all_customers()
