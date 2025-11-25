# menu/management/commands/generate_embeddings.py
"""
Django management command to generate embeddings from MenuItem database.

Usage:
    python manage.py generate_embeddings
    python manage.py generate_embeddings --restaurant-id 1
    python manage.py generate_embeddings --output-dir /path/to/embeddings
"""

import json
import numpy as np
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from sentence_transformers import SentenceTransformer

from menu.models import MenuItem


class Command(BaseCommand):
    help = 'Generate embeddings for menu items for AI-powered chatbot'

    def add_arguments(self, parser):
        parser.add_argument(
            '--restaurant-id',
            type=int,
            help='Generate embeddings for specific restaurant only',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='.',
            help='Directory to save embeddings (default: project root)',
        )
        parser.add_argument(
            '--model',
            type=str,
            default='sentence-transformers/all-mpnet-base-v2',
            help='Sentence transformer model to use',
        )

    def handle(self, *args, **options):
        restaurant_id = options.get('restaurant_id')
        output_dir = Path(options['output_dir'])
        model_name = options['model']

        # Create output directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build queryset
        qs = MenuItem.objects.filter(available=True)
        self.stdout.write("yes")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)
            self.stdout.write(f"Filtering by restaurant_id={restaurant_id}")
            self.stdout.write("yes")

        # Extract text chunks
        self.stdout.write("Extracting menu items...")
        chunks = []
        item_ids = []
        
        for item in qs.select_related('restaurant'):
            text = f"Category: {item.category}. Item: {item.name}. Price: {item.price}"
            chunks.append(text)
            item_ids.append(item.id)

        if not chunks:
            msg = (
                "No menu items found for embeddings! "
                "This may happen if no MenuItem.objects.filter(available=True)"
                f" exist for restaurant_id={restaurant_id}."
            )
            self.stdout.write(self.style.WARNING(msg))
            # Don't crash – just skip
            return

        self.stdout.write(self.style.SUCCESS(f"✓ Extracted {len(chunks)} menu items"))

        # Load model and generate embeddings
        self.stdout.write(f"Loading model: {model_name}...")
        model = SentenceTransformer(model_name)
        
        self.stdout.write("Generating embeddings...")
        embeddings = model.encode(chunks, convert_to_numpy=True, show_progress_bar=True)

        # Save embeddings
        embeddings_path = output_dir / "menu_embeddings.npy"
        np.save(embeddings_path, embeddings)
        self.stdout.write(self.style.SUCCESS(f"✓ Saved: {embeddings_path}"))
        self.stdout.write(f"  Shape: {embeddings.shape}")

        # Save text chunks
        chunks_path = output_dir / "text_chunks.json"
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        self.stdout.write(self.style.SUCCESS(f"✓ Saved: {chunks_path}"))

        # Save metadata (mapping chunk index to MenuItem ID)
        metadata_path = output_dir / "embedding_metadata.json"
        metadata = {
            "model": model_name,
            "total_items": len(chunks),
            "restaurant_id": restaurant_id,
            "item_ids": item_ids,  # Maps index → MenuItem.id
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        self.stdout.write(self.style.SUCCESS(f"✓ Saved: {metadata_path}"))

        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("✅ Embeddings generated successfully!"))
        self.stdout.write("="*50)
        self.stdout.write(f"Items processed: {len(chunks)}")
        self.stdout.write(f"Embedding dimensions: {embeddings.shape[1]}")
        self.stdout.write(f"Output directory: {output_dir.absolute()}")
        self.stdout.write("\nNext steps:")
        self.stdout.write("1. Make sure GROQ_API_KEY is set in your .env")
        self.stdout.write("2. Update chatbot/engine.py paths if needed")
        self.stdout.write("3. Test: python manage.py runserver")
        self.stdout.write("4. Try: curl -X POST http://localhost:8000/api/chatbot/simple/ \\")
        self.stdout.write('     -H "Content-Type: application/json" \\')
        self.stdout.write('     -d \'{"restaurant_id": 1, "message": "I want something spicy"}\'')
