# System Architecture Improvements

## 1. Memory Hierarchy

### Levels
| Level | Scope | Persistence | Size Limit |
|-------|-------|-------------|------------|
| **Working Context** | Per task | Cleared on task complete | ~4K tokens |
| **Session Summary** | Per session | Survives context resets | ~1K tokens |
| **Long-term Store** | Permanent | In `canon.md` + `prompts/` | Unlimited |

### Implementation
- **Working Context:** Current conversation in Discord channel
- **Session Summary:** Controller summarizes every completed task into ≤300 tokens, logged to `#completed`
- **Long-term Store:** `canon.md` (facts, decisions, assumptions), prompt files (rules)

---

## 2. Failure Mode Handling

### Failure Paths
| Failure | Detection | Response |
|---------|-----------|----------|
| Confident but wrong answer | Sanity check by Gemini (free) | Flag uncertainty, suggest verification |
| Conflicting web sources | Require 2+ source agreement | Mark as "unconfirmed" |
| Controller misroutes task | User can override with `!research` or `!build` | Log misroutes for pattern detection |
| API failure | Catch exceptions | Fallback to next model |

### Sanity Check Gate
For heavy reasoning outputs:
1. Run quick check with Gemini: "Does this answer contain obvious errors or contradictions?"
2. If flagged, add disclaimer to output
3. Log for review

---

## 3. Research vs Build Enforcement

### Current (Conceptual)
- Research AI: Claude, reasoning-focused
- Build AI: GPT-4, implementation-focused

### Proposed (Enforced)
| Rule | Research AI | Build AI |
|------|-------------|----------|
| Can speculate | ✅ | ❌ |
| Can explore branches | ✅ | ❌ |
| Can invent features | ❌ | ❌ |
| Can act on unproven assumptions | ✅ (flagged) | ❌ (blocked) |

### Implementation
Build AI prompt already includes:
> "If the request requires inventing new features or redefining the experiment, respond: '⚠️ This requires Research AI approval.'"

**Add:** Research AI must tag outputs as `[SPECULATION]` or `[APPROVED]` so Build AI knows what's actionable.

---

## 4. Kill Assumptions First Gate

Before any major build step, the Controller should:

1. **List top 3 assumptions** for this task
2. **Design cheap tests** to falsify each
3. **Run tests** before scaling effort
4. **Gate:** Only proceed if assumptions survive

### Trigger
Add to `!build` command:
```
Before implementing, list:
1. Top 3 assumptions this depends on
2. How to falsify each cheaply
3. Whether any are already refuted in Canon
```

---

## 5. Summary Update Rule

When a task completes:
1. Controller generates ≤300 token summary
2. Summary includes: what was tested, result, Canon update needed
3. Posted to `#completed` with task
4. Key learnings → `canon.md`

---

## Priority Implementation Order

1. **Kill Assumptions Gate** (immediate) - Add to `!build` prompt
2. **Research/Build tagging** (next) - Add `[SPECULATION]` markers
3. **Session summaries** (later) - Auto-summarize on `!complete`
4. **Sanity check gate** (later) - Add Gemini verification step
