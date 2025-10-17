# seatsteal directory (frontend)

## Code style

- Use ES modules (import/export) syntax, not CommonJS (require).
- Destructure imports when possible (eg. import { foo } from 'bar').
- Do not use type `any`.
- Use `const` for constants and `let` for variables that change.
- Use `async/await` for asynchronous code, not callbacks or `.then()`.

## Workflow

- IMPORTANT: Always build after making changes. Fix all build errors.
- When you're done making changes, run `prettier -w **/*.ts && prettier -w **/*.tsx` from the seatsteal directory to format all code.

# webapp directory (backend)

## Code style

## Workflow
- Make sure to `source venv/bin/activate` to activate the virtual environment before running or testing the webapp.
- When you're done making changes, run `black .` from the webapp directory to format all code. If you don't have black installed, run `pip install black`.
- Make sure to run all tests before committing changes. Use `pytest` to run the tests.
