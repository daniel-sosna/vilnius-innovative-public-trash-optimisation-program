import { createContext, useContext } from 'react'

export type ToastMessage = { message: string; variant: 'success' | 'error' }
export const ToastContext = createContext<
  ((toast: ToastMessage) => void) | null
>(null)

export function useToast() {
  const notify = useContext(ToastContext)
  if (!notify) throw new Error('useToast requires ToastProvider')
  return notify
}
