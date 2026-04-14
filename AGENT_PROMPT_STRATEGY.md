---
title: "Agent Prompt Strategy Summary"
description: "Overview of all agent-facing phase reference materials and how to use them"
---

# AI Medical Multi-Agent: Agent Prompt Strategy Summary

## 📊 What Was Created

I've drafted **3 comprehensive agent-facing documents** to guide AI agents on how to reference and execute the phase plan:

### 1. **`.github/instructions/PHASE_EXECUTION.instructions.md`** (Detailed)
- **Purpose:** Comprehensive agent execution guide with all details
- **Length:** ~650 lines
- **When to use:** When agents need deep context, understanding dependencies, architecture principles
- **Contains:**
  - Phase plan document discovery (which file to read)
  - When to reference each phase (specific use cases)
  - How to structure work using phases (7-step process)
  - Deliverable anatomy (what each deliverable contains)
  - Exit criteria patterns (how to verify completion)
  - Common agent mistakes to avoid (5 examples)
  - Data/service layer progression across phases
  - Success criteria definition

**Best for:** Initial onboarding, complex phase transitions, understanding dependencies

---

### 2. **`QUICK_REFERENCE_FOR_AGENTS.md`** (Concise)
- **Purpose:** Quickly scannable one-page equivalent for agents
- **Length:** ~300 lines
- **When to use:** Quick lookup during work, phase transitions, urgent questions
- **Contains:**
  - Phase table with use-when triggers
  - Hub documents list
  - How agents should use phase documents (3-step process)
  - Phase deliverable overview
  - Dependency chain (visual)
  - Architecture principles summary
  - Common tasks by phase
  - Anti-patterns vs. correct patterns (comparison table)
  - Document locations
  - Reading order
  - Metadata

**Best for:** Quick reference, phase transitions, pattern checking

---

### 3. **ADDITION TO AGENTS.md** (Optional - I can add this)
- **Purpose:** High-level phase plan mention in existing agent guidelines
- **Length:** ~50-100 lines
- **When to use:** When agents first open AGENTS.md
- **Could contain:**
  - Reference to phase plan documents
  - Link to .github/instructions/PHASE_EXECUTION.instructions.md
  - Quick phase table
  - "Read PHASE_INDEX.md first" guidance

---

## 🎯 How These Documents Work Together

```
Agent asks: "How should I structure work on the backend?"
    ↓
Agent reads: QUICK_REFERENCE_FOR_AGENTS.md (fast orientation)
    ↓
Agent needs details: Opens PHASE_EXECUTION.instructions.md (comprehensive)
    ↓
Agent needs phase content: Opens specific phase file (PHASE_1_FOUNDATION.md, etc.)
    ↓
Agent needs overview: Opens PHASE_INDEX.md (roadmap & dependencies)
```

---

## 📋 Key Features of the Strategy

### Discovery Architecture
**Goal:** Agents can find the right document for any question

| Agent Question | Document to Reference |
|---|---|
| "What phases exist?" | PHASE_INDEX.md |
| "What should I do now?" | QUICK_REFERENCE_FOR_AGENTS.md |
| "How do I execute Phase 3?" | PHASE_EXECUTION.instructions.md (detailed) or current phase file |
| "What are the exit criteria?" | Current phase file > Exit Criteria Checklist |
| "What's the timeline?" | QUICK_REFERENCE.md or PHASE_INDEX.md |
| "What deliverables are in Phase 2?" | PHASE_2_CORE_DOMAIN.md or PHASE_EXECUTION.instructions.md |

---

### Anti-Pattern Prevention

Both documents explicitly warn against:
1. ❌ Skipping phases
2. ❌ Ignoring dependencies  
3. ❌ Not tracking deliverables
4. ❌ Proceeding without exit criteria
5. ❌ Missing PHI boundary enforcement

---

### Structured Reference Benefits

**Consistency:**
- All phases follow same structure (Overview → Goals → Deliverables → Sequence → Exit Criteria)
- Agents know what to expect in each phase file
- Deliverables follow predictable anatomy (Description → Acceptance Criteria → Artifacts)

**Clarity:**
- Each phase explicitly states "Depends On"
- Exit criteria are measurable, observable, verifiable
- Acceptance criteria are checkboxes (binary done/not done)

**Navigability:**
- Cross-references between documents (markdown links)
- Quick reference tables in every document
- Clear "next steps" after each phase

---

## 🚀 How to Use These Documents

