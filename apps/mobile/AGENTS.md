# AGENTS.md

Instructions for AI agents working in `apps/mobile`. The app uses Expo 58, React Native 0.88, Expo Router, and Uniwind.

Repo-wide rules live in the root `AGENTS.md`: repository layout, the checks to run, lint and format configuration, the TypeScript arrangement, git commits, and project state.

## Expo and library docs

- Use Context7 to check Expo 58 documentation before writing Expo code.
- This project uses Zod 4. Check its current documentation before writing schemas.
- This project uses Uniwind with Tailwind CSS 4. Check the Uniwind docs for API details.
- `react-native-gesture-handler` is on v3 (`~3.2.1`). Use the v3 hook API. Only use the RNGH 2 `Gesture.*()` builder API when migrating legacy code.

## Uniwind

This project uses free Uniwind only. Never suggest, install, document, or rely on Uniwind Pro.

## Running the app

Do not run `pnpm start`, `pnpm ios`, `pnpm android`, or native build commands unless the user asks.

## Project structure

- `src/app/` contains Expo Router routes and layouts.
- `src/features/<feature>/` contains UI, hooks, providers, constants, helpers, messages, and types owned by one feature.
- Put constants used by more than one file in a feature in `src/features/<feature>/constants.ts`. For a larger set, use `src/features/<feature>/constants/` and group related constants into separate files. If a constant is only used in one file, you should probably keep it in that file.
- `src/common/` contains shared helpers, hooks, providers, and app-level code.
- `src/global.css` contains the Tailwind CSS 4 and Uniwind theme configuration.
- Use the `@/` alias to import from `src`.
- Stores follow a fixed four-file layout and an exhaustive persistence map. The `zustand-store` skill covers both.

## Code conventions

- Put one component in each file.
- Order component files as imports, constants, component, component props type, then helper functions.
- Organize component bodies as a top-to-bottom account of their behavior. Use small paragraphs grouped by concern, not one block sorted by declaration kind.
- Keep an input or source hook beside its derived values, callbacks, and effects. Add a blank line between concerns, but keep declarations from one concern together.
- Start with component-wide dependencies such as context, stores, queries, and form setup. Follow with concern-specific state and behavior.
- Put early returns after every unconditional hook and before calculations that need guarded data. Put the remaining render state and event handlers before the JSX return.
- Treat this order as a default. Keeping related code together matters more than following the template.
- Put an effect beside the state, callback, or external synchronization it coordinates. Put a derived value beside its source or first meaningful consumer.
- Keep related handlers together only when that does not separate them from the behavior they belong to. Do not create generic sections for hooks, derived values, effects, or handlers.
- If a component mixes several unrelated concerns, extract a hook or component instead of adding more sections.
- Annotate `useMemo` return types on the variable, not the callback. Write `const state: MyType = useMemo(() => { ... }, deps)`, not `const state = useMemo((): MyType => { ... }, deps)`.
- Use `TranslateFn` from `@/features/i18n/types/translate` when typing the `t` function from `useTranslation`. Do not write `ReturnType<typeof useTranslation>['t']`.
- Use `keysOf`, `valuesOf`, `entriesOf`, and `fromEntriesOf` from `@/common/helpers/object` instead of the matching raw `Object` methods. These helpers preserve type inference.
- In the default branch of an exhaustive `switch` over a discriminated union or enum, use `unreachable(value)` from `@/common/helpers/unreachable`. Use `assertUnreachable(value)` when the branch should throw at runtime.
- When a component has no meaningful `else` branch, use `&&` instead of a ternary. Write `{isOpen && <Modal />}`, not `{isOpen ? <Modal /> : null}`.
- Always prefer `value && <Component />` over `value !== null && <Component />`. Prefer truthy checks, unless they are likely to cause issues, for example when empty values like `''` or `0` are valid. Prefer `if (stringValue)` over things like `if (stringValue !== undefined)` most of the times `''` can be ignored anyways.

### Reanimated

- Add an `Sv` suffix to Reanimated `SharedValue` variables and props, such as `rawZoomSv` and `pressScaleSv`. This distinguishes them from plain values.
- Read and write shared values with `xyzSv.get()` and `xyzSv.set()`. Direct `.value` access is discouraged with the React Compiler. See Reanimated's [useSharedValue documentation](https://docs.swmansion.com/react-native-reanimated/docs/core/useSharedValue/).

### Styling

