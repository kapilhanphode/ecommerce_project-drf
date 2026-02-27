from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from store.models import Product

# delete cache based on save and delete
# @receiver(post_save, sender=Product)
# def clear_product_cache_on_save(sender, instance, created, **kwargs):
#     print("Signal triggered for product:>>>>>>>>>>>>>>>>>>>>>>>", instance.pk)
#     cache.delete(f"product_static_{instance.pk}")
#     cache.delete("product_list")
#
# @receiver(post_delete, sender=Product)
# def clear_product_cache_on_delete(sender, instance, **kwargs):
#     cache.delete(f"product_static_{instance.pk}")
#     cache.delete("product_list")


# Version-based caching
@receiver(post_save, sender=Product)
def bump_category_version_on_save(sender, instance, **kwargs):
    version_key = f"category_{instance.category_id}_version"
    print('cache......................',cache.get(version_key))
    if cache.get(version_key):
        cache.incr(version_key)
    else:
        cache.set(version_key, 1)

    print(f"Version bumped for category>>>>>>>>>> {instance.category_id}")


@receiver(post_delete, sender=Product)
def bump_category_version_on_delete(sender, instance, **kwargs):
    version_key = f"category_{instance.category_id}_version"

    if cache.get(version_key):
        cache.incr(version_key)