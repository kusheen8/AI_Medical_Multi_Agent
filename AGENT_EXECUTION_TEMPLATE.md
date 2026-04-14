---
title: "Agent Execution Template"
description: "Ready-to-use template for agents executing phase work"
---

# AI Medical Multi-Agent: Agent Execution Template

Use this template when starting work on any phase. Copy and fill in the details.

---

## Phase Execution Checklist

```markdown
# Execution Log: Phase [X] - [Phase Name]

## Phase Information
- **Phase:** [X: Name]
- **Timeline:** Weeks [Y-Z]
- **Duration:** [# days]
- **Team Member:** [Agent/Name]
- **Start Date:** [Date]
- **Expected End Date:** [Date]

## Phase Dependencies Verified
- [ ] Previous phase exit criteria verified
- [ ] .github/instructions/PHASE_EXECUTION.instructions.md reviewed
- [ ] QUICK_REFERENCE_FOR_AGENTS.md reviewed
- [ ] PHASE_INDEX.md reviewed for cross-phase dependencies
- [ ] Previous phase's exit criteria are all checked ✓

## Current Phase Context
- [ ] Read [PHASE_X_NAME.md](../PHASE_X_NAME.md)
- [ ] Reviewed entry criteria
- [ ] Reviewed goals (X goals)
- [ ] Noted deliverable count (X deliverables)
- [ ] Understood implementation sequence (X days breakdown)

## Deliverables Tracking

### Deliverable 1: [D[X].[#]: Name]
**Status:** [Not Started / In Progress / Blocked / Complete]

- [ ] Description understood
- [ ] Acceptance Criteria 1: [description]
- [ ] Acceptance Criteria 2: [description]
- [ ] Acceptance Criteria 3: [description]
- [ ] Artifacts created/updated:
  - [ ] [File 1]
  - [ ] [File 2]
  - [ ] [File 3]

**Notes:** [Any blockers, decisions, or context]

---

### Deliverable 2: [D[X].[#]: Name]
**Status:** [Not Started / In Progress / Blocked / Complete]

- [ ] Description understood
- [ ] Acceptance Criteria...
- [ ] Artifacts...

**Notes:** [Details]

---

[Repeat for each deliverable]

## Phase Exit Criteria Verification

- [ ] Exit criterion 1 [measurable]
- [ ] Exit criterion 2 [observable]
- [ ] Exit criterion 3 [verifiable]
- [ ] Exit criterion 4
- [ ] Exit criterion 5

**All exit criteria must be checked before proceeding to next phase.**

## Known Risks & Mitigations

| Risk | Likelihood | Mitigation | Status |
|------|-----------|-----------|--------|
| [Risk 1] | [High/Med/Low] | [Action] | [Pending/Active/Resolved] |
| [Risk 2] | [H/M/L] | [Action] | [P/A/R] |

## Architecture Principles - Reminder

- [ ] [Principle 1]: [Verification]
- [ ] [Principle 2]: [Verification]
- [ ] [Principle 3]: [Verification]

## Testing Checkpoints

- [ ] Unit tests written (coverage: X%)
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Security tests (if Phase 5): [Results]
- [ ] Performance tests (if applicable): [Results]

## Sign-Off

- **Work Completed By:** [Agent/Name]
- **Date Completed:** [Date]
- **Phase Exit Criteria Verified By:** [Reviewer]
- **Ready for Next Phase:** [ ] Yes [ ] No

**Comments:**
[Any notes for next phase or handoff]

---

## Next Phase Prep

- [ ] All deliverables documented
- [ ] Acceptance criteria all marked ✓
- [ ] Exit criteria all verified ✓
- [ ] Known issues documented for next phase
- [ ] Next phase "Depends On" section reviewed
- [ ] Next phase team member notified
```

---

## Quick Start: Day 1 Checklist

```markdown
# Day 1 of Phase [X]

## Morning (30 min)
- [ ] Open PHASE_[X]_[NAME].md
- [ ] Read "Phase Overview" section
- [ ] Skim "Goals" (X goals)
- [ ] Review "Deliverables" section (X deliverables total)
- [ ] Check "Entry Criteria" — are they all met?

## Mid-Morning (30 min)
- [ ] Review "Implementation Sequence" for Day 1-X breakdown
- [ ] Understand which deliverables are "Day 1" work
- [ ] Check dependencies: do all prerequisite artifacts exist?
- [ ] Review "Technical Decisions" table for context

## Before Starting Code (15 min)
- [ ] Verify Phase Entry Criteria in document
- [ ] Open QUICK_REFERENCE_FOR_AGENTS.md > "Architecture Principles"
- [ ] Confirm critical principles (especially for Phase 3: PHI boundary)
- [ ] Ask clarifying questions if architecture is unclear

## Implementation (rest of day)
- [ ] Start with first deliverable's acceptance criteria
- [ ] Create/modify artifacts listed
- [ ] Mark each criterion as complete: `[x]`
- [ ] Run tests after each major piece
- [ ] Document any blockers

## End of Day (15 min)
- [ ] Update execution log with progress
- [ ] Mark completed acceptance criteria ✓
- [ ] Note any blockers for tomorrow
- [ ] Commit changes with phase reference in message: "WIP: Phase [X] D[X].[#]"
```

