# Image Slot Audit V1.13

Image-capable slots covered by the managed-image system:

- Home Hero
- Shop products (all active products)
- Us / Studio
- Us / Sound 1–3
- Gallery 1–5
- Live background

Behavior:
- Empty slot: only the image area/placeholder remains; former CSS illustration is not rendered for Home, Shop, or Us Studio.
- Custom image: uploaded image becomes the only visual content in the slot.
- Replacement: the previous managed image reference is replaced; orphaned local upload files can be pruned by the backend.
- Admin: every upload input has an explicit preview target.

Temporary verification:
`TEMP_IMAGE_SLOT_TEST.webp` is bundled.
`backend/seed_temp_image_slots.py` can assign it to all image slots in a disposable local database for verification. It also updates the products table because the public API reads active shop products from that table.
