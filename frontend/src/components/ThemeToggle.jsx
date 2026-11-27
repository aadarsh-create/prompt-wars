import { Moon, Sun } from "lucide-react";
import styles from "../styles/App.module.css";

function ThemeToggle({ theme, onToggle }) {
  const Icon = theme === "dark" ? Sun : Moon;
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";

  return (
    <button className={styles.themeToggle} type="button" onClick={onToggle} aria-label={label}>
      <Icon size={19} aria-hidden="true" />
      <span>{theme === "dark" ? "Light" : "Dark"} mode</span>
    </button>
  );
}

export default ThemeToggle;
