from django.db import transaction
from store.models import Order, OrderItem, Product


class OrderService:

    @staticmethod
    @transaction.atomic
    def create_order(user, items):
        order = Order.objects.create(user=user)
        product_ids = [item["product_id"] for item in items]
        products = Product.objects.filter(id__in=product_ids)
        product_map = {p.id: p for p in products}
        order_items = []

        for item in items:
            product = product_map[item["product_id"]]
            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    price=product.price,
                    quantity=item["quantity"]
                )
            )
        OrderItem.objects.bulk_create(order_items)

        return order