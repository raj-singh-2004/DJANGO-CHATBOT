# menu/tasks.py
from celery import shared_task
from django.core.management import call_command
from django.core.management.base import CommandError


@shared_task
def regenerate_menu_embeddings(restaurant_id=None):
    """
    Regenerate menu_embeddings.npy + text_chunks.json from the DB
    and reload them into the chatbot RAG engine.

    Usually called after menu extraction (PDF -> MenuItem) completes.
    """
    from chatbot.engine import reload_rag_system
    from menu.models import MenuItem

    # 🔹 Safety: if a restaurant_id is provided but has no available items,
    # just skip instead of raising CommandError from the management command.
    if restaurant_id is not None:
        has_items = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            available=True,
        ).exists()
        if not has_items:
            print(
                f"[Celery] Skip regen: no available MenuItem for restaurant_id={restaurant_id}"
            )
            return

    try:
        # 1) Regenerate embeddings file from DB
        call_command(
            "generate_embeddings",
            restaurant_id=restaurant_id,
            output_dir=".",  # same as your EMBEDDINGS_PATH/CHUNKS_PATH
        )
    except CommandError as e:
        # Don't crash the worker, just log and exit
        print(f"[Celery] generate_embeddings failed: {e}")
        return

    # 2) Reload into memory for chatbot
    reload_rag_system()
    print(f"[Celery] Regenerated embeddings for restaurant_id={restaurant_id}")
