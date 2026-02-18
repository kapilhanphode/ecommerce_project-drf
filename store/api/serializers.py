from rest_framework import serializers
from store.models import Product, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.ReadOnlyField(source='seller.username')
    category = CategorySerializer()

    class Meta:
        model = Product
        fields = ['id', 'name', 'seller', 'description', 'price', 'category']

    def validate_price(self, value):
        print('validate_price....................')
        if value <= 10:
            raise serializers.ValidationError("Price must be greater than 10.")
        return value

    def validate_name(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Name must be at least 5 characters long.")
        return value

    def create(self, validated_data):
        category_data = validated_data.pop('category')

        category, created = Category.objects.get_or_create(
            name=category_data['name']
        )
        product = Product.objects.create(
            category=category,
            **validated_data
        )
        return product

    def update(self, instance, validated_data):
        category_data = validated_data.pop('category', None)
        if category_data:
            category, created = Category.objects.get_or_create(
                name=category_data['name']
            )
            instance.category = category
        return super().update(instance, validated_data)

    # def validate(self, data):
    #     price = data.get('price', self.instance.price if self.instance else None)
    #     category = data.get('category', self.instance.category if self.instance else None)
    #
    #     if price and category:
    #         if price > 100000 and category.name == "Mobile":
    #             raise serializers.ValidationError(
    #                 "Mobile category products cannot exceed 100000."
    #             )
    #
    #     return data

    # def create(self, validated_data):
    #     user = self.context['request'].user
    #     validated_data['seller'] = user
    #     return super().create(validated_data)
