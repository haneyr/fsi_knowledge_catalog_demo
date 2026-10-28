# Agent Operating Rules — Retail KC Demo Refactor

## Token discipline (most important)
1. NEVER re-read a file you already summarized. STATE.md is your memory.
2. NEVER hand-edit in bulk. For any change touching >3 files, WRITE A SCRIPT
   (tools/transform.py driven by tools/retail_mapping.json), run it once, then
   spot-check exactly 5 representative files. Do not read the rest.
3. Long-running commands (post_deploy.sh ~30+ min, agent deploys) run backgrounded
   to a log, then poll:
   nohup bash X.sh > logs/X.log 2>&1 &  →  sleep 120; tail -5 logs/X.log
   NEVER dump a full log into context. Grep only for Error|Traceback|FAILED|409|403.
4. Batch cloud calls into scripts under tools/. No dozens of one-off terminal commands.
5. Surgical reads only: grep -n, head, sed -n '1,40p'. Not whole files.
6. Never print directory listings >50 lines. Never echo file contents back.

## Error policy
7. On failure: ONE self-correction attempt. If it fails again, STOP, write the failure
   and diagnosis to STATE.md, and ask. Never retry-loop.
8. Every script must be IDEMPOTENT and resumable. A failure at step N must never
   require redoing steps 1..N-1.

## Safety
9. Never terraform destroy. Never delete BQ datasets. Never delete the project.
10. Never commit secrets (OAuth client IDs go to Secret Manager, not git).
11. If a cloud resource already exists, report it — do not overwrite.

## Git
12. Work only on branch `retail-refactor`. Never touch `main`.
13. origin = aelitchfield/knowledge_catalog_demo (safe to push, but ASK first).
    upstream = haneyr/fsi_knowledge_catalog_demo (NEVER push).
14. Never force-push, never rewrite history.
