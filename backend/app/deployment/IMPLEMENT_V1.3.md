# Implement v1.3 Estimator Review Alpha

No Neon database migration is required for this release.

1. Upload the contents of this package to the existing GitHub repository, replacing the existing project files while preserving the repository itself.
2. Commit the update to the `main` branch with the message `v1.3 estimator review alpha`.
3. Render will automatically redeploy both the web API and the background worker from the same commit.
4. Netlify will automatically redeploy the frontend from the same commit.
5. Wait until both Render services show Live and Netlify shows Published.
6. Open an existing analyzed project and test editing a field, accepting a field, resolving a conflict, and filling a missing item.

## Verification
- API health reports version 1.3.0.
- Existing extracted fields appear as review cards.
- Clicking a card opens the source-and-edit drawer.
- Saving an edited value persists after refresh.
- Missing required items can be manually entered.
