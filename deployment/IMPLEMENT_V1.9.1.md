# Deploy v1.9.1

Commit the release to GitHub. Allow both Render web service and worker to auto-deploy.

Recommended commit message:

`fix: prevent large drawing OCR from stalling analysis`

Optional Render worker environment variables:
- `OCR_DPI=140`
- `OCR_TIMEOUT_SECONDS=35`
- `OCR_MAX_PIXELS=12000000`
- `FORCE_DRAWING_OCR=false`

After both services are Live, reopen the existing project and click **Start Analysis**. Uploaded PDFs do not need to be uploaded again.
