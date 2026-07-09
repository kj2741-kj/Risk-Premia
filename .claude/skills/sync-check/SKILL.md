---
name: sync-check
description: Check local git state against the remote (origin), identify whether a collaborator has pushed changes that overlap with local/uncommitted work, and recommend a safe way to realign. Use when the user wants to check for collaborator changes, verify local vs remote git state before pulling, or make sure nothing will be silently overwritten.
---

# Sync Check

Systematically compare the local repo against `origin` before pulling anything,
so nothing gets silently overwritten or lost. Do not pull, merge, or push
anything until you've reported findings and the user has confirmed.

## Steps

1. **Fetch, don't merge.** Run `git fetch origin` (read-only — updates remote
   refs without touching working files).

2. **Classify the sync state.** Compare local `HEAD` to `origin/<branch>` via
   `git status -uno` (after the fetch). Report plainly which case applies:
   - **Fast-forward possible** (local has no commits remote doesn't) — safe,
     lowest risk.
   - **Ahead** (local has unpushed commits) — push first, or local work can
     be lost/orphaned.
   - **Diverged** (both sides have new commits) — real merge required,
     conflicts possible. Flag this clearly; it's the risky case.

3. **List what's incoming.** `git log HEAD..origin/<branch> --oneline` for
   the commits, `git diff --stat HEAD..origin/<branch>` for which files and
   how much changed.

4. **Cross-reference against local work.** Check `git status` for
   uncommitted local changes, and consider what's been discussed/edited this
   session. Flag any file touched on **both** sides — that's where silent
   overwrites and merge conflicts happen. Don't just note the overlap; look
   at *why* each side touched that file (read both diffs) to judge whether
   they're additive (safe) or conflicting (risky).

5. **Verify substantive changes, don't just read them.** If a flagged file
   has logic/algorithm changes (not just formatting/comments), don't trust
   the commit message or a surface-level diff read:
   - `grep` for specific functions/identifiers you know matter (fixes,
     config entries, etc.) to confirm they survived.
   - If the change is significant enough (e.g. a rewritten algorithm), pull
     the incoming version into an isolated test (e.g. `git show
     origin/<branch>:path/to/file > /tmp/theirs.py`, copy it into place
     under a throwaway filename inside the repo so relative paths resolve,
     import and run it against known test cases) and empirically compare
     behavior before vs after, rather than assuming from the diff alone.
     Clean up the throwaway file afterward.

6. **Give a clear verdict and next step.** One of:
   - Safe to pull as-is (fast-forward, no overlapping files) — just do
     `git pull origin <branch>`.
   - Overlapping files reviewed, no actual conflict found — safe to pull,
     but mention what was checked.
   - Needs the user's judgment — explain the specific conflict/tradeoff
     found and let them decide before proceeding.
   - Diverged with real conflicts — recommend `git stash` first if there are
     uncommitted local changes, then merge/rebase, and be ready to walk
     through conflict resolution file-by-file.

Never pull/merge/push without stating findings first and getting
confirmation, unless the user has already told you to just go ahead.
