import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'

const KEY = 'nexora-theme'

function getStored(): Theme {
  const v = localStorage.getItem(KEY)
  return v === 'light' ? 'light' : 'dark' // defaults to dark
}

function applyTheme(theme: Theme) {
  const isDark = theme === 'dark'
  document.documentElement.classList.toggle('dark', isDark)
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => getStored())

  function setTheme(next: Theme) {
    localStorage.setItem(KEY, next)
    setThemeState(next)
    applyTheme(next)
  }

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  return { theme, setTheme }
}