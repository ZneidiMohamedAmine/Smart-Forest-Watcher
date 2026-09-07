# Squad Decisions

## Active Decisions

### 2026-09-04 — Squad AI adopted, customized for this stack

**What:** Installed Squad (`@bradygaster/squad-cli`, default preset) to handle GitHub issue
triage and (eventually) autonomous coding via GitHub Copilot's coding agent.

**Customization from defaults:**
- Replaced the generic `devrel` persona with `backend` (Django/Celery/MQTT/PostGIS) —
  devrel (developer-facing quickstarts) doesn't fit a private internal platform.
- Added `mobile` (Flutter/SmartForGreenApp) and `ml` (YOLO/detection pipeline) as new
  dedicated personas — the default preset only ships `lead`/`reviewer`/`devrel`/`security`/`docs`.
- `lead` and `security` charters were grounded in this repo's actual concerns (the
  backend/mobile/ml split, the CI/CD auto-deploy-to-production path).
- Stripped the `release:v0.4.0`–`v1.0.0` placeholder labels from `sync-squad-labels.yml`
  — those were Squad's own template versioning, not this project's.

**Guardrails:**
- Branch protection enabled on `main`: requires `pytest` + `security` CI checks and
  1 approving review before merge; no force-push/delete. `enforce_admins` left off
  so the owner isn't locked out solo. Set via `gh api repos/.../branches/main/protection`.
- The 4 Squad workflows (`squad-triage`, `squad-issue-assign`, `squad-heartbeat`,
  `sync-squad-labels`) only touch issues/labels/comments — none of them modify code,
  merge PRs, or touch the `deploy` job in `CI-CD.yml`. That boundary was deliberate:
  a sandboxed coding agent can't spin up Postgres+PostGIS+Redis+real TTN traffic to
  verify hardware/ML-dependent changes, so those stay human-reviewed regardless of
  whether the coding agent is later enabled.

**Verified working (2026-09-04):** Test issue #1 (labeled `squad`) was correctly
auto-triaged and routed to `squad:backend` based on keyword matching — confirms
team.md → routing.md → label → comment pipeline works end to end.

**Mechanism verified (2026-09-04):** The "write code and open a PR" path needs GitHub
Copilot's coding agent, which requires **Copilot Pro or higher** — this account was
on `free_limited_copilot` with 0 premium-interaction quota (checked via
`gh api copilot_internal/user`), so a friend's Copilot Pro account/PAT was used to
test the `squad:copilot` flow temporarily. It worked as intended end to end (issue
assignment → coding agent → PR). That token was never added as a persistent repo
secret (confirmed via `gh secret list` — no `COPILOT_ASSIGN_TOKEN` present) and
access was removed after the test since the account wasn't this project's own.

**Still open:** This account itself is not yet on Copilot Pro, so there is currently
no working `COPILOT_ASSIGN_TOKEN` configured — the mechanism is proven, not
provisioned. To make it usable on an ongoing basis:
1. Get Copilot Pro active on an account authorized for this project long-term
   (resolve the Student Pack grant on this account, or a paid seat) — using
   someone else's personal account/token again isn't a sustainable setup.
2. Enable coding agent for this repo (org/repo admin setting under Copilot policies).
3. Create a classic PAT (`repo` scope) at github.com/settings/tokens — do this
   yourself, not via an assistant, since token values should never be typed into
   a chat session.
4. Add it as a repo secret named `COPILOT_ASSIGN_TOKEN`, either via
   `gh secret set COPILOT_ASSIGN_TOKEN` (paste when prompted, in your own terminal)
   or the repo's Settings → Secrets and variables → Actions page.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
