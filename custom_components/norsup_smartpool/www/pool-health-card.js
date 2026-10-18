/**
 * Norsup Smartpool — Pool Health Lovelace card (pH + ORP).
 * Resource: /norsup_smartpool/pool-health-card.js (type: module)
 */

const CARD_TAG = "norsup-pool-health-card";
const CARD_NAME = "Norsup Pool Health";

function parseLocalizedNumber(raw) {
  if (raw === undefined || raw === null) return null;
  let text = String(raw).trim();
  if (!text || text === "unavailable" || text === "unknown") return null;
  text = text.replace(/\s/g, "");
  if (text.includes(",") && text.includes(".")) {
    text = text.replace(/\./g, "").replace(",", ".");
  } else if (text.includes(",") && !text.includes(".")) {
    text = text.replace(",", ".");
  }
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
}

function parseNumber(state) {
  if (!state) return null;
  return parseLocalizedNumber(state.state);
}

function isNorsupState(hass, entityId) {
  const ent = hass?.states?.[entityId];
  if (!ent) return false;
  const platform = ent.attributes?.platform ?? "";
  return (
    entityId.includes("norsup") ||
    platform === "norsup_smartpool" ||
    ent.attributes?.norsup_entity_key !== undefined
  );
}

function entityDeviceId(hass, entityId) {
  const reg = hass?.entities?.[entityId];
  return reg?.device_id ?? null;
}

function findEntityByNorsupKey(hass, key, preferSameDeviceAs) {
  if (!hass?.states) return "";
  const deviceId = preferSameDeviceAs ? entityDeviceId(hass, preferSameDeviceAs) : null;
  let fallback = "";
  for (const entityId of Object.keys(hass.states)) {
    if (!entityId.startsWith("sensor.")) continue;
    const ent = hass.states[entityId];
    if (ent.attributes?.norsup_entity_key !== key) continue;
    if (deviceId && entityDeviceId(hass, entityId) === deviceId) {
      return entityId;
    }
    if (!fallback) fallback = entityId;
  }
  return fallback;
}

function companionTargetEntity(hass, liveEntityId, targetKey) {
  if (!liveEntityId?.startsWith("sensor.")) return "";
  const slug = liveEntityId.slice("sensor.".length);
  let candidateSlug = "";
  if (targetKey === "ph_target") {
    if (slug === "ph" || slug.endsWith("_ph")) {
      const base = slug === "ph" ? "" : slug.slice(0, -3);
      candidateSlug = base ? `${base}_ph_target` : "ph_target";
    }
  } else if (targetKey === "orp_target") {
    if (slug === "orp" || slug.endsWith("_orp")) {
      const base = slug === "orp" ? "" : slug.slice(0, -4);
      candidateSlug = base ? `${base}_orp_target` : "orp_target";
    }
  }
  if (candidateSlug && hass?.states[`sensor.${candidateSlug}`]) {
    return `sensor.${candidateSlug}`;
  }
  return findEntityByNorsupKey(hass, targetKey, liveEntityId);
}

function resolveTargetEntity(hass, configuredId, liveEntityId, targetKey) {
  if (configuredId && hass?.states[configuredId]) return configuredId;
  return companionTargetEntity(hass, liveEntityId, targetKey);
}

function pickNorsupLiveSensor(hass, key) {
  const ids = Object.keys(hass.states).filter(
    (id) => id.startsWith("sensor.") && isNorsupState(hass, id)
  );
  const exact = ids.find((id) => hass.states[id].attributes?.norsup_entity_key === key);
  if (exact) return exact;
  if (key === "ph") {
    return (
      ids.find((id) => {
        const slug = id.slice("sensor.".length);
        return (slug === "ph" || slug.endsWith("_ph")) && !slug.includes("ph_target");
      }) ?? ""
    );
  }
  if (key === "orp") {
    return (
      ids.find((id) => {
        const slug = id.slice("sensor.".length);
        return (slug === "orp" || slug.endsWith("_orp")) && !slug.includes("orp_target");
      }) ?? ""
    );
  }
  return findEntityByNorsupKey(hass, key, "");
}

function resolveTarget(hass, entityId, manual) {
  if (entityId && hass?.states[entityId]) {
    const fromEntity = parseNumber(hass.states[entityId]);
    if (fromEntity !== null) return fromEntity;
  }
  if (manual !== undefined && manual !== null && manual !== "") {
    const value = Number(manual);
    if (Number.isFinite(value)) return value;
  }
  return null;
}

