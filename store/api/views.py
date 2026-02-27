from django.core.paginator import Paginator
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from store.models import Product, Order
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


#update the price immediately but description after 30 sec
class ProductDetailAPIView(APIView):
    def get(self, request, pk):
        static_key = f"product_static_{pk}"
        print('static_key.......................', static_key)
        static_data = cache.get(static_key)
        print('static_data.........................',static_data)

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
    print('Order anon throttle.............................')
    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return None
        return self.get_ident(request)

class OrderUserThrottle(SimpleRateThrottle):
    scope = 'orders_user'
    print('Order User throttle...........................')
    def get_cache_key(self, request, view):
        if request.user.is_authenticated and not request.user.is_staff:
            return str(request.user.id)
        return None
class StaffOrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    # permission_classes = [IsStaffUser] #Allow access only if user belongs to a specific role (e.g., is_staff).
    # permission_classes = [IsAuthenticated, IsOwner] #User can only access objects that belong to them.
    permission_classes = [IsOwnerOrAdmin] #Owner can access their object. Admin can access all.
    # permission_classes = [CanEditDraftOrder] #Owner can access their object. Admin can access all.
    # throttle_classes = [ScopedRateThrottle]
    throttle_classes = [OrdersAnonThrottle, OrderUserThrottle]
    throttle_scope = 'orders'
    # pagination_class = PageNumberPagination



    def get_throttles(self):
        throttles = super().get_throttles()
        for t in throttles:
            print(f'Throttle>>>>>>>>>>>>>>>>>: {t.__class__.__name__} limit={getattr(t, "rate", None)}')
        return throttles

    #Dynamic Permission Per Action
    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminUser()]
        return [AllowAny()]

    # to get the only user records in the list view.
    # def get_queryset(self):
    #     # admin can see all record normal user can see their own records
    #     if self.request.user.is_staff:
    #         return Order.objects.all()
    #     return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        print('perform create.......................')
        serializer.save(user=self.request.user)

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
    filter_backends = [DjangoFilterBackend,SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price']
    # permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        print('perform_create.............................')
        price  = serializer.validated_data.get('price')
        if price <= 10:
            raise ValueError("Price must be greater than 10.")
        serializer.save(price=price)


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

