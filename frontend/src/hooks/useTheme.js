import { useEffect, useState } from 'react'
import { DEFAULT_THEME, THEMES, THEME_STORAGE_KEY, isTheme } from '../constants/theme.js'

function readInitialTheme() {
  const currentTheme = document.documentElement.dataset.theme
  if (isTheme(currentTheme)) return currentTheme

  try {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY)
    if (isTheme(storedTheme)) return storedTheme
  } catch {
    return DEFAULT_THEME
  }

  return DEFAULT_THEME
}

export function applyTheme(theme) {
  const nextTheme = isTheme(theme) ? theme : DEFAULT_THEME
  document.documentElement.dataset.theme = nextTheme
  document.documentElement.style.colorScheme = nextTheme

  try {
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme)
  } catch {
    // Theme remains applied even if storage is unavailable.
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(readInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  function toggleTheme() {
    setTheme((currentTheme) => (currentTheme === THEMES.dark ? THEMES.light : THEMES.dark))
  }

  return {
    isDark: theme === THEMES.dark,
    setTheme,
    theme,
    toggleTheme,
  }
}
