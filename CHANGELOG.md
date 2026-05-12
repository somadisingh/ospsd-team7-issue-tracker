# Changelog

All notable API and contract changes for downstream consumers are recorded here.

## [Unreleased]

### Shared vertical API (HW3) — breaking for older HTTP / generated clients

Aligning with the course **shared issue-tracker API** and regenerated OpenAPI client introduced **JSON field and model renames**. Update any code that was generated against or hand-coded to the pre-HW3 service spec.

| Area | Before (informal) | After |
|------|-------------------|--------|
| Board title in JSON | `name` | `board_name` (matches shared `Board` contract) |
| Issue / card payloads | Ad hoc shapes | Shared `Issue` / `Status` enum (`to_do`, `in_progress`, `completed`, …) |
| Service routes | HW2-only surface | Added shared CRUD where required by the vertical (`get_issues`, `update_board`, `delete_board`, …) |

**Action for consumers:** Regenerate **`issue_tracker_service_api_client`** from the current OpenAPI spec (or bump your pin to the team’s latest tag) and migrate field accessors (`Board.name` → `board_name` on **HTTP** models; the in-process **`issue_tracker_client_api.Board`** ABC still exposes `.board_name` as the property name).

### AI assistant

- New routes under **`/ai`**: health probe and authenticated chat. See **`docs/ai-integration.md`**.
- LLM tool catalogue includes **issue assignment** via **`assign_issue`** (issue id + member id), plus existing board/issue/chat tools.
- Optional e2e: set **`E2E_DEPLOYED_HEALTH=1`** and **`SERVICE_BASE_URL`** to run **`tests/e2e/service_health_e2e_tests.py`** (`GET /health` on the deployed service).
