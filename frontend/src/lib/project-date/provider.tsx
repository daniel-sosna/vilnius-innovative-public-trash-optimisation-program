import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { dateStorageKey, defaultDate, ProjectDateContext, validDate } from './context'

export function ProjectDateProvider({ children }: { children: ReactNode }) {
  const [projectDate, setProjectDate] = useState(() => {
    try { const stored = localStorage.getItem(dateStorageKey); return validDate(stored) ? stored : defaultDate } catch { return defaultDate }
  })
  const owner = useRef<symbol | null>(null)
  const [locked, setLocked] = useState(false)
  const setDate = useCallback((value: string) => {
    if (owner.current || !validDate(value)) return false
    setProjectDate(value)
    try { localStorage.setItem(dateStorageKey, value) } catch { /* Session selection remains usable. */ }
    return true
  }, [])
  const acquire = useCallback((token: symbol) => {
    if (owner.current && owner.current !== token) return false
    owner.current = token; setLocked(true); return true
  }, [])
  const release = useCallback((token: symbol) => {
    if (owner.current !== token) return
    owner.current = null; setLocked(false)
  }, [])
  const value = useMemo(() => ({ projectDate, locked, setDate, acquire, release }), [projectDate, locked, setDate, acquire, release])
  return <ProjectDateContext.Provider value={value}>{children}</ProjectDateContext.Provider>
}