function bandFromTarget(value, target, tolerance, fallback) {
  if (value === null) return { label: "—", level: "unknown", score: 0 };
  if (target === null) return fallback(value);
  const delta = Math.abs(value - target);
  if (delta <= tolerance * 0.5) return { label: "On target", level: "great", score: 100 };
  if (delta <= tolerance) return { label: "Ideal", level: "great", score: 95 };
  if (delta <= tolerance * 1.5) return { label: "OK", level: "good", score: 72 };
  if (delta <= tolerance * 2.5) return { label: "Check", level: "warn", score: 45 };
  return { label: "Out of range", level: "bad", score: 20 };
}

function phBandFixed(value) {
  if (value === null) return { label: "—", level: "unknown", score: 0 };
  if (value >= 7.2 && value <= 7.6) return { label: "Ideal", level: "great", score: 100 };
  if (value >= 7.0 && value <= 7.8) return { label: "OK", level: "good", score: 72 };
  if (value >= 6.8 && value <= 8.0) return { label: "Check", level: "warn", score: 45 };
  return { label: "Out of range", level: "bad", score: 20 };
}

function orpBandFixed(value) {
  if (value === null) return { label: "—", level: "unknown", score: 0 };
  if (value >= 650 && value <= 750) return { label: "Ideal", level: "great", score: 100 };
  if (value >= 550 && value <= 800) return { label: "OK", level: "good", score: 72 };
  if (value >= 450 && value <= 850) return { label: "Check", level: "warn", score: 45 };
  return { label: "Out of range", level: "bad", score: 20 };
}

function phBand(value, target, tolerance) {
  return bandFromTarget(value, target, tolerance, phBandFixed);
}

function orpBand(value, target, tolerance) {
  return bandFromTarget(value, target, tolerance, orpBandFixed);
}

function overallHealth(ph, orp) {
  if (ph.score === 0 && orp.score === 0) {
    return { label: "Waiting for data", level: "unknown", score: null };
  }
  const scores = [ph.score, orp.score].filter((s) => s > 0);
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  if (avg >= 90) return { label: "Excellent", level: "great", score: avg };
  if (avg >= 70) return { label: "Good", level: "good", score: avg };
  if (avg >= 50) return { label: "Needs attention", level: "warn", score: avg };
  return { label: "Critical", level: "bad", score: avg };
}

function gaugeArc(value, min, max) {
  if (value === null) return 0;
  const clamped = Math.min(max, Math.max(min, value));
  return (clamped - min) / (max - min);
}

function targetMarker(pct, onTarget) {
  const theta = pct * 2 * Math.PI - Math.PI / 2;
  const x = 60 + 54 * Math.cos(theta);
  const y = 60 + 54 * Math.sin(theta);
  const pulse = onTarget ? ' class="target-marker pulse"' : ' class="target-marker"';
  return `<circle${pulse} cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="5" />`;
}

function targetZoneArc(pctMin, pctMax, circumference) {
  const start = Math.min(pctMin, pctMax);
  const end = Math.max(pctMin, pctMax);
  const length = Math.max(0.01, (end - start) * circumference);
  const offset = circumference * (1 - end);
  return `
    <circle
      class="target-zone"
      cx="60" cy="60" r="54"
      style="stroke-dasharray: ${length} ${circumference - length}; stroke-dashoffset: ${offset}"
    />
  `;
}

function formatPh(value) {
  return value === null ? "—" : value.toFixed(2);
}

function formatOrp(value) {
  return value === null ? "—" : `${Math.round(value)}`;
}

function formatDelta(value, target, decimals) {
  if (value === null || target === null) return null;
  const delta = value - target;
  const sign = delta > 0 ? "+" : "";
  if (decimals === 0) return `${sign}${Math.round(delta)}`;
  return `${sign}${delta.toFixed(decimals)}`;
}

