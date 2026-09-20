# Builder response 1

I could inspect `artifact.md` and `attachments.json`. The attachments are represented as synthetic inline descriptions: a wildlife folder containing `fox-01.jpg`, `heron-02.heic`, and `fox-01-copy.jpg`, plus a location table in which `fox-01.jpg` has coordinates and `heron-02.heic` has no location. No actual image pixels, HEIC metadata, or CSV file were available, so image quality, visual relatedness, duplicate similarity, and coordinate handling have not been tested.

Before treating the recommendation as final, please answer these consequential choices:

1. What starts a run: a watched folder as soon as a batch arrives, a weekly scheduled run, or a button you press after selecting a folder?
2. Where should the phone review arrive: a private cloud album, a messaging channel, or another service you already use?
3. What are the defaults for portrait versus square, carousel size, and location safety: may a map show only a broad area, or should all location-derived cards be withheld until you approve them?

Provisional recommendation: use a small fixed workflow with a local intake step and a phone-based review album. A coding agent can build and validate the intake/packaging utility once, but recurring processing should run as bounded software with an explicit review gate. This keeps original JPEG and HEIC files read-only, makes exception handling repeatable, and avoids requiring an agent to improvise permissions during every weekly run. The service choice and visual defaults remain open until answered.

The first usable version should copy references into a run workspace, compute stable file identities, detect likely duplicates, read available location metadata, make contact-sheet previews, classify image quality and related sightings, draft carousel text and captions, and produce a review package. It must retain every input in an “exceptions” report when blurry, duplicated, locationless, or unmatched. A map card is generated only when the configured safety rule allows it; otherwise the location is redacted or marked for review. Delivery is a private draft album or equivalent review destination. Nothing is posted or deleted automatically.

This is a provisional plan based on the brief; processing and delivery have not occurred.
