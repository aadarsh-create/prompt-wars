import { Clock3 } from "lucide-react";
import styles from "../styles/App.module.css";

function exactTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function StaleBanner({ observedAt }) {
  return (
    <p className={styles.staleBanner} role="status">
      <Clock3 size={18} aria-hidden="true" />
      <span>
        Showing last real reading from <time dateTime={observedAt}>{exactTime(observedAt)}</time>.
        {" "}Live data is unavailable.
      </span>
    </p>
  );
}

export default StaleBanner;
