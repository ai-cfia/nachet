# nachet-mini

A lightweight, offline-capable Progressive Web App (PWA) for weed seed identification. ML models run entirely in-browser via Web Workers — no backend connection required for local development.

## Prerequisites

- [Node.js](https://nodejs.org/) ^24.5.0
- npm ^11.5.2

## Installation

From the `nachet-mini/` directory:

```bash
npm ci
```

## Development

Before making changes, run `npm version patch`. This updates `package.json`,
`package-lock.json`, and `src/_versions.ts`.

```bash
npm run dev
```

Opens the app at `http://localhost:5173` with hot-module replacement.

## Building

```bash
npm run build
```

Output is written to `dist/`. To set a non-root base URL (e.g. for GitHub Pages), set `VITE_BASE_URL` before building:

```bash
VITE_BASE_URL=/nachet-mini/ npm run build
```

## Testing

### Unit tests (jsdom)

```bash
npm test
```

### Unit tests with coverage

```bash
npm run test:coverage
```

### Browser tests (Playwright / Chromium)

One-time setup — install the Chromium browser binary:

```bash
npx playwright install chromium --with-deps
```

Then run:

```bash
npm run test:browser
```

Browser tests cover the inference Web Worker integration and run in a real Chromium instance. They run separately from the unit tests and require the unit tests to pass first in CI.

## Code quality

```bash
npm run lint          # ESLint + TypeScript type check
npm run format        # Format all source files with Prettier
npm run format:check  # Check formatting without writing changes
```
