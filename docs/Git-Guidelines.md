 # Git Branching Guidelines

## Branch Structure

```
master        ← production-ready, stable
  └── develop ← active development, all PRs target here
        ├── feature/your-feature
        └── bugfix/your-fix
```

> **DO NOT PUSH directly to `master` or `develop`.** All changes go through a PR.

---

## Branch Naming

```
feature/<short-description>    # new functionality
bugfix/<short-description>     # bug fixes
hotfix/<short-description>     # urgent production fixes (branch from master)
chore/<short-description>      # deps, config, tooling
```

**Examples:**
```
feature/user-authentication
bugfix/fix-login-redirect
chore/update-dependencies
```

---

## Daily Workflow

```bash
# 1. Start fresh from develop
git checkout develop
git pull origin develop

# 2. Create your branch
git checkout -b feature/<your-branch-name>

# 3. Develop and commit
git add <files>
git commit -m "feat: add user authentication"

# 4. Push your branch
git push -u origin feature/<your-branch-name>

# 5. Open a PR → target: develop
```

---

## Commit Messages

Use a short, clear prefix:

```
feat: add payment integration
fix: resolve null pointer on login
chore: upgrade boto3 to 1.34
docs: update setup instructions
```

---

## Pull Request Rules

- **Target branch is always `develop`** — never `master`
- At least **1 approval** required before merging
- Keep PRs small and focused — one feature or fix per PR
- **Do not merge your own PR** without a review
- Delete your branch after merge

---

## Do's and Don'ts

| ✅ Do | ❌ Don't |
|---|---|
| Branch from `develop` | Push directly to `master` or `develop` |
| Keep PRs small | Open PRs with unrelated changes mixed in |
| Pull `develop` before branching | Commit secrets or `.env` files |
| Delete branch after merge | Force push to shared branches |
