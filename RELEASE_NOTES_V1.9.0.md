# v1.9.1 Field Test Notes

Primary objective: improve clean extraction from real drawings without adding a paid API dependency yet.

### Implemented from the extraction review PDF
- Real OCR fallback instead of skipping image/low-signal pages.
- OCR assistance for high-value drawing sheets even when embedded text exists.
- Meaningful-text routing instead of a 40-character cutoff.
- Coordinate-aware label/value pairing from native PDF blocks.
- Tight value windows for critical design-load regexes.
- Safer wind-speed matching (ultimate/basic only; nominal wind is not treated as basic wind).
- S1/Ss context protection against sheet-number false positives.
- Improved page and sheet classification.
- Correct fractional roof slope parsing (`3/8:12` -> `0.375:12`).

### Decatur smoke-test observations
Using the uploaded Decatur drawings/specs, the new engine correctly isolates examples including:
- 2021 International Building Code
- 112 mph ultimate wind speed
- 10 psf ground snow load
- 0.375:12 roof slope (from 3/8:12)
- 150 ft / 90 ft overall elevation dimensions as geometry candidates
- 20 ft eave-height candidate from elevation callouts

Risk category / exposure remain deliberately conservative when the PDF text/OCR cannot isolate a safe value. The engine should leave ambiguous data missing rather than inventing it.
