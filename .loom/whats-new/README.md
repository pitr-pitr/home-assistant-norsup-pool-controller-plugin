# What's new popup

Loom ships this template so every product can show a calm "What's new" dialog the first time
someone opens the UI after an update.

## Integrate

1. Copy `whatsNewStorage.ts`, `WhatsNew.tsx`, and `whats-new.json` into your frontend (for example `src/components/`).
2. Mount `<WhatsNew appId="your-product-slug" manifest={whatsNewManifest} />` in the root app component.
3. Import the manifest: `import whatsNewManifest from './whats-new.json'` (or the path you chose).

## When you ship improvements

1. Bump the top-level `version` in `whats-new.json`.
2. Add a matching entry under `entries` with a short title and bullet list of user-visible changes.
3. Rebuild the frontend so the new version ships to users.

Users who already saw the previous version will see the popup once after the update.
