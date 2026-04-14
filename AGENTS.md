# AI Medical Multi-Agent Agent Guidelines

## Environment Setup
- Copy `.env.example` to `.env` and fill in required values:
  - `GEMINI_API_KEY` (from Google AI Studio)
  - `MONGODB_URI` (MongoDB Atlas connection string)
  - `OLLAMA_BASE_URL` (default: http://localhost:11434)
  - `OLLAMA_MODEL` (default: medgemma:4b)
- Ensure Ollama is running locally with the specified model pulled

## Local Model Testing
- Test MedGemma 4B integration: `python backend/test_medgemma.py`
- This verifies Ollama connectivity and model responsiveness

## Important Notes
- Motor MongoDB driver is deprecated (will be removed May 14, 2026) - consider migrating to PyMongo Async driver
- Google Generative AI packages are deprecated - migrate to `google-genai` SDK
- Local agents process sensitive data via MedGemma 4B (Ollama) for privacy
- Cloud agents use Gemini 1.5 Flash for task coordination and caregiver notifications

## Project Structure
- Cloud Agents: LLM Coordinator, Caregiver Notification
- Local Agents: Medical Analyzer, History Summarizer
- Backend: FastAPI with asynchronous task handling

## Phase-Based Implementation

All backend development follows **5 modular phases** with clear deliverables, dependencies, and exit criteria. Reference these documents:

### Quick Start for Agents
1. **First time?** Start with [`PHASE_INDEX.md`](PHASE_INDEX.md) (5 min overview)
2. **Need guidance?** Use [`QUICK_REFERENCE_FOR_AGENTS.md`](QUICK_REFERENCE_FOR_AGENTS.md) (quick reference)
3. **Ready to execute?** Follow [`.github/instructions/PHASE_EXECUTION.instructions.md`](.github/instructions/PHASE_EXECUTION.instructions.md) (detailed execution guide)
4. **Starting phase work?** Copy [`AGENT_EXECUTION_TEMPLATE.md`](AGENT_EXECUTION_TEMPLATE.md) (ready-to-use checklist)

### Phase Overview

| Phase | Weeks | Focus | File |
|-------|-------|-------|------|
| **1: Foundation** | 1-2 | FastAPI scaffold, config, logging, health checks | [`PHASE_1_FOUNDATION.md`](PHASE_1_FOUNDATION.md) |
| **2: Core Domain** | 3-4 | Data models, repositories, CRUD API endpoints | [`PHASE_2_CORE_DOMAIN.md`](PHASE_2_CORE_DOMAIN.md) |
| **3: Agent Pipeline** | 5-6 | Hybrid cloud/local workflow, PHI boundary enforcement | [`PHASE_3_AGENT_PIPELINE.md`](PHASE_3_AGENT_PIPELINE.md) |
| **4: Alerts & Reliability** | 7 | Notifications, retries, circuit breaker, delivery tracking | [`PHASE_4_ALERTS_RELIABILITY.md`](PHASE_4_ALERTS_RELIABILITY.md) |
| **5: Hardening & Compliance** | 8 | Auth, encryption, privacy tests, security, runbooks | [`PHASE_5_HARDENING_COMPLIANCE.md`](PHASE_5_HARDENING_COMPLIANCE.md) |

### Key Principles
- ✅ **Hybrid Security:** Gemini (cloud) handles non-sensitive reasoning; Ollama (local) processes PHI
- ✅ **Async & Decoupled:** API accepts tasks immediately; background workers process via queue
- ✅ **Auditable:** Every PHI access logged; encryption at rest and in transit
- ✅ **Sequential Phases:** Each phase builds on previous; no parallel work

### Phase Execution Workflow
1. Read current phase document (e.g., `PHASE_3_AGENT_PIPELINE.md`)
2. Review deliverables and acceptance criteria (checkboxes)
3. Follow implementation sequence
4. Verify all exit criteria before next phase
5. Move to next phase only when gates are passed

### For Questions
- "What phase should I work on?" → [`PHASE_INDEX.md`](PHASE_INDEX.md)
- "How do I execute a phase?" → [`.github/instructions/PHASE_EXECUTION.instructions.md`](.github/instructions/PHASE_EXECUTION.instructions.md)
- "What's a quick reference?" → [`QUICK_REFERENCE_FOR_AGENTS.md`](QUICK_REFERENCE_FOR_AGENTS.md)
- "I'm confused about sequencing" → [`.github/instructions/PHASE_EXECUTION.instructions.md`](.github/instructions/PHASE_EXECUTION.instructions.md) "Common Agent Mistakes" section
- "What prevents PHI leakage?" → [`PHASE_3_AGENT_PIPELINE.md`](PHASE_3_AGENT_PIPELINE.md) "D3.9: PHI Boundary Enforcement"

### Important Notes for Phase Execution
- **Motor deprecation (May 2026):** Phase 1 D1.4 handles migration path to PyMongo async
- **Google SDK deprecation:** Phase 1 uses `google-genai` SDK (not deprecated packages)
- **PHI boundary (Phase 3 critical):** Never send raw patient data to Gemini API; only Reasoning Traces
- **Exit gates required:** All phases must have exit criteria verified ✓ before proceeding

---

## `.gitignore` Maintenance

AI agents **must** maintain a root-level `.gitignore` file at all times. Follow these rules:

### Mandatory Rules
1. **Check on every phase start:** Before beginning any phase, verify that `.gitignore` exists at the project root. If it does not exist, create it immediately using the baseline below.
2. **Update when adding dependencies or tooling:** Whenever you introduce a new tool, framework, dependency, or generate build artifacts, add the corresponding ignore patterns to `.gitignore` **before** committing.
3. **Never commit ignored files:** If a file matches a `.gitignore` pattern, it must **never** be committed. If you find tracked files that should be ignored, untrack them with `git rm --cached <file>` and commit the change.
4. **Keep patterns organized:** Group patterns under clear section headers (comments). Do not duplicate patterns.
5. **Preserve existing patterns:** When updating `.gitignore`, append or modify — never delete existing patterns unless they are confirmed obsolete.

### Baseline `.gitignore` (minimum required patterns)

```gitignore
# ── Python ──
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
*.egg
.venv/
venv/
env/

# ── Environment & Secrets ──
.env
.env.*
!.env.example

# ── Node / Frontend ──
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# ── IDE & Editor ──
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# ── Logs & Runtime ──
*.log
logs/
*.pid

# ── Testing & Coverage ──
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/

# ── Build & Artifacts ──
*.whl
*.tar.gz
```


---

## Git Commit Policy — Commit After Every Phase

AI agents **must** commit their work to the `main` branch after the **successful completion** of every phase. This is a hard requirement, not optional.

### Workflow
1. **Complete all phase deliverables** and verify all exit criteria pass (tests green, checklists checked).
2. **Stage all changed files:**
   ```bash
   git add -A
   ```
3. **Commit with a standardized message:**
   ```bash
   git commit -m "Phase <N>: <Phase Title> — completed

   - <bullet summary of key deliverables>
   - All exit criteria verified ✓"
   ```
   Example:
   ```bash
   git commit -m "Phase 1: Foundation — completed

   - FastAPI scaffold with health checks
   - Config management and structured logging
   - PyMongo async driver integrated
   - All exit criteria verified ✓"
   ```
4. **Push to remote (if configured):**
   ```bash
   git push origin main
   ```

### Rules
- ⚠️ **Do NOT defer commits** — commit immediately after phase completion, before starting the next phase.
- ⚠️ **Do NOT squash phases** — each phase gets its own distinct commit so the history is traceable.
- ✅ **Mid-phase commits are allowed** for significant milestones (e.g., completing a major deliverable group), but the end-of-phase commit is **mandatory**.
- ✅ **Verify `.gitignore` is up to date** before committing (see section above).
- ✅ **Run `git status`** before committing to ensure no secrets, `.env` files, or generated artifacts are staged.