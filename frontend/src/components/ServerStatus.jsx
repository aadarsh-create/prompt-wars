import { useEffect, useState } from "react";
import { beginServerRequest, getServerStatus, subscribeServerStatus } from "../api/serverStatus.js";
import styles from "../styles/ServerStatus.module.css";

const HEALTH_CHECK_INTERVAL = 90_000;
const HEALTH_CHECK_TIMEOUT = 75_000;

function ServerStatus() {
  const [status, setStatus] = useState(getServerStatus);

  useEffect(() => {
    return subscribeServerStatus(setStatus);
  }, []);

  useEffect(() => {
    let checking = false;
    let controller;
    let activeRequest;

    async function checkServer() {
      if (checking) return;
      checking = true;
      controller = new AbortController();
      activeRequest = beginServerRequest({ healthCheck: true });
      let timedOut = false;
      const timeoutId = window.setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, HEALTH_CHECK_TIMEOUT);

      try {
        const response = await fetch("/api/health", { signal: controller.signal });
        const payload = await response.json();
        if (response.ok && payload?.status === "ok") {
          activeRequest.succeed();
        } else {
          activeRequest.fail();
        }
      } catch (error) {
        if (timedOut || error.name !== "AbortError") {
          activeRequest.fail();
        } else {
          activeRequest.cancel();
        }
      } finally {
        window.clearTimeout(timeoutId);
        activeRequest = null;
        checking = false;
      }
    }

    const initialCheckId = window.setTimeout(checkServer, 0);
    const intervalId = window.setInterval(checkServer, HEALTH_CHECK_INTERVAL);

    return () => {
      window.clearTimeout(initialCheckId);
      window.clearInterval(intervalId);
      activeRequest?.cancel();
      controller?.abort();
    };
  }, []);

  const label = status === "online"
    ? "Server online"
    : status === "offline"
      ? "Server offline"
      : status === "waiting"
        ? "Waiting for server"
        : "Checking server";

  return (
    <div className={`${styles.serverStatus} ${styles[status]}`} role="status" aria-label={label}>
      <span>Server</span>
      <span className={styles.statusDot} aria-hidden="true" />
    </div>
  );
}

export default ServerStatus;
