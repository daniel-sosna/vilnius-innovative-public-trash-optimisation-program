import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { carriers, wasteTypes, type BinDraft } from './bin-form-values'
import { wasteLabel } from './format'

export function BinForm({ value, onChange, errors, pending }: { value: BinDraft; onChange: (value: BinDraft) => void; errors: Record<string, string>; pending: boolean }) {
  const fields = [ ['object_group', 'Naudotojai'], ['capacity_m3', 'Talpa (m³)'], ['inventory_number', 'Inventorinis numeris'], ['waste_carrier', 'Atliekų vežėjas'], ['waste_type', 'Atliekų rūšis'] ] as const
  return <div className="grid min-w-0 gap-4 sm:grid-cols-2">
    {fields.map(([name, label]) => {
      const id = `${value.id}-${name}`
      const options = name === 'waste_carrier' ? carriers : name === 'waste_type' ? wasteTypes : null
      return <div key={name} className="min-w-0 space-y-2">
        <Label htmlFor={id}>{label}</Label>
        {options ? <Select value={value[name]} onValueChange={(text) => onChange({ ...value, [name]: text })} disabled={pending}>
          <SelectTrigger id={id} className="w-full min-w-0" aria-required aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${id}-error` : undefined}>
            <SelectValue placeholder="Pasirinkite" />
          </SelectTrigger>
          <SelectContent position="popper" className="max-w-[calc(100vw-2rem)]">
            {options.map((option) => <SelectItem key={option} value={option}>{name === 'waste_type' ? wasteLabel(option) : option}</SelectItem>)}
          </SelectContent>
        </Select> : <Input id={id} required value={value[name]} inputMode={name === 'capacity_m3' ? 'decimal' : undefined}
          onChange={(event) => onChange({ ...value, [name]: event.target.value })} disabled={pending} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${id}-error` : undefined} />}
        {errors[name] && <p id={`${id}-error`} role="alert" className="text-sm text-destructive">{errors[name]}</p>}
      </div>
    })}
  </div>
}
