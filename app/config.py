# config.py
import os

class Config:
    # secrets
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

    # testing
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'default_stripe_secret_key')
    WEBHOOK_SIGNING_SECRET = os.getenv('WEBHOOK_SIGNING_SECRET', 'default_webhook_signing_secret')
    SUCCESS_URL = os.getenv('SUCCESS_URL', 'default_success_url')
    CANCEL_URL = os.getenv('CANCEL_URL', 'default_cancel_url')

    # sendgrid
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', 'default_sendgrid_api_key')
    
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'default_company_name')
    STAFF_EMAIL = os.getenv('COMPANY_EMAIL', 'default_company_email')
    SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'default_support_email')
    
    ENDPOINT_URL = os.getenv('ENDPOINT_URL', 'default_endpoint_url')
    
    UPDATE_PAYMENT_TEMPLATE_ID = os.getenv('UPDATE_PAYMENT_TEMPLATE_ID', 'default_update_payment_template_id')

    # database
    DATABASE_URL = os.getenv('DATABASE_URL', 'default_database_url')
