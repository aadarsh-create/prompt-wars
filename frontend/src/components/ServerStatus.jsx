import { useEffect, useState } from "react";
import { getServerStatus, subscribeServerStatus } from "../api/serverStatus.js";
import styles from "../styles/ServerStatus.module.css";

function ServerStatus() {
  const [status, setStatus] = useState(getServerStatus);

  useEffect(() => {
    return subscribeServerStatus(setStatus);
  }, []);

  const label = status === "online"
    ? "Server online"
    : status === "offline"
      ? "Server offline"
      : status === "waiting"
        ? "Waiting for server"
        : "Checking server";

  return (
    <div
      className={`${styles.serverStatus} ${styles[status]}`}
      role="status"
      aria-label={label}
      tabIndex={0}
    >
      <span>Server</span>
      <span className={styles.statusDot} aria-hidden="true" />
      <span className={styles.tooltip} role="tooltip">
        First start may take 20–40 seconds due to free-tier cold start
      </span>
    </div>
  );
}

export default ServerStatus;
