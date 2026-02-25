from django.urls import path
from .views import ProductListCreateAPIView, ProductDetailAPIView
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, StaffOrderViewSet
# urlpatterns = [
#     path('products/', ProductListCreateAPIView.as_view(), name='product_list_create'),
#     path('products/<int:pk>/', ProductDetailAPIView.as_view(), name='product_detail'),
# ]

router = DefaultRouter()
router.register('products', ProductViewSet, basename='products')
router.register('orders', StaffOrderViewSet, basename='orders') # use this url for the 'Advance Permission Topic'

urlpatterns = router.urls