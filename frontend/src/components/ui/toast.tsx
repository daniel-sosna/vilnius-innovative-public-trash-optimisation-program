import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { CheckCircle2, CircleAlert, X } from 'lucide-react'
import { Toast as ToastPrimitive } from 'radix-ui'
import { cn } from '@/lib/utils'
import { ToastContext, type ToastMessage } from './toast-context'

type Notification = ToastMessage & { id: number }

export function ToastProvider({ children }: { children: ReactNode }) {
  const sequence = useRef(0)
  const viewport = useRef<HTMLOListElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)
  const [notifications, setNotifications] = useState<Notification[]>([])
  useEffect(() => {
    function rememberFocus(event: FocusEvent) {
      if (
        event.target instanceof HTMLElement &&
        !viewport.current?.contains(event.target)
      )
        previousFocus.current = event.target
    }
    document.addEventListener('focusin', rememberFocus)
    return () => document.removeEventListener('focusin', rememberFocus)
  }, [])
  const notify = useCallback((toast: ToastMessage) => {
    const id = ++sequence.current
    setNotifications((current) => [...current, { ...toast, id }])
  }, [])

  return (
    <ToastContext.Provider value={notify}>
      <ToastPrimitive.Provider
        duration={5000}
        label="Pranešimas"
        swipeDirection="right"
      >
        {children}
        {notifications.map(({ id, message, variant }) => (
          <ToastPrimitive.Root
            key={id}
            data-slot="toast"
            data-variant={variant}
            type={variant === 'error' ? 'foreground' : 'background'}
            onOpenChange={(open) => {
              if (!open) {
                // Move focus out before removal so Radix resumes its paused timer.
                if (viewport.current?.contains(document.activeElement)) {
                  if (previousFocus.current?.isConnected)
                    previousFocus.current.focus()
                  else viewport.current.blur()
                }
                setNotifications((current) =>
                  current.filter((toast) => toast.id !== id),
                )
              }
            }}
            className={cn(
              'pointer-events-auto flex items-start gap-3 rounded-lg border bg-card p-4 text-card-foreground shadow-lg outline-none focus-visible:ring-2 focus-visible:ring-ring motion-safe:data-[state=open]:animate-in motion-safe:data-[state=open]:fade-in-0 motion-safe:data-[state=open]:slide-in-from-top-2 motion-safe:data-[state=open]:slide-in-from-right-4',
              variant === 'error'
                ? 'border-destructive/50'
                : 'border-primary/50',
            )}
          >
            {variant === 'success' ? (
              <CheckCircle2
                aria-hidden="true"
                className="size-5 shrink-0 text-primary"
              />
            ) : (
              <CircleAlert
                aria-hidden="true"
                className="size-5 shrink-0 text-destructive"
              />
            )}
            <ToastPrimitive.Title className="min-w-0 flex-1 break-words text-sm font-medium">
              <span className="sr-only">
                {variant === 'error' ? 'Klaida: ' : 'Pavyko: '}
              </span>
              {message}
            </ToastPrimitive.Title>
            <ToastPrimitive.Close
              aria-label="Uždaryti pranešimą"
              className="shrink-0 rounded-sm text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
            >
              <X aria-hidden="true" className="size-4" />
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport
          ref={viewport}
          label="Pranešimai ({hotkey})"
          aria-live="off"
          className="pointer-events-none fixed top-0 right-0 z-[100] flex max-h-dvh w-96 max-w-full flex-col gap-2 overflow-y-auto p-4 outline-none"
        />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  )
}
