# SDD ledger — plan: docs/superpowers/plans/2026-11-26-researchagent.md

Spec approved by user on 2026-11-26. Independent project and upload authorized.
Pre-flight: ingestion->retrieval->PaperQA->workflow->API contracts aligned.
Ruling: use separate local project directory, feature branch, connector upload if shell Git credentials fail; do not include resume workspace data.

Task 1: complete — PDF/SQLite tests passed.
Task 2: complete — actual FAISS and PaperQA pipeline, local HTTP provider tests passed.
Task 3: complete — LangGraph, real MCP local transport, API and desktop/mobile checks passed.
Task 4: verification complete — 19 tests, lint and pip check pass; BM25 synthetic evaluation executed. Uploaded and remote contents verified: 55d17d3240ea2cb296fc1fce8291e399b6693a76.
Review: independent reviewer found no Critical/Important blockers; malformed embedding response classification fixed with regression test. Thread cancellation limitation documented; embedding batches now share a deadline.
Ruling: pin LiteLLM 1.83.9 for tested PaperQA compatibility; Windows install needed extended-length target for dependency files. Recommend short checkout path for users. Keep credentials and running data out of Git.
