# PEMB Spec Extractor Pro v0.3

## Added in v0.3
- Expanded PEMB-specific extraction library for architectural section notes and keynotes
- Primary rigid frame detection
- Purlin, girt, end-column, and bent-plate detection
- Roof and wall panel gauge extraction
- Exterior and interior door-cladding scope
- Mineral-wool, liner, cavity, and rigid-perimeter insulation extraction
- HDPE scrim liner and support-banding extraction
- Gutter, downspout, and eave-trim extraction
- Hydraulic-door and overhead-door detection
- PEMB contractor scope and metal-building-drawing coordination flags
- Rules are stored in `pemb-rules.json` so the field library can be expanded without rewriting the interface

## Current limitation
The static Netlify version can only analyze searchable PDF text. Image-only sheets still require the upcoming OCR/drawing-vision service.

## Test
Deploy this ZIP over v0.2, start a new project, upload searchable PDFs, and click Analyze Uploaded Files.
