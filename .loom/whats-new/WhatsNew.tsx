import { useEffect, useState } from 'react'
import {
  latestEntry,
  markVersionSeen,
  shouldShowWhatsNew,
  whatsNewStorageKey,
  type WhatsNewManifest,
} from './whatsNewStorage'

export default function WhatsNew({
  appId,
  manifest,
}: {
  appId: string
  manifest: WhatsNewManifest
}) {
  const [open, setOpen] = useState(false)
  const entry = latestEntry(manifest)

  useEffect(() => {
    if (!entry) return
    const key = whatsNewStorageKey(appId)
    if (shouldShowWhatsNew(key, manifest.version)) {
      setOpen(true)
    }
  }, [appId, entry, manifest.version])

  if (!open || !entry) return null

  function dismiss() {
    markVersionSeen(whatsNewStorageKey(appId), manifest.version)
    setOpen(false)
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="whats-new-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <button
        type="button"
        aria-label="Close what's new"
        onClick={dismiss}
        style={{
          position: 'absolute',
          inset: 0,
          border: 'none',
          background: 'rgba(0, 0, 0, 0.45)',
          cursor: 'pointer',
        }}
      />
      <div
        style={{
          position: 'relative',
          width: 'min(28rem, 100%)',
          borderRadius: '1rem',
          padding: '1.25rem',
          background: 'var(--panel-solid, #fff)',
          color: 'var(--text, #111)',
          boxShadow: '0 18px 50px rgba(0, 0, 0, 0.22)',
        }}
      >
        <h2 id="whats-new-title" style={{ margin: '0 0 0.5rem', fontSize: '1.25rem' }}>
          {entry.title}
        </h2>
        {entry.date ? <p style={{ margin: '0 0 1rem', opacity: 0.7, fontSize: '0.85rem' }}>{entry.date}</p> : null}
        <ul style={{ margin: '0 0 1.25rem', paddingLeft: '1.1rem' }}>
          {entry.items.map(item => (
            <li key={item} style={{ marginBottom: '0.45rem' }}>{item}</li>
          ))}
        </ul>
        <button type="button" onClick={dismiss}>Got it</button>
      </div>
    </div>
  )
}