### Scenario 1: Agent Starting New Phase
```
1. Agent reads: PHASE_EXECUTION.instructions.md (Step 1: Determine Current Phase)
2. Agent opens: PHASE_INDEX.md (verify dependencies)
3. Agent opens: Specific phase file (e.g., PHASE_3_AGENT_PIPELINE.md)
4. Agent marks: Phase start in execution log
5. Agent begins: Day 1 work from Implementation Sequence
```

### Scenario 2: Agent Verifying Phase Completion
```
1. Agent opens: Current phase file
2. Agent navigates to: Exit Criteria Checklist
3. Agent verifies: Each criterion ✓
4. Agent confirms: Ready for next phase
5. Agent links: PHASE_INDEX.md to show completed phase, starting next
```

### Scenario 3: Agent Confused About Phase Order
```
1. Agent reads: QUICK_REFERENCE_FOR_AGENTS.md (phase table + dependency chain)
2. Agent opens: PHASE_EXECUTION.instructions.md (How to Structure Work section)
3. Agent understands: Sequential execution required
4. Agent confirms: Current phase must complete before next
```

### Scenario 4: Agent Working on Specific Deliverable
```
1. Agent has: Deliverable name (e.g., "D3.5: Internal Async Queue")
2. Agent opens: PHASE_3_AGENT_PIPELINE.md
3. Agent navigates: Ctrl+F "D3.5"
4. Agent sees: Description, Acceptance Criteria, Artifacts
5. Agent tracks: Progress using checkboxes
```

---

## ✨ Special Features

### Phase YAML Frontmatter
Each phase file has metadata:
```yaml
---
title: "Phase X: Name"
phase: X
duration: "Weeks Y-Z"
dependencies: ["PHASE_Y.md", "PHASE_Z.md"]
tags: ["tag1", "tag2"]
---
```

This enables:
- Consistent discovery
- Filtering by tag
- Understanding dependencies programmatically

---

### Acceptance Criteria Checkboxes
Every deliverable uses markdown checkboxes:
```markdown
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
```

Agents can:
- Copy the phase file locally
- Check items as they complete work: `[x]`
- Commit the updated phase file as a progress log

---

### Linked Navigation
All 3 documents link to each other and to phase files:
- PHASE_EXECUTION.instructions.md → phase files (specific phases)
- QUICK_REFERENCE_FOR_AGENTS.md → phase files (examples)
- PHASE_INDEX.md → all phase files (roadmap)

Enables agents to navigate the entire structure via markdown links.

---

## 📊 Comparison: Which Document to Follow

| Situation | Document | Why |
|-----------|----------|-----|
| Agent is confused about phase order | QUICK_REFERENCE_FOR_AGENTS.md | Visual + concise |
| Agent needs implementation details for Phase 4 | PHASE_4_ALERTS_RELIABILITY.md | Detailed deliverables |
| Agent needs to understand architecture before starting | PHASE_EXECUTION.instructions.md | Full context |
| Agent needs one-sentence answers (metrics, timeline) | QUICK_REFERENCE.md | Summary tables |
| Agent needs to verify phase dependencies | PHASE_INDEX.md | Dependency matrix |
| Agent is starting Phase 1 for first time | PHASE_EXECUTION.instructions.md + PHASE_1_FOUNDATION.md | Guided + detailed |

---

## 🎯 Recommended Reading Order (First Time)

1. **PHASE_INDEX.md** (10 min) — Understand what phases exist, dependencies
2. **QUICK_REFERENCE_FOR_AGENTS.md** (10 min) — Quick reference of phase table + anti-patterns
3. **PHASE_EXECUTION.instructions.md** (20 min) — Detailed process for using phases
4. **Current phase file** (30-45 min) — Deep dive on specific phase deliverables
5. **Reference as needed** — Jump to specific sections based on work

---

## 💡 Example Agent Use Cases

### Use Case 1: "Implement Phase 2"
Agent would:
- Read QUICK_REFERENCE_FOR_AGENTS.md to understand Phase 2 is "Core Domain + API"
- Open PHASE_2_CORE_DOMAIN.md
- See 7 deliverables with sequences for weeks 3-4
- Follow day-by-day breakdown
- Mark acceptance criteria as complete
- Verify exit criteria before moving to Phase 3

### Use Case 2: "I think there's a PHI boundary issue"
Agent would:
- Skim QUICK_REFERENCE_FOR_AGENTS.md → Critical Architecture Principles section
- See: "PHI Boundary (Phase 3 Critical)"
- Understand: Gemini sees only Reasoning Traces, Ollama sees full PHI
- Open PHASE_3_AGENT_PIPELINE.md
- Find D3.9: PHI Boundary Enforcement
- Review acceptance criteria and privacy middleware requirements

