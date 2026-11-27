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
  }

  function handleSubmit(event) {
    event.preventDefault();
    loadAqi(profile.city);
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
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