---

## Common Work Patterns

### Pattern 1: "Implementing a Deliverable"

```markdown
Working on: D[X].[#]: [Name]

Step 1: Understanding
- [ ] Read deliverable description
- [ ] Review all acceptance criteria (count: [X])
- [ ] List all artifacts to create/modify

Step 2: Design
- [ ] Sketch architecture/schema
- [ ] Identify dependencies
- [ ] Review related deliverables

Step 3: Implementation
- [ ] Create/modify [Artifact 1]
- [ ] Create/modify [Artifact 2]
- [ ] Implement [Feature]

Step 4: Verification
- [ ] Criterion 1: [check method]
- [ ] Criterion 2: [check method]
- [ ] Criterion 3: [check method]
- [ ] All tests passing

Step 5: Documentation
- [ ] Update acceptance criteria: `[x]`
- [ ] Add docstrings/comments
- [ ] Commit with message: "WIP: Phase [X] D[X].[#]: [short description]"
```

### Pattern 2: "Verifying Exit Criteria"

```markdown
Before moving to next phase:

For each exit criterion:
1. Read the criterion carefully
2. Determine how to verify it (test, manual, observation)
3. Perform the verification
4. Document the result
5. Mark: [ ] ✓ or [ ] ✗ with reason

Example:
- [ ] "All CRUD endpoints functional with validation"
  - Verification: Test all 5 endpoints (POST, GET, PUT, DELETE, LIST)
  - Result: All endpoints return correct status codes
  - Status: ✓ Complete

If any criterion is ✗, address it before proceeding.
```

### Pattern 3: "Coordinating Between Agents"

```markdown
Handing off to next agent:

Subject: Phase [X] Exit Criteria Verified - Ready for Phase [X+1]

Body:
- Phase [X] ([Name]) is complete
- All [N] deliverables implemented
- All exit criteria verified and checked ✓
- Known issues/notes for Phase [X+1]:
  - [Issue 1]
  - [Issue 2]
- Files modified: [list]
- Ready for: Phase [X+1] ([Name])

Reference: [Link to PHASE_[X+1]_NAME.md]
Depends On verification: [Confirmation]
```

---

## Troubleshooting: "I'm Stuck"

| Situation | What to Do |
|-----------|-----------|
| **Unclear acceptance criterion** | Read deliverable description again; check "Technical Decisions" table; review related deliverables |
| **Don't understand architecture** | Read QUICK_REFERENCE_FOR_AGENTS.md > Architecture Principles; check PHASE_EXECUTION.instructions.md |
| **Unsure if work is done** | Review acceptance criteria carefully; can you verify each with a test/observation? If not, it's not done. |
| **Blocked by Phase N-1** | Check PHASE_INDEX.md > Cross-Phase Dependencies; verify previous phase exit criteria |
| **Wondering about next steps** | Check "Implementation Sequence" in current phase; what's next on the list? |
| **Not sure about dependencies** | Check PHASE_EXECUTION.instructions.md > Data Layer Progression / Service Layer Progression |

---

## Document References Quick Links

When you need:

| Question | Document | Section |
|----------|----------|---------|
| "What phase am I on?" | PHASE_INDEX.md | Phase Roadmap |
| "What do I do first?" | QUICK_REFERENCE_FOR_AGENTS.md | How Agents Should Use Phase Documents |
| "What has to be done before this?" | Current PHASE_[X].md | Depends On / Entry Criteria |
| "How do I know when I'm done?" | Current PHASE_[X].md | Exit Criteria Checklist |
| "What comes next?" | PHASE_INDEX.md or QUICK_REFERENCE_FOR_AGENTS.md | Phase table |
| "What's the architecture?" | QUICK_REFERENCE_FOR_AGENTS.md | Critical Architecture Principles |
| "How do I track work?" | This document | Execution Checklist |
| "I'm confused about phase order" | PHASE_EXECUTION.instructions.md | How to Structure Work (7-step process) |
| "I made a mistake in phase sequencing" | PHASE_EXECUTION.instructions.md | Common Agent Mistakes to Avoid |

---

## Success Checklist: Phase Complete

When all of these are true, you're done with the phase:

- [ ] All deliverables created (count: X)
- [ ] All acceptance criteria marked ✓ (count: X)
- [ ] All exit criteria verified ✓ (count: X)
- [ ] All tests passing (unit + integration)
- [ ] No blockers or TODOs remaining
- [ ] Documentation complete (docstrings, comments, schema docs)
- [ ] Code reviewed / quality gates passed
- [ ] Ready for next phase transition

---

## Document Metadata

- **Purpose:** Practical execution template for agents
- **Created:** 2026-04-14
- **Use When:** Starting any phase work
- **Update:** Customize the phase/deliverable numbers for your current phase
