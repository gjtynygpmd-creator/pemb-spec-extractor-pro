# Implement v1.5.0

1. Keep the current Netlify, Render, Neon, and Cloudflare services.
2. Extract this release.
3. Copy everything inside `pemb-spec-extractor-pro-v1.5.0` into the root of the existing GitHub repository, replacing matching files.
4. Commit to `main` with: `v1.5.0 core PEMB extraction`.
5. Allow the Render API, Render worker, and Netlify site to redeploy.
6. Confirm the Render build installs `reportlab==4.2.5`.
7. Verify the API health endpoint reports version `1.5.0`.
8. Open a project and confirm the new **Export PDF** button downloads an estimator summary.

No Neon migration or environment-variable changes are required.

Important: exports contain fields already captured by extraction or entered manually. If a project has zero extracted fields, click items in the Missing Information panel, enter confirmed values, save them, and export again.
