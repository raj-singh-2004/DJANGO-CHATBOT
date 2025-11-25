# menu/services.py
import os, json
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django.core.files.base import ContentFile
from .models import MenuItem
from restaurants.menu_extractor import extract_menu_to_json  # <- function import

def _coerce(row: dict):
    name = (row.get("name") or "").strip()
    if not name:
        raise ValueError("Missing 'name'")
    try:
        price = Decimal(str(row.get("price", 0)))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid price for '{name}'")
    return name, {
        "price": price,
        "currency": (row.get("currency") or "INR")[:3].upper(),
        "category": row.get("category") or "",
        "description": row.get("description") or "",
        "is_vegetarian": bool(row.get("is_vegetarian", False)),
        "is_vegan": bool(row.get("is_vegan", False)),
        "ingredients": list(row.get("ingredients") or []),
        "available": bool(row.get("available", True)),
    }

def build_menu_from_pdf(restaurant, *, save_json_to_field=True, purge_missing=False):
    if not restaurant.menu_pdf:
        return {"created": 0, "updated": 0, "skipped": 0, "json_path": None}

    pdf_path = restaurant.menu_pdf.path
    out_dir = os.path.join(settings.BASE_DIR, "menu")
    os.makedirs(out_dir, exist_ok=True)
    json_name = f"{slugify(restaurant.name)}-{restaurant.pk}.json"
    json_path_fs = os.path.join(out_dir, json_name)

    try:
        # 1) Extract
        items = extract_menu_to_json(pdf_path, json_path_fs) or []
        if isinstance(items, dict) and "items" in items:
            items = items["items"]

        # 2) Upsert
        created = updated = skipped = 0
        with transaction.atomic():
            for row in items:
                try:
                    name, defaults = _coerce(row)
                    _, was_created = MenuItem.objects.update_or_create(
                        restaurant=restaurant, name=name, defaults=defaults
                    )
                    created += int(was_created)
                    updated += int(not was_created)
                except Exception:
                    skipped += 1

        # 3) Save JSON snapshot (optional)
        if save_json_to_field:
            try:
                json_bytes = json.dumps(items, ensure_ascii=False, indent=2, default=str).encode("utf-8")
                restaurant.menu_json.save(json_name, ContentFile(json_bytes), save=False)
            except Exception as e:
                # Don’t fail the whole pipeline for snapshot issues
                restaurant.menu_extract_error = f"JSON snapshot failed: {e}"

        # 4) ✅ Flip status to succeeded
        restaurant.menu_extract_status = "succeeded"
        restaurant.menu_last_extracted_at = timezone.now()
        # clear any previous error unless we set a snapshot warning above
        restaurant.menu_extract_error = getattr(restaurant, "menu_extract_error", "") or ""
        restaurant.save(update_fields=[
            "menu_json",
            "menu_extract_status",
            "menu_last_extracted_at",
            "menu_extract_error",
            "updated_at",
        ])

        return {"created": created, "updated": updated, "skipped": skipped, "json_path": json_path_fs}

    except Exception as e:
        # ✅ Ensure failures aren’t stuck at "processing"
        restaurant.menu_extract_status = "failed"
        restaurant.menu_extract_error = f"{type(e).__name__}: {e}"
        restaurant.save(update_fields=["menu_extract_status", "menu_extract_error", "updated_at"])
        raise
