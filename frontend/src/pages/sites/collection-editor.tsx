import { useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LocationMap } from '@/components/maps/location-map'
import { addBin, createSite, CollectionMutationError, fieldMessages, mutationError } from './api'
import { BinForm } from './bin-form'
import { binPayload, emptyBin, validateBin } from './bin-form-values'

export function CollectionEditor({ siteId, onClose, onSaved, restoreFocus }: {
  siteId?: string; onClose: () => void; onSaved: () => void; restoreFocus: () => void
}) {
  const [address, setAddress] = useState({ street: '', sub_district: '', house_number: '', postal_code: '' })
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null)
  const [bins, setBins] = useState(() => [emptyBin()])
  const [fields, setFields] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [missing, setMissing] = useState(false)
  const [pending, setPending] = useState(false)
  const submitting = useRef(false)
  const cancel = useRef<HTMLButtonElement>(null)
  async function save(event: FormEvent) {
    event.preventDefault()
    if (submitting.current) return
    const validation: Record<string, string> = {}
    if (!siteId) {
      for (const name of ['street', 'sub_district', 'house_number'] as const) if (!address[name].trim()) validation[name] = fieldMessages[name]
      if (!location) validation.location = fieldMessages.latitude
    }
    for (const bin of bins) for (const [name, message] of Object.entries(validateBin(bin))) validation[`${bin.id}.${name}`] = message
    setFields(validation)
    setError('')
    if (Object.keys(validation).length) {
      window.requestAnimationFrame(() => document.querySelector<HTMLElement>('[role="dialog"] [aria-invalid="true"]')?.focus())
      return
    }
    const initiating = document.activeElement
    submitting.current = true
    setPending(true)
    try {
      if (siteId) await addBin(siteId, binPayload(bins[0]))
      else if (location) await createSite({ ...address, postal_code: address.postal_code.trim() || null, ...location, bins: bins.map(binPayload) })
      onSaved()
    } catch (failure) {
      setError(mutationError(failure))
      if (failure instanceof CollectionMutationError) {
        const mapped: Record<string, string> = {}
        for (const [path, message] of Object.entries(failure.fields)) {
          const parts = path.split('.')
          const name = parts.at(-1)!
          if (parts[0] === 'bins' && parts.length === 3) {
            const bin = bins[Number(parts[1])]
            if (bin) mapped[`${bin.id}.${name}`] = message
          } else if (siteId && name in bins[0]) mapped[`${bins[0].id}.${name}`] = message
          else mapped[name === 'latitude' || name === 'longitude' ? 'location' : name] = message
        }
        setFields(mapped)
        setMissing(failure.status === 404)
      }
    } finally {
      submitting.current = false
      setPending(false)
      window.requestAnimationFrame(() => {
        if (initiating instanceof HTMLElement && initiating.isConnected && (document.activeElement === document.body || document.activeElement?.getAttribute('role') === 'dialog')) {
          if (initiating.hasAttribute('disabled')) cancel.current?.focus()
          else initiating.focus()
        }
      })
    }
  }
  return <Dialog open onOpenChange={(open) => { if (!open && !submitting.current) onClose() }}>
    <DialogContent className={`max-h-[calc(100dvh-2rem)] overflow-y-auto ${siteId ? '' : 'sm:max-w-3xl'}`} showCloseButton={false}
      onCloseAutoFocus={(event) => { event.preventDefault(); restoreFocus() }}
      onEscapeKeyDown={(event) => { if (submitting.current) event.preventDefault() }}
      onInteractOutside={(event) => { if (submitting.current) event.preventDefault() }}>
      <DialogHeader><DialogTitle>{siteId ? 'Pridėti konteinerį' : 'Pridėti surinkimo vietą'}</DialogTitle>
        <DialogDescription>{siteId ? 'Įveskite konteinerio duomenis.' : 'Įveskite adresą, pasirinkite vietą žemėlapyje ir pridėkite konteinerius.'}</DialogDescription></DialogHeader>
      <form noValidate onSubmit={save} className="min-w-0 space-y-5">
        {!siteId && <>
          <div className="grid gap-4 sm:grid-cols-2">{([['street', 'Gatvė'], ['sub_district', 'Seniūnija'], ['house_number', 'Namo numeris'], ['postal_code', 'Pašto kodas (neprivalomas)']] as const).map(([name, label]) =>
            <div key={name} className="min-w-0 space-y-2"><Label htmlFor={`create-${name}`}>{label}</Label>
              <Input id={`create-${name}`} required={name !== 'postal_code'} value={address[name]} disabled={pending} onChange={(event) => setAddress({ ...address, [name]: event.target.value })} aria-invalid={!!fields[name]} aria-describedby={fields[name] ? `${name}-error` : undefined} />
              {fields[name] && <p id={`${name}-error`} role="alert" className="text-sm text-destructive">{fields[name]}</p>}
            </div>)}
          </div>
          <h2 className="text-sm font-medium">Spauskite ant žemėlapio, kad pasirinktumėte lokaciją</h2>
          {fields.location && <p role="alert" className="text-sm text-destructive">{fields.location}</p>}
          <LocationMap latitude={location?.latitude ?? null} longitude={location?.longitude ?? null} interactive canvasClassName="h-64 sm:h-80" onSelect={(value) => { if (!submitting.current) { setLocation(value); setFields((old) => ({ ...old, location: '' })) } }} />
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="create-latitude">Platuma (lat)</Label>
              <Input id="create-latitude" disabled value={location?.latitude ?? ''} className="pointer-events-none select-none bg-muted" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-longitude">Ilguma (lon)</Label>
              <Input id="create-longitude" disabled value={location?.longitude ?? ''} className="pointer-events-none select-none bg-muted" />
            </div>
          </div>
        </>}
        {bins.map((bin, index) => <fieldset key={bin.id} className={siteId ? 'min-w-0' : 'min-w-0 space-y-4 rounded-lg border p-3 sm:p-4'}>
          {!siteId && <legend className="px-1 text-sm font-medium">Konteineris {index + 1}</legend>}
          <BinForm value={bin} pending={pending} onChange={(value) => setBins((old) => old.map((item) => item.id === value.id ? value : item))}
            errors={Object.fromEntries(Object.entries(fields).filter(([key]) => key.startsWith(`${bin.id}.`)).map(([key, value]) => [key.slice(bin.id.length + 1), value]))} />
          {!siteId && <Button type="button" variant="outline" size="sm" disabled={pending || bins.length === 1} onClick={() => setBins((old) => old.filter((item) => item.id !== bin.id))}>Pašalinti konteinerio formą</Button>}
        </fieldset>)}
        {!siteId && <Button type="button" variant="outline" disabled={pending} onClick={() => setBins((old) => [...old, emptyBin()])}>Pridėti dar vieną konteinerį</Button>}
        {fields.bins && <p role="alert" className="text-sm text-destructive">{fields.bins}</p>}
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        {missing && <Button asChild variant="outline"><Link to="/admin/sites">Grįžti į vietų sąrašą</Link></Button>}
        <DialogFooter><Button ref={cancel} type="button" variant="outline" disabled={pending} onClick={onClose}>Atšaukti</Button>
          <Button type="submit" disabled={pending || missing || (!siteId && !location)}>{pending ? 'Saugoma…' : 'Sukurti'}</Button></DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
}
