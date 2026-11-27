import { ArrowRightLeft, House, Sun } from "lucide-react";
import AdviceItem from "./AdviceItem.jsx";
import styles from "../styles/App.module.css";

function AdviceSection({ advice, status, error, onRetry, onCompare, comparisonStatus }) {
  if (status === "loading") {
    return (
      <section className={styles.card} aria-labelledby="advice-title" aria-busy="true">
        <p className={styles.sectionEyebrow}>Your personal plan</p>
        <h2 id="advice-title">Putting together practical next steps</h2>
        <div className={styles.adviceSkeleton} role="status" aria-label="Loading personalized advice">
          <span /><span /><span />
        </div>
      </section>
    );
  }

  if (status === "error") {
    return (
      <section className={styles.card} aria-labelledby="advice-title">
        <p className={styles.sectionEyebrow}>Your personal plan</p>
        <h2 id="advice-title">Advice is temporarily unavailable</h2>
        <div className={styles.inlineError} role="alert">
          <p>{error}</p>
          <button className={styles.secondaryButton} type="button" onClick={onRetry}>Retry</button>
        </div>
      </section>
    );
  }

  if (!advice) return null;

  return (
    <section className={styles.adviceCard} aria-labelledby="advice-title">
      <div className={styles.adviceHeader}>
        <div>
          <p className={styles.sectionEyebrow}>Your personal plan</p>
          <h2 id="advice-title">A few helpful next steps</h2>
        </div>
        <span className={styles.cautionBadge}>{advice.caution_level}</span>
      </div>
      <p className={styles.adviceSummary}>{advice.summary}</p>

      <AdviceGroup title="Your day" Icon={Sun}>
        <ol className={styles.adviceList}>
          {advice.daily_routine.slice(0, 3).map((item, index) => (
            <AdviceItem
              key={`${item.time_slot}-${index}`}
              heading={item.time_slot}
              action={item.action}
              why={item.why}
            />
          ))}
        </ol>
      </AdviceGroup>

      <div className={styles.adviceColumns}>
        <AdviceGroup title="Inside your home" Icon={House}>
          <ul className={styles.adviceList}>
            {advice.indoor_actions.slice(0, 2).map((item, index) => (
              <AdviceItem key={`${item.action}-${index}`} action={item.action} why={item.why} />
            ))}
          </ul>
        </AdviceGroup>
        <AdviceGroup title="Greener swaps" Icon={ArrowRightLeft}>
          <ul className={styles.adviceList}>
            {advice.sustainable_swaps.slice(0, 2).map((item, index) => (
              <AdviceItem key={`${item.swap}-${index}`} action={item.swap} why={item.why} />
            ))}
          </ul>
        </AdviceGroup>
      </div>

      <div className={styles.comparePrompt}>
        <div>
          <strong>Would another routine change the advice?</strong>
          <span>Compare suggestions for all four personas in this city.</span>
        </div>
        <button
          className={styles.secondaryButton}
          type="button"
          onClick={onCompare}
          disabled={comparisonStatus === "loading"}
        >
          Compare personas
        </button>
      </div>
    </section>
  );
}

function AdviceGroup({ title, Icon, children }) {
  return (
    <section className={styles.adviceGroup} aria-label={title}>
      <h3><Icon size={18} aria-hidden="true" />{title}</h3>
      {children}
    </section>
  );
}

export default AdviceSection;