function comparisonBar(value, target, tolerance, min, max, unit) {
  const valuePct = gaugeArc(value, min, max) * 100;
  const targetPct = target !== null ? gaugeArc(target, min, max) * 100 : null;
  const zoneMin =
    target !== null ? gaugeArc(target - tolerance, min, max) * 100 : null;
  const zoneMax =
    target !== null ? gaugeArc(target + tolerance, min, max) * 100 : null;

  let zoneHtml = "";
  if (zoneMin !== null && zoneMax !== null) {
    const left = Math.min(zoneMin, zoneMax);
    const width = Math.max(2, Math.abs(zoneMax - zoneMin));
    zoneHtml = `<div class="bar-zone" style="left:${left}%;width:${width}%"></div>`;
  }

  const valueDot =
    value !== null
      ? `<div class="bar-dot bar-dot--live" style="left:${valuePct}%" title="Now"></div>`
      : "";
  const targetTick =
    targetPct !== null
      ? `<div class="bar-tick" style="left:${targetPct}%" title="Doel / target"></div>`
      : "";

  const formatReading = unit === "mV" ? (v) => `${formatOrp(v)} mV` : formatPh;

  const targetLabel =
    target !== null
      ? `<span class="bar-label bar-label--target">Doel ${formatReading(target)}</span>`
      : `<span class="bar-label bar-label--muted">No target set</span>`;

  const nowLabel =
    value !== null
      ? `<span class="bar-label bar-label--live">Nu ${formatReading(value)}</span>`
      : `<span class="bar-label bar-label--muted">—</span>`;

  const delta =
    unit === "mV"
      ? formatDelta(value, target, 0)
      : formatDelta(value, target, 2);
  const deltaHtml =
    delta !== null
      ? `<span class="bar-delta" data-sign="${delta.startsWith("+") ? "pos" : delta.startsWith("-") ? "neg" : "zero"}">Δ ${delta}${unit === "mV" ? " mV" : ""}</span>`
      : "";

  return `
    <div class="comparison-bar" data-has-target="${target !== null ? "yes" : "no"}">
      <div class="bar-track">
        ${zoneHtml}
        ${targetTick}
        ${valueDot}
      </div>
      <div class="bar-legend">
        ${targetLabel}
        ${nowLabel}
        ${deltaHtml}
      </div>
    </div>
  `;
}

function targetChip(name, target, formatTarget, source) {
  if (target === null) {
    return `
      <div class="target-chip target-chip--empty">
        <span class="chip-kicker">${name} doel</span>
        <span class="chip-value">—</span>
        <span class="chip-source">Enable the pH/ORP target sensors on your Norsup device</span>
      </div>
    `;
  }
  const sourceLabel =
    source === "entity" ? "From sensor" : source === "manual" ? "Manual" : "";
  return `
    <div class="target-chip">
      <span class="chip-kicker">${name} · doel</span>
      <span class="chip-value">${formatTarget(target)}</span>
      ${sourceLabel ? `<span class="chip-source">${sourceLabel}</span>` : ""}
    </div>
  `;
}

function targetSource(hass, entityId, manual, resolved) {
  if (resolved === null) return "none";
  if (entityId && hass?.states[entityId] && parseNumber(hass.states[entityId]) !== null) {
    return "entity";
  }
  if (manual !== undefined && manual !== null && manual !== "") return "manual";
  return "entity";
}

class NorsupPoolHealthCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
  }

  static getStubConfig(hass) {
    const ph = pickNorsupLiveSensor(hass, "ph");
    const orp = pickNorsupLiveSensor(hass, "orp");
    const phTarget = resolveTargetEntity(hass, "", ph, "ph_target");
    const orpTarget = resolveTargetEntity(hass, "", orp, "orp_target");
    return {
      type: `custom:${CARD_TAG}`,
      ph_entity: ph,
      orp_entity: orp,
      ph_target_entity: phTarget,
      orp_target_entity: orpTarget,
      title: "Pool health",
    };
  }

  setConfig(config) {
    if (!config.ph_entity || !config.orp_entity) {
      throw new Error("Set ph_entity and orp_entity to your Norsup pH and ORP sensors");
    }
    this._config = {
      title: config.title ?? "Pool health",
      ph_entity: config.ph_entity,
      orp_entity: config.orp_entity,
      ph_target_entity: config.ph_target_entity ?? "",
      orp_target_entity: config.orp_target_entity ?? "",
      ph_target: config.ph_target ?? null,
      orp_target: config.orp_target ?? null,
      ph_min: config.ph_min ?? 6.8,
      ph_max: config.ph_max ?? 8.0,
      orp_min: config.orp_min ?? 400,
      orp_max: config.orp_max ?? 850,
      ph_target_tolerance: config.ph_target_tolerance ?? 0.2,
      orp_target_tolerance: config.orp_target_tolerance ?? 50,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 5;
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;

    const phState = this._hass?.states[this._config.ph_entity];
    const orpState = this._hass?.states[this._config.orp_entity];
    const phVal = parseNumber(phState);
    const orpVal = parseNumber(orpState);
    const phTargetEntity = resolveTargetEntity(
      this._hass,
      this._config.ph_target_entity,
      this._config.ph_entity,
      "ph_target"
    );
    const orpTargetEntity = resolveTargetEntity(
      this._hass,
      this._config.orp_target_entity,
      this._config.orp_entity,
      "orp_target"
    );
    const phTarget = resolveTarget(this._hass, phTargetEntity, this._config.ph_target);
    const orpTarget = resolveTarget(this._hass, orpTargetEntity, this._config.orp_target);
    const ph = phBand(phVal, phTarget, this._config.ph_target_tolerance);
    const orp = orpBand(orpVal, orpTarget, this._config.orp_target_tolerance);
    const health = overallHealth(ph, orp);

    const phPct = gaugeArc(phVal, this._config.ph_min, this._config.ph_max);
    const orpPct = gaugeArc(orpVal, this._config.orp_min, this._config.orp_max);

    const phOnTarget = ph.label === "On target" || ph.label === "Ideal";
    const orpOnTarget = orp.label === "On target" || orp.label === "Ideal";

    const ring = (pct, level, label, valueText, unit, target, tolerance, scaleMin, scaleMax, formatTarget, onTarget) => {
      const circumference = 2 * Math.PI * 54;
      const offset = circumference * (1 - pct);
      let targetSvg = "";
      let targetInGauge = "";
      if (target !== null) {
        const zoneMin = gaugeArc(target - tolerance, scaleMin, scaleMax);
        const zoneMax = gaugeArc(target + tolerance, scaleMin, scaleMax);
        const markerPct = gaugeArc(target, scaleMin, scaleMax);
        targetSvg = `${targetZoneArc(zoneMin, zoneMax, circumference)}${targetMarker(markerPct, onTarget)}`;
        targetInGauge = `<span class="gauge-target">doel ${formatTarget(target)}</span>`;
      }
      return `
        <div class="gauge" data-level="${level}" data-on-target="${onTarget ? "yes" : "no"}">
          <svg viewBox="0 0 120 120" aria-hidden="true">
            <defs>
              <filter id="glow-${unit.replace(/\s/g, "")}">
                <feGaussianBlur stdDeviation="2" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <circle class="track" cx="60" cy="60" r="54" />
            ${targetSvg}
            <circle
              class="progress"
              cx="60" cy="60" r="54"
              style="stroke-dasharray: ${circumference}; stroke-dashoffset: ${offset}"
            />
          </svg>
          <div class="gauge-center">
            <span class="gauge-value">${valueText}</span>
            <span class="gauge-unit">${unit}</span>
            ${targetInGauge}
            <span class="gauge-band">${label}</span>
          </div>
        </div>
      `;
    };

    const usesManualTarget =
      (phTarget !== null && !phTargetEntity) ||
      (orpTarget !== null && !orpTargetEntity);
    const footerNote = usesManualTarget
      ? "Manual doelwaarden · targets also sync from Norsup pH/ORP target sensors when present"
      : "Green arc = dosing band · tick = doel (target) from your pool";

    const phSource = targetSource(this._hass, phTargetEntity, this._config.ph_target, phTarget);
    const orpSource = targetSource(this._hass, orpTargetEntity, this._config.orp_target, orpTarget);

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: var(--ha-font-family, system-ui, sans-serif);
        }
        .card {
          position: relative;
          overflow: hidden;
          border-radius: 20px;
          padding: 1.1rem 1.25rem 1.25rem;
          color: #e8f7ff;
          background:
            radial-gradient(120% 80% at 100% 0%, rgba(56, 189, 248, 0.35), transparent 55%),
            radial-gradient(90% 70% at 0% 100%, rgba(13, 148, 136, 0.45), transparent 50%),
            linear-gradient(155deg, #042f3a 0%, #064e5e 42%, #0a3d4a 100%);
          box-shadow: 0 12px 40px rgba(2, 44, 56, 0.35);
          min-height: 220px;
        }
        .card::after {
          content: "";
          position: absolute;
          inset: 0;
          background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120' viewBox='0 0 120 120'%3E%3Cpath fill='%23ffffff08' d='M0 60 Q30 40 60 60 T120 60 V120 H0Z'/%3E%3C/svg%3E") repeat-x bottom;
          opacity: 0.5;
          pointer-events: none;
        }
        .header {
          position: relative;
          z-index: 1;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.75rem;
          margin-bottom: 0.75rem;
        }
        h2 {
          margin: 0;
          font-size: 1.05rem;
          font-weight: 600;
          letter-spacing: 0.02em;
        }
        .badge {
          font-size: 0.72rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          padding: 0.35rem 0.65rem;
          border-radius: 999px;
          border: 1px solid rgba(255,255,255,0.2);
          background: rgba(0,0,0,0.2);
        }
        .badge[data-level="great"] { background: rgba(16, 185, 129, 0.35); border-color: rgba(52, 211, 153, 0.5); }
        .badge[data-level="good"] { background: rgba(56, 189, 248, 0.3); border-color: rgba(125, 211, 252, 0.45); }
        .badge[data-level="warn"] { background: rgba(251, 191, 36, 0.35); border-color: rgba(252, 211, 77, 0.5); color: #fff8e7; }
        .badge[data-level="bad"] { background: rgba(248, 113, 113, 0.4); border-color: rgba(252, 165, 165, 0.55); }
        .badge[data-level="unknown"] { opacity: 0.85; }
        .doel-strip {
          position: relative;
          z-index: 1;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.5rem;
          margin-bottom: 0.85rem;
        }
        .target-chip {
          padding: 0.45rem 0.65rem;
          border-radius: 14px;
          background: linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0.04));
          border: 1px solid rgba(255,255,255,0.18);
          backdrop-filter: blur(8px);
          text-align: left;
        }
        .target-chip--empty {
          opacity: 0.75;
        }
        .chip-kicker {
          display: block;
          font-size: 0.62rem;
          text-transform: uppercase;
          letter-spacing: 0.1em;
          opacity: 0.8;
        }
        .chip-value {
          display: block;
          font-size: 1.05rem;
          font-weight: 700;
          margin-top: 0.1rem;
        }
        .chip-source {
          display: block;
          font-size: 0.58rem;
          opacity: 0.65;
          margin-top: 0.15rem;
        }
        .gauges {
          position: relative;
          z-index: 1;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0.75rem;
        }
        .gauge-wrap {
          text-align: center;
        }
        .gauge {
          position: relative;
          text-align: center;
        }
        svg {
          width: 100%;
          max-width: 140px;
          margin: 0 auto;
          display: block;
          transform: rotate(-90deg);
        }
        .track {
          fill: none;
          stroke: rgba(255,255,255,0.12);
          stroke-width: 10;
        }
        .target-zone {
          fill: none;
          stroke: rgba(52, 211, 153, 0.5);
          stroke-width: 10;
          stroke-linecap: butt;
          filter: drop-shadow(0 0 6px rgba(52, 211, 153, 0.35));
        }
        .target-marker {
          fill: #ecfdf5;
          stroke: rgba(6, 78, 59, 0.85);
          stroke-width: 1.5;
          transform: rotate(90deg);
          transform-origin: 60px 60px;
        }
        .target-marker.pulse {
          animation: target-pulse 2.2s ease-in-out infinite;
        }
        @keyframes target-pulse {
          0%, 100% { filter: drop-shadow(0 0 2px rgba(236, 253, 245, 0.6)); }
          50% { filter: drop-shadow(0 0 8px rgba(52, 211, 153, 0.9)); }
        }
        .progress {
          fill: none;
          stroke-width: 10;
          stroke-linecap: round;
          transition: stroke-dashoffset 0.45s ease, stroke 0.3s ease;
        }
        .gauge[data-level="great"] .progress { stroke: #34d399; filter: drop-shadow(0 0 4px rgba(52, 211, 153, 0.45)); }
        .gauge[data-level="good"] .progress { stroke: #38bdf8; }
        .gauge[data-level="warn"] .progress { stroke: #fbbf24; }
        .gauge[data-level="bad"] .progress { stroke: #f87171; }
        .gauge[data-level="unknown"] .progress { stroke: rgba(255,255,255,0.25); }
        .gauge-center {
          position: absolute;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -58%);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.05rem;
        }
        .gauge-value {
          font-size: 1.35rem;
          font-weight: 700;
          line-height: 1.1;
        }
        .gauge-unit {
          font-size: 0.65rem;
          opacity: 0.75;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }
        .gauge-target {
          font-size: 0.62rem;
          font-weight: 600;
          color: #a7f3d0;
          letter-spacing: 0.04em;
          text-transform: lowercase;
        }
        .gauge-band {
          margin-top: 0.1rem;
          font-size: 0.68rem;
          opacity: 0.9;
        }
        .metric-label {
          margin-top: 0.35rem;
          font-size: 0.78rem;
          font-weight: 600;
          opacity: 0.92;
        }
        .comparison-bar {
          margin-top: 0.55rem;
          padding: 0 0.15rem;
        }
        .bar-track {
          position: relative;
          height: 8px;
          border-radius: 999px;
          background: rgba(0,0,0,0.25);
          border: 1px solid rgba(255,255,255,0.12);
          overflow: visible;
        }
        .bar-zone {
          position: absolute;
          top: 0;
          bottom: 0;
          border-radius: 999px;
          background: linear-gradient(90deg, rgba(52,211,153,0.15), rgba(52,211,153,0.45), rgba(52,211,153,0.15));
        }
        .bar-tick {
          position: absolute;
          top: -3px;
          width: 3px;
          height: 14px;
          margin-left: -1.5px;
          border-radius: 2px;
          background: #ecfdf5;
          box-shadow: 0 0 6px rgba(236, 253, 245, 0.65);
        }
        .bar-dot {
          position: absolute;
          top: 50%;
          width: 12px;
          height: 12px;
          margin: -6px 0 0 -6px;
          border-radius: 50%;
          border: 2px solid rgba(255,255,255,0.9);
        }
        .bar-dot--live {
          background: #38bdf8;
          box-shadow: 0 0 10px rgba(56, 189, 248, 0.75);
        }
        .bar-legend {
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 0.35rem 0.65rem;
          margin-top: 0.35rem;
          font-size: 0.62rem;
          opacity: 0.88;
        }
        .bar-label--target { color: #a7f3d0; font-weight: 600; }
        .bar-label--live { font-weight: 600; }
        .bar-label--muted { opacity: 0.55; }
        .bar-delta {
          font-weight: 700;
          padding: 0.1rem 0.35rem;
          border-radius: 6px;
          background: rgba(0,0,0,0.2);
        }
        .bar-delta[data-sign="pos"] { color: #fde68a; }
        .bar-delta[data-sign="neg"] { color: #7dd3fc; }
        .bar-delta[data-sign="zero"] { color: #a7f3d0; }
        .footer {
          position: relative;
          z-index: 1;
          margin-top: 0.85rem;
          font-size: 0.68rem;
          opacity: 0.65;
          text-align: center;
        }
      </style>
      <div class="card">
        <div class="header">
          <h2>${this._config.title}</h2>
          <span class="badge" data-level="${health.level}">${health.label}</span>
        </div>
        <div class="doel-strip">
          ${targetChip("pH", phTarget, formatPh, phSource)}
          ${targetChip("ORP", orpTarget, (v) => `${formatOrp(v)} mV`, orpSource)}
        </div>
        <div class="gauges">
          <div class="gauge-wrap">
            ${ring(
              phPct,
              ph.level,
              ph.label,
              formatPh(phVal),
              "pH",
              phTarget,
              this._config.ph_target_tolerance,
              this._config.ph_min,
              this._config.ph_max,
              formatPh,
              phOnTarget
            )}
            <div class="metric-label">pH · live vs doel</div>
            ${comparisonBar(
              phVal,
              phTarget,
              this._config.ph_target_tolerance,
              this._config.ph_min,
              this._config.ph_max,
              "pH"
            )}
          </div>
          <div class="gauge-wrap">
            ${ring(
              orpPct,
              orp.level,
              orp.label,
              formatOrp(orpVal),
              "mV ORP",
              orpTarget,
              this._config.orp_target_tolerance,
              this._config.orp_min,
              this._config.orp_max,
              formatOrp,
              orpOnTarget
            )}
            <div class="metric-label">ORP · live vs doel</div>
            ${comparisonBar(
              orpVal,
              orpTarget,
              this._config.orp_target_tolerance,
              this._config.orp_min,
              this._config.orp_max,
              "mV"
            )}
          </div>
        </div>
        <div class="footer">Norsup Smartpool · ${footerNote}</div>
      </div>
    `;
  }
}

customElements.define(CARD_TAG, NorsupPoolHealthCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: `custom:${CARD_TAG}`,
  name: CARD_NAME,
  description: "Pool health dashboard from pH and ORP sensors with doel/target dosing bands",
  preview: true,
});
