import { BriefcaseBusiness, GraduationCap, Heart, PersonStanding, RefreshCw } from "lucide-react";
import styles from "../styles/App.module.css";

export const PERSONAS = [
  { value: "child_family", label: "Family with children", Icon: Heart },
  { value: "senior", label: "Senior citizen", Icon: PersonStanding },
  { value: "working_professional", label: "Working professional", Icon: BriefcaseBusiness },
  { value: "student", label: "Student", Icon: GraduationCap },
];

const COMMUTE_MODES = [
  { value: "none", label: "Mostly indoors" },
  { value: "walk", label: "Walking" },
  { value: "cycle", label: "Cycling" },
  { value: "public_transport", label: "Public transport" },
  { value: "car", label: "Car" },
];

function FieldError({ id, children }) {
  return children ? <span className={styles.fieldError} id={id}>{children}</span> : null;
}

function ProfileForm({
  cities,
  citiesStatus,
  profile,
  errors,
  submitting,
  onChange,
  onSubmit,
  onRetryCities,
}) {
  return (
    <form id="daily-context" className={styles.profileCard} onSubmit={onSubmit} noValidate>
      <div>
        <p className={styles.sectionEyebrow}>Make it personal</p>
        <h2>Your daily context</h2>
        <p className={styles.cardIntro}>A few details help shape relevant suggestions.</p>
      </div>

      <div className={styles.field}>
        <label htmlFor="city">City</label>
        <select
          id="city"
          name="city"
          value={profile.city}
          onChange={onChange}
          disabled={citiesStatus !== "success" || submitting}
          aria-invalid={Boolean(errors.city)}
          aria-describedby={
            errors.city
              ? "city-error"
              : citiesStatus === "loading" || citiesStatus === "success"
                ? "city-help"
                : undefined
          }
          required
        >
          <option value="" disabled>
            {citiesStatus === "loading" ? "Loading available cities…" : "Choose your city"}
          </option>
          {cities.map((city) => <option key={city} value={city}>{city}</option>)}
        </select>
        {citiesStatus === "loading" && <span className={styles.helperText} id="city-help">Loading cities from the service.</span>}
        {citiesStatus === "success" && !errors.city && <span className={styles.helperText} id="city-help">Choose a supported city.</span>}
        <FieldError id="city-error">{errors.city}</FieldError>
        {citiesStatus === "error" && (
          <div className={styles.inlineError} role="alert">
            <span>We couldn’t load the available cities.</span>
            <button type="button" className={styles.textButton} onClick={onRetryCities}>
              <RefreshCw size={15} aria-hidden="true" /> Try again
            </button>
          </div>
        )}
      </div>

      <fieldset className={styles.personaFieldset} disabled={submitting}>
        <legend>Who is this plan for?</legend>
        <div className={styles.personaOptions} role="radiogroup" aria-describedby={errors.persona ? "persona-error" : undefined}>
          {PERSONAS.map(({ value, label, Icon }) => (
            <label
              className={`${styles.personaOption} ${profile.persona === value ? styles.personaSelected : ""}`}
              key={value}
            >
              <input
                type="radio"
                name="persona"
                value={value}
                checked={profile.persona === value}
                onChange={onChange}
                aria-invalid={Boolean(errors.persona)}
                aria-describedby={errors.persona ? "persona-error" : undefined}
              />
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </label>
          ))}
        </div>
        <FieldError id="persona-error">{errors.persona}</FieldError>
      </fieldset>

      <div className={styles.field}>
        <label htmlFor="commuteMode">How do you usually get around?</label>
        <select
          id="commuteMode"
          name="commuteMode"
          value={profile.commuteMode}
          onChange={onChange}
          disabled={submitting}
          aria-invalid={Boolean(errors.commute_mode)}
          aria-describedby={errors.commute_mode ? "commute-error" : "commute-help"}
          required
        >
          {COMMUTE_MODES.map((mode) => (
            <option key={mode.value} value={mode.value}>{mode.label}</option>
          ))}
        </select>
        {!errors.commute_mode && <span className={styles.helperText} id="commute-help">Choose the option that best fits your routine.</span>}
        <FieldError id="commute-error">{errors.commute_mode}</FieldError>
      </div>

      <fieldset className={styles.purifierFieldset} disabled={submitting}>
        <legend>Do you have an air purifier at home?</legend>
        <div className={styles.toggleOptions}>
          {[{ value: true, label: "Yes" }, { value: false, label: "No" }].map((option) => (
            <label className={styles.toggleOption} key={String(option.value)}>
              <input
                type="radio"
                name="hasPurifier"
                value={String(option.value)}
                checked={profile.hasPurifier === option.value}
                onChange={(event) => onChange({
                  target: { name: "hasPurifier", value: option.value, type: "checkbox", checked: option.value },
                })}
                aria-invalid={Boolean(errors.has_purifier)}
                aria-describedby={errors.has_purifier ? "purifier-error" : undefined}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
        <FieldError id="purifier-error">{errors.has_purifier}</FieldError>
      </fieldset>

      {errors.form && <p className={styles.fieldError} role="alert">{errors.form}</p>}
      <button className={styles.primaryButton} type="submit" disabled={citiesStatus !== "success" || submitting}>
        {submitting ? "Preparing your plan…" : "Get my plan"}
      </button>
    </form>
  );
}

export default ProfileForm;
