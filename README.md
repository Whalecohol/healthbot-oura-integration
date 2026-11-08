# HealthBot Personal Oura Integration

Public, provisional pages for a personal Oura integration that is not enabled.

The site is static HTML in `docs/`:

- `docs/index.html` — overview of the intended single-user integration
- `docs/privacy/index.html` — privacy draft
- `docs/terms/index.html` — terms draft

The pages were drafted on 2026-11-08. That date is a drafting date. The owner has not adopted the pages as a privacy policy or as terms of service. The HTML does not include the MCP server, OAuth code, credentials, or a connection to Oura.

## Checks

From the repository root:

```bash
python3 tests/check_site.py
```

The check confirms the three pages, their cross-links, mobile and contrast CSS, the provisional wording, and the absence of forms, scripts, trackers, email addresses, and external assets. The same check runs in GitHub Actions on pull requests and on pushes to `main`.

## GitHub Pages

Publication uses GitHub's native Pages setting. This repository does not turn that setting on by itself.

After the pages are on `main`, a person who can administer the repository opens:

https://github.com/Whalecohol/healthbot-oura-integration/settings/pages

Then:

1. Build and deployment: **Deploy from a branch**.
2. Branch: **main**.
3. Folder: **/docs**.
4. Save.

`docs/.nojekyll` tells that branch deployment to publish the HTML as written.

When GitHub reports the deployment finished, the paths are:

- https://whalecohol.github.io/healthbot-oura-integration/
- https://whalecohol.github.io/healthbot-oura-integration/privacy/
- https://whalecohol.github.io/healthbot-oura-integration/terms/

Treat those addresses as live only after an anonymous HTTP request returns the pages. No custom domain, extra account, or payment is required for this setting.