- Use `cn()` from `cn` to merge conditional class names. Put shared classes in the base string and only the changing classes in the condition.
- Do not duplicate layout or positioning classes across branches. Write `cn('absolute inset-0', isActive ? 'bg-black' : 'bg-white')`, not `isActive ? 'absolute inset-0 bg-black' : 'absolute inset-0 bg-white'`.
- Prefer `className="absolute inset-0"` over `style={StyleSheet.absoluteFill}` on Uniwind-capable components.
- Use Uniwind theme variants such as `dark:` with the numbered `primary`, `container`, and `base` color scales instead of choosing class names from the theme in JavaScript.
- Write `bg-white dark:bg-black`, or use a theme token, instead of `theme === 'dark' ? 'bg-black' : 'bg-white'`.
- Only use `useUniwind()` when logic needs the resolved theme value, such as when supplying Expo Router or React Navigation themes.
- Prefer Uniwind `className` to the `style` prop.
- Native modules such as `expo-blur`, `expo-linear-gradient`, and `expo-symbols` do not resolve `className`. Add a small `withUniwind` wrapper under `src/common/components/` and use the wrapper throughout the app.
- Use inline `style={{ ... }}` only when a class cannot express the value.
- When JavaScript needs the resolved light or dark theme, use `useUniwind()` from `uniwind`. Do not import `useColorScheme` from `react-native` for app theming.

### Wrapper components

- When wrapping a Uniwind-capable host such as `View`, `Text`, or `Pressable`, accept `className` and merge it with the defaults using `cn('base-classes', className)`.
- Forward the remaining props to the host with `...props`. Type them as an intersection with `ComponentProps<typeof Host>`. Use `Omit` for props that the wrapper owns, such as `children` or `pointerEvents`.
- Destructure `className` and every owned prop before spreading `props` so callers cannot bypass the defaults.

### File placement

- Before adding a file, inspect the nearby feature or domain for similar code.
- Keep code in `src/features/<feature>/` when only one feature uses it, even if it could become reusable later.
- Use `src/common/` for code shared by unrelated features and for app-level code with no feature owner.
- Move code from a feature to `common` when it becomes shared. Do not start it in `common` based on possible future reuse.
- Follow the feature's existing folders, such as `components`, `hooks`, `helpers`, `constants`, and `providers`, unless the code calls for a different structure.
- Do not create a file for every small helper. Keep closely related helpers together. Split a file when the code has a separate responsibility, has grown large, or has several callers.

### Required component wrappers

Oxlint's `no-restricted-imports` rule blocks the raw imports below. Use the project wrapper or replacement.

| Instead of                                                             | Use                                                                        | Reason                                                                                                                                                  |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Text` from `react-native`                                             | `ThemedText` from `@/common/components/themed-text/ThemedText`             | It applies numbered base text colors for light and dark themes without repeated classes.                                                                |
| `SafeAreaView` from `react-native` or `react-native-safe-area-context` | `SafeAreaView` from `@/common/components/safe-area-view/SafeAreaView`      | React Native's built-in component is deprecated. The package component needs `withUniwind` to support `className`; the project wrapper already adds it. |
| `BlurView` from `expo-blur`                                            | `BlurView` from `@/common/components/blur-view/BlurView`                   | The native Expo component needs `withUniwind` to resolve `className`. Rounded corners also need `overflow-hidden`.                                      |
| `Image` from `expo-image`                                              | `Image` from `@/common/components/image/Image`                             | The native Expo component needs `withUniwind` to resolve `className`.                                                                                   |
| `LinearGradient` from `expo-linear-gradient`                           | `LinearGradient` from `@/common/components/linear-gradient/LinearGradient` | The native Expo component needs `withUniwind` to resolve `className`. Gradient `colors` still must be passed explicitly.                                |
| `Button` from `react-native`                                           | `Button` from `@/common/components/ui/button/Button`                       | It applies the variant palette, press feedback, and accessibility state.                                                                                |
| `Switch` from `react-native`                                           | `Switch` from `@/common/components/ui/switch/Switch`                       | It applies the app palette through Uniwind accent color props for the thumb and track.                                                                  |
| `@expo/ui` in any form                                                 | the wrappers in `@/common/components/ui/`                                  | Expo UI controls only pick up the app palette inside `ExpoUiHost`, and Android derives its own Material 3 palette from the seed.                        |
| `useColorScheme` from `react-native`                                   | `useUniwind()` from `uniwind`                                              | It returns the active theme after `Uniwind.setTheme`, including the system preference.                                                                  |

Other exports from `react-native-safe-area-context`, including `SafeAreaProvider`, `SafeAreaListener`, and `useSafeAreaInsets`, may be imported directly.
