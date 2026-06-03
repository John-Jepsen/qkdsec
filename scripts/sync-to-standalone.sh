#!/usr/bin/env bash
#
# sync-to-standalone.sh
#
# Mirror the in-monorepo qkdsec/ directory to the standalone public repo at
# github.com/John-Jepsen/qkdsec so that external contributors have a single
# canonical source of truth.
#
# Strategy: this script does NOT try to merge histories. It clones the
# standalone repo into a scratch directory, replaces its working tree with the
# current monorepo qkdsec/ contents, commits the diff, and pushes.
#
# Usage:
#   ./scripts/sync-to-standalone.sh                       # commit + push to a sync branch
#   ./scripts/sync-to-standalone.sh --branch main         # commit + push directly to main
#   ./scripts/sync-to-standalone.sh --dry-run             # show diff, do not commit or push
#   ./scripts/sync-to-standalone.sh --no-push             # commit locally, do not push
#
# Requirements:
#   - git
#   - SSH or token access to John-Jepsen/qkdsec
#   - rsync
#
# The script refuses to run if the monorepo working tree has uncommitted
# changes inside qkdsec/, to make sure what gets mirrored is what is committed.

set -euo pipefail

# ---- config ------------------------------------------------------------------
STANDALONE_REPO="${QKDSEC_STANDALONE_REPO:-git@github.com:John-Jepsen/qkdsec.git}"
DEFAULT_BRANCH="${QKDSEC_DEFAULT_BRANCH:-main}"
SYNC_BRANCH_PREFIX="sync/from-monorepo"

# ---- args --------------------------------------------------------------------
BRANCH=""
DRY_RUN=0
PUSH=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)   BRANCH="$2"; shift 2 ;;
    --dry-run)  DRY_RUN=1; shift ;;
    --no-push)  PUSH=0; shift ;;
    -h|--help)
      sed -n '2,30p' "$0"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ---- locate the monorepo qkdsec/ source dir ---------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"      # the qkdsec/ directory itself
MONOREPO_ROOT="$(git -C "$SRC_DIR" rev-parse --show-toplevel)"
REL_SRC="${SRC_DIR#$MONOREPO_ROOT/}"

echo "monorepo root : $MONOREPO_ROOT"
echo "qkdsec source : $SRC_DIR  (rel: $REL_SRC)"
echo "standalone    : $STANDALONE_REPO"
echo

# ---- safety: no dirty qkdsec/ in the monorepo --------------------------------
if ! git -C "$MONOREPO_ROOT" diff --quiet -- "$REL_SRC" \
   || ! git -C "$MONOREPO_ROOT" diff --cached --quiet -- "$REL_SRC"; then
  echo "error: uncommitted changes inside $REL_SRC/. Commit or stash first." >&2
  exit 1
fi

LAST_SHA="$(git -C "$MONOREPO_ROOT" log -n1 --format=%H -- "$REL_SRC")"
LAST_SHORT="$(git -C "$MONOREPO_ROOT" log -n1 --format=%h -- "$REL_SRC")"
LAST_SUBJECT="$(git -C "$MONOREPO_ROOT" log -n1 --format=%s -- "$REL_SRC")"

# ---- workspace ---------------------------------------------------------------
WORK_DIR="$(mktemp -d -t qkdsec-sync-XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT
echo "scratch dir   : $WORK_DIR"

git clone --quiet "$STANDALONE_REPO" "$WORK_DIR/standalone"
cd "$WORK_DIR/standalone"

# pick a branch name
if [[ -z "$BRANCH" ]]; then
  BRANCH="$SYNC_BRANCH_PREFIX/$LAST_SHORT"
fi

if git rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
  git checkout -B "$BRANCH" "origin/$BRANCH"
else
  git checkout -B "$BRANCH" "origin/$DEFAULT_BRANCH"
fi

# ---- mirror the source tree --------------------------------------------------
# Wipe everything except .git, then copy the monorepo qkdsec/ contents in.
# rsync with --delete keeps the standalone tree in lock-step with the source.
shopt -s dotglob nullglob
for f in "$WORK_DIR/standalone"/*; do
  [[ "$(basename "$f")" == ".git" ]] && continue
  rm -rf "$f"
done
shopt -u dotglob nullglob

rsync -a \
  --exclude='.git' \
  --exclude='dist' \
  --exclude='build' \
  --exclude='*.egg-info' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='docs/_build' \
  "$SRC_DIR"/ ./

# ---- show what changed -------------------------------------------------------
git add -A
if git diff --cached --quiet; then
  echo "no changes to sync — standalone repo already matches $LAST_SHORT"
  exit 0
fi

echo
echo "diff summary:"
git diff --cached --stat | tail -n 20
echo

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "(dry-run) not committing or pushing."
  exit 0
fi

# ---- commit ------------------------------------------------------------------
COMMIT_MSG="sync from qkd-avantheir@$LAST_SHORT

Mirrors qkdsec/ from John-Jepsen/qkd-avantheir at commit $LAST_SHA.
Upstream subject: $LAST_SUBJECT
"

git commit -m "$COMMIT_MSG"

# ---- push --------------------------------------------------------------------
if [[ "$PUSH" -eq 1 ]]; then
  git push -u origin "$BRANCH"
  echo
  echo "pushed to branch: $BRANCH"
  if [[ "$BRANCH" != "$DEFAULT_BRANCH" ]]; then
    echo "open a PR:"
    echo "  https://github.com/John-Jepsen/qkdsec/compare/$DEFAULT_BRANCH...$BRANCH?expand=1"
  fi
else
  echo "(--no-push) committed locally in $WORK_DIR/standalone but did not push."
  echo "to push manually:"
  echo "  cd $WORK_DIR/standalone && git push -u origin $BRANCH"
  # don't auto-clean the scratch dir if the user asked for --no-push
  trap - EXIT
fi
