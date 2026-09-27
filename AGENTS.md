# AGENTS.md

## Repository layout

- pnpm workspace. Apps live in `apps/*` and packages shared between them live in `packages/*`.
- `pnpm-workspace.yaml` holds every pnpm setting, not just the package globs: the `catalog` of shared dependency versions, `minimumReleaseAge`, `allowBuilds`, and `patchedDependencies`. Check it before adding a dependency.
- `workbench/` is a space where different experiments are conducted, such as video download / analysis strategies.
- Keep code in the app or package that uses it. Do not add anything to `packages/` until a second workspace package needs it.

## Before you finish

Run the project checks after changing relevant code:

```bash
pnpm check
```

Do not start dev servers, or run native build commands, unless the user asks.

## Git commits

Use [Conventional Commits](https://www.conventionalcommits.org/) when writing commit messages.

- Prefer a feature or domain scope when the change is localized, such as `feat(gallery): ...` or `fix(camera): ...`. Match scopes to folders under `src/features/<feature>/` when possible.
- Use the package name when a change is specific to one package but not to one feature, such as `chore(mobile): ...` or `feat(backend): ...`.
- Omit the scope when the change spans multiple features or is repo-wide, such as `chore: ...` or `docs(AGENTS): ...`.

## Project state

- The app is under active development. It has no production users or shipped releases. For this reason, do not think about backwards compatibility or migration paths.
- Do not add compatibility shims, migrations for old storage keys or data, or fallback paths for previous app versions unless the user asks.
- Prefer a clean breaking refactor over preserving old formats, deprecated keys, or compatibility layers.

## Code conventions

- Use named exports unless a framework requirement, such as an Expo Router route, requires a default export.
- Write new components and helpers as `const` arrow functions, except when Expo Router requires a default exported route component.
- Do not add barrel files or modules that only re-export values. Import from the file that defines the value or type.
- Do not add a helper that only renames, re-exports, or lightly wraps another helper. When it has one real caller, use the underlying helper at that call site.
- Keep one-off values and configuration objects inline when that reads clearly. Extract a constant when code reuses it or when its name explains intent.
- Avoid `any`. Use precise TypeScript types.
- Use strict equality (`===` and `!==`). Check nullable values explicitly with `value === null || value === undefined`, or use the inverse.
- Name enum member keys with `UPPER_SNAKE_CASE`, such as `ELocale.EN` and `ELocalStorageKey.DEBUG_STORE`. Do not use PascalCase.
- Do not compress code at the cost of readability. Prefer code that explains itself.
- Keep comments that still describe the code after a refactor, and move them with the code they describe.
- Add comments only to explain intent, edge cases, platform quirks, or trade-offs that the code does not make clear. Avoid adding comments that explain the obvious.
