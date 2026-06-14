You are helping prepare a clean git commit for the PenguWave project. The user will do the actual git commands themselves — your job is to get everything ready and give them the exact commands to copy-paste.

Follow these steps every time:

## Step 1 — Safety check
Run `git status` and scan the output. Flag immediately if any of these appear:
- `.env` files
- Files containing passwords, tokens, or API keys
- `venv/`, `node_modules/`, `__pycache__/` directories

If anything dangerous is staged or untracked without a .gitignore entry, fix the .gitignore BEFORE continuing.

## Step 2 — Assess what changed
Read `git status` and `git diff --stat HEAD` to understand what files changed. Group them into logical units (e.g. "auth router", "database setup", "seed script").

## Step 3 — Decide on commit grouping
Follow the assignment rule: small, clear commits — one per logical unit of work. If multiple unrelated things changed, tell the user to commit them separately and give a commit message for each group.

## Step 4 — Verify .gitignore coverage
Check that `.gitignore` exists and covers at minimum:
- `backend/.env`
- `backend/venv/`
- `backend/__pycache__/`
- `.DS_Store`
- `node_modules/`

Add any missing entries.

## Step 5 — Give the user exact commands
Output a numbered list of copy-paste terminal commands, like this format:

```bash
# Stage these specific files (never use git add . without listing what's included)
git add backend/docker-compose.yml backend/requirements.txt backend/.gitignore backend/.env.example

# Check nothing secret snuck in
git status

# Commit
git commit -m "Add backend scaffolding: FastAPI + MongoDB docker-compose setup"

# Push to your branch
git push
```

Rules for commit messages (from the assignment):
- Say WHAT changed, not just "fix" or "stuff"
- Format: `<verb> <what>: <brief detail>` — e.g. "Add auth router: JWT login and logout endpoints"
- Keep it under 72 characters

## Step 6 — Remind about the PR
If the user says they are done with a feature or the whole backend, remind them:
- Open a Pull Request from `Omri-Backend` → `main`
- PR title should summarize the feature
- Merge only when everything is working