### Use Case 3: "What happens after Phase 4?"
Agent would:
- Check PHASE_INDEX.md or QUICK_REFERENCE_FOR_AGENTS.md
- See phase dependency chain
- Understand Phase 5 (Hardening & Compliance) comes next
- Can preview Phase 5 requirements (security, privacy tests, runbooks)

---

## 🔧 How to Integrate Into Existing Workflow

### Option A: Add Brief Reference to AGENTS.md
Edit existing `AGENTS.md` to add:
```markdown
## Phase-Based Implementation

All backend development follows 5 modular phases. Reference these documents:
- **Overview:** `PHASE_INDEX.md` (start here)
- **Agent Guide:** `QUICK_REFERENCE_FOR_AGENTS.md` (quick reference)
- **Detailed Execution:** `.github/instructions/PHASE_EXECUTION.instructions.md`
- **Individual phases:** `PHASE_1_FOUNDATION.md` through `PHASE_5_HARDENING_COMPLIANCE.md`

See QUICK_REFERENCE_FOR_AGENTS.md for quick answers.
```

### Option B: Use .github/instructions auto-loading
File `.github/instructions/PHASE_EXECUTION.instructions.md` will be auto-discovered by agents when working in `backend/**` directory due to its `applyTo` pattern.

### Option C: Create Agent Onboarding Prompt
Create `.github/prompts/onboard-phase-execution.prompt.md`:
```yaml
---
name: Onboard to Phase Execution
---

You are joining the AI Medical Multi-Agent backend project. Here's how to reference the phase plan:

1. **Overview:** Read PHASE_INDEX.md (5 minutes)
2. **Quick Help:** Read QUICK_REFERENCE_FOR_AGENTS.md anytime
3. **Details:** Use PHASE_EXECUTION.instructions.md
4. **Work on Phase X:** Open PHASE_X_NAME.md

Current phase status: [INSERT CURRENT PHASE]
```

---

## ✅ Validation Checklist

**Created documents:**
- [x] PHASE_EXECUTION.instructions.md (detailed guide, 650+ lines)
- [x] QUICK_REFERENCE_FOR_AGENTS.md (quick reference, 300+ lines)
- [ ] Optional: Addition to AGENTS.md (awaiting approval)
- [ ] Optional: .prompt.md onboarding file (awaiting approval)

**Document features:**
- [x] Clear discovery mechanism (use-when patterns)
- [x] Anti-pattern warnings
- [x] Architecture principles
- [x] Deliverable tracking guidance
- [x] Exit criteria verification
- [x] Cross-document linking
- [x] Example agent scenarios
- [x] Reading order guidance

---

## 📍 File Locations

```
AI_Medical_Multi_Agent/
├── AGENTS.md                                        (existing, could add reference)
├── PHASE_INDEX.md                                   (phase overview)
├── PHASE_1_FOUNDATION.md                            (Week 1-2)
├── PHASE_2_CORE_DOMAIN.md                           (Week 3-4)
├── PHASE_3_AGENT_PIPELINE.md                        (Week 5-6)
├── PHASE_4_ALERTS_RELIABILITY.md                    (Week 7)
├── PHASE_5_HARDENING_COMPLIANCE.md                  (Week 8)
├── QUICK_REFERENCE.md                               (1-page summary for humans)
├── QUICK_REFERENCE_FOR_AGENTS.md                    ✨ NEW (agent-focused summary)
└── .github/instructions/
    └── PHASE_EXECUTION.instructions.md              ✨ NEW (detailed agent guide)
```

---

## 🎓 Next Steps (Your Choice)

1. **Review the drafts:** Read through both new documents
2. **Customize as needed:** Adjust any wording, examples, or warnings
3. **Optional additions:**
   - Add brief reference to AGENTS.md
   - Create onboarding prompt file
   - Create agent-specific checklist template
4. **Share with team:** Point agents to PHASE_EXECUTION.instructions.md
5. **Use in practice:** Reference specific phases/deliverables in task descriptions

---

## Document Metadata

- **Created:** 2026-04-14
- **Purpose:** Provide AI agents with clear, discoverable phase plan references
- **Status:** Ready for review and customization
- **Files:** 2 new markdown files + 3 optional additions
- **Total content:** 950+ lines of agent-focused guidance
