import styles from './PoolHealthPreview.module.css'

/** Static preview of the Lovelace Pool Health card (demo values). */
export default function PoolHealthPreview() {
  return (
    <div
      className={styles.card}
      role="img"
      aria-label="Pool health preview: pH 7.35 vs doel 7.20, ORP 682 mV vs doel 700 mV, status Good"
    >
      <div className={styles.header}>
        <h3 className={styles.title}>Pool health</h3>
        <span className={styles.badge} data-level="good">Good</span>
      </div>
      <div className={styles.doelStrip}>
        <div className={styles.targetChip}>
          <span className={styles.chipKicker}>pH · doel</span>
          <span className={styles.chipValue}>7.20</span>
          <span className={styles.chipSource}>From sensor</span>
        </div>
        <div className={styles.targetChip}>
          <span className={styles.chipKicker}>ORP · doel</span>
          <span className={styles.chipValue}>700 mV</span>
          <span className={styles.chipSource}>From sensor</span>
        </div>
      </div>
      <div className={styles.gauges}>
        <div className={styles.gaugeBlock}>
          <div className={styles.gauge} data-level="great" data-on-target="yes">
            <svg viewBox="0 0 120 120" aria-hidden="true">
              <circle className={styles.track} cx="60" cy="60" r="54" />
              <circle className={styles.targetZone} cx="60" cy="60" r="54" />
              <circle className={styles.targetMarker} cx="60" cy="6" r="5" />
              <circle className={styles.progress} cx="60" cy="60" r="54" />
            </svg>
            <div className={styles.gaugeCenter}>
              <span className={styles.gaugeValue}>7.35</span>
              <span className={styles.gaugeUnit}>pH</span>
              <span className={styles.gaugeTarget}>doel 7.20</span>
              <span className={styles.gaugeBand}>Ideal</span>
            </div>
          </div>
          <p className={styles.metricLabel}>pH · live vs doel</p>
          <div className={styles.comparisonBar}>
            <div className={styles.barTrack}>
              <div className={styles.barZone} style={{ left: '42%', width: '12%' }} />
              <div className={styles.barTick} style={{ left: '48%' }} />
              <div className={styles.barDot} style={{ left: '52%' }} />
            </div>
            <div className={styles.barLegend}>
              <span className={styles.barTarget}>Doel 7.20</span>
              <span className={styles.barLive}>Nu 7.35</span>
              <span className={styles.barDelta}>Δ +0.15</span>
            </div>
          </div>
        </div>
        <div className={styles.gaugeBlock}>
          <div className={styles.gauge} data-level="great" data-on-target="yes">
            <svg viewBox="0 0 120 120" aria-hidden="true">
              <circle className={styles.track} cx="60" cy="60" r="54" />
              <circle className={styles.targetZone} cx="60" cy="60" r="54" style={{ strokeDashoffset: 120 }} />
              <circle className={styles.targetMarker} cx="88" cy="60" r="5" />
              <circle className={styles.progress} cx="60" cy="60" r="54" style={{ strokeDashoffset: 95 }} />
            </svg>
            <div className={styles.gaugeCenter}>
              <span className={styles.gaugeValue}>682</span>
              <span className={styles.gaugeUnit}>mV ORP</span>
              <span className={styles.gaugeTarget}>doel 700</span>
              <span className={styles.gaugeBand}>Ideal</span>
            </div>
          </div>
          <p className={styles.metricLabel}>ORP · live vs doel</p>
          <div className={styles.comparisonBar}>
            <div className={styles.barTrack}>
              <div className={styles.barZone} style={{ left: '55%', width: '14%' }} />
              <div className={styles.barTick} style={{ left: '62%' }} />
              <div className={styles.barDot} style={{ left: '58%' }} />
            </div>
            <div className={styles.barLegend}>
              <span className={styles.barTarget}>Doel 700 mV</span>
              <span className={styles.barLive}>Nu 682 mV</span>
              <span className={styles.barDelta} data-sign="neg">Δ -18 mV</span>
            </div>
          </div>
        </div>
      </div>
      <p className={styles.footer}>Bundled Lovelace card · doel band + live comparison bars</p>
    </div>
  )
}
