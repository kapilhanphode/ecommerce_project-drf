from rest_framework import serializers
from store.models import Product, Category, ProductImage

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'color']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    images = ProductImageSerializer(many=True)

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "category", "images"]

    def create(self, validated_data):
        category = validated_data.pop('category')
        images = validated_data.pop('images')

        category, created = Category.objects.get_or_create(
            slug=category.get('slug'),
            defaults={'name': category.get('name')}
        )

        product = Product.objects.create(
            category=category,
            **validated_data
        )
        for image in images:
            ProductImage.objects.create(product=product, **image)
        return product

    # def update(self, instance, validated_data):
    #     images = validated_data.pop('images')
    #     for attr, value in validated_data.items():
    #         print('instance...............................', instance)
    #         print('attr and value.........................', attr, value)
    #         setattr(instance, attr, value)
    #     instance.save()
    #     if images is not None:
    #         instance.images.all().delete()
    #         for image in images:
    #             ProductImage.objects.create(product=instance, **image)
    #     return instance

    def update(self, instance, validated_data):
        category = validated_data.pop('category')
        images = validated_data.pop('images')

        instance.name = validated_data.get('name', instance.name)
        instance.price = validated_data.get('price', instance.price)
        instance.description = validated_data.get('description', instance.description)
        if category:
            category, created = Category.objects.get_or_create(
                slug=category.get('slug'),
                defaults={'name': category.get('name')}
            )
            instance.category = category
        for image in images:
            ProductImage.objects.create(product=instance, **image)

        instance.save()
        return instance