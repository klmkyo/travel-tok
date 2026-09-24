---
name: add-i18n
description: >
  Add or update react-i18next translations. Use when adding user-facing copy,
  replacing hardcoded strings, or editing a file that does not already use i18n.
---

# Add i18n

Use this skill when adding user-facing text or converting hardcoded copy to translations.

## Files

- `en.ts` is canonical.
- Locale enum and namespace live in `src/features/i18n/constants/locales.ts`.
- Locale message files are registered in the `messages` map in `src/features/i18n/constants/messages.ts` (`ELocale` → messages module). `resources` is derived from that map.
- Message files live under `src/features/i18n/messages/` as TypeScript modules with `as const` (required for type-safe interpolation).
- Typed i18next setup lives in `src/features/i18n/types/i18next.d.ts`.
- Locale helpers live in `src/features/i18n/helpers.ts`. Import helpers directly from the file that defines them.
- Sync state lives in `scripts/i18n/sync-state.json`. `scripts/i18n_diff.py` discovers locale files from each asset directory and tracks both source and target hashes.

Before editing translations, inspect the `messages` map in `messages.ts` and the existing message files. Do not hardcode the locale list in your assumptions.

## Locale sync

The script records which committed English file each translation is based on, so sync work does not overwrite intentional human edits, and so that small changes to the English copy are not missed.

The script enforces a clean worktree before a locale sync. The English source must already be committed. Run the diff script first — do not hand-diff entire locale files.

Run these from `apps/mobile`:

```bash
uv run scripts/i18n_diff.py status
uv run scripts/i18n_diff.py diff --locale pl
uv run scripts/i18n_diff.py diff --asset messages --locale pl
```

Use `--force` only to inspect the needed source changes while unrelated work is in progress. It bypasses the clean-worktree check but never records a sync baseline. `mark-synced` always requires a committed English source.

Apply only the printed source diff to the matching target file (`pl.ts`, etc.). After syncing, record the baseline:

```bash
uv run scripts/i18n_diff.py mark-synced --asset messages --locale pl
```

After updating target files, run `mark-synced`. It records the committed English source and the updated target hashes; it intentionally permits dirty target files so both can be committed together. There is no force option. State is tracked per asset and locale in `scripts/i18n/sync-state.json` — no metadata blocks in locale files.

## Interpolation

Use i18next's default `{{variable}}` syntax in message strings.

```ts
// en.ts
export default {
  greeting: 'Hello, {{name}}!',
  resolved_date: 'Resolved date: {{date}}',
} as const
```

```tsx
t($ => $.greeting, { name: 'Ada' })
t($ => $.resolved_date, { date: resolvedDateLabel })
```

Keep placeholder names identical across every locale file. Non-English locales must mirror the same key structure as `en.ts`.

## Workflow

1. Check whether the target file already imports `useTranslation` from `react-i18next`.
2. If it does not, add:

```ts
import { useTranslation } from 'react-i18next'
```

3. Inside the component, add:

```ts
const { t } = useTranslation()
```

4. Replace user-facing literals with selector-style calls:

```tsx
{
  t($ => $.routes.camera)
}
```

5. Add matching keys to `en.ts`.
6. Only when syncing locales (see **Source of truth** and **Locale sync**): run `i18n_diff.py`, apply the diff to target locale files, then `mark-synced`. Use the English string as a temporary fallback when a translation is unclear — never omit keys.

## Key conventions

- Use nested objects that produce full selector paths like `$.routes.camera`.
- Use lowercase `snake_case` for new key segments. Existing established namespaces such as `routes` and `language` may be reused as-is.
- Reuse an existing namespace before creating a new top-level namespace.
- Scope feature copy to the feature or UI area, for example `gallery.empty_state.title` or `camera.permissions.request_button`.
- Prefer semantic key names such as `title`, `description`, `label`, `placeholder`, `button`, `error`, and `empty_state` over names copied from the English sentence.
- Shared generic copy should go under a shared namespace such as `common.action.*`, `common.error.*`, or `common.form.*` only when it is genuinely reused.
- When copy is driven by an enum or string union, prefer message keys whose final segment matches the enum value and use that value in the selector path when possible. Do not create a duplicate switch or mapping object unless the copy needs extra logic.
- Keep interpolation placeholder names consistent between the message string and the `t()` call.
- Keep the same placeholder names across every locale.

## Rules

- Use i18next `{{variable}}` interpolation in message strings.
- Do not use `defaultMessage`.
- Do not leave new user-facing strings hardcoded in JSX props, button labels, placeholders, titles, alerts, or visible text nodes.
- Preserve the existing selector syntax; do not switch to string-key calls.
