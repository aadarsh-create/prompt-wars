import styles from "../styles/App.module.css";

function AdviceItem({ heading, action, why, highlighted = false }) {
  return (
    <li className={`${styles.adviceItem} ${highlighted ? styles.adviceDifferent : ""}`}>
      {heading && <strong className={styles.adviceTime}>{heading}</strong>}
      <p>{action}</p>
      <small><span>Why this helps:</span> {why}</small>
    </li>
  );
}

export default AdviceItem;
