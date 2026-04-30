# GitHub: create the remote and push

Target remote (already in git config):

- `git@github-second:codergoel/project_elena.git`

GitHub does not allow creating repositories over SSH. You need **either** a [Personal Access Token](https://github.com/settings/tokens) (for the **`codergoel`** account) **or** the [new repository](https://github.com/new) page in the browser.

## Option 1 — Script (API + push)

1. On **`codergoel`**: **Settings → Developer settings → Personal access tokens** and create a token with at least **repo** (classic) for a private/push workflow, or **public_repo** for public-only, or a fine-grained token with “Contents” and repository creation permissions.
2. In a terminal:

```bash
cd /Users/tanmay.goel/Desktop/Project_Elena
export GITHUB_TOKEN=ghp_your_token_here
./scripts/create_github_repo.sh
```

The script creates `project_elena` on that account (if missing) and runs `git push -u origin main`.

**Security:** Do not commit the token. Do not paste it into the repo. Revoke the token if it leaks.

## Option 2 — Browser + push

1. Open **https://github.com/new** while logged in as **codergoel**.
2. Repository name: **`project_elena`** (match the URL exactly: lowercase, no typo).
3. **Public** or **Private** as you prefer. Do **not** add README, .gitignore, or license (avoids a merge on first push).
4. **Create repository**, then run:

```bash
cd /Users/tanmay.goel/Desktop/Project_Elena
git push -u origin main
```

## If push says “Repository not found”

- The repo name or owner in `git remote -v` does not match GitHub (e.g. typo).
- The repo is under a different org/user than **codergoel**.
- The SSH key is for **codergoel**; confirm: `ssh -T git@github-second`.

## Optional: install GitHub CLI (otherwise)

With Homebrew working on your machine:

```bash
brew install gh
gh auth login
gh repo create project_elena --public --source=. --remote=origin --push
```

(Adjust flags if the repo already exists; `create_github_repo.sh` is enough if you prefer not to install `gh`.)
