from celery import shared_task

@shared_task
def send_order_email(product_id):
    print(f'send_order_email running for Product >>>>>>>>>>>>>>!!!!!!!#{product_id}')