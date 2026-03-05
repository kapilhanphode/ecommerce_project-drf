from django.db import transaction
from store.models import Order, OrderItem, Product

class OrderService:

    @staticmethod
    @transaction.atomic
    def create_order(user, items):

        order = Order.objects.create(user=user)
        print('order.................',order)
        for item in items:

            product = Product.objects.get(id=item["product_id"])

            OrderItem.objects.create(
                order=order,
                product=product,
                price=product.price,
                quantity=item["quantity"]
            )

        return order