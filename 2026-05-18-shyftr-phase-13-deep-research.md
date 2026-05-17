# ShyftR Phase 13 deep research: full-dataset local runbook and optional judge gating

Date: 2026-05-18
Repo: `/Users/stefan/ShyftR`
Status: research complete; implementation not started

## Starting truth

Phase 12 is complete (closeout: `2026-05-18-shyftr-phase-12-final-closeout.md`). Delivered:
- LongMemEval and BEAM local-path/private-by-default mapping scaffolds
- Deterministic runner-owned answerer/judge contracts
- Opt-in answer-eval integration via `--enable-answer-eval`
- Retrieval metric completion (nDCG, answer-support coverage)
- Optional LLM judge design gate documentation

Phase 12 explicitly did NOT claim any full standard-dataset run. Human approval is still required before downloading full LongMemEval or BEAM, using credentials, or publishing converted artifacts.

## Research question

What external evaluation guidance, licensing rules, and reproducibility guardrails should shape Phase 13 (full-dataset local runbook, dry-run validation, optional LLM judge gating)?

## External benchmark findings

### LongMemEval

**Source:** https://github.com/xiaowu0162/LongMemEval
**Paper:** https://arxiv.org/abs/2410.10813 (ICLR 2025)
**Dataset:** https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned
**License:** MIT

**Key details:**
- 500 evaluation instances across 3 splits:
  - `longmemeval_oracle.json` — evidence sessions only
  - `longmemeval_s_cleaned.json` — ~115k tokens, ~40 history sessions
  - `longmemeval_m_cleaned.json` — ~500 sessions per question
- Question types: `single-session-user`, `single-session-assistant`, `single-session-preference`, `temporal-reasoning`, `knowledge-update`, `multi-session`
- Abstention questions identified by `_abs` suffix in `question_id`
- Each instance contains: `question_id`, `question_type`, `question`, `answer`, `question_date`, `haystack_session_ids`, `haystack_dates`, `haystack_sessions`, `answer_session_ids`
- Sessions are lists of `{role, content, date}` turns; evidence turns marked with `has_answer: true`

