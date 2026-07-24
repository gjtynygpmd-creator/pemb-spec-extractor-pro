# Implement v1.5.1 Universal Field Finder

This release improves field capture from searchable pages and adds a fallback that recognizes common label/value tables even when a page is classified as `unclassified`.

## Deploy
1. Copy the contents of this release into the root of the existing GitHub repository and replace matching files.
2. Commit to `main` with `v1.5.1 universal field finder`.
3. Confirm the Netlify frontend and Render web service redeploy.
4. **Also open the separate Render background worker and confirm it redeploys from the same GitHub commit.** The API version alone does not prove the worker is running the new extraction code.
5. In the worker logs, confirm the startup message contains `PEMB processing worker v1.5.1 started`.
6. Open `/health` on the Render API and confirm `"version":"1.5.1"`.
7. Reopen the project and click **Start Analysis**. Existing zero-field results will not change until analysis is rerun.

## Expected benchmark behavior
For searchable PEMB design criteria, the completed job should report a nonzero field count. This release was locally checked against the available specification and structural samples and captured building-code, wind, snow, seismic, panel, framing, finish, opening, and accessory fields.

## No infrastructure changes
No database migration or new environment variables are required.
