# Contributing

Thank you for helping improve the **Norsup Smartpool** Home Assistant integration.

## Before you open an issue or pull request

- Read [INSTALL.md](INSTALL.md) for API key and pool ID setup.
- **Never paste API keys, bearer tokens, or session cookies** in GitHub issues, discussions, or pull requests. Use Home Assistant’s **redacted** log download when sharing logs (see [INSTALL.md — Troubleshooting](INSTALL.md#troubleshooting)).
- Search existing issues to avoid duplicates.

## Development setup

1. Clone the repository into a folder on your machine.
2. Copy or symlink `custom_components/norsup_smartpool` into your Home Assistant `config/custom_components/` directory, **or** run tests from the repo root (see below).
3. Restart Home Assistant after code changes to the integration.

### Running tests

From the repository root (with Home Assistant test dependencies installed):

```bash
pytest tests/
```

## Pull requests

- Keep changes focused; one logical change per PR when possible.
- Match existing code style (type hints, `ruff` if configured).
- Add or update tests when changing API parsing or config flow behavior.
- Update [README.md](README.md) or [INSTALL.md](INSTALL.md) when user-facing behavior changes.

## Releases

Version tags and GitHub Releases are managed via GitHub Actions (`.github/workflows/release.yml`).

1. Bump `"version"` in `custom_components/norsup_smartpool/manifest.json` (semver, no `v` prefix).
2. Merge to the default branch.
3. Create and push an annotated tag that matches the manifest, for example `v0.1.0` for manifest `"0.1.0"`:

   ```bash
   git tag -a v0.1.0 -m "Release 0.1.0"
   git push origin v0.1.0
   ```

The release workflow runs tests, verifies the manifest version, builds `norsup_smartpool-<version>.zip` for manual install, and publishes a GitHub Release with generated notes.

## Recommended default-branch protection

Repository maintainers should enable **branch protection** on `main` (or your default branch) with at least:

| Setting | Recommendation |
|--------|----------------|
| Require a pull request before merging | On (no direct pushes to default branch) |
| Require status checks to pass | On — require the **CI** workflow (`lint-and-test`) |
| Require branches to be up to date | On (optional but helps avoid stale merges) |
| Require signed commits | Optional |
| Restrict who can push | Limit to maintainers; use PRs from forks |

These rules keep `manifest.json` version bumps and integration changes reviewed while CI blocks broken tests or lint failures.

## Unofficial integration disclaimer

This project is **not** affiliated with Norsup. It uses the public Smart Pool Connect cloud API. Breaking changes on Norsup’s side may require integration updates.
