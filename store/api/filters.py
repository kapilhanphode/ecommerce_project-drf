import django_filters
from store.models import Product

class CustomProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    expensive = django_filters.BooleanFilter(method='filter_expensive')

    def filter_expensive(self, queryset, name, value):
        if value:
            # http://127.0.0.1:8000/api/products/?expensive=true
            return queryset.filter(price__gt=100000, category__name="Laptop")
        return queryset

    class Meta:
        model = Product
        fields = ['category']