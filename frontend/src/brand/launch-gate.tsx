import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import './launch-gate.css'

type Props = { children: ReactNode; maxWaitMs?: number; enabled?: boolean }
/** Mount once above App. App mounts immediately; the overlay covers startup. */
export function LaunchGate({ children, maxWaitMs = 6000, enabled = true }: Props) {
  const [visible, setVisible] = useState(true)
  const frame = useRef<HTMLIFrameElement>(null)
  const overlay = useRef<HTMLDivElement>(null)
  const restoreFocus = useRef(false)
  const instance = useId()
  const active = enabled && visible
  const finish = useCallback(() => {
    restoreFocus.current = !!overlay.current?.contains(document.activeElement)
    setVisible(false)
  }, [])
  useEffect(() => {
    if (active || !restoreFocus.current) return
    restoreFocus.current = false
    const target = document.querySelector<HTMLElement>('main, h1')
    if (!target || (document.activeElement !== document.body && document.activeElement !== null)) return
    const hadTabIndex = target.hasAttribute('tabindex')
    if (!hadTabIndex) target.setAttribute('tabindex', '-1')
    target.focus({ preventScroll: true })
    if (!hadTabIndex) target.removeAttribute('tabindex')
  }, [active])
  useEffect(() => {
    if (!active) return
    // Radix portals are body siblings of #root, outside the child inert wrapper.
    const root = overlay.current?.closest('#root')
    const siblings = new Map<HTMLElement, { inert: boolean; hidden: string | null }>()
    function isolatePortals() {
      for (const node of document.body.children) {
        if (!(node instanceof HTMLElement) || node === root || siblings.has(node)) continue
        siblings.set(node, { inert: node.inert, hidden: node.getAttribute('aria-hidden') })
        node.inert = true
        node.setAttribute('aria-hidden', 'true')
      }
    }
    isolatePortals()
    const observer = new MutationObserver(isolatePortals)
    observer.observe(document.body, { childList: true })
    function keepFocus(event: FocusEvent) {
      if (!overlay.current?.contains(event.target as Node)) overlay.current?.focus()
    }
    function trapTab(event: KeyboardEvent) {
      if (event.key === 'Tab') { event.preventDefault(); event.stopPropagation(); overlay.current?.focus() }
      else if (!overlay.current?.contains(event.target as Node)) { event.preventDefault(); event.stopPropagation() }
    }
    document.addEventListener('focusin', keepFocus, true)
    document.addEventListener('keydown', trapTab, true)
    overlay.current?.focus({ preventScroll: true })
    return () => {
      observer.disconnect()
      document.removeEventListener('focusin', keepFocus, true)
      document.removeEventListener('keydown', trapTab, true)
      for (const [node, previous] of siblings) {
        node.inert = previous.inert
        if (previous.hidden === null) node.removeAttribute('aria-hidden')
        else node.setAttribute('aria-hidden', previous.hidden)
      }
    }
  }, [active])
  const sendStart = useCallback(() => {
    frame.current?.contentWindow?.postMessage({ type: 'viptop-launch:start', instance }, window.location.protocol === 'file:' ? '*' : window.location.origin)
  }, [instance])
  useEffect(() => {
    if (!active) return
    function onMessage(event: MessageEvent) {
      const expectedOrigin = window.location.protocol === 'file:' ? 'null' : window.location.origin
      if (event.source !== frame.current?.contentWindow || event.origin !== expectedOrigin || event.data?.instance !== instance) return
      if (event.data?.type === 'viptop-launch:ready') sendStart()
      if (event.data?.type === 'viptop-launch:done') finish()
    }
    window.addEventListener('message', onMessage)
    const timeout = window.setTimeout(finish, Math.max(1000, maxWaitMs))
    return () => { window.removeEventListener('message', onMessage); window.clearTimeout(timeout) }
  }, [active, finish, instance, maxWaitMs, sendStart])
  return <>
    <div className="vip-launch__app" inert={active || undefined} aria-hidden={active || undefined}>{children}</div>
    {active && <div ref={overlay} tabIndex={-1} className="vip-launch" role="status" aria-live="polite" aria-label="VipTop kraunama">
      <iframe ref={frame} src={`${import.meta.env.BASE_URL}brand/launch/launch.html?autoplay=0&instance=${encodeURIComponent(instance)}`} title="VipTop start animation" className="vip-launch__frame" tabIndex={-1} aria-hidden="true" onLoad={sendStart} onError={finish} />
      <span className="vip-launch__sr-only">VipTop kraunama</span>
    </div>}
  </>
}
