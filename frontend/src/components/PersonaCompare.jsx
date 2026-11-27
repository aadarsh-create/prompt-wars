import styles from "../styles/App.module.css";

const ADVICE_GROUPS = [
  { field: "daily_routine", label: "Your day", actionField: "action" },
  { field: "indoor_actions", label: "Inside your home", actionField: "action" },
  { field: "sustainable_swaps", label: "Greener swaps", actionField: "swap" },
];

function recommendationKey(item, group) {
  const action = item?.[group.actionField]?.trim().toLowerCase();
  const why = item?.why?.trim().toLowerCase();
  return group.field === "daily_routine"
    ? `${item?.time_slot?.trim().toLowerCase()}|${action}|${why}`
    : `${action}|${why}`;
}

function firstRecommendation(advice) {
  for (const group of ADVICE_GROUPS) {
    const item = advice?.[group.field]?.[0];
    if (item) return { group, item };
  }
  return null;
}

function findDifference(advice, baseline) {
  for (const group of ADVICE_GROUPS) {
    const baselineKeys = new Set(
      (baseline?.[group.field] || []).map((item) => recommendationKey(item, group)),
    );
    const item = (advice?.[group.field] || []).find(
      (candidate) => !baselineKeys.has(recommendationKey(candidate, group)),
    );
    if (item) return { group, item };
  }
  return null;
}

function PersonaCompare({ results, selectedPersona }) {
  const selected = results.find((result) => result.persona.value === selectedPersona?.value);
  const baseline = selected?.advice;

  return (
    <section className={styles.compareSection} aria-labelledby="compare-title">
      <div className={styles.compareHeading}>
        <div>
          <p className={styles.sectionEyebrow}>Same city, different needs</p>
          <h2 id="compare-title">Advice by persona</h2>
        </div>
      </div>
      <p className={styles.compareLegend}>
        One practical recommendation for each persona. Highlighted cards differ from{" "}
        {selectedPersona?.label || "your selected persona"}.
      </p>
      <div className={styles.comparisonGrid}>
        {results.map(({ persona, advice }) => {
          const isSelected = persona.value === selectedPersona?.value;
          const difference = isSelected
            ? firstRecommendation(advice)
            : findDifference(advice, baseline);
          const action = difference?.item?.[difference.group.actionField];

          return (
            <article
              className={`${styles.comparisonCard} ${isSelected ? styles.comparisonSelected : ""}`}
              key={persona.value}
            >
              <div className={styles.comparisonCardHeading}>
                <h3>{persona.label}</h3>
                <span className={styles.cautionBadge}>{advice.caution_level}</span>
              </div>
              {difference ? (
                <>
                  <p className={styles.comparisonKicker}>
                    {isSelected ? "Your plan" : `Key difference: ${difference.group.label}`}
                  </p>
                  <div className={`${styles.comparisonDifference} ${isSelected ? "" : styles.adviceDifferent}`}>
                    {difference.group.field === "daily_routine" && (
                      <strong className={styles.adviceTime}>{difference.item.time_slot}</strong>
                    )}
                    <p className={styles.comparisonAction}>{action}</p>
                    <small className={styles.comparisonWhy}>
                      <span>Why this helps:</span> {difference.item.why}
                    </small>
                  </div>
                </>
              ) : (
                <p className={styles.comparisonSimilar}>
                  The main practical steps are similar to {selectedPersona?.label || "your plan"}.
                </p>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

export default PersonaCompare;
