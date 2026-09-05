# Temporary image slot verification

The bundled `TEMP_IMAGE_SLOT_TEST.webp` is a copy of an existing project image.

For a disposable local database only:
1. Start the backend once.
2. Run `python backend/seed_temp_image_slots.py`.
3. Refresh Home, Shop, Us and Gallery.
4. Every image-capable slot should show the same temporary image, with no former CSS artwork behind it.

Do not run this against a production database because it intentionally replaces image URLs for testing.
