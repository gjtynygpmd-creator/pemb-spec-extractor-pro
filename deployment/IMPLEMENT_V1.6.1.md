# v1.6.1 Insulation Core

This release makes insulation specifications a first-class core estimating requirement.

## Added required fields
- Roof insulation type
- Roof insulation R-value
- Roof insulation thickness
- Roof insulation facing / vapor retarder
- Wall insulation type
- Wall insulation R-value
- Wall insulation thickness
- Wall insulation facing / vapor retarder

## Deployment
Commit the release contents to the connected GitHub repository. Render and Netlify should auto-deploy from the configured branch. After deployment, rerun analysis so existing projects are evaluated against the new field rules.
