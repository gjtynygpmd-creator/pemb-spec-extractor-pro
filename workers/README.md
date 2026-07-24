# Processing Worker — v1.9.1

The production worker lives at `backend/app/worker.py` and is started by Render with:

```bash
python -m app.worker
```

v1.9.1 adds a two-path document intelligence pipeline:

- rich specification text uses the existing fast extraction/value engine;
- drawing and low-signal pages are rendered and OCR-assisted with Tesseract;
- native PDF text blocks retain coordinates for spatial label/value pairing;
- every candidate is still validated and normalized by the PEMB estimator rules before persistence.

This release requires no new API key. A paid document/vision service can be added later as a third path without replacing the estimator validation engine.
