# # # restaurants/signals.py
# # from django.db.models.signals import pre_save, post_save
# # from django.dispatch import receiver
# # from django.db import transaction
# # from .models import Restaurant
# # from menu.services import build_menu_from_pdf

# # @receiver(pre_save, sender=Restaurant)
# # def _flag_pdf_change(sender, instance: Restaurant, **kwargs):
# #     if not instance.pk:
# #         instance._menu_pdf_changed = bool(instance.menu_pdf)
# #         return
# #     try:
# #         old = sender.objects.get(pk=instance.pk)
# #     except sender.DoesNotExist:
# #         instance._menu_pdf_changed = bool(instance.menu_pdf)
# #         return
# #     old_name = (old.menu_pdf.name or "")
# #     new_name = (instance.menu_pdf.name or "")
# #     instance._menu_pdf_changed = (old_name != new_name) and bool(new_name)

# # @receiver(post_save, sender=Restaurant)
# # def _process_pdf_after_save(sender, instance: Restaurant, **kwargs):
# #     if getattr(instance, "_menu_pdf_changed", False):
# #         # mark pending, then run after commit (file is safely written)
# #         sender.objects.filter(pk=instance.pk).update(menu_extract_status="pending", menu_extract_error="")
# #         def _go():
# #                 sender.objects.filter(pk=instance.pk).update(menu_extract_status="processing")
# #                 build_menu_from_pdf(instance)
# #         transaction.on_commit(_go)

# # restaurants/signals.py
# from django.db.models.signals import pre_save, post_save
# from django.dispatch import receiver
# from django.db import transaction
# from .models import Restaurant
# from restaurants.menu_extractor import OCREnhancedMenuExtractor
# import os
# from myapp import build_menu
# @receiver(post_save, sender=Restaurant)
# def _flag_pdf_change(sender, instance: Restaurant, created, **kwargs):
#     if created:
#        if instance.menu_pdf:
#            extractor = OCREnhancedMenuExtractor(debug=True, use_ocr=True)
#            items = extractor.extract_from_pdf(instance.menu_pdf)
#            output_dir = os.path.dirname(instance.menu_pdf.path)  # /.../media/restaurant_menu
#            # optional: make filename unique per restaurant
#            json_filename = f"menu_structured_{instance.id}.json"
#            output_path = os.path.join(output_dir, json_filename)
#            extractor.save_to_json(items, output_path) 
#            build_menu(json_filename=output_path,id=instance.id)  
#            print("created")
#     else:
#         if instance.menu_pdf:
#            extractor = OCREnhancedMenuExtractor(debug=True, use_ocr=True)
#            items = extractor.extract_from_pdf(instance.menu_pdf)
#            output_dir = os.path.dirname(instance.menu_pdf.path)  # /.../media/restaurant_menu
#            # optional: make filename unique per restaurant
#            json_filename = f"menu_structured_{instance.id}.json"
#            output_path = os.path.join(output_dir, json_filename)
#            extractor.save_to_json(items, output_path)   
#            build_menu(json_filename=output_path,id=instance.id)  
#            print("updated")

# restaurants/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from django.conf import settings
import os

from .models import Restaurant
from restaurants.menu_extractor import MenuExtractor
from myapp import build_menu_from_json  # << new import


@receiver(pre_save, sender=Restaurant)
def _flag_pdf_change(sender, instance: Restaurant, **kwargs):
    """
    Set a flag on the instance if menu_pdf has actually changed.
    So we don't re-run extraction on every save.
    """
    if not instance.pk:
        # New restaurant
        instance._menu_pdf_changed = bool(instance.menu_pdf)
        return

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._menu_pdf_changed = bool(instance.menu_pdf)
        return

    old_name = old.menu_pdf.name or ""
    new_name = instance.menu_pdf.name or ""
    instance._menu_pdf_changed = (old_name != new_name) and bool(new_name)

@receiver(post_save, sender=Restaurant)
def _process_pdf_after_save(sender, instance: Restaurant, **kwargs):
    """
    After Restaurant is saved,
    if menu_pdf changed, run extractor and rebuild MenuItems.
    """

    if not getattr(instance, "_menu_pdf_changed", False):
        return  # no change in PDF, nothing to do

    def _go():
        # This runs only after DB commit
        if not instance.menu_pdf:
            return

        pdf_path = instance.menu_pdf.path  # absolute path
        extractor = MenuExtractor()

        # 1) extract list[MenuItem] from PDF
        items = extractor.extract(pdf_path)

        # 2) save JSON next to the PDF
        output_dir = os.path.dirname(pdf_path)
        json_filename = f"menu_structured_{instance.id}.json"
        output_path = os.path.join(output_dir, json_filename)

        extractor.save_json(items, output_path)

        # 3) build MenuItem rows from JSON
        build_menu_from_json(json_filename=output_path, restaurant=instance)

        print(f"[signals] Menu rebuilt for restaurant {instance.id}")

    # ensure this runs only after transaction commit
    transaction.on_commit(_go)