#!/usr/bin/env bash
# SessionStart hook: surface commits since the recorded understanding baseline
# (the "Session Anchor" at the top of HANDOVER_NOTES.md) so a resuming Claude
# Code session reconciles the diff against the code before trusting the docs.
# Read-only; designed never to fail the session (always exits 0).
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
command -v git >/dev/null 2>&1 || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

anchor=$(grep -m1 'Understanding baseline' HANDOVER_NOTES.md 2>/dev/null \
         | sed -nE 's/.*commit `([0-9a-f]{7,40})`.*/\1/p')
[ -z "$anchor" ] && exit 0

echo "MacHuna Session Anchor (from HANDOVER_NOTES.md): $anchor"
if ! git cat-file -e "$anchor" 2>/dev/null; then
  echo "  Anchor commit not present locally - run 'git fetch', then reconcile manually."
  exit 0
fi

count=$(git rev-list --count "$anchor"..HEAD 2>/dev/null)
if [ -z "$count" ] || [ "$count" = "0" ]; then
  echo "  No commits since the anchor - understanding baseline is current."
else
  echo "  $count commit(s) since the anchor. Reconcile these against the code before trusting the docs:"
  git log --oneline "$anchor"..HEAD 2>/dev/null | sed 's/^/    /'
fi

dirty=$(git status --porcelain 2>/dev/null)
[ -n "$dirty" ] && { echo "  Uncommitted working-tree changes:"; echo "$dirty" | sed 's/^/    /'; }
exit 0
