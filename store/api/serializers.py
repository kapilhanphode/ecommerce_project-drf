from rest_framework import serializers
from store.models import Product, Category, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "category"]

    def create(self, validated_data):
        category = validated_data.pop('category')
        # images = validated_data.pop('images')

        category, created = Category.objects.get_or_create(
            slug=category.get('slug'),
            defaults={'name': category.get('name')}
        )

        product = Product.objects.create(
            category=category,
            **validated_data
        )
        return product


    def update(self, instance, validated_data):
        category = validated_data.pop('category')

        instance.name = validated_data.get('name', instance.name)
        instance.price = validated_data.get('price', instance.price)
        instance.description = validated_data.get('description', instance.description)
        if category:
            category, created = Category.objects.get_or_create(
                slug=category.get('slug'),
                defaults={'name': category.get('name')}
            )
            instance.category = category
        instance.save()
        return instance