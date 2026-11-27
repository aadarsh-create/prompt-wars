import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

const CITIES = [
  "Delhi",
  "Mumbai",
  "Kolkata",
  "Chennai",
  "Bengaluru",
  "Hyderabad",
];

const PERSONAS = [
  { value: "child_family", label: "Child or family" },
  { value: "senior", label: "Senior" },
  { value: "working_professional", label: "Working professional" },
  { value: "student", label: "Student" },
];

const COMMUTE_MODES = [
  { value: "none", label: "Mostly indoors" },
  { value: "walk", label: "Walk" },
  { value: "cycle", label: "Cycle" },
  { value: "public_transport", label: "Public transport" },
  { value: "car", label: "Car" },
];

function categoryClass(category) {
  return category.toLowerCase().replace(/[^a-z]+/g, "-");
}

function formatObservedAt(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function App() {
  const [profile, setProfile] = React.useState({
    city: "Delhi",
    persona: "working_professional",
    commuteMode: "public_transport",
    hasPurifier: false,
  });
  const [reading, setReading] = React.useState(null);
  const [status, setStatus] = React.useState("idle");
  const [error, setError] = React.useState("");
  const [comparePersona, setComparePersona] = React.useState("senior");
  const [adviceResults, setAdviceResults] = React.useState([]);
  const [adviceStatus, setAdviceStatus] = React.useState("idle");
  const [adviceError, setAdviceError] = React.useState("");

  async function loadAqi(city) {
    setStatus("loading");
    setError("");

    try {
      const response = await fetch(`/api/aqi?city=${encodeURIComponent(city)}`);
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Air-quality data is unavailable.");
      }

      setReading(payload);
      setStatus("success");
    } catch (requestError) {
      setReading(null);
      setStatus("error");
      setError(requestError.message || "Could not load air-quality data.");
    }
  }

  React.useEffect(() => {
    loadAqi(profile.city);
  }, []);

  function handleProfileChange(event) {
    const { name, value, type, checked } = event.target;
    setProfile((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
    if (name === "persona") {
      setComparePersona(value === "senior" ? "working_professional" : "senior");
      setAdviceResults([]);
      setAdviceStatus("idle");
      setAdviceError("");
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    setAdviceResults([]);
    setAdviceStatus("idle");
    setAdviceError("");
    loadAqi(profile.city);
  }

  function profilePayload(persona) {
    return {
      city: profile.city,
      persona,
      commute_mode: profile.commuteMode,
      has_purifier: profile.hasPurifier,
    };
  }

  async function getAdvice(personas) {
    if (!reading) return;

    setAdviceStatus("loading");
    setAdviceError("");
    setAdviceResults([]);

    try {
      const responses = await Promise.all(
        personas.map(async (persona) => {
          const response = await fetch("/api/advice", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ profile: profilePayload(persona.value) }),
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.detail || "Personalized advice is unavailable.");
          }
          return { ...persona, advice: payload };
        }),
      );
      setAdviceResults(responses);
      setAdviceStatus("success");
    } catch (requestError) {
      setAdviceStatus("error");
      setAdviceError(requestError.message || "Could not generate personalized advice.");
    }
  }

  return (
    <main className="app-shell">
      <header className="page-header">
        <p className="eyebrow">Urban air guide</p>
        <h1>Plan your day around the air</h1>
        <p className="intro">
          Check the live AQI and tailor the next steps to your household.
        </p>
      </header>

      <div className="dashboard">
        <form className="profile-form" onSubmit={handleSubmit} aria-label="Air quality profile">
          <h2>Your profile</h2>

          <div className="field">
            <label htmlFor="city">City</label>
            <select id="city" name="city" value={profile.city} onChange={handleProfileChange}>
              {CITIES.map((city) => (
                <option key={city} value={city}>{city}</option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="persona">Who is this for?</label>
            <select id="persona" name="persona" value={profile.persona} onChange={handleProfileChange}>
              {PERSONAS.map((persona) => (
                <option key={persona.value} value={persona.value}>{persona.label}</option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="commuteMode">Daily commute</label>
            <select id="commuteMode" name="commuteMode" value={profile.commuteMode} onChange={handleProfileChange}>
              {COMMUTE_MODES.map((mode) => (
                <option key={mode.value} value={mode.value}>{mode.label}</option>
              ))}
            </select>
          </div>

          <label className="checkbox-field" htmlFor="hasPurifier">
            <input
              id="hasPurifier"
              name="hasPurifier"
              type="checkbox"
              checked={profile.hasPurifier}
              onChange={handleProfileChange}
            />
            <span>I have an indoor air purifier</span>
          </label>

          <button type="submit" disabled={status === "loading"}>
            {status === "loading" ? "Checking air…" : "Check air quality"}
          </button>

          <div className="advice-actions" aria-label="Advice options">
            <button
              type="button"
              className="secondary-button"
              disabled={!reading || status !== "success" || adviceStatus === "loading"}
              onClick={() => getAdvice([PERSONAS.find((item) => item.value === profile.persona)])}
            >
              {adviceStatus === "loading" ? "Preparing advice…" : "Get advice"}
            </button>

            <div className="comparison-control">
              <label htmlFor="comparePersona">Compare with</label>
              <select
                id="comparePersona"
                value={comparePersona}
                onChange={(event) => setComparePersona(event.target.value)}
              >
                {PERSONAS.filter((persona) => persona.value !== profile.persona).map((persona) => (
                  <option key={persona.value} value={persona.value}>{persona.label}</option>
                ))}
              </select>
              <button
                type="button"
                disabled={!reading || status !== "success" || adviceStatus === "loading"}
                onClick={() => getAdvice([
                  PERSONAS.find((item) => item.value === profile.persona),
                  PERSONAS.find((item) => item.value === comparePersona),
                ])}
              >
                Compare personas
              </button>
            </div>
          </div>
        </form>

        <section className="aqi-card" aria-labelledby="aqi-heading" aria-live="polite">
          <div className="card-heading">
            <div>
              <p className="label">Current reading</p>
              <h2 id="aqi-heading">{profile.city}</h2>
            </div>
            {reading?.source && <span className="source">{reading.source}</span>}
          </div>

          {status === "loading" && (
            <p className="card-message" role="status">Loading current air quality…</p>
          )}

          {status === "error" && (
            <div className="error-message" role="alert">
              <strong>Reading unavailable</strong>
              <p>{error}</p>
              <button type="button" onClick={() => loadAqi(profile.city)}>Try again</button>
            </div>
          )}

          {reading && (
            <>
              {reading.is_stale && (
                <p className="stale-banner" role="status">
                  <strong>Last available reading</strong>
                  <span> This reading may be outdated.</span>
                </p>
              )}

              <div className="reading">
                <div
                  className={`aqi-value ${categoryClass(reading.category)}`}
                  aria-label={`AQI ${reading.aqi}, ${reading.category}`}
                >
                  <strong>{reading.aqi}</strong>
                  <span>AQI</span>
                </div>
                <div className="category">
                  <span className={`category-dot ${categoryClass(reading.category)}`} aria-hidden="true" />
                  <strong>{reading.category}</strong>
                </div>
              </div>

              <dl className="pollutants">
                <div>
                  <dt>PM2.5</dt>
                  <dd>{reading.pm25} µg/m³</dd>
                </div>
                <div>
                  <dt>PM10</dt>
                  <dd>{reading.pm10} µg/m³</dd>
                </div>
              </dl>

              <p className="observed-at">
                Observed <time dateTime={reading.observed_at}>{formatObservedAt(reading.observed_at)}</time>
              </p>
            </>
          )}
        </section>
      </div>

      {(adviceStatus !== "idle" || adviceResults.length > 0) && (
        <section className="advice-section" aria-labelledby="advice-heading" aria-live="polite">
          <div className="advice-heading">
            <div>
              <p className="label">Personalized guidance</p>
              <h2 id="advice-heading">
                {adviceResults.length > 1 ? "Persona comparison" : "Today's advice"}
              </h2>
            </div>
            {reading?.is_stale && (
              <span className="stale-label">Based on the last available reading</span>
            )}
          </div>

          {adviceStatus === "loading" && (
            <p className="advice-message" role="status">Generating practical guidance…</p>
          )}

          {adviceStatus === "error" && (
            <div className="error-message" role="alert">
              <strong>Advice unavailable</strong>
              <p>{adviceError}</p>
            </div>
          )}

          {adviceResults.length > 0 && (
            <div className={`advice-grid ${adviceResults.length > 1 ? "comparison" : ""}`}>
              {adviceResults.map((result) => (
                <article className="advice-card" key={result.value}>
                  <div className="persona-heading">
                    <h3>{result.label}</h3>
                    <span className="caution-level">{result.advice.caution_level}</span>
                  </div>

                  <p className="advice-summary">{result.advice.summary}</p>

                  <div className="advice-block">
                    <h4>Daily routine</h4>
                    <ol>
                      {result.advice.daily_routine.map((item, index) => (
                        <li key={`${item.time_slot}-${index}`}>
                          <strong>{item.time_slot}</strong>
                          <p>{item.action}</p>
                          <small>{item.why}</small>
                        </li>
                      ))}
                    </ol>
                  </div>

                  <div className="advice-columns">
                    <div className="advice-block">
                      <h4>Indoor actions</h4>
                      <ul>
                        {result.advice.indoor_actions.map((item, index) => (
                          <li key={`${item.action}-${index}`}>
                            <strong>{item.action}</strong>
                            <small>{item.why}</small>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="advice-block">
                      <h4>Sustainable swaps</h4>
                      <ul>
                        {result.advice.sustainable_swaps.map((item, index) => (
                          <li key={`${item.swap}-${index}`}>
                            <strong>{item.swap}</strong>
                            <small>{item.why}</small>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
