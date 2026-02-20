from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register('viewset/manual-products', ProductManualViewSet, basename='manual')
router.register('viewset/readonly-products', ProductReadOnlyViewSet, basename='readonly')
router.register('viewset/model-products', ProductModelViewSet, basename='model')

urlpatterns = [

    # APIView
    path('apiview/products/', ProductAPIView.as_view()),
    path('apiview/products/<int:pk>/', ProductDetailAPIView.as_view()),

    # Generics
    path('generic/list/', ProductListView.as_view()),
    path('generic/create/', ProductCreateView.as_view()),
    path('generic/<int:pk>/', ProductRetrieveView.as_view()),
    path('generic/<int:pk>/update/', ProductUpdateView.as_view()),
    path('generic/<int:pk>/delete/', ProductDeleteView.as_view()),

    path('generic/list-create/', ProductListCreateView.as_view()),
    path('generic/rud/<int:pk>/', ProductRetrieveUpdateDestroyView.as_view()),

] + router.urls