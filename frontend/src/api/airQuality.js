const FIELD_MESSAGES = {
  city: "Choose a supported city.",
  persona: "Choose who this plan is for.",
  commute_mode: "Choose a commute option.",
  has_purifier: "Choose whether you have an air purifier.",
};

export class ApiError extends Error {
  constructor(kind, fieldErrors = {}) {
    super(kind);
    this.name = "ApiError";
    this.kind = kind;
    this.fieldErrors = fieldErrors;
  }
}

function mapValidationErrors(detail) {
  if (!Array.isArray(detail)) return {};

  return detail.reduce((errors, issue) => {
    const field = Array.isArray(issue.loc) ? issue.loc[issue.loc.length - 1] : null;
    if (FIELD_MESSAGES[field]) errors[field] = FIELD_MESSAGES[field];
    return errors;
  }, {});
}

async function requestJson(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new ApiError("network");
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 422) {
      throw new ApiError("validation", mapValidationErrors(payload?.detail));
    }
    if (response.status === 429) throw new ApiError("rate-limit");
    if (response.status === 503 && path === "/api/aqi") {
      throw new ApiError("no-data");
    }
    if (response.status === 503) throw new ApiError("unavailable");
    throw new ApiError("request");
  }

  return payload;
}

export async function fetchCities() {
  const payload = await requestJson("/api/cities");
  if (
    !Array.isArray(payload?.cities)
    || payload.cities.length === 0
    || payload.cities.some((city) => typeof city !== "string" || city.length === 0)
  ) {
    throw new ApiError("request");
  }
  return payload.cities;
}

export async function fetchAqi(city) {
  const reading = await requestJson(`/api/aqi?city=${encodeURIComponent(city)}`);
  if (
    !reading
    || typeof reading.city !== "string"
    || typeof reading.aqi !== "number"
    || !Number.isFinite(reading.aqi)
    || reading.aqi < 0
    || reading.aqi > 500
    || typeof reading.category !== "string"
    || typeof reading.pm25 !== "number"
    || !Number.isFinite(reading.pm25)
    || reading.pm25 < 0
    || typeof reading.pm10 !== "number"
    || !Number.isFinite(reading.pm10)
    || reading.pm10 < 0
    || typeof reading.observed_at !== "string"
    || typeof reading.source !== "string"
    || typeof reading.is_stale !== "boolean"
    || !Array.isArray(reading.history)
    || reading.history.some((point) => (
      typeof point?.timestamp !== "string"
      || !Number.isFinite(Date.parse(point.timestamp))
      || typeof point?.aqi !== "number"
      || !Number.isInteger(point.aqi)
      || point.aqi < 0
      || point.aqi > 500
    ))
  ) {
    throw new ApiError("request");
  }
  return reading;
}

export async function fetchAdvice(profile) {
  const advice = await requestJson("/api/advice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      profile: {
        city: profile.city,
        persona: profile.persona,
        commute_mode: profile.commuteMode,
        has_purifier: profile.hasPurifier,
      },
    }),
  });
  const hasText = (value) => typeof value === "string" && value.trim().length > 0;
  const hasWhy = (item) => hasText(item?.why);
  if (
    !advice
    || !hasText(advice.summary)
    || !hasText(advice.caution_level)
    || !Array.isArray(advice.daily_routine)
    || advice.daily_routine.length === 0
    || advice.daily_routine.some((item) => !hasText(item?.time_slot) || !hasText(item?.action) || !hasWhy(item))
    || !Array.isArray(advice.indoor_actions)
    || advice.indoor_actions.length === 0
    || advice.indoor_actions.some((item) => !hasText(item?.action) || !hasWhy(item))
    || !Array.isArray(advice.sustainable_swaps)
    || advice.sustainable_swaps.length === 0
    || advice.sustainable_swaps.some((item) => !hasText(item?.swap) || !hasWhy(item))
  ) {
    throw new ApiError("request");
  }
  return advice;
}
