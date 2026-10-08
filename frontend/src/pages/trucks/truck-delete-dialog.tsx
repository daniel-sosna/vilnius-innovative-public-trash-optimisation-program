import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { operationError, truckRequest, type Truck } from './api'

export function TruckDeleteDialog({
  truck,
  onClose,
  onDeleted,
  restoreFocus,
}: {
  truck: Truck
  onClose: () => void
  onDeleted: () => void
  restoreFocus: () => void
}) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const submitting = useRef(false)
  async function remove() {
    if (submitting.current) return
    submitting.current = true
    setPending(true)
    setError('')
    try {
      await truckRequest<void>(`/${truck.id}`, { method: 'DELETE' })
      onDeleted()
    } catch (failure) {
      setError(operationError(failure))
    } finally {
      submitting.current = false
      setPending(false)
    }
  }
  return (
    <AlertDialog
      open
      onOpenChange={(open) => {
        if (!open && !submitting.current) onClose()
      }}
    >
      <AlertDialogContent
        className="max-h-[calc(100dvh-2rem)] overflow-y-auto"
        onOpenAutoFocus={(event) => {
          event.preventDefault()
          document.getElementById('cancel-truck-delete')?.focus()
        }}
        onCloseAutoFocus={(event) => {
          event.preventDefault()
          restoreFocus()
        }}
        onEscapeKeyDown={(event) => {
          if (submitting.current) event.preventDefault()
        }}
      >
        <AlertDialogHeader>
          <AlertDialogTitle>
            Ar tikrai norite ištrinti šią šiukšliavežę?
          </AlertDialogTitle>
          <AlertDialogDescription className="break-words">
            {truck.name}
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <AlertDialogFooter>
          <Button
            id="cancel-truck-delete"
            variant="outline"
            disabled={pending}
            onClick={onClose}
          >
            Atšaukti
          </Button>
          <Button variant="destructive" disabled={pending} onClick={remove}>
            {pending ? 'Trinama…' : 'Ištrinti'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
