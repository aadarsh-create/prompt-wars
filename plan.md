# Plan: Urban Air Quality Assistant

## 1. Architecture

```
React (Vite)  ──▶  FastAPI  ──▶  AQI provider (OpenAQ / CPCB)
                      │
                      └──▶  Gemini (server-side only)
```

One deployable unit: FastAPI serves the built React files and the `/api/*` routes. That means one URL, no CORS setup, and one place to deploy and test in incognito.

```
backend/app/
  main.py          # app factory, middleware, routers
  config.py        # env settings (pydantic-settings)
  schemas.py       # request/response models (validation lives here)
  routers/         # aqi.py, advice.py, health.py
  services/
    aqi_client.py  # fetch + parse provider data
    aqi_cache.py   # last-real-reading store, with timestamp
    advice.py      # prompt build, Gemini call, JSON validation
  prompts/         # versioned prompt files (feeds the "prompt evolution" post)
backend/tests/
frontend/src/      # components/, api/, pages/
README.md, .env.example, .gitignore
```

## 2. Key design decisions

**AQI data (hard rule: real only)**
- Primary source: OpenAQ (v3, free API key) or CPCB via data.gov.in (free key). Day 1 spike: check which one actually returns recent PM2.5/PM10 for Delhi, Mumbai, Kolkata, Hyderabad, Chennai and Bengaluru, and pick the one with better coverage.
- Every reading carries `observed_at`, `source` and `is_stale`.
- On provider failure, return the last real reading with `is_stale: true` and a visible "Last updated X ago" banner. If there is no prior reading, return an honest "data unavailable" and no advice built on invented numbers.
- Where the source gives no AQI, compute it from PM2.5/PM10 using the CPCB breakpoints. That is a documented calculation, not fake data.

**Advice (Gemini)**
- The backend builds the prompt from validated profile + live AQI + city, then requests structured JSON through Gemini's response schema.
- The output is re-validated with Pydantic. On malformed output, retry once, then return a safe error.
- Output shape: `daily_routine[]` (time slot, action, why), `indoor_actions[]`, `sustainable_swaps[]` (swap, why it helps air and health), `caution_level`, `summary`.
- Personalization is explicit in the prompt: persona rules (seniors are more cautious, kids' playtime gets a go/no-go with AQI thresholds), commute mode, purifier yes/no, and the city's typical pollution sources.
- Prompts live in versioned files, and I'd log what changed between versions as we go, since the LinkedIn post and README both need that.

**Persona comparison**
- Presets are two or more persona profiles (e.g. child family vs. senior vs. commuting professional). The same city's AQI is fetched once and the advice endpoint is called per persona. The UI shows them side by side.

**Safety and quality**
- Pydantic validation with allowlists for city and persona and bounded enums for commute mode.
- `slowapi` rate limiting per IP, tighter on the advice endpoint since it spends Gemini quota.
- Generic error messages to the client, details only in server logs. Secrets only in `.env`, plus `.env.example`.
- Tests use pytest with provider-response fixtures for AQI parsing and a mocked Gemini for the advice endpoint. The fixtures exist only in tests and never reach runtime, so they don't conflict with the no-mock-data rule. I'd note that distinction in the README.
- Accessibility: labelled form fields, colour-plus-text AQI categories (not colour alone), keyboard-navigable, visible focus states, and an `aria-live` region for results.

## 3. Task breakdown

Each task is small, ends with a diff for you to review, and waits for your OK.

| # | Task | Output |
|---|------|--------|
| 0 | Repo scaffold, `.gitignore`, `.env.example`, config | Skeleton and a health endpoint |
| 1 | AQI source spike (check both providers for the 6 cities) | Short findings and a recommendation |
| 2 | `aqi_client` + parser + stale-fallback cache | Working `/api/aqi?city=` |
| 3 | Pytest for AQI parsing and fallback | Green tests |
| 4 | Schemas + validation + rate limiting | Hardened input layer |
| 5 | Gemini service + prompt v1 + schema'd JSON | `/api/advice` |
| 6 | Pytest for advice endpoint (mocked Gemini) | Green tests |
| 7 | React: profile form + AQI card | Accessible form, live card |
| 8 | React: advice display + persona comparison | Full flow |
| 9 | Prompt iteration pass (v2/v3) and notes | Prompt evolution log |
| 10 | Deploy, then test the live URL in incognito | Public URL |
| 11 | README, demo video script, LinkedIn post draft | Submission pack |

If time gets tight, 9 can shrink. Everything else is needed for the checklist.

## 4. Submission checklist mapping
- **Deployed link**: task 10.
- **Public repo**: from task 0. Make it public at the end, after checking the git history for leaked keys.
- **Demo video**: a 2-3 minute script covering Delhi with two personas, the stale-data banner, and the impact explanations.
- **LinkedIn post and README "human vs AI"**: keep a running log from task 0 of what you decided and what the agent produced, so you aren't reconstructing it at the end.

## 5. Decisions I need from you
1. **Deployment host.** I'd suggest Render, since you've used it already. The catch is free-tier cold starts, which could hurt an automated checker, so I'd add a lightweight keep-warm or a loading state. Alternatives are Railway or Cloud Run.
2. **Stale-reading storage.** Start with an in-memory cache plus a small file, which is free and has no new dependency. It resets on redeploy or restart, so the "last real reading" would be lost then. Neon would persist it but adds a dependency. Do you want Neon or the lighter option?
3. **AQI provider.** Approve the Day 1 spike (task 1) and let the findings decide, or do you already prefer one?
4. **Gemini model and quota.** I'd verify the current free-tier model name and limits at task 5 instead of assuming. OK?
5. **City scope.** Is 6 cities enough (Delhi, Mumbai, Kolkata, Chennai, Bengaluru, Hyderabad), or do you want free-text city entry? Free text means more validation work and a higher chance of no data, so I'd go with the allowlist.

Reply with approvals or changes, and I'll start at task 0.