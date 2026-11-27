import styles from "../styles/App.module.css";

const TEMPERATURE_SCALE = { minimum: -10, maximum: 50, left: 24, right: 456 };

function TemperatureChart({ temperatureC }) {
  const clampedTemperature = Math.min(
    TEMPERATURE_SCALE.maximum,
    Math.max(TEMPERATURE_SCALE.minimum, temperatureC ?? TEMPERATURE_SCALE.minimum),
  );
  const markerX = TEMPERATURE_SCALE.left
    + ((clampedTemperature - TEMPERATURE_SCALE.minimum)
      / (TEMPERATURE_SCALE.maximum - TEMPERATURE_SCALE.minimum))
      * (TEMPERATURE_SCALE.right - TEMPERATURE_SCALE.left);

  return (
    <section className={styles.temperatureCard} aria-labelledby="temperature-title">
      <div className={`${styles.historyHeading} ${styles.temperatureHeading}`}>
        <div>
          <p className={styles.sectionEyebrow}>Current weather</p>
          <h2 id="temperature-title">Temperature</h2>
        </div>
        {typeof temperatureC === "number" && (
          <p className={styles.temperatureValue}>{temperatureC.toFixed(1)} <span>°C</span></p>
        )}
      </div>
      {typeof temperatureC === "number" ? (
        <div className={styles.temperatureChart}>
          <svg
            className={styles.historyChart}
            viewBox="0 0 480 76"
            role="img"
            aria-label={`Current temperature is ${temperatureC.toFixed(1)} degrees Celsius, on a scale from ${TEMPERATURE_SCALE.minimum} to ${TEMPERATURE_SCALE.maximum} degrees`}
          >
            <defs>
              <linearGradient id="temperature-gradient">
                <stop offset="0%" stopColor="#60A5FA" />
                <stop offset="45%" stopColor="#34D399" />
                <stop offset="72%" stopColor="#FBBF24" />
                <stop offset="100%" stopColor="#EF4444" />
              </linearGradient>
            </defs>
            <rect
              x={TEMPERATURE_SCALE.left}
              y="20"
              width={TEMPERATURE_SCALE.right - TEMPERATURE_SCALE.left}
              height="12"
              rx="6"
              className={styles.temperatureScale}
            />
            <line
              x1={markerX}
              x2={markerX}
              y1="14"
              y2="38"
              className={styles.temperatureMarker}
            />
            {[-10, 0, 10, 20, 30, 40, 50].map((temperature) => {
              const x = TEMPERATURE_SCALE.left
                + ((temperature - TEMPERATURE_SCALE.minimum)
                  / (TEMPERATURE_SCALE.maximum - TEMPERATURE_SCALE.minimum))
                  * (TEMPERATURE_SCALE.right - TEMPERATURE_SCALE.left);
              return (
                <text
                  key={temperature}
                  x={x}
                  y="66"
                  textAnchor={temperature === -10 ? "start" : temperature === 50 ? "end" : "middle"}
                >
                  {temperature}°
                </text>
              );
            })}
          </svg>
        </div>
      ) : (
        <p className={styles.temperatureUnavailable}>
          Current temperature data isn’t available right now.
        </p>
      )}
    </section>
  );
}

export default TemperatureChart;
