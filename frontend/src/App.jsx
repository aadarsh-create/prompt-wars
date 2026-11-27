import { useEffect, useRef, useState } from "react";
import { ArrowDown, Sparkles, Wind } from "lucide-react";
import { ApiError, fetchAdvice, fetchAqi, fetchCities } from "./api/airQuality.js";
import AdviceSection from "./components/AdviceSection.jsx";
import AqiCard from "./components/AqiCard.jsx";
import AqiHistoryChart from "./components/AqiHistoryChart.jsx";
import Header from "./components/Header.jsx";
import PersonaCompare from "./components/PersonaCompare.jsx";
import ProfileForm, { PERSONAS } from "./components/ProfileForm.jsx";
import ServerStatus from "./components/ServerStatus.jsx";
import styles from "./styles/App.module.css";

function errorMessage(error) {
  if (error instanceof ApiError) {
    if (error.kind === "rate-limit") return "Please wait a moment and try again.";
    if (error.kind === "network") return "We couldn’t connect. Check your connection and try again.";
    if (error.kind === "no-data") return "There’s no live reading or saved recent reading for this city.";
  }
  return "We couldn’t load your plan just now. Please try again.";
}

function App() {
  const [themeOverride, setThemeOverride] = useState(null);
  const [systemTheme, setSystemTheme] = useState(() => (
    window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  ));
  const [cities, setCities] = useState([]);
  const [citiesStatus, setCitiesStatus] = useState("loading");
  const [profile, setProfile] = useState({
    city: "",
    persona: "child_family",
    commuteMode: "none",
    hasPurifier: false,
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [reading, setReading] = useState(null);
  const [aqiStatus, setAqiStatus] = useState("idle");
  const [aqiError, setAqiError] = useState("");
  const [advice, setAdvice] = useState(null);
  const [adviceStatus, setAdviceStatus] = useState("idle");
  const [adviceError, setAdviceError] = useState("");
  const [comparison, setComparison] = useState([]);
  const [comparisonStatus, setComparisonStatus] = useState("idle");
  const [comparisonError, setComparisonError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const initialCitiesLoadStarted = useRef(false);
  const initialPlanRequested = useRef(false);

  const theme = themeOverride || systemTheme;

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const updateSystemTheme = () => setSystemTheme(media.matches ? "dark" : "light");
    updateSystemTheme();
    media.addEventListener("change", updateSystemTheme);
    return () => media.removeEventListener("change", updateSystemTheme);
  }, []);

  useEffect(() => {
    if (themeOverride) {
      document.documentElement.dataset.theme = themeOverride;
    } else {
      delete document.documentElement.dataset.theme;
    }
  }, [themeOverride]);

  async function loadCities() {
    setCitiesStatus("loading");
    try {
      const availableCities = await fetchCities();
      setCities(availableCities);
      setCitiesStatus("success");
      setProfile((current) => ({
        ...current,
        city: current.city || availableCities[0],
      }));
    } catch (error) {
      setCitiesStatus("error");
      setCities([]);
    }
  }

  useEffect(() => {
    if (initialCitiesLoadStarted.current) return;
    initialCitiesLoadStarted.current = true;
    loadCities();
  }, []);

  function clearResults() {
    setReading(null);
    setAqiStatus("idle");
    setAqiError("");
    setAdvice(null);
    setAdviceStatus("idle");
    setAdviceError("");
    setComparison([]);
    setComparisonStatus("idle");
    setComparisonError("");
  }

  function handleProfileChange(event) {
    const { name, value, type, checked } = event.target;
    const errorField = name === "commuteMode"
      ? "commute_mode"
      : name === "hasPurifier"
        ? "has_purifier"
        : name;
    setProfile((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
    setFieldErrors((current) => {
      const next = { ...current };
      delete next[errorField];
      delete next.form;
      return next;
    });
    clearResults();
  }

  function validateProfile() {
    const errors = {};
    if (!profile.city) errors.city = "Choose a city.";
    if (!profile.persona) errors.persona = "Choose who this plan is for.";
    if (!profile.commuteMode) errors.commute_mode = "Choose a commute option.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function loadAdvice(currentProfile) {
    setAdviceStatus("loading");
    setAdviceError("");
    setComparison([]);
    setComparisonStatus("idle");
    try {
      const result = await fetchAdvice(currentProfile);
      setAdvice(result);
      setAdviceStatus("success");
      return result;
    } catch (error) {
      setAdviceStatus("error");
      if (error instanceof ApiError && error.kind === "validation") {
        setFieldErrors((current) => ({ ...current, ...error.fieldErrors }));
      }
      setAdviceError(
        error instanceof ApiError && error.kind === "unavailable"
          ? "Air-quality data became unavailable, so we couldn’t prepare a plan."
          : error instanceof ApiError && error.kind === "validation"
            ? "Please review the highlighted details and try again."
            : errorMessage(error),
      );
      return null;
    }
  }

  async function loadPlan(currentProfile = profile) {
    setSubmitting(true);
    setFieldErrors({});
    setReading(null);
    setAqiStatus("loading");
    setAqiError("");
    setAdvice(null);
    setAdviceStatus("idle");
    setAdviceError("");
    setComparison([]);
    setComparisonStatus("idle");

    let currentReading;
    try {
      currentReading = await fetchAqi(currentProfile.city);
      setReading(currentReading);
      setAqiStatus("success");
    } catch (error) {
      if (error instanceof ApiError && error.kind === "validation") {
        setFieldErrors(Object.keys(error.fieldErrors).length > 0
          ? error.fieldErrors
          : { form: "Please review your details and try again." });
      }
      setAqiStatus(error instanceof ApiError && error.kind === "no-data" ? "no-data" : "error");
      setAqiError(errorMessage(error));
      setSubmitting(false);
      return;
    }

    if (currentReading) await loadAdvice(currentProfile);
    setSubmitting(false);
  }

  useEffect(() => {
    if (citiesStatus !== "success" || !profile.city || initialPlanRequested.current) return;
    initialPlanRequested.current = true;
    loadPlan(profile);
  }, [citiesStatus, profile.city]);

  function handleSubmit(event) {
    event.preventDefault();
    if (validateProfile()) loadPlan(profile);
  }

  async function loadComparison() {
    if (!advice || !reading) return;
    setComparisonStatus("loading");
    setComparisonError("");
    const otherPersonas = PERSONAS.filter((persona) => persona.value !== profile.persona);
    try {
      const otherAdvice = await Promise.all(
        otherPersonas.map(async (persona) => ({
          persona,
          advice: await fetchAdvice({ ...profile, persona: persona.value }),
        })),
      );
      setComparison([
        { persona: PERSONAS.find((persona) => persona.value === profile.persona), advice },
        ...otherAdvice,
      ]);
      setComparisonStatus("success");
    } catch (error) {
      setComparisonStatus("error");
      setComparisonError(errorMessage(error));
    }
  }

  function handleThemeToggle() {
    setThemeOverride(theme === "dark" ? "light" : "dark");
  }

  const selectedPersona = PERSONAS.find((persona) => persona.value === profile.persona);

  return (
    <div className={styles.appShell}>
      <a className={styles.skipLink} href="#main-content">Skip to content</a>
      <ServerStatus />
      <Header theme={theme} onThemeToggle={handleThemeToggle} />
      <main id="main-content" className={styles.mainContent}>
        <section className={styles.hero} aria-labelledby="page-title">
          <div className={styles.heroCopy}>
            <p className={styles.heroEyebrow}>
              <span aria-hidden="true" />
              YOUR CITY. YOUR AIR. YOUR PLAN.
            </p>
            <h1 id="page-title">
              Know the air.
              <span>Make a better day.</span>
            </h1>
            <p className={styles.heroDescription}>
              Understand your city’s air quality, then find practical steps
              that fit your household and routine.
            </p>
            <a className={styles.heroAction} href="#daily-context">
              Check your city’s air <ArrowDown size={17} aria-hidden="true" />
            </a>
          </div>

          <div
            className={styles.heroVisual}
            role="img"
            aria-label="Illustration of the six air quality index levels, from good to severe."
          >
            <div className={styles.heroOrb} />
            <div className={styles.heroSkyline} aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className={styles.heroMetric}>
              <span className={styles.heroMetricIcon}><Wind size={17} aria-hidden="true" /></span>
              <span>Air quality, made personal</span>
            </div>
            <div className={styles.heroGuide}>
              <div className={styles.heroGuideHeading}>
                <span>THE AQI SPECTRUM</span>
                <span>6 health categories</span>
              </div>
              <div className={styles.aqiSpectrum} aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
                <span />
                <span />
              </div>
              <div className={styles.aqiLabels} aria-hidden="true">
                <span>Good</span>
                <span>Satisfactory</span>
                <span>Moderate</span>
                <span>Poor</span>
                <span>Very poor</span>
                <span>Severe</span>
              </div>
              <div className={styles.heroGuideFooter}>
                <span>Read the conditions</span>
                <span>Choose your next step</span>
              </div>
            </div>
            <div className={styles.heroParticles} aria-hidden="true" />
          </div>
        </section>

        <div className={styles.dashboard}>
          <ProfileForm
            cities={cities}
            citiesStatus={citiesStatus}
            profile={profile}
            errors={fieldErrors}
            submitting={submitting}
            onChange={handleProfileChange}
            onSubmit={handleSubmit}
            onRetryCities={loadCities}
          />

          <div className={styles.aqiColumn} aria-live="polite" aria-busy={aqiStatus === "loading"}>
            {aqiStatus === "idle" && (
              <section className={styles.emptyCard}>
                <span className={styles.emptyIcon}><Sparkles size={21} aria-hidden="true" /></span>
                <h2>Your air-quality plan starts here</h2>
                <p>Choose your city and a few details to see a reading and useful next steps.</p>
              </section>
            )}

            <AqiCard
              city={profile.city}
              reading={reading}
              status={aqiStatus}
              error={aqiError}
              onRetry={() => loadPlan(profile)}
            />
            {aqiStatus === "success" && reading && (
              <AqiHistoryChart history={reading.history} reading={reading} />
            )}
          </div>
        </div>

        <div className={styles.results} aria-live="polite">
          {aqiStatus === "success" && adviceStatus !== "idle" && (
            <AdviceSection
              advice={advice}
              status={adviceStatus}
              error={adviceError}
              onRetry={() => loadAdvice(profile)}
              onCompare={loadComparison}
              comparisonStatus={comparisonStatus}
            />
          )}

          {comparisonStatus === "loading" && (
            <p className={styles.statusText} role="status">Preparing the persona comparison…</p>
          )}
          {comparisonStatus === "error" && (
            <div className={styles.inlineError} role="alert">
              <p>{comparisonError}</p>
              <button className={styles.secondaryButton} type="button" onClick={loadComparison}>
                Retry comparison
              </button>
            </div>
          )}
          {comparisonStatus === "success" && (
            <PersonaCompare
              results={comparison}
              selectedPersona={selectedPersona}
            />
          )}
        </div>
      </main>
      <footer className={styles.footer}>
        Air readings are a guide, not a substitute for medical advice.
      </footer>
    </div>
  );
}

export default App;
