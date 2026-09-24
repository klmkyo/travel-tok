import 'tsx/cjs'

import { getDefaultConfig } from 'expo/metro-config'
import { withUniwindConfig } from 'uniwind/metro'

type MetroConfig = ReturnType<typeof getDefaultConfig>
type MetroConfigHandler = (config: MetroConfig) => MetroConfig

const pipeMetroConfig = (handlers: MetroConfigHandler[]): MetroConfig =>
  handlers.reduce((config, handler) => handler(config), undefined as unknown as MetroConfig)

const withDefaultConfig: MetroConfigHandler = () => getDefaultConfig(__dirname)

const withUniwind: MetroConfigHandler = config =>
  // Uniwind depends on a different Metro type tree than `expo/metro-config`.
  withUniwindConfig(config, {
    cssEntryFile: './src/global.css',
    dtsFile: './src/uniwind-types.d.ts',
  }) as unknown as MetroConfig

module.exports = pipeMetroConfig([withDefaultConfig, withUniwind])
