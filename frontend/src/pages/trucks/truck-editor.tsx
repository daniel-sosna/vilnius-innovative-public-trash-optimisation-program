import { useEffect, useRef, useState, type FormEvent } from 'react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useToast } from '@/components/ui/toast-context'
import {
  ApiError,
  getLandfills,
  isVolumeInput,
  parseVolume,
  operationError,
  truckRequest,
  wasteCarriers,
  type Landfill,
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
  const [volume, setVolume] = useState(
    truck ? String(truck.max_volume_m3).replace('.', ',') : '',
  )
  const unlistedCarrier = truck && !wasteCarriers.includes(truck.waste_carrier)
  const [carrier, setCarrier] = useState(
    truck && !unlistedCarrier ? truck.waste_carrier : '',
  )
  const [available, setAvailable] = useState(truck?.available ?? true)
  const [landfill, setLandfill] = useState(
    truck?.landfill_id ? String(truck.landfill_id) : '',
  )
  const [catalogRetry, setCatalogRetry] = useState(0)
  const [catalog, setCatalog] = useState<{
    key: number
    data: Landfill[] | null
    error: boolean
  } | null>(null)
  const currentCatalog = catalog?.key === catalogRetry ? catalog : null
  const landfills = currentCatalog?.data
  const [fields, setFields] = useState<Record<string, string>>({})
  const notify = useToast()
  const [missing, setMissing] = useState(false)
  const [pending, setPending] = useState(false)
  const submitting = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    getLandfills(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted)
          setCatalog({ key: catalogRetry, data, error: false })
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setCatalog({ key: catalogRetry, data: null, error: true })
      })
    return () => controller.abort()
  }, [catalogRetry])

  async function save(event: FormEvent) {
    event.preventDefault()
    if (submitting.current) return
    const validation: Record<string, string> = {}
    if (!name.trim()) validation.name = 'Įveskite pavadinimą.'
    const parsedVolume = parseVolume(volume)
    if (parsedVolume === null)
      validation.max_volume_m3 = 'Įveskite skaičių, didesnį už nulį.'
    if (!wasteCarriers.includes(carrier))
      validation.waste_carrier = 'Pasirinkite atliekų vežėją.'
    if (!landfills?.some((choice) => String(choice.id) === landfill))
      validation.landfill_id = 'Pasirinkite sąvartyną.'
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
          max_volume_m3: parsedVolume,
          waste_carrier: carrier,
          landfill_id: Number(landfill),
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
            <Label htmlFor="truck-volume" className="leading-relaxed">
              Maksimali talpa
            </Label>
            <div className="relative">
              <Input
                id="truck-volume"
                inputMode="decimal"
                className="pr-12"
                value={volume}
                onChange={(e) => {
                  if (isVolumeInput(e.target.value)) setVolume(e.target.value)
                }}
                disabled={pending}
                aria-invalid={!!fields.max_volume_m3}
                aria-describedby={`volume-unit${fields.max_volume_m3 ? ' volume-error' : ''}`}
              />
              <span
                id="volume-unit"
                className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-sm text-muted-foreground"
              >
                m³
              </span>
            </div>
            {fields.max_volume_m3 && (
              <p
                id="volume-error"
                className="text-sm text-destructive"
                role="alert"
              >
                {fields.max_volume_m3}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="truck-carrier">Atliekų vežėjas</Label>
            <Select value={carrier} onValueChange={setCarrier} disabled={pending}>
              <SelectTrigger
                id="truck-carrier"
                className="w-full"
                aria-invalid={!!fields.waste_carrier}
                aria-describedby={[
                  unlistedCarrier ? 'stored-carrier' : '',
                  fields.waste_carrier ? 'carrier-error' : '',
                ].filter(Boolean).join(' ') || undefined}
              >
                <SelectValue placeholder="Pasirinkite atliekų vežėją" />
              </SelectTrigger>
              <SelectContent>
                {wasteCarriers.map((value) => (
                  <SelectItem key={value} value={value}>{value}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {unlistedCarrier && (
              <p id="stored-carrier" className="break-words text-sm text-muted-foreground">
                Dabartinis atliekų vežėjas: {truck.waste_carrier}
              </p>
            )}
            {fields.waste_carrier && (
              <p id="carrier-error" className="text-sm text-destructive" role="alert">
                {fields.waste_carrier}
              </p>
            )}
          </div>
          <div className="space-y-2" aria-busy={!currentCatalog}>
            <Label htmlFor="truck-landfill">Sąvartynas</Label>
            <Select
              value={landfill}
              onValueChange={setLandfill}
              disabled={pending || !landfills?.length}
            >
              <SelectTrigger
                id="truck-landfill"
                className="w-full min-w-0 whitespace-normal data-[size=default]:h-auto data-[size=default]:min-h-9 *:data-[slot=select-value]:line-clamp-none *:data-[slot=select-value]:min-w-0"
                aria-invalid={!!fields.landfill_id}
                aria-describedby={fields.landfill_id ? 'landfill-error' : 'landfill-status'}
              >
                <SelectValue placeholder="Pasirinkite sąvartyną" className="break-words text-left" />
              </SelectTrigger>
              <SelectContent position="popper" className="w-[var(--radix-select-trigger-width)]">
                {landfills?.map((choice) => (
                  <SelectItem
                    key={choice.id}
                    value={String(choice.id)}
                    className="whitespace-normal *:[span]:last:min-w-0"
                  >
                    <span className="min-w-0 break-words">{choice.name}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div id="landfill-status">
              {!currentCatalog ? (
                <p role="status" className="text-sm text-muted-foreground">Kraunami sąvartynai…</p>
              ) : currentCatalog.error ? (
                <div role="alert" className="space-y-2">
                  <p className="text-sm text-destructive">Nepavyko įkelti sąvartynų.</p>
                  <Button type="button" variant="outline" onClick={() => setCatalogRetry((value) => value + 1)}>
                    Bandyti dar kartą
                  </Button>
                </div>
              ) : !landfills?.length ? (
                <p role="status" className="text-sm text-muted-foreground">Šiuo metu nėra sąvartynų.</p>
              ) : null}
            </div>
            {fields.landfill_id && (
              <p id="landfill-error" role="alert" className="text-sm text-destructive">
                {fields.landfill_id}
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
            <Button type="submit" disabled={pending || missing || !landfills?.length}>
              {pending ? 'Saugoma…' : 'Išsaugoti'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
