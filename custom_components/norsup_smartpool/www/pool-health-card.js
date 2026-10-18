/**
 * Norsup Smartpool — Pool Health Lovelace card (pH + ORP).
 * Resource: /norsup_smartpool/pool-health-card.js (type: module)
 */

const CARD_TAG = "norsup-pool-health-card";
const CARD_NAME = "Norsup Pool Health";

function parseNumber(state) {
  if (!state || state.state === "unavailable" || state.state === "unknown") {
    return null;
  }
  const value = Number(state.state);
  return Number.isFinite(value) ? value : null;
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

function targetMarker(pct) {
  const theta = pct * 2 * Math.PI - Math.PI / 2;
  const x = 60 + 54 * Math.cos(theta);
  const y = 60 + 54 * Math.sin(theta);
  return `<circle class="target-marker" cx="${x.toFixed(2)}" cy="${y.toFixed(2)}" r="4.5" />`;
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

class NorsupPoolHealthCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
  }

  static getStubConfig(hass) {
    const candidates = Object.keys(hass.states).filter((id) =>
      id.startsWith("sensor.") && hass.states[id].attributes?.device_class !== undefined
    );
    const norsup = candidates.filter((id) => {
      const ent = hass.states[id];
      const platform = ent.attributes?.platform ?? "";
      return id.includes("norsup") || platform === "norsup_smartpool";
    });
    const ph =
      norsup.find((id) => id.endsWith("_ph") || id.includes("ph")) ??
      candidates.find((id) => id.includes("ph")) ??
      "";
    const orp =
      norsup.find((id) => id.endsWith("_orp") || id.includes("orp")) ??
      candidates.find((id) => id.includes("orp")) ??
      "";
    const phTarget =
      norsup.find((id) => id.includes("ph_target")) ??
      candidates.find((id) => id.includes("ph_target")) ??
      "";
    const orpTarget =
      norsup.find((id) => id.includes("orp_target")) ??
      candidates.find((id) => id.includes("orp_target")) ??
      "";
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
    return 4;
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;

    const phState = this._hass?.states[this._config.ph_entity];
    const orpState = this._hass?.states[this._config.orp_entity];
    const phVal = parseNumber(phState);
    const orpVal = parseNumber(orpState);
    const phTarget = resolveTarget(this._hass, this._config.ph_target_entity, this._config.ph_target);
    const orpTarget = resolveTarget(this._hass, this._config.orp_target_entity, this._config.orp_target);
    const ph = phBand(phVal, phTarget, this._config.ph_target_tolerance);
    const orp = orpBand(orpVal, orpTarget, this._config.orp_target_tolerance);
    const health = overallHealth(ph, orp);

    const phPct = gaugeArc(phVal, this._config.ph_min, this._config.ph_max);
    const orpPct = gaugeArc(orpVal, this._config.orp_min, this._config.orp_max);

    const ring = (pct, level, label, valueText, unit, target, tolerance, scaleMin, scaleMax, formatTarget) => {
      const circumference = 2 * Math.PI * 54;
      const offset = circumference * (1 - pct);
      let targetSvg = "";
      let targetCaption = "";
      if (target !== null) {
        const zoneMin = gaugeArc(target - tolerance, scaleMin, scaleMax);
        const zoneMax = gaugeArc(target + tolerance, scaleMin, scaleMax);
        const markerPct = gaugeArc(target, scaleMin, scaleMax);
        targetSvg = `${targetZoneArc(zoneMin, zoneMax, circumference)}${targetMarker(markerPct)}`;
        targetCaption = `<div class="target-hint">Target ${formatTarget(target)}</div>`;
      }
      return `
        <div class="gauge" data-level="${level}">
          <svg viewBox="0 0 120 120" aria-hidden="true">
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
            <span class="gauge-band">${label}</span>
          </div>
        </div>
        ${targetCaption}
      `;
    };

    const usesManualTarget =
      (phTarget !== null && !this._config.ph_target_entity) ||
      (orpTarget !== null && !this._config.orp_target_entity);
    const footerNote = usesManualTarget
      ? "Manual targets · enable pH/ORP target sensors when the API exposes them"
      : "Green band and tick show dosing targets from your pool";

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
          min-height: 200px;
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
          margin-bottom: 1rem;
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
          stroke: rgba(52, 211, 153, 0.42);
          stroke-width: 10;
          stroke-linecap: butt;
        }
        .target-marker {
          fill: #ecfdf5;
          stroke: rgba(6, 78, 59, 0.85);
          stroke-width: 1.5;
          transform: rotate(90deg);
          transform-origin: 60px 60px;
        }
        .progress {
          fill: none;
          stroke-width: 10;
          stroke-linecap: round;
          transition: stroke-dashoffset 0.45s ease, stroke 0.3s ease;
        }
        .gauge[data-level="great"] .progress { stroke: #34d399; }
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
          gap: 0.1rem;
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
        .gauge-band {
          margin-top: 0.15rem;
          font-size: 0.68rem;
          opacity: 0.9;
        }
        .metric-label {
          margin-top: 0.35rem;
          font-size: 0.78rem;
          font-weight: 600;
          opacity: 0.92;
        }
        .target-hint {
          margin-top: 0.2rem;
          font-size: 0.68rem;
          opacity: 0.78;
          letter-spacing: 0.02em;
        }
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
              formatPh
            )}
            <div class="metric-label">pH</div>
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
              formatOrp
            )}
            <div class="metric-label">ORP</div>
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
  description: "Pool health dashboard from pH and ORP sensors with visual dosing targets",
  preview: true,
});
