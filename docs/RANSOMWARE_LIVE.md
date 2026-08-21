# Ransomware.live API integration

The project includes an adapter for API Pro.

Because API Pro routes can differ by plan/version, configure the exact documented endpoint in:

`backend/.env`

```env
RANSOMWARE_LIVE_API_KEY=...
RANSOMWARE_LIVE_GROUP_ENDPOINT=...
```

Use `{slug}` in the endpoint if the documented route accepts a group slug.

The adapter sends the API key as both:
- `Authorization: Bearer <key>`
- `X-API-Key: <key>`

and accepts flexible JSON wrappers (`data`, `results`, `items`, `victims`, etc.).

The importer normalizes:
- victim/name/company
- country
- activity/industry/sector
- published/date
- discovered
- description
- website
- post/source URL

The importer never exposes the API key to the browser.
