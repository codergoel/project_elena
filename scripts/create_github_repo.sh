#!/usr/bin/env bash
# Create github.com/codergoel/project_elena if it does not exist, then push main.
# Requires: GITHUB_TOKEN (classic PAT with "repo" scope, or fine-grained with Contents read/write
# to create and push; for API-only create use classic "repo" or "public_repo" for public repos).

set -euo pipefail

REPO_NAME="${REPO_NAME:-project_elena}"
OWNER="${GITHUB_OWNER:-codergoel}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Error: GITHUB_TOKEN is not set."
  echo ""
  echo "Option A — use this script:"
  echo "  1. Create a token: https://github.com/settings/tokens (classic: enable 'repo')"
  echo "  2. export GITHUB_TOKEN=ghp_yourtoken"
  echo "  3. $0"
  echo ""
  echo "Option B — create the repo in the browser, then push only:"
  echo "  1. https://github.com/new — Repository name: ${REPO_NAME} — create empty (no README)"
  echo "  2. cd ${REPO_DIR} && git push -u origin main"
  exit 1
fi

api_create() {
  local json
  json=$(printf '{"name":"%s","description":"Elena: AI LaTeX resume editor","private":false}' "$REPO_NAME")
  curl -sS -w "\n%{http_code}" -X POST \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/user/repos" \
    -d "$json"
}

# Try Bearer first (PATs and fine-grained)
resp=$(api_create) || true
http_code=$(echo "$resp" | tail -n1)
body=$(echo "$resp" | sed '$d')

if [[ "$http_code" == "201" ]]; then
  echo "Created https://github.com/${OWNER}/${REPO_NAME}"
elif [[ "$http_code" == "422" ]] && echo "$body" | grep -qiE 'already|exists|in use'; then
  echo "Repository already exists: https://github.com/${OWNER}/${REPO_NAME}"
elif [[ "$http_code" -ge 200 ]] && [[ "$http_code" -lt 300 ]]; then
  echo "Unexpected success code $http_code: $body"
else
  echo "GitHub API error (HTTP $http_code):"
  echo "$body" | head -c 2000
  echo
  exit 1
fi

cd "$REPO_DIR"
if git push -u origin main; then
  echo "Pushed to origin main."
else
  echo "Push failed. If the repo is empty and exists, run: git push -u origin main"
  exit 1
fi
