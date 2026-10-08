import { useRef, useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useToast } from '@/components/ui/toast-context'
import {
  ApiError,
  isSiteCapacity,
  operationError,
  truckRequest,
  type Truck,
} from './api'

type Props = {
  truck: Truck | null
  onClose: () => void
  onSaved: () => void
  onRefresh: () => void
  restoreFocus: () => void
}

export function TruckEditor({
  truck,
  onClose,
  onSaved,
  onRefresh,
  restoreFocus,
}: Props) {
  const [name, setName] = useState(truck?.name ?? '')
  const [capacity, setCapacity] = useState(
    truck ? String(truck.max_bins_per_trip) : '',
  )
  const [available, setAvailable] = useState(truck?.available ?? true)
  const [fields, setFields] = useState<Record<string, string>>({})
  const notify = useToast()
  const [missing, setMissing] = useState(false)
  const [pending, setPending] = useState(false)
  const submitting = useRef(false)

  async function save(event: FormEvent) {
    event.preventDefault()
    if (submitting.current) return
    const validation: Record<string, string> = {}
    if (!name.trim()) validation.name = 'Įveskite pavadinimą.'
    if (!isSiteCapacity(capacity))
      validation.max_bins_per_trip = 'Įveskite sveikąjį skaičių nuo 1 iki 99.'
    setFields(validation)
    if (Object.keys(validation).length) return
    const initiatingControl = document.activeElement
    submitting.current = true
    setPending(true)
    try {
      await truckRequest<Truck>(truck ? `/${truck.id}` : '', {
        method: truck ? 'PATCH' : 'POST',
        body: JSON.stringify({
          name: name.trim(),
          max_bins_per_trip: Number(capacity),
          available,
        }),
      })
      onSaved()
    } catch (failure) {
      notify({ message: operationError(failure), variant: 'error' })
      if (failure instanceof ApiError) {
        setFields(failure.fields)
        setMissing(failure.status === 404)
      }
    } finally {
      submitting.current = false
      setPending(false)
      window.requestAnimationFrame(() => {
        if (
          initiatingControl instanceof HTMLElement &&
          initiatingControl.isConnected &&
          (document.activeElement === document.body ||
            document.activeElement?.getAttribute('role') === 'dialog')
        )
          initiatingControl.focus()
      })
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !submitting.current) onClose()
      }}
    >
      <DialogContent
        className="max-h-[calc(100dvh-2rem)] overflow-y-auto"
        showCloseButton={false}
        onCloseAutoFocus={(event) => {
          event.preventDefault()
          restoreFocus()
        }}
        onEscapeKeyDown={(event) => {
          if (submitting.current) event.preventDefault()
        }}
        onInteractOutside={(event) => {
          if (submitting.current) event.preventDefault()
        }}
      >
        <DialogHeader>
          <DialogTitle>
            {truck ? 'Redaguoti šiukšliavežę' : 'Pridėti šiukšliavežę'}
          </DialogTitle>
          <DialogDescription>
            Įveskite šiukšliavežės duomenis.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={save} noValidate className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="truck-name">Pavadinimas</Label>
            <Input
              id="truck-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={pending}
              aria-invalid={!!fields.name}
              aria-describedby={fields.name ? 'name-error' : undefined}
            />
            {fields.name && (
              <p
                id="name-error"
                className="text-sm text-destructive"
                role="alert"
              >
                {fields.name}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="truck-capacity" className="leading-relaxed">
              Maksimalus aikštelių skaičius per reisą
            </Label>
            <Input
              id="truck-capacity"
              type="number"
              min={1}
              max={99}
              step={1}
              inputMode="numeric"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              disabled={pending}
              aria-invalid={!!fields.max_bins_per_trip}
              aria-describedby={`capacity-help${fields.max_bins_per_trip ? ' capacity-error' : ''}`}
            />
            <p id="capacity-help" className="text-sm text-muted-foreground">
              Viena aikštelė gali turėti kelis konteinerius.
            </p>
            {fields.max_bins_per_trip && (
              <p
                id="capacity-error"
                className="text-sm text-destructive"
                role="alert"
              >
                {fields.max_bins_per_trip}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Switch
              id="truck-available"
              checked={available}
              onCheckedChange={setAvailable}
              disabled={pending}
            />
            <Label htmlFor="truck-available">Prieinamas</Label>
          </div>
          <DialogFooter>
            {missing && (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  onClose()
                  onRefresh()
                }}
              >
                Atnaujinti sąrašą
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              disabled={pending}
              onClick={onClose}
            >
              Atšaukti
            </Button>
            <Button type="submit" disabled={pending || missing}>
              {pending ? 'Saugoma…' : 'Išsaugoti'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
