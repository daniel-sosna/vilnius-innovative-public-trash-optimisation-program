import { useState } from 'react'
import { CalendarDays } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { useProjectDate } from '@/lib/project-date/context'

export function ProjectCalendar() {
  const { projectDate, locked, setDate } = useProjectDate()
  const [open, setOpen] = useState(false)
  return <Dialog open={open} onOpenChange={setOpen}>
    <DialogTrigger asChild><Button variant="outline" size="icon" disabled={locked} aria-label={`Projekto data: ${projectDate}. Atidaryti kalendorių`} title={projectDate}>
      <CalendarDays aria-hidden="true" />
    </Button></DialogTrigger>
    <DialogContent className="sm:max-w-sm p-4">
      <DialogTitle>2026 m. rugsėjis</DialogTitle>
      <DialogDescription>Projekto data: {projectDate}{locked ? '. Planavimas vyksta; data užrakinta.' : ''}</DialogDescription>
      <table role="grid" aria-label="2026 m. rugsėjo kalendorius" className="w-full table-fixed text-center">
        <thead><tr>{['Pr', 'An', 'Tr', 'Kt', 'Pn', 'Št', 'Sk'].map(day => <th key={day} scope="col" className="py-2 text-xs font-normal text-muted-foreground">{day}</th>)}</tr></thead>
        <tbody>{Array.from({ length: 5 }, (_, week) => <tr key={week}>{Array.from({ length: 7 }, (_, weekday) => {
          const day = week * 7 + weekday, value = `2026-09-${String(day).padStart(2, '0')}`
          if (day < 1 || day > 30) return <td key={weekday} />
          return <td key={weekday} aria-selected={value === projectDate} className="p-0.5"><Button aria-label={`${value}${value === projectDate ? ', pasirinkta' : ''}`} variant={value === projectDate ? 'default' : 'ghost'} disabled={locked} className="h-9 w-full px-0" autoFocus={value === projectDate} onClick={() => { if (setDate(value)) setOpen(false) }} onKeyDown={event => {
            const offsets: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7, Home: 1 - day, End: 30 - day }
            if (event.key in offsets) {
              event.preventDefault()
              const target = Math.max(1, Math.min(30, day + offsets[event.key]))
              event.currentTarget.closest('table')?.querySelector<HTMLButtonElement>(`button[aria-label^="2026-09-${String(target).padStart(2, '0')}"]`)?.focus()
            }
          }}>{day}</Button></td>
        })}</tr>)}</tbody>
      </table>
    </DialogContent>
  </Dialog>
}
