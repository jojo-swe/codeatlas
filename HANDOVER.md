# HANDOVER.md

Överlämning mellan agenter och sessioner. Läs innan du börjar, uppdatera innan du slutar.

## Aktuellt läge

*Senast inventerat 2026-11-04 av Claude (Cowork).*

Projekt: CodeAtlas turns a Python repository into an interactive symbol, dependency, change-impact and engineering-risk map without executing the target code.

- Huvudbranch: `main`
- Senaste commit på `main`: 2026-11-01 `9582cf9` Add privacy guard checks for the working tree (#5)
- Öppna PR:er: 0
- Andra brancher på remote: 5

## Pågående arbete

| Agent/vem | Branch | Status | Beskrivning |
|-----------|--------|--------|-------------|
| Cursor | `cursor/privacy-guard-4d73` | branch utan PR, senaste commit 2026-11-01 | Add privacy guard checks for the working tree |
| Cursor | `agent/symbol-resolution-mermaid` | branch utan PR, senaste commit 2026-10-03 | Clear ruff findings on the merged tree |
| okänd (människa/agent) | `agent/architecture-policies` | branch utan PR, senaste commit 2026-07-19 | Document architecture policies and CI guardrails |
| okänd (människa/agent) | `agent/interactive-web-ui` | branch utan PR, senaste commit 2026-07-18 | docs: document git intelligence and ownership guardrails |
| okänd (människa/agent) | `agent/graph-intelligence` | branch utan PR, senaste commit 2026-07-18 | Test graph hotspots cycles impact and Mermaid export |

## Nästa steg

- Gå igenom brancher utan PR: öppna PR, merga eller radera (fråga användaren innan radering).
- Fyll på "Bygga och testa" i AGENTS.md om något saknas eller är fel.

## Kända problem

- Inga dokumenterade ännu.

## Senaste commits

- 2026-11-01 `9582cf9` Add privacy guard checks for the working tree (#5)
- 2026-10-03 `667083e` Merge pull request #1 from jojo-swe/agent/symbol-resolution-mermaid
- 2026-10-03 `fc1df69` Clear ruff findings on the merged tree
- 2026-10-03 `d547067` Merge origin/main into agent/symbol-resolution-mermaid
- 2026-07-20 `5166e31` Merge pull request #4 from jojo-swe/agent/architecture-policies
- 2026-07-19 `baaa910` Document architecture policies and CI guardrails
- 2026-07-19 `0ac0e9f` Add example layered architecture policy
- 2026-07-19 `9d6eed6` Test architecture policy evaluation
- 2026-07-19 `3599dd1` Integrate architecture policies into CLI and reports
- 2026-07-19 `72e5012` Add architecture policy engine

## Logg

| Datum | Agent | Vad som gjordes |
|-------|-------|-----------------|
| 2026-11-04 | Claude (Cowork) | Lade till AGENTS.md, HANDOVER.md och CLAUDE.md; inventerade PR:er, brancher och commits. |
