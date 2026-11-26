# Urban Air Quality Assistant Tasks

| # | Task | Output |
|---|------|--------|
| 0 | Create the repo scaffold, `.gitignore`, `.env.example`, and app configuration | Skeleton app and health endpoint |
| 1 | Compare OpenAQ and CPCB coverage across Delhi, Mumbai, Kolkata, Chennai, Bengaluru, and Hyderabad | Provider findings and recommendation |
| 2 | Build the AQI provider client, parser, and stale-reading cache | Working `/api/aqi?city=` endpoint |
| 3 | Add pytest coverage for AQI parsing and stale fallback | Passing AQI tests |
| 4 | Define Pydantic schemas, input validation, and rate limiting | Hardened API input layer |
| 5 | Build the Gemini advice service and versioned prompt | Working `/api/advice` endpoint |
| 6 | Add mocked Gemini advice endpoint tests | Passing advice tests |
| 7 | Build the React profile form and AQI card | Accessible form and live AQI display |
| 8 | Build the advice display and side-by-side persona comparison | Complete frontend flow |
| 9 | Iterate prompts through v2/v3 and record changes | Prompt evolution log |
| 10 | Deploy the application and test the public URL in incognito | Public deployed link |
| 11 | Prepare README, demo script, and LinkedIn post | Submission pack |
