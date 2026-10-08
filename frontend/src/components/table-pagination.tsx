import { useId, useState, type FormEvent } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type Props = {
  page: number
  pageSize: number
  total: number | null
  disabled?: boolean
  loading?: boolean
  onPageChange: (page: number) => void
}

export function TablePagination({
  page,
  pageSize,
  total,
  disabled = false,
  loading = false,
  onPageChange,
}: Props) {
  const id = useId()
  const [draft, setDraft] = useState({ page, value: String(page), error: '' })
  if (draft.page !== page) {
    setDraft({ page, value: String(page), error: '' })
  }
  const value = draft.page === page ? draft.value : String(page)
  const error = draft.page === page ? draft.error : ''
  const lastPage =
    total === null ? null : Math.max(1, Math.ceil(total / pageSize))
  const blocked = disabled || loading || !total

  function jump(event: FormEvent) {
    event.preventDefault()
    if (blocked) return
    const target = Number(value)
    if (
      !value.trim() ||
      !Number.isInteger(target) ||
      target < 1 ||
      lastPage === null ||
      target > lastPage
    ) {
      setDraft({
        page,
        value,
        error: `Įveskite puslapį nuo 1 iki ${lastPage ?? 1}.`,
      })
      return
    }
    setDraft({ page, value: String(target), error: '' })
    onPageChange(target)
  }

  return (
    <nav
      aria-label="Sąrašo puslapiai"
      className="flex flex-wrap items-center justify-between gap-4"
    >
      <p className="text-sm text-muted-foreground" aria-live="polite">
        {loading
          ? 'Kraunama…'
          : lastPage === null
            ? `Puslapis ${page}`
            : `Puslapis ${page} iš ${lastPage}`}
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={blocked || page === 1}
            onClick={() => onPageChange(page - 1)}
          >
            <ChevronLeft aria-hidden="true" />
            Ankstesnis puslapis
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={blocked || lastPage === null || page >= lastPage}
            onClick={() => onPageChange(page + 1)}
          >
            Kitas puslapis
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
        <form onSubmit={jump} noValidate className="space-y-1">
          <div className="flex items-center gap-2">
            <Label htmlFor={id}>Puslapis</Label>
            <Input
              id={id}
              inputMode="numeric"
              className="h-8 w-16"
              value={value}
              disabled={blocked}
              onChange={(event) =>
                setDraft({ page, value: event.target.value, error: '' })
              }
              aria-invalid={!!error}
              aria-describedby={error ? `${id}-error` : undefined}
            />
            <Button
              type="submit"
              variant="outline"
              size="sm"
              disabled={blocked}
            >
              Eiti
            </Button>
          </div>
          {error && (
            <p
              id={`${id}-error`}
              role="alert"
              className="text-sm text-destructive"
            >
              {error}
            </p>
          )}
        </form>
      </div>
    </nav>
  )
}
