import styles from "../styles/App.module.css";

const HISTORY_WINDOW_MS = 24 * 60 * 60 * 1000;
const CHART = { left: 36, right: 468, top: 14, bottom: 124 };

function formatTime(timestamp) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

function AqiHistoryChart({ history }) {
  const now = Date.now();
  const cutoff = now - HISTORY_WINDOW_MS;
  const points = history
    .map((point) => ({ ...point, time: Date.parse(point.timestamp) }))
    .filter((point) => point.time >= cutoff && point.time <= now + 5 * 60 * 1000)
    .sort((first, second) => first.time - second.time);

  const values = points.map((point) => point.aqi);
  let minimum = values.length ? Math.max(0, Math.floor(Math.min(...values) / 50) * 50 - 25) : 0;
  let maximum = values.length ? Math.min(500, Math.ceil(Math.max(...values) / 50) * 50 + 25) : 500;
  if (maximum - minimum < 50) {
    minimum = Math.max(0, maximum - 50);
    maximum = Math.min(500, minimum + 50);
  }

  const coordinates = points.map((point) => ({
    ...point,
    x: CHART.left + ((point.time - cutoff) / HISTORY_WINDOW_MS) * (CHART.right - CHART.left),
    y: CHART.bottom - ((point.aqi - minimum) / (maximum - minimum)) * (CHART.bottom - CHART.top),
  }));
  const path = coordinates.reduce((result, point, index) => {
    const previous = coordinates[index - 1];
    const startsSegment = !previous || point.time - previous.time > 2.5 * 60 * 60 * 1000;
    return `${result}${startsSegment ? "M" : "L"}${point.x.toFixed(1)},${point.y.toFixed(1)} `;
  }, "");

  return (
    <section className={styles.historyCard} aria-labelledby="history-title">
      <div className={styles.historyHeading}>
        <div>
          <p className={styles.sectionEyebrow}>Recent trend</p>
          <h2 id="history-title">24-hour AQI history</h2>
        </div>
        {points.length > 0 && (
          <span className={styles.historyCount}>{points.length} hourly readings</span>
        )}
      </div>

      {points.length > 0 ? (
        <svg
          className={styles.historyChart}
          viewBox="0 0 480 158"
          role="img"
          aria-label={`AQI history over the past 24 hours, from ${minimum} to ${maximum}. ${points.length} hourly readings.`}
        >
          {[CHART.top, (CHART.top + CHART.bottom) / 2, CHART.bottom].map((y) => (
            <line
              key={y}
              x1={CHART.left}
              x2={CHART.right}
              y1={y}
              y2={y}
              className={styles.historyGridLine}
            />
          ))}
          <text x="0" y={CHART.top + 4}>{maximum}</text>
          <text x="0" y={CHART.bottom + 4}>{minimum}</text>
          <path d={path.trim()} className={styles.historyLine} />
          {coordinates.map((point) => (
            <circle
              key={point.timestamp}
              cx={point.x}
              cy={point.y}
              r="3"
              className={styles.historyPoint}
            >
              <title>{formatTime(point.time)} · AQI {point.aqi}</title>
            </circle>
          ))}
          <text x={CHART.left} y="151">24h ago</text>
          <text x={(CHART.left + CHART.right) / 2} y="151" textAnchor="middle">12h ago</text>
          <text x={CHART.right} y="151" textAnchor="end">Now</text>
        </svg>
      ) : (
        <p className={styles.historyEmpty}>
          Hourly history isn’t available for this station yet.
        </p>
      )}
    </section>
  );
}

export default AqiHistoryChart;
