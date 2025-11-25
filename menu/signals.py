# # menu/signals.py
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from django.db import transaction

# from .models import MenuItem
# from .tasks import regenerate_menu_embeddings


# @receiver(post_save, sender=MenuItem)
# def menuitem_saved(sender, instance: MenuItem, created, **kwargs):
#     """
#     When a MenuItem is created or updated, enqueue a Celery task
#     to regenerate embeddings for THAT restaurant's menu.

#     Wrapped in transaction.on_commit so it only runs after the DB
#     transaction is successfully committed.
#     """
#     restaurant_id = getattr(instance, "restaurant_id", None)
#     if not restaurant_id:
#         return

#     def enqueue_task():
#         print(f"[Signals] MenuItem saved, scheduling embeddings regen for restaurant_id={restaurant_id}")
#         regenerate_menu_embeddings.delay(restaurant_id=restaurant_id)

#     transaction.on_commit(enqueue_task)


# @receiver(post_delete, sender=MenuItem)
# def menuitem_deleted(sender, instance: MenuItem, **kwargs):
#     """
#     When a MenuItem is deleted, also regenerate embeddings for that restaurant.
#     """
#     restaurant_id = getattr(instance, "restaurant_id", None)
#     if not restaurant_id:
#         return

#     def enqueue_task():
#         print(f"[Signals] MenuItem deleted, scheduling embeddings regen for restaurant_id={restaurant_id}")
#         regenerate_menu_embeddings.delay(restaurant_id=restaurant_id)

#     transaction.on_commit(enqueue_task)
