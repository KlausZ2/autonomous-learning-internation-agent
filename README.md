# Instagram Comment Agent

The custom context policy lives in `policy/policy_for_context.txt`. The backend loads that file every time it calls the LLM, so editing the text file immediately changes the agent behavior without code changes.

## Actions

The agent is fully automatic and only uses:

- `reply_public`
- `ignore`
- `hide`
- `delete`

No other actions are implemented.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your Meta token and IDs:

```env
OPENAI_API_KEY=
META_ACCESS_TOKEN=
IG_BUSINESS_ACCOUNT_ID=17841417684673566
FB_PAGE_ID=1138256019376037
```

Run:

```powershell
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Useful Endpoints

- `GET /health`
- `GET /policy`
- `GET /memory`
- `GET /interactions`
- `POST /agent/decide`
- `POST /instagram/sync-media`
- `POST /instagram/process-media/{media_id}`
- `POST /feedback`
- `POST /memory/teach`
- `POST /memory/consolidate`
- `GET /audit`

## Current Coding Plan Status

Done:

- Adaptive style selector chooses `professional` or `humorous` from context, memories, inside jokes, and policy.
- Reply generator writes the final reply from the selected style and the same policy context.
- Human-edited inside jokes are loaded from `inside_jokes_database.jsonl`.
- Learned memories are loaded from `memory_store.jsonl`.
- Every processed comment is logged to `interactions.jsonl`.
- Feedback can be attached to an interaction with `POST /feedback`.
- Strong positive or negative feedback writes a reflection memory automatically.
- Manual teaching memories can be added with `POST /memory/teach`.
- Duplicate active memories can be cleaned up with `POST /memory/consolidate`.

## Feedback Loop

1. Run `POST /instagram/process-media/{media_id}`.
2. Open `GET /interactions` and copy the `interaction_id` you want to rate.
3. Run `POST /feedback` with either `rating` from 1 to 5 or a `label` such as `good`, `bad`, or `terrible`.
4. Ratings of 5/1 or strong labels create a new active memory in `memory_store.jsonl`.

Example feedback body:

```json
{
  "interaction_id": "int_example",
  "rating": 5,
  "note": "This used the right short, teasing tone."
}
```

Example manual teaching body:

```json
{
  "lesson": "For casual Chinese comments, keep replies short and naturally Chinese.",
  "style": "humorous",
  "trigger": "中文评论"
}
```
