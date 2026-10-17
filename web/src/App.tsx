import { useEffect, useState } from 'react'
import WhatsNew from '@loom/whats-new/WhatsNew'
import whatsNewManifest from '@loom/whats-new/whats-new.json'
import styles from './App.module.css'

const HACS_REPO =
  'https://github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin'

type IntegrationInfo = {
  domain: string
  name: string
  version: string
  hacs: { repository: string; category: string; path: string }
  portal: string
}

export default function App() {
  const [info, setInfo] = useState<IntegrationInfo | null>(null)
  const [copied, setCopied] = useState(false)
  const [apiStatus, setApiStatus] = useState<'loading' | 'ok' | 'offline'>('loading')

  useEffect(() => {
    fetch('/v1/integration')
      .then(r => {
        if (!r.ok) throw new Error('bad status')
        return r.json()
      })
      .then(data => {
        setInfo(data)
        setApiStatus('ok')
      })
      .catch(() => setApiStatus('offline'))
  }, [])

  async function copyRepo() {
    await navigator.clipboard.writeText(HACS_REPO)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.kicker}>Smart Pool Connect · Home Assistant</p>
        <h1>Norsup Smartpool</h1>
        <p className={styles.lead}>
          Unofficial integration for Norsup pools. Sign in with your Smart Pool Connect email and
          password (pool UUID optional), or use a Norsup-issued bearer token. Monitor chemistry and
          pump status from Home Assistant.
        </p>
        {info ? (
          <p className={styles.version}>
            Integration v{info.version} · domain <code>{info.domain}</code>
          </p>
        ) : null}
        <span className={styles.apiPill} data-state={apiStatus}>
          {apiStatus === 'loading' && 'Checking companion API…'}
          {apiStatus === 'ok' && 'Companion API online'}
          {apiStatus === 'offline' && 'API offline — docs still apply'}
        </span>
      </header>

      <main className={styles.grid}>
        <section className={styles.card} aria-labelledby="hacs-title">
          <h2 id="hacs-title">Install via HACS</h2>
          <p>
            In HACS choose <strong>Integrations</strong> → menu → <strong>Custom repositories</strong>.
            Use category <strong>Integration</strong> (not Plugin).
          </p>
          <div className={styles.hacsFix}>
            <strong>HACS “No manifest.json” error?</strong> This repo ships{' '}
            <code>custom_components/norsup_smartpool/manifest.json</code>. Do not enable
            “content in root” — the integration lives under <code>custom_components/</code>.
          </div>
          <label className={styles.fieldLabel} htmlFor="repo-url">Repository URL</label>
          <div className={styles.copyRow}>
            <input id="repo-url" readOnly value={HACS_REPO} className={styles.input} />
            <button type="button" className={styles.primaryBtn} onClick={() => void copyRepo()}>
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <ol className={styles.steps}>
            <li>Add the repository, then download <strong>Norsup Smartpool</strong> from HACS.</li>
            <li>Restart Home Assistant.</li>
            <li>
              Settings → Devices &amp; services → Add integration → <strong>Norsup Smartpool</strong>.
            </li>
          </ol>
        </section>

        <section className={styles.card} aria-labelledby="key-title">
          <h2 id="key-title">Sign in (recommended)</h2>
          <p>
            In Home Assistant choose <strong>Smart Pool Connect account</strong> and use the same email
            and password as the website. Pool UUID is optional when you have one pool — the integration
            discovers it. <strong>SPC API keys</strong> (<code>spc_…</code>) use the REST API at{' '}
            <code>api.smartpoolconnect.eu</code> — not the portal live-status URL.
          </p>
          <ul className={styles.checklist}>
            <li>
              Sign in at{' '}
              <a href="https://www.smartpoolconnect.eu" target="_blank" rel="noreferrer">
                smartpoolconnect.eu
              </a>
            </li>
            <li>Claim your pool with the NorsupOne MAC if you have not already.</li>
            <li>Copy your API key from the portal (Integrations / API / Developer — if available).</li>
            <li>
              Open your pool in the portal and copy the UUID from the address bar (
              <code>/pool/&lt;uuid&gt;/…</code>).
            </li>
          </ul>
          <p>
            Full credential steps:{' '}
            <a href={`${HACS_REPO}/blob/main/INSTALL.md`} target="_blank" rel="noreferrer">
              INSTALL.md on GitHub
            </a>
            . Never paste API keys into issues or this page.
          </p>
        </section>

        <section className={styles.card} aria-labelledby="debug-title">
          <h2 id="debug-title">Debug invalid auth locally</h2>
          <p>
            If Home Assistant shows <strong>invalid auth</strong>, test the same cloud check in your
            local Python environment (this repo clone). For API keys it calls{' '}
            <code>GET /pool</code> on the REST host with <code>X-API-Key</code> (same as Home
            Assistant). Pool ID is optional when you have one pool. If you see a certificate/SSL error
            on macOS, add <code>--insecure</code> (debug only).
          </p>
          <pre className={styles.codeBlock}>
{`python -m pip install -r requirements-dev.txt
export NORSUP_EMAIL='you@example.com'
export NORSUP_PASSWORD='portal-password'
python scripts/debug_auth.py --portal
python scripts/debug_auth.py --portal --insecure   # skip TLS verify, local debug only

# SPC API key (pool id optional):
export NORSUP_API_KEY='spc_your_key'
python scripts/debug_auth.py --verbose`}
          </pre>
          <p>
            Exit <strong>0</strong> = OK · <strong>1</strong> = rejected (invalid auth) ·{' '}
            <strong>2</strong> = network/server error. Full steps:{' '}
            <a href={`${HACS_REPO}/blob/main/INSTALL.md#test-credentials-in-your-local-python-environment`} target="_blank" rel="noreferrer">
              INSTALL.md
            </a>
            .
          </p>
        </section>

        <section className={styles.cardWide} aria-labelledby="release-title">
          <h2 id="release-title">GitHub release</h2>
          <p>
            Prefer a zip? Download the latest release asset or clone the repository and copy{' '}
            <code>custom_components/norsup_smartpool</code> into your HA <code>config/</code> folder.
          </p>
          <a
            className={styles.secondaryLink}
            href={`${HACS_REPO}/releases`}
            target="_blank"
            rel="noreferrer"
          >
            View releases on GitHub →
          </a>
        </section>
      </main>

      <footer className={styles.footer}>
        <span>Made with Loom</span>
        <span className={styles.footerSep}>·</span>
        <a href={HACS_REPO} target="_blank" rel="noreferrer">Source repository</a>
      </footer>

      <WhatsNew appId="norsup-smartpool-ha" manifest={whatsNewManifest} />
    </div>
  )
}
