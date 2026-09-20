# WF-2 baseline response 1

I can specify an event-driven weekly wildlife-photo workflow, but several choices change the outputs and privacy behavior. Please decide:

1. **Carousel format:** square (1:1), portrait (4:5), or both? What maximum photos per pack?
2. **Phone delivery:** a local phone-sync folder, a named cloud drive, or another method?
3. **Location privacy:** should map end cards use an approximate area (recommended), exact coordinates only with explicit approval, or never show location? Should GPS metadata be stripped from exports?
4. **Retention:** how long should generated packs and review exceptions be kept, and where should originals remain?

Proposed defaults if you want me to proceed without further choices: portrait 4:5, 8 photos per pack, a review folder ready for phone sync, approximate map area only, strip GPS from shared exports, retain generated packs and exceptions for 30 days, and preserve originals indefinitely without overwrite or deletion.

## Current workflow outline (proposed, not verified)

- Watch an intake folder and enqueue new photos automatically.
- Preserve originals as read-only inputs; never delete or overwrite them.
- Extract capture time, GPS presence, dimensions, and file identity; flag missing metadata.
- Group by time and likely scene/species, detect duplicates, and route blurry or ambiguous items to a review queue.
- Generate candidate crops and resized exports after the format choice; attach captions/metadata suggestions.
- Add a map end card only when location is available and passes the selected privacy rule; otherwise omit it.
- Write packs and exceptions to a review area for phone inspection and approval before sharing.

The supplied fixtures imply one GPS-bearing fox image and one blurry, GPS-free heron image. They do not establish grouping quality, crop quality, privacy safety, phone delivery, or successful processing.
