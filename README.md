# Urban Air Quality Assistant

AI-powered web app that helps families and communities in Indian cities
cope with winter smog and urban air pollution through personalized,
actionable, explained recommendations.

Built for Hack2skill PromptWars Virtual, Challenge 6.

## Problem Statement

Build a Generative AI-powered Urban Air Quality Assistant that helps
families and communities manage severe winter smog and pollution through
personalized guidance. It must cover three areas:

1. **Low-emission daily routines**
   - Suggest lower-emission alternatives to usual commutes/activities.
   - Adjust plans using real-time outdoor AQI (PM2.5, PM10, etc.).
   - Plan to minimize pollution exposure, tailored to the user's city
     (Delhi, Mumbai, Kolkata, etc.).
2. **Indoor air quality improvement**
   - Actionable steps (purifiers, indoor plants, ventilation timing),
     not just reporting numbers.
3. **Sustainable alternatives with impact explanation**
   - Every recommendation must include a clear, simple explanation of
     how the choice affects air quality and health.

### Users and personalization
- Families with children (e.g., outdoor playtime decisions)
- Senior citizens (more cautious advice)
- Working professionals (commute and office air)
- Students (outdoor activities)

Two users in the same city must NOT get identical advice. Advice depends
on persona, lifestyle, commute, and location.

The app must be simple and understandable for non-experts.

## Hard Rules
- **Real-time AQI data only.** No mock, simulated or static data. If the
  data source fails, show the last real reading with its timestamp and
  say it is stale. Never invent values.
- Public data sources for AQI (e.g., OpenAQ, CPCB). Free options only
  unless I approve otherwise.
- No secrets in code or in the repo. Use `.env`, and keep `.env` in
  `.gitignore`.
- Validate all user inputs on the backend.
- Original work only.

## Tech Stack
- **Backend:** Python, FastAPI
- **Frontend:** React
- **AI:** Gemini API (called only from the backend)
- **Deployment:** TBD (live public URL is required)

## AQI Provider

`GET /api/cities` returns the backend-supported city allowlist used by the
frontend profile form.

Set `OPENAQ_API_KEY` in `.env` to enable `GET /api/aqi?city=Delhi`. The endpoint
selects the nearest station within 10 km that has PM2.5 and PM10 readings no
older than 48 hours, then calculates AQI using CPCB breakpoints. Responses
include the station, source, pollutant observation times, and a stale flag.
If OpenAQ fails, the last successful reading is returned with `is_stale: true`;
this in-memory cache is cleared when the backend restarts.

## Planned Features
- Profile form: city, persona, commute mode, has purifier (y/n)
- Live AQI card (PM2.5, PM10, AQI, last updated time)
- Personalized advice from Gemini as structured JSON:
  daily routine (time-specific), indoor actions, sustainable swaps with
  "why it helps"
- Persona comparison: preset profiles so two personas in the same city
  can be compared side by side

## Quality Requirements (automated scoring)
- Clean, modular code and clear project structure
- Unit tests (pytest) for AQI parsing and the advice endpoint
- Input validation, basic rate limiting, safe error handling
- Accessible UI: labels, contrast, keyboard navigation
- Clear README with setup instructions and sample inputs

## Submission Checklist
- [ ] Deployed app link (tested in incognito)
- [ ] Public GitHub repo
- [ ] Demo video (2-3 minutes)
- [ ] LinkedIn post: thought process, architecture, tools, prompt evolution
- [ ] README documents tool choices, prompt engineering process, and
      what the human did vs what the AI did

## Working Agreement for the AI Agent
- Always write a plan first and wait for my approval before coding.
- Work in small tasks. Show me diffs.
- Ask before adding any paid service or new major dependency.
- Never hardcode keys or use fake data to make a demo pass.