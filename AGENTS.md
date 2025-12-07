# Repository Guidelines

## Project Structure & Module Organization
- App source lives in `src/` with feature code split by role: shared UI in `src/components/`, screens in `src/pages/`, hooks in `src/hooks/`, state in `src/store/`, and utilities in `src/lib/`. Assets go in `src/assets/`. Styling is via `src/index.css`, `src/App.css`, and Tailwind tokens in `src/variables.css`.
- Tests and helpers sit under `src/test/` (`setup.ts`, `utils.tsx`, mocks). Bundled output lands in `dist/` after a production build. Vite, Tailwind, and Capacitor configs are in the repo root.

## Build, Test, and Development Commands
- `npm run dev` — start the Vite dev server with HMR.
- `npm run build` — type-check with `tsc -b`, then build optimized assets to `dist/`.
- `npm run preview` — serve the production build locally.
- `npm run lint` — run ESLint over the codebase.
- `npm run test` — run Vitest in watch/UI mode; `npm run test:run` for CI-friendly runs.

## Coding Style & Naming Conventions
- Language: TypeScript + React function components; prefer hooks and composition over class components.
- Indentation: 2 spaces; favor double quotes in TSX/TS to match existing files.
- Components and hooks: `PascalCase` for components (`SeatList.tsx`), `camelCase` for helpers, `useX` for hooks.
- Keep UI logic in components and business logic in `lib/` or `store/`. Co-locate small feature styles or fixtures with their components when practical.

## Testing Guidelines
- Framework: Vitest with React Testing Library and JSDOM (`src/test/setup.ts` wires defaults). Add screen interactions via `@testing-library/user-event`.
- Place unit/component tests alongside the code under test or in `src/test/` when shared. Name files `*.test.ts`/`*.test.tsx`.
- Prefer behavior-focused assertions (`getByRole`, `findByText`) over implementation details. Mock network/Capacitor calls in `src/test/mocks/`.

## Commit & Pull Request Guidelines
- Commits should be scoped, present-tense summaries (e.g., `Add seat selection state sync`, `Fix checkout price calculation`). Avoid bundling unrelated changes.
- Before a PR: run `npm run lint` and `npm run test:run`; attach summaries of test output.
- PRs should describe the change, link issues, and include user-facing notes (screenshots or short clips for UI updates, especially mobile views). Call out risky areas (payments, navigation, data fetch) and any follow-up tasks.

## Security & Configuration Tips
- Keep secrets out of the repo; use environment variables and platform secret stores. Do not commit `seatsteal.pem` updates.
- Capacitor/IOS builds rely on local platform tooling; verify native configs after changing `capacitor.config.ts` or `ios/` assets.
