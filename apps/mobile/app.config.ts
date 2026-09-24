import 'tsx/cjs'

import type { ExpoConfig } from 'expo/config'

import { EAppVariant } from '@/common/constants/app-variant'
import { environment } from '@/environment'

type AppConfig = {
  name: string
  slug: string
  android: {
    package: string
  }
  ios: {
    bundleIdentifier: string
  }
}

const APP_CONFIGS: Record<EAppVariant, AppConfig> = {
  [EAppVariant.PRODUCTION]: {
    name: 'Travel Tok',
    slug: 'travel-tok',
    android: {
      package: 'com.anonymous.travel_tok',
    },
    ios: {
      bundleIdentifier: 'com.anonymous.travel-tok',
    },
  },
  [EAppVariant.DEVELOPMENT]: {
    name: 'Travel Tok (Dev)',
    slug: 'travel-tok-dev',
    android: {
      package: 'com.anonymous.travel_tok_dev',
    },
    ios: {
      bundleIdentifier: 'com.anonymous.travel-tok-dev',
    },
  },
}

const APP_CONFIG = APP_CONFIGS[environment.EXPO_PUBLIC_APP_VARIANT]

const config: ExpoConfig = {
  platforms: ['ios', 'android'],
  name: APP_CONFIG.name,
  slug: APP_CONFIG.slug,
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/images/icon.png',
  scheme: 'traveltok',
  ios: {
    icon: './assets/images/icon.png',
    bundleIdentifier: APP_CONFIG.ios.bundleIdentifier,
  },
  android: {
    adaptiveIcon: {
      backgroundColor: '#EFFAFF',
      foregroundImage: './assets/images/android-icon-foreground.png',
      backgroundImage: './assets/images/android-icon-background.png',
      monochromeImage: './assets/images/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: true,
    package: APP_CONFIG.android.package,
  },
  plugins: [
    'expo-router',
    [
      'expo-splash-screen',
      {
        backgroundColor: '#1BAAF2',
        image: './assets/images/splash-icon.png',
        imageWidth: 76,
      },
    ],
    [
      'expo-localization',
      {
        supportedLocales: {
          ios: ['en', 'pl'],
          android: ['en', 'pl'],
        },
      },
    ],
    'expo-asset',
    'expo-font',
    'expo-image',
    'expo-status-bar',
  ],
  experiments: {
    typedRoutes: true,
    reactCompiler: true,
  },
}

export default config
