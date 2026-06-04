export const THEME_STORAGE_KEY = 'clipiq.theme'

export const THEMES = {
  dark: 'dark',
  light: 'light',
}

export const DEFAULT_THEME = THEMES.dark

export function isTheme(value) {
  return value === THEMES.dark || value === THEMES.light
}