**Upstream evaluation method (LLM judge):**
- Uses GPT-4o (`gpt-4o-2024-08-06`) as metric model with temperature=0, max_tokens=10
- Per-question-type prompt templates in `src/evaluation/evaluate_qa.py`:
  - For factual questions (single-session-user, single-session-assistant, multi-session): asks yes/no "does response contain correct answer?"
  - For temporal-reasoning: as above, plus "do not penalize off-by-one errors for number of days"
  - For knowledge-update: accepts responses containing old + updated info as correct
  - For single-session-preference: uses a rubric-based yes/no (correct if user's personal info recalled correctly)
  - For abstention: yes if model correctly identifies question as unanswerable
- Has exponential backoff on OpenAI RateLimitError/APIError
- Evaluation output saved as JSONL with `autoeval_label` field
- Metrics printed: overall accuracy, per-question-type accuracy, task-averaged accuracy, abstention accuracy

**Guardrails for Phase 13:**
- `longmemeval_s_cleaned.json` is the recommended starting split (~115k tokens, fits most context windows)
- `longmemeval_m_cleaned.json` is for stress testing (~500 sessions, very long)
- Per-question isolation is critical: each question's haystack sessions must be ingested, queried, and cleared independently unless a specific experiment declares shared warm memory
- The upstream evaluation uses GPT-4o as judge — ShyftR's deterministic judge should be the default, with optional LLM judge as a gated alternative
- Evidence-level recall accuracy (`has_answer: true` label on turns) and session-level recall (`answer_session_ids`) are upstream metrics ShyftR should optionally support

### BEAM

**Dataset:** https://huggingface.co/datasets/Mohammadta/BEAM
**Paper:** Evaluating LLM abilities for long-term memory tasks (see arXiv)
**License:** CC BY-SA 4.0 (Creative Commons Attribution-ShareAlike 4.0)

**Key details:**
- 100 conversations, 2,000 validated probing questions
- Splits by token count: 100K, 500K, 1M tokens
- 10 memory ability categories:
  - Abstention, Contradiction Resolution, Event Ordering, Information Extraction
  - Instruction Following, Knowledge Update, Multi-Session Reasoning
  - Preference Following, Summarization, Temporal Reasoning
- Each conversation includes: `conversation_id`, `conversation_seed` (category, id, subtopics, theme, title), `conversation_plan`, `user_questions` (with messages and questions)
- BEAM-10M dataset also exists at `Mohammadta/BEAM-10M` for extreme-scale testing

**Guardrails for Phase 13:**
- **License obligation:** CC BY-SA 4.0 requires attribution to the original authors AND any derivative works (including converted fixtures, reports using BEAM data) must be shared under the same license. This is stricter than MIT. ShyftR reports containing BEAM-derived metrics must include the CC BY-SA 4.0 notice.
- Start with 100K split only; 500K and 1M splits require explicit operator choice
- BEAM-10M should not be mapped until timeout/chunking/resume controls are proven on smaller splits
- The BEAM question structure (ability categories) maps cleanly to `BenchmarkQuestion.question_type`

### LLM-as-Judge Reproducibility

**Key sources:**
1. "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" — https://arxiv.org/abs/2306.05685
2. "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment" — https://arxiv.org/abs/2303.16634
3. "Who Validates the Validators?" (EvalGen) — https://arxiv.org/abs/2404.12272
4. LongMemEval's own judge implementation — https://github.com/xiaowu0162/LongMemEval/blob/main/src/evaluation/evaluate_qa.py

**Known biases (from MT-Bench paper):**
- **Position bias:** LLM judges prefer answers in certain positions (mitigated by swapping positions and averaging)
- **Verbosity bias:** Longer answers tend to score higher regardless of quality
- **Self-enhancement bias:** LLMs favor their own outputs over other models'
- **Limited reasoning:** LLM judges struggle with complex multi-step reasoning evaluation

**Reproducibility guardrails:**
- **Pin everything:** model name + version (e.g., `gpt-4o-2024-08-06`), temperature (always 0 for judging), max_tokens, prompt template hash
- **Deterministic-first:** Always run deterministic composite judge first; LLM judge is a supplementary second pass
- **Skip gracefully:** Missing credentials must produce `skipped` status, not a crash or silent fallback
- **Prompt versioning:** Every LLM judge prompt must be versioned (hash or version string) and recorded in report metadata
- **Cost tracking:** Token counts and cost estimates must be recorded per-judgment and aggregated
- **Rate-limit handling:** Use exponential backoff (as LongMemEval does) with configurable max retries
- **Judgment log:** Save raw LLM judge responses as JSONL sidecar for auditability (LongMemEval pattern)
- **Agreement check:** When both deterministic and LLM judges run, report agreement rate

**LongMemEval-specific judge design (for optional P13 LLM judge):**
- Per-question-type prompt templates (see evaluate_qa.py)
- Binary yes/no output with `temperature=0`, `max_tokens=10`
- GPT-4o is the standard metric model; open-weight alternatives served via vLLM at `http://localhost:8001/v1`
- ShyftR should support both OpenAI API and local vLLM endpoints

### Data Licensing and Output Safeguards

| Dataset | License | Attribution Required? | Share-Alike? | Derivative Rules |
|---------|---------|----------------------|--------------|------------------|
| LongMemEval (`xiaowu0162/longmemeval-cleaned`) | MIT | No (but cite paper) | No | Free use, modification, distribution |
| BEAM (`Mohammadta/BEAM`) | CC BY-SA 4.0 | Yes | Yes | Derivatives must use same license; must credit original |
| LOCOMO (`snap-research/locomo`) | Custom/Academic | Check upstream | Unknown | Do not vendor; recheck before publishing |

**Output safeguard rules (from Phase 12 + extensions for Phase 13):**
- Converted fixtures must stay under `artifacts/`, `reports/`, or `tmp/`
- Default `contains_private_data=true` for any operator-provided file
- `--public-output` only allowed when `contains_private_data=false` is explicitly declared
- Reports containing BEAM-derived metrics must include CC BY-SA 4.0 notice
- Never commit converted third-party dataset files to the repo
- Full-dataset reports go under `reports/benchmarks/` with SHA-256 manifest sidecars
- Public reports must not contain actual dataset content (only aggregate metrics)

## Practical Phase 13 guardrails

### P13-0: Full-dataset local runbook

**Operator prerequisites (document in runbook, do not automate):**
1. Obtain LongMemEval or BEAM outside the implementation run after explicit human approval.
2. Place the approved local file at a path represented in docs as `<LOCAL_LONGMEMEVAL_JSON>` or `<LOCAL_BEAM_JSON>`.
3. Keep local dataset files outside committed repo content or under an ignored scratch area.
4. Declare `contains_private_data` appropriately and keep the default private when unsure.

**Runbook command shape (placeholders only):**
```bash
# Convert an operator-provided LongMemEval file to a guarded ShyftR fixture.
PYTHONPATH=.:src python scripts/convert_longmemeval_standard_fixture.py \
  --input <LOCAL_LONGMEMEVAL_JSON> \
  --output artifacts/benchmarks/<RUN_ID>.fixture.json
  --allow-private-input

# Dry-run: bounded local validation with deterministic answer-eval.
# Requires P13-1 runner flags before it is executable.
PYTHONPATH=.:src python scripts/run_memory_benchmark.py \
  --fixture-path artifacts/benchmarks/<RUN_ID>.fixture.json \
  --fixture-format longmemeval-standard \
  --run-id <RUN_ID>-dryrun \
  --output artifacts/benchmarks/<RUN_ID>-dryrun.json \
  --top-k 1,3,5,10 \
  --limit-questions 5 \
  --isolate-per-case \
  --enable-answer-eval \
  --allow-private-fixture
```

**Per-case reset contract:**
- Runner must reset backend state between benchmark questions when the flag is enabled.
- Each question's haystack sessions are ingested fresh.
- No cross-question memory leakage.
- Shared warm-memory experiments are out of scope for P13-0..P13-2.

**Timeout and resume:**
- `--timeout-seconds 300` recommended for full LongMemEval runs (500 questions x ingest + search)
- `--max-retries 2` recommended
- `--resume-existing` for interrupted runs

### P13-1: Dry-run validation

**Purpose:** Validate the full pipeline on a tiny subset before committing to a full run.

**Dry-run contract:**
- Run exactly N questions (initially N=5, configurable via `--dry-run-limit N`)
- Must complete within a few minutes
- All backends (ShyftR, no-memory, optional mem0) must participate
- Report must include `dry_run: true` and `dry_run_limit: N`
- Must catch: schema mismatches, conversion errors, timeout configuration issues, per-question isolation failures

**Validation checklist (automated in dry-run mode):**
1. Fixture loads without error
2. All questions parse into `BenchmarkQuestion` objects
3. All haystack sessions parse into `BenchmarkConversation` objects
4. Per-question reset does not crash
5. Deterministic answer-eval produces valid `AnswerResult` and `JudgeResult` per question
6. Report JSON validates against schema
7. No backend produces unexpected `failed` status
8. SHA-256 manifest matches fixture

### P13-2: Optional LLM judge gating

**Design requirements (from P12-7, extended):**
1. **Provider interface:** Explicit CLI flag `--llm-judge-provider openai|local-vllm`, never inferred from ambient env
2. **Model pinning:** `--llm-judge-model gpt-4o-2024-08-06` or local equivalent; report must include exact model version
3. **Prompt versioning:** Each prompt template gets a version hash; recorded in report metadata
4. **Temperature:** Always 0 for judging
5. **Credentials:** Missing `OPENAI_API_KEY` or unreachable vLLM endpoint produces `skipped` judge status, not a crash
6. **Cost tracking:** Token counts per judgment + cost estimate; aggregated in report
7. **Rate limiting:** Exponential backoff with configurable `--llm-judge-max-retries`
8. **Judgment log:** Save raw LLM responses as JSONL sidecar (`artifacts/benchmarks/{run_id}_llm_judgments.jsonl`)
9. **Deterministic-first:** Always run deterministic composite judge; LLM judge is a supplementary pass
10. **Agreement reporting:** Report agreement rate between deterministic and LLM judges

**Per-question-type prompt templates (adapted from LongMemEval evaluate_qa.py):**
- ShyftR should use the same prompt templates as LongMemEval for comparability
- Question type mapping: LongMemEval types → ShyftR prompt variant
- Abstention detection: `_abs` suffix in `question_id` → use abstention prompt

**Output posture:**
- Private scaling outputs must stay under guarded local directories
- Reports containing LLM judge results must disclose: model, prompt version, temperature, token counts, cost
- LLM judge results must not supersede deterministic results in primary metrics; they are supplementary

**Claim boundaries for LLM judge results:**
- Allowed: "Under judge model X at temperature 0, backend A scored Y on dataset Z"
- Not allowed: "Backend A is better at answering" without disclosing judge model, prompt, and agreement with deterministic baseline

## BEAM-specific runbook notes

**License obligation for reports:** Any ShyftR report containing BEAM-derived metrics must include:
```
This report uses data from the BEAM dataset (CC BY-SA 4.0).
Original: https://huggingface.co/datasets/Mohammadta/BEAM
Attribution: Mohammadta/BEAM contributors
```

**Start small rule:**
- Phase 13 should start with the BEAM 100K split only
- 500K and 1M splits gated behind explicit `--beam-split` flag and operator approval
- BEAM-10M is out of scope for Phase 13

**BEAM ability types → ShyftR `question_type` mapping:**
- The BEAM mapper already preserves ability labels in `question_type`
- The LLM judge needs per-ability prompt templates (BEAM paper defines expected answer formats per ability)

## Runbook safety checklist

Before any full-dataset run, confirm:
- [ ] Dataset file is local, not auto-downloaded
- [ ] `contains_private_data` is correctly declared
- [ ] Output path is under `artifacts/`, `reports/`, or `tmp/`
- [ ] Dry-run completed successfully on 5+ questions
- [ ] Per-question isolation verified (no cross-question leakage)
- [ ] Timeout and resume config is appropriate for dataset size
- [ ] No credentials are stored in committed files
- [ ] LLM judge (if enabled) uses pinned model + temperature=0
- [ ] Report includes all required metadata (schema version, git SHA, model names, etc.)
- [ ] BEAM-derived reports include CC BY-SA 4.0 attribution
- [ ] `claims_allowed` and `claims_not_allowed` are populated honestly

## Recommended Phase 13 tranche ordering

| Tranche | Title | Stop boundary |
|---------|-------|---------------|
| P13-0 | Contract-first local full-dataset runbook | Docs and approval checklist only; no dataset download, no full run |
| P13-1 | Dry-run and per-case reset runner controls | Bounded local validation support only; no full standard-dataset run by default |
| P13-2 | Optional LLM judge gating scaffold | Skip-safe code/tests only; no credentials required and no paid calls |

No public-summary tranche is included in this Phase 13 plan slice.

## Key source URLs

- LongMemEval paper: https://arxiv.org/abs/2410.10813
- LongMemEval repo: https://github.com/xiaowu0162/LongMemEval
- LongMemEval dataset: https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned (MIT)
- LongMemEval evaluation script: https://github.com/xiaowu0162/LongMemEval/blob/main/src/evaluation/evaluate_qa.py
- BEAM dataset: https://huggingface.co/datasets/Mohammadta/BEAM (CC BY-SA 4.0)
- MT-Bench LLM-as-judge paper: https://arxiv.org/abs/2306.05685
- G-Eval paper: https://arxiv.org/abs/2303.16634
- EvalGen (Who Validates the Validators?): https://arxiv.org/abs/2404.12272
- FastChat LLM Judge code: https://github.com/lm-sys/FastChat/tree/main/fastchat/llm_judge
- CC BY-SA 4.0 full text: https://creativecommons.org/licenses/by-sa/4.0/
