import {
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
  CircleHelp,
  Leaf,
  ShieldAlert,
  Wind,
} from "lucide-react";
import StaleBanner from "./StaleBanner.jsx";
import styles from "../styles/App.module.css";

const CATEGORY_DETAILS = {
  Good: { className: styles.aqiGood, Icon: CheckCircle2, meaning: "Air quality is good for most everyday activities." },
  Satisfactory: { className: styles.aqiSatisfactory, Icon: Leaf, meaning: "Most people can continue their usual outdoor activities." },
  Moderate: { className: styles.aqiModerate, Icon: CircleHelp, meaning: "Some people may want to take extra care during longer outdoor activities." },
  Poor: { className: styles.aqiPoor, Icon: AlertTriangle, meaning: "Shorten strenuous outdoor activity if you are more sensitive to air pollution." },
  "Very Poor": { className: styles.aqiVeryPoor, Icon: CircleAlert, meaning: "Choose lighter or shorter outdoor activities when you can." },
  Severe: { className: styles.aqiSevere, Icon: ShieldAlert, meaning: "Keep outdoor time brief and follow local health guidance." },
};

function relativeTime(value) {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "time unavailable";
  const minutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return `${Math.round(hours / 24)} days ago`;
}

function exactTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function LoadingReading() {
  return (
    <div className={styles.skeletonGroup} role="status" aria-label="Loading air-quality reading">
      <span className={styles.skeletonCircle} />
      <span className={styles.skeletonLine} />
      <span className={styles.skeletonLineShort} />
      <span className={styles.skeletonPair}><i /><i /></span>
    </div>
  );
}

function AqiCard({ city, reading, status, error, onRetry }) {
  if (status === "idle") return null;

  return (
    <section className={styles.card} aria-labelledby="aqi-title">
      <div className={styles.cardHeading}>
        <div>
          <p className={styles.sectionEyebrow}>Current air quality</p>
          <h2 id="aqi-title">{city || "Your city"}</h2>
        </div>
        {reading?.source && <span className={styles.source}>{reading.source} data</span>}
      </div>

      {status === "loading" && <LoadingReading />}

      {(status === "error" || status === "rate-limited" || status === "no-data") && (
        <div className={styles.inlineError} role="alert">
          <p>{error}</p>
          <button className={styles.secondaryButton} type="button" onClick={onRetry}>Retry</button>
        </div>
      )}

      {status === "success" && reading && (
        <>
          {reading.is_stale && <StaleBanner observedAt={reading.observed_at} />}
          <ReadingDetails reading={reading} />
        </>
      )}
    </section>
  );
}

function ReadingDetails({ reading }) {
  const category = CATEGORY_DETAILS[reading.category] || {
    className: styles.aqiUnknown,
    Icon: Wind,
    meaning: "This reading shows the current air-quality level.",
  };
  const CategoryIcon = category.Icon;

  return (
    <>
      <div className={styles.readingTop}>
        <div className={`${styles.aqiBadge} ${category.className}`}>
          <span className={styles.aqiNumber}>{reading.aqi}</span>
          <span className={styles.aqiUnit}>AQI</span>
        </div>
        <div className={styles.categoryCopy}>
          <span className={`${styles.categoryBadge} ${category.className}`}>
            <CategoryIcon size={17} aria-hidden="true" />
            <strong>{reading.category}</strong>
          </span>
          <p>{category.meaning}</p>
        </div>
      </div>

      <dl className={styles.pollutants}>
        <div className={styles.pollutant}>
          <dt>
            PM2.5
            <details className={styles.explainer}>
              <summary aria-label="What is PM2.5?"><CircleHelp size={15} aria-hidden="true" /></summary>
              <p>Tiny particles that can travel deep into the lungs.</p>
            </details>
          </dt>
          <dd>{reading.pm25} <span>µg/m³</span></dd>
        </div>
        <div className={styles.pollutant}>
          <dt>
            PM10
            <details className={styles.explainer}>
              <summary aria-label="What is PM10?"><CircleHelp size={15} aria-hidden="true" /></summary>
              <p>Airborne particles such as dust and pollen.</p>
            </details>
          </dt>
          <dd>{reading.pm10} <span>µg/m³</span></dd>
        </div>
      </dl>

      <p className={styles.observedAt}>
        Last updated{" "}
        <time
          dateTime={reading.observed_at}
          title={exactTime(reading.observed_at)}
          aria-label={`Last updated ${exactTime(reading.observed_at)}`}
          tabIndex={0}
        >
          {relativeTime(reading.observed_at)}
        </time>
        {reading.station && <span> · {reading.station}</span>}
      </p>
    </>
  );
}

export default AqiCard;
