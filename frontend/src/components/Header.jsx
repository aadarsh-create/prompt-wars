import { Wind } from "lucide-react";
import ThemeToggle from "./ThemeToggle.jsx";
import styles from "../styles/App.module.css";

function Header({ theme, onThemeToggle }) {
  return (
    <header className={styles.header}>
      <a className={styles.brand} href="#main-content" aria-label="Urban Air Quality Assistant home">
        <span className={styles.brandIcon}><Wind size={22} aria-hidden="true" /></span>
        <span>
          <strong>Airwise</strong>
          <small>Urban Air Quality Assistant</small>
        </span>
      </a>
      <ThemeToggle theme={theme} onToggle={onThemeToggle} />
    </header>
  );
}

export default Header;
