# Implement v1.6.0 — Estimator Core

1. Deploy the backend/API from `backend` on Render.
2. Deploy the background worker separately from the same `backend` directory. Verify logs show `v1.6.0 Estimator Core`.
3. Deploy the `frontend` directory to Netlify.
4. Open the Marshall University project and upload both the specification manual and combined drawing set.
5. Run analysis again. Existing manual estimator entries are preserved.
6. Review the 32 quote-critical fields on the project dashboard and export **Estimator Input** XLSX.

Key changes: field-specific validation, drawing-aware source confidence, reduced false conflicts, exact bid-template field map, and narrative-text rejection for panels/accessories.
