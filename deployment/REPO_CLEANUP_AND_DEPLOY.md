# Repo cleanup and deploy (v1.9.4)

Your GitHub repo picked up ~95 stray files from repeated web uploads (numbered duplicates,
loose copies of backend files at the repo root, pytest cache files, and a committed zip).
The reliable fix is to replace the entire repo contents with this clean tree in ONE commit,
which preserves your history and your Render connection.

Do NOT use GitHub's web "Add file / Upload files" for this; that is what created the mess.
Use one of the two methods below.

Important: never delete the hidden `.git` folder. It holds your history and the GitHub link.

--------------------------------------------------------------------------------
METHOD A - GitHub Desktop (easiest, no command line)
--------------------------------------------------------------------------------
1. Install GitHub Desktop and sign in.
2. File > Clone repository > pick gjtynygpmd-creator/pemb-spec-extractor-pro. Note the
   local folder it clones to.
3. Open that local folder in Finder (Mac) or File Explorer (Windows). Turn on "show hidden
   files" so you can see the `.gitignore` later.
4. Select everything in the folder EXCEPT the hidden `.git` folder, and delete it.
5. Unzip the clean package. Copy ALL of its contents (the folders backend, database,
   deployment, docs, frontend, schema, tests, workers and the files README.md,
   CHANGELOG.md, .gitignore) into the repo folder so they sit at the top level, next to
   `.git`. Make sure `.gitignore` comes across (hidden files must be visible).
6. Back in GitHub Desktop you will see a large list of changes. Enter a summary like
   "Clean repo + v1.9.4 hardening", click Commit to main, then Push origin.

--------------------------------------------------------------------------------
METHOD B - git command line
--------------------------------------------------------------------------------
Run these from a terminal. Replace /path/to/clean with wherever you unzipped the package.

    git clone https://github.com/gjtynygpmd-creator/pemb-spec-extractor-pro.git
    cd pemb-spec-extractor-pro
    git checkout main && git pull

    # Delete everything tracked/working except the .git folder
    # Mac/Linux:
    find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
    # Windows PowerShell equivalent:
    #   Get-ChildItem -Force -Exclude '.git' | Remove-Item -Recurse -Force

    # Copy the clean tree's CONTENTS into the repo root (note the trailing /. )
    cp -R /path/to/clean/. .

    git add -A
    git commit -m "Clean repo: remove duplicates/cache, add v1.9.4 hardening"
    git push origin main

--------------------------------------------------------------------------------
After the push
--------------------------------------------------------------------------------
1. Render auto-deploys `main`. Open the worker service > Logs and confirm the start line:
   "PEMB processing worker v1.9.4 Hardened Schema-Driven started".
2. The build uses Root Directory `backend` and `backend/Dockerfile` (your confirmed
   settings). Nothing about that changes here.
3. Stuck job: you do not need to touch the database. Once the new worker is live, its
   recovery sweep re-queues or fails any job stuck in "processing" after WORKER_STALE_SECONDS.

--------------------------------------------------------------------------------
Environment variables (optional - safe defaults exist)
--------------------------------------------------------------------------------
Every setting has a default in config, so the worker runs correctly with only your current
vars (DATABASE_URL, S3_*, CORS_ORIGINS, OPENAI_API_KEY). Set any of these on the worker
service only if you want to tune behavior:

    VISION_DPI=200              # lower (e.g. 150) trades small-text legibility for less cost/memory
    VISION_MAX_PAGES_PER_JOB=300  # cap vision calls per job to bound cost/time on huge sets
    WORKER_MAX_ATTEMPTS=3       # retries before a stuck job is failed
    VISION_TIMEOUT_SECONDS=60   # per-call network timeout
    PAGE_TIMEOUT_SECONDS=120    # hard per-page wall-clock guard
    VISION_PROVIDER=openai      # you are on openai; switch to anthropic only with an
                                # Anthropic Console API key (separate from a Claude.ai plan)

Since your worker is now on the Standard plan (2 GB) and renders are edge-capped to a few MB
per page, the defaults are safe; you do not need to lower VISION_DPI or the page cap unless
you want to reduce API cost.
