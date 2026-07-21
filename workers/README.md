# Processing Workers

This folder will contain the long-running document-processing services:

- PDF inspection and page rendering
- ZIP package expansion and validation
- OCR for image-only pages
- Drawing and sheet classification
- PEMB field extraction
- Conflict detection and normalization
- Excel and Zoho export generation

The workers will consume queued jobs created by the FastAPI backend.
