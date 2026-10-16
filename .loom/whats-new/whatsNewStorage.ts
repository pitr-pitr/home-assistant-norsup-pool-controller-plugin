export type WhatsNewEntry = {
  version: string
  date?: string
  title: string
  items: string[]
}

export type WhatsNewManifest = {
  version: string
  entries: WhatsNewEntry[]
}

const STORAGE_PREFIX = 'loom-whats-new-seen:'

export function whatsNewStorageKey(appId: string): string {
  return `${STORAGE_PREFIX}${appId}`
}

export function getSeenVersion(storageKey: string): string | null {
  try {
    return localStorage.getItem(storageKey)
  } catch {
    return null
  }
}

export function markVersionSeen(storageKey: string, version: string): void {
  try {
    localStorage.setItem(storageKey, version)
  } catch {
    // ignore quota / private mode
  }
}

export function shouldShowWhatsNew(storageKey: string, version: string): boolean {
  if (!version) return false
  return getSeenVersion(storageKey) !== version
}

export function latestEntry(manifest: WhatsNewManifest): WhatsNewEntry | null {
  if (!manifest.entries?.length) return null
  const match = manifest.entries.find(entry => entry.version === manifest.version)
  return match ?? manifest.entries[manifest.entries.length - 1]
}
