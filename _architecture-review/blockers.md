# Blockers & Risks

Items that need human decision or are too risky to execute autonomously.

---

## Critical — Needs Human Action

### 1. Google cookies in git history
- **File:** `skills/meeting-bot/google-cookies.json`
- **Issue:** Real Google auth cookies (SID, HSID, SSID, APISID, etc.) are in git history
- **Required action:** Run `git filter-repo` or BFG to purge from history. This rewrites git history and requires force-push.
- **Status:** BLOCKED — destructive operation, needs explicit user approval and coordination

### 2. Server vs repo divergence (gws-auth migration)
- **Issue:** Server has been migrated from `gog` to `gws-auth` with shared `lib/gws.py`. Repo still uses `gog`.
- **Required action:** Port server migration to repo (Phase 8 of modernization plan)
- **Status:** DEFERRED — out of scope for this rearchitecture pass; will be addressed separately

---

## Medium — Needs Clarification

### 3. deck-analyzer deprecation path
- **Issue:** deck-analyzer is a strict subset of deal-analyzer. Plan says deprecate it.
- **Question:** Should we add deprecation notice only, or actually delete the skill?
- **Status:** Will add deprecation notice per plan; deletion deferred

### 4. vc-automation/linkedin-api-helper.py
- **Issue:** Non-functional (acknowledged in code). Plan says remove or archive.
- **Question:** Archive to docs/archive/ or just delete?
- **Status:** Will delete per plan; it provides no value
