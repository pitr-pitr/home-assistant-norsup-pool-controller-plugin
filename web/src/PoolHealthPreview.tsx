import styles from './PoolHealthPreview.module.css'

/** Static preview of the Lovelace Pool Health card (demo values). */
export default function PoolHealthPreview() {
  return (
    <div className={styles.card} role="img" aria-label="Pool health preview: pH 7.35, ORP 682 mV, status Good">
      <div className={styles.header}>
        <h3 className={styles.title}>Pool health</h3>
        <span className={styles.badge} data-level="good">Good</span>
      </div>
      <div className={styles.gauges}>
        <div className={styles.gaugeBlock}>
          <div className={styles.gauge} data-level="great">
            <svg viewBox="0 0 120 120" aria-hidden="true">
              <circle className={styles.track} cx="60" cy="60" r="54" />
              <circle className={styles.targetZone} cx="60" cy="60" r="54" />
              <circle className={styles.targetMarker} cx="60" cy="6" r="4.5" />
              <circle className={styles.progress} cx="60" cy="60" r="54" />
            </svg>
            <div className={styles.gaugeCenter}>
              <span className={styles.gaugeValue}>7.35</span>
              <span className={styles.gaugeUnit}>pH</span>
              <span className={styles.gaugeBand}>Ideal</span>
            </div>
          </div>
          <p className={styles.metricLabel}>pH</p>
          <p className={styles.targetHint}>Target 7.20</p>
        </div>
        <div className={styles.gaugeBlock}>
          <div className={styles.gauge} data-level="great">
            <svg viewBox="0 0 120 120" aria-hidden="true">
              <circle className={styles.track} cx="60" cy="60" r="54" />
              <circle className={styles.targetZone} cx="60" cy="60" r="54" style={{ strokeDashoffset: 120 }} />
              <circle className={styles.targetMarker} cx="88" cy="60" r="4.5" />
              <circle className={styles.progress} cx="60" cy="60" r="54" style={{ strokeDashoffset: 95 }} />
            </svg>
            <div className={styles.gaugeCenter}>
              <span className={styles.gaugeValue}>682</span>
              <span className={styles.gaugeUnit}>mV ORP</span>
              <span className={styles.gaugeBand}>Ideal</span>
            </div>
          </div>
          <p className={styles.metricLabel}>ORP</p>
          <p className={styles.targetHint}>Target 700</p>
        </div>
      </div>
      <p className={styles.footer}>Bundled Lovelace card · uses your pH &amp; ORP sensors</p>
    </div>
  )
}
