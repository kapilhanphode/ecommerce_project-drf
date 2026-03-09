from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Sum, F, Avg, Case, When, Value, CharField, IntegerField, ExpressionWrapper, \
    DecimalField, Prefetch, Subquery, OuterRef, Q
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from store.services.order_service import OrderService
from store.models import Product, Order, OrderItem
from .exceptions import PriceTooLowException, success_response
from .permission import IsStaffUser, IsOwner, IsOwnerOrAdmin, CanEditDraftOrder
from .serializers import ProductSerializer, OrderSerializer
from .pagination import CustomPageNumberPagination, ProductCursorPagination
from .filters import CustomProductFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser, BasePermission, \
    SAFE_METHODS, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import LimitOffsetPagination
from django.views.decorators.cache import cache_page, never_cache
from django.core.cache import cache
from django.utils.decorators import method_decorator
import time
from django.shortcuts import get_object_or_404
from store.api.tasks import send_order_email


# Due to caching (timeout=30), updated product data will not be
# visible until the cache expires and new data is fetched from the database.
# class ProductListAPIView(APIView):
#     def get(self, request):
#         cache_key = "product_list"
#         data = cache.get(cache_key)
#         if not data:
#             products = Product.objects.all()
#             serializer = ProductSerializer(products, many=True)
#             data = serializer.data
#             cache.set(cache_key, data, timeout=30)
#         return Response(data)

# Version-based caching
class ProductListAPIView(APIView):
    def get(self, request):
        category_id = request.GET.get("category")

        if not category_id:
            return Response({"error": "category query param required"})

        # 🔹 Get category version
        version_key = f"category_{category_id}_version"
        version = cache.get(version_key)

        if not version:
            cache.set(version_key, 1)
            version = 1

        # 🔹 Build versioned cache key
        cache_key = f"product_list_category_{category_id}_v{version}"

        data = cache.get(cache_key)

        if not data:
            products = Product.objects.filter(category_id=category_id)
            serializer = ProductSerializer(products, many=True)
            data = serializer.data
            cache.set(cache_key, data, timeout=60)

        return Response({
            "version": version,
            "cache_key": cache_key,
            "data": data
        })


# update the price immediately but description after 30 sec
class ProductDetailAPIView(APIView):
    def get(self, request, pk):
        static_key = f"product_static_{pk}"
        static_data = cache.get(static_key)

        # 🔹 If static data not cached
        if not static_data:
            product = get_object_or_404(Product, pk=pk)

            static_data = {
                "name": product.name,
                "description": product.description,
            }

            cache.set(static_key, static_data, 30)

            # We already have product → reuse it
            price = product.price

        else:
            # 🔹 Only fetch dynamic fields
            dynamic_data = (
                Product.objects
                .filter(pk=pk)
                .values("price")
                .first()
            )

            if not dynamic_data:
                return Response({"error": "Product not found"}, status=404)

            price = dynamic_data["price"]

        return Response({
            **static_data,
            "price": price,
        })


@method_decorator(cache_page(30), name='dispatch')  # cache for 30 seconds
class TimeAPIView(APIView):
    def get(self, request):
        return Response({
            "time": time.time()
        })


class OrdersAnonThrottle(SimpleRateThrottle):
    scope = 'orders_anon'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return None
        return self.get_ident(request)


class OrderUserThrottle(SimpleRateThrottle):
    scope = 'orders_user'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated and not request.user.is_staff:
            return str(request.user.id)
        return None


class StaffOrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    # permission_classes = [IsStaffUser] #Allow access only if user belongs to a specific role (e.g., is_staff).
    # permission_classes = [IsAuthenticated, IsOwner] #User can only access objects that belong to them.
    permission_classes = [IsOwnerOrAdmin]  # Owner can access their object. Admin can access all.
    # permission_classes = [CanEditDraftOrder] #Owner can access their object. Admin can access all.
    # throttle_classes = [ScopedRateThrottle]
    throttle_classes = [OrdersAnonThrottle, OrderUserThrottle]
    throttle_scope = 'orders'
    # pagination_class = PageNumberPagination

    # Case / When
    # def get_queryset(self):
    #     # return Order.objects.annotate(status_label=Case(When(status='success', then=Value('Paid')),
    #     #                                                 When(status='pending', then=Value('Awaiting Payment')),
    #     #                                                 default=Value('Other'),
    #     #                                                 output_field=CharField()))
    #     discount_per = Order.objects.annotate(total_amount=Sum(F('items__price') * F('items__quantity'))
    #                                           ).annotate(
    #         discount_percentage=Case(When(total_amount__gt=35000, then=Value(10)),
    #                                  When(total_amount__gt=20000, then=Value(5)),
    #                                  default=Value(2),
    #                                  output_field=IntegerField()))
    #
    #     discount_amt = Order.objects.annotate(total_amount=Sum(F('items__price') * F('items__quantity'))
    #                                           ).annotate(
    #         discount_percentage=Case(When(total_amount__gt=35000, then=Value(10)),
    #                                  When(total_amount__gt=20000, then=Value(5)),
    #                                  default=Value(2),
    #                                  output_field=IntegerField())).annotate(
    #         discount_amount=ExpressionWrapper(F('total_amount') * F('discount_percentage') / 100,
    #                                           output_field=DecimalField(max_digits=12, decimal_places=2))
    #     )
    #     payable_amt = Order.objects.annotate(total_amount=Sum(F('items__price') * F('items__quantity'))
    #                                          ).annotate(
    #         discount_percentage=Case(When(total_amount__gt=35000, then=Value(10)),
    #                                  When(total_amount__gt=20000, then=Value(5)),
    #                                  default=Value(2),
    #                                  output_field=IntegerField())).annotate(
    #         discount_amount=ExpressionWrapper(F('total_amount') * F('discount_percentage') / 100,
    #                                           output_field=DecimalField(max_digits=12, decimal_places=2))).annotate(
    #         payable_amount=ExpressionWrapper(F('total_amount') - F('discount_amount'),
    #                                          output_field=DecimalField(max_digits=12, decimal_places=2)),
    #     )
    #     return payable_amt

    # prefetch
    # Return Orders
    # But prefetch ONLY bulk items (qty >= 5)
    # And annotate each order with total bulk quantity
    # def get_queryset(self):
    # #     # return Order.objects.select_related('user').prefetch_related(Prefetch('items',queryset=OrderItem.objects.filter(quantity__gt=1), to_attr='bulk_items'))
    #     bulk_items_qs = OrderItem.objects.filter(quantity__gte=5)
    # #     # Annotate total quantity items
    # #     # return (
    # #     #     Order.objects
    # #     #     .filter(status='success')
    # #     #     .annotate(total_bulk_qty=Sum('items__quantity'))
    # #     #     .prefetch_related(
    # #     #         Prefetch('items', queryset=bulk_items_qs, to_attr='bulk_items')
    # #     #     )
    # #     # )
    # #     # Annotate total bulk quantity only (not all items)
    #     return (
    #         Order.objects
    #         .filter(status='success')
    #         .annotate(
    #             total_bulk_qty=Sum(
    #                 'items__quantity',
    #                 filter=Q(items__quantity__gte=5)
    #             )
    #         )
    #         .prefetch_related(
    #             Prefetch(
    #                 'items',
    #                 queryset=bulk_items_qs,
    #                 to_attr='bulk_items'
    #             )
    #         )
    #     )

    # only & defer
    # def get_queryset(self):
    #     return Order.objects.select_related('user').only('id', 'user')

    # Subquery & OuterRef
    # def get_queryset(self):
    #     # Subquery 1: Latest item price per order
    #     latest_price_subquery = OrderItem.objects.filter(
    #         order=OuterRef('pk')
    #     ).order_by('-id').values('price')[:1]
    #
    #     # Subquery 2: Total quantity per order
    #     total_qty_subquery = OrderItem.objects.filter(
    #         order=OuterRef('pk')
    #     ).values('order').annotate(
    #         total_qty=Sum('quantity')
    #     ).values('total_qty')
    #
    #     return Order.objects.annotate(
    #         latest_item_price=Subquery(latest_price_subquery),
    #         total_quantity=Subquery(total_qty_subquery)
    #     )

    # def get_queryset(self):
    # annotate()
    # return Order.objects.annotate(total_item=Count('items'),total_amount=Sum(F("items__price") * F('items__quantity')))
    # annotate + filter
    # return Order.objects.annotate(total_items=Count('items')).filter(total_items__gt=2)
    # Conditional Count Using filter = inside Count
    # return Order.objects.filter(status='success').annotate(total_items=Count('items'))
    # Conditional Sum()
    # return Order.objects.filter(status='pending').annotate(total_amount=Sum('items__price'))

    # def list(self, request, *args, **kwargs):
    #     # aggregate()
    #     queryset = self.get_queryset()
    #     serializer = self.get_serializer(queryset, many=True)
    #     summary = Order.objects.aggregate(total_orders=Count('id'), total_items=Sum('items__quantity'),
    #                                    total_revenue=Sum(F('items__price') * F('items__quantity')))
    #     return Response({
    #         "orders": serializer.data,
    #         "summary": summary
    #     })

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def pay(self, request, pk=None):
        updated = Order.objects.filter(
            id=pk,
            status="pending"
        ).update(status="success")

        if updated == 0:
            return Response({"message": "Already Processed"})

        return Response({"message": "Payment Successful"})

    def get_throttles(self):
        throttles = super().get_throttles()
        # for t in throttles:
        #     print(f'Throttle>>>>>>>>>>>>>>>>>: {t.__class__.__name__} limit={getattr(t, "rate", None)}')
        return throttles

    # Dynamic Permission Per Action
    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAuthenticated()]
        return [AllowAny()]

    def destroy(self, request, *args, **kwargs):
        order = self.get_object()

        if order.status in ["success", "pending", "shipped", "delivered"]:
            raise PermissionDenied(
                "Only cancelled or other state orders can be deleted."
            )
        if request.user != order.user and not request.user.is_staff:
            raise PermissionDenied(
                "You do not have permission to delete this order."
            )

        return super().destroy(request, *args, **kwargs)

    # to get the only user records in the list view.
    # def get_queryset(self):
    #     # admin can see all record normal user can see their own records
    #     if self.request.user.is_staff:
    #         return Order.objects.all()
    #     return Order.objects.filter(user=self.request.user)


    def perform_create(self, serializer):
        items = self.request.data.get("items")
        print('items......................',items)
        order = OrderService.create_order(
            user=self.request.user,
            items=items
        )
        serializer.instance = order


class IsSellerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return obj.seller == request.user


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # permission_classes = [IsSellerOrAdmin]
    pagination_class = LimitOffsetPagination
    filterset_fields = ['category', 'price']
    # filterset_class = CustomProductFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price']
    # permission_classes = [IsAdminUser]

    def list(self, request, *args, **kwargs):
        products = self.get_queryset()

        serializer = self.get_serializer(products, many=True)

        if request.version == "v1":
            return Response({
                "version": "v1",
                "data": serializer.data
            })

        if request.version == "v2":
            return Response({
                "version": "v2",
                "total_products": products.count(),
                "data": serializer.data
            })

    def perform_create(self, serializer):
        price = serializer.validated_data.get('price')
        if price <= 10:
            raise PriceTooLowException
            # raise ValidationError({
            #     "price": "Price must be greater than 10."
            # })
        product = serializer.save()
        send_order_email.delay(product.id)
        serializer.instance = product

class ProductListCreateAPIView(ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]


# class ProductDetailAPIView(RetrieveUpdateDestroyAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializer
#     permission_classes = [IsAuthenticated]


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_staff
