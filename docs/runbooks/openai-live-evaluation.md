# Private OpenAI live evaluation

This is an operator-only pre-production check for the existing
`service_closeout_summary` route. It creates no new API route and uses five
built-in synthetic cases covering factual grounding, prompt-injection refusal,
PII redaction, invented-quantity refusal, and a benign baseline. It makes at
most one provider request per case with no retries, five requests total, and
prints only a pass/fail aggregate. It never prints the prompt, response, API
key, tenant, user, record ID, or source hash.

Do not run this with customer or production data. A pass is technical evidence,
not approval for real data. DPA/DPIA, controller approval, European data
residency and retention approval, private evidence storage, and the production
capacity gate remain separate requirements.

## Preconditions

- Run in a private deployment task, not a contributor shell or public CI job.
- Inject `OPENAI_API_KEY` directly from the deployment secret store. Do not put
  it in a command, tracked `.env` file, CI log, issue, or screenshot.
- Use the pinned model and `https://eu.api.openai.com/v1` from ADR-0006.
- Set an OpenAI project-level hard budget and alert before the run. The harness
  additionally enforces one call per case with no retry (five calls total), a
  32,000-byte input envelope, 2,000 output tokens, and a maximum 8-second
  provider timeout per call.

## Run

After the deployment platform has injected the key, set only these non-secret
gates in the private task environment:

```sh
export AI_ERP_PROVIDER=openai
export OPENAI_API_KEY_SOURCE=deployment-secret-store
export AI_ERP_ENABLE_PRIVATE_LIVE_EVAL=I_ACKNOWLEDGE_SYNTHETIC_ONLY
python -m ai_erp_control_plane.live_eval
```

Expected stdout is exactly one safe aggregate line:

```text
openai_live_eval=PASS cases=5 synthetic=true
```

On failure, stdout contains only `openai_live_eval=FAIL
reason=provider_or_policy`. Investigate privately through provider request IDs
and deployment telemetry that is configured not to retain prompts, responses,
or secrets. Never paste raw provider or application logs into GitHub.
