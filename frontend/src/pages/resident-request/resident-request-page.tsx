import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { VipTopLogo } from '@/components/viptop-logo'
import { WolfMascot } from '@/brand/wolf-mascot'
import { Check, Info, LoaderCircle } from 'lucide-react'
import { LocationMap } from '@/components/maps/location-map'
import { VilniusLogo } from '@/components/vilnius-logo'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/toast-context'
import { formatValue, wasteLabel } from '@/pages/sites/format'
import { getBin, REQUEST_ERROR, ResidentRequestError, submitResidentRequest, type PublicBin } from './api'

type BinResult = {
  revision: number
  bin: PublicBin | null
  error: 'missing' | 'failed' | null
}

export function ResidentRequestPage() {
  const { bin_id = '' } = useParams()
  return <ResidentRequestContent key={bin_id} binId={bin_id} />
}

function ResidentRequestContent({ binId }: { binId: string }) {
  const notify = useToast()
  const validId = /^\d+$/.test(binId) && /[1-9]/.test(binId)
  const [revision, setRevision] = useState(0)
  const [result, setResult] = useState<BinResult | null>(null)
  const [submission, setSubmission] = useState<'idle' | 'pending' | 'success'>('idle')
  const active = useRef(false)
  const pending = useRef(false)
  const current = result?.revision === revision ? result : null
  const bin = current?.bin
  const missing = !validId || current?.error === 'missing'

  useEffect(() => {
    active.current = true
    return () => { active.current = false }
  }, [])

  useEffect(() => {
    if (!validId) return
    const controller = new AbortController()
    getBin(binId, controller.signal)
      .then((bin) => {
        if (!controller.signal.aborted) setResult({ revision, bin, error: null })
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setResult({
          revision, bin: null,
          error: error instanceof ResidentRequestError && [404, 422].includes(error.status)
            ? 'missing' : 'failed',
        })
      })
    return () => controller.abort()
  }, [binId, revision, validId])

  async function submit() {
    if (!bin || pending.current || submission !== 'idle') return
    pending.current = true
    setSubmission('pending')
    try {
      await submitResidentRequest(binId)
      if (active.current) setSubmission('success')
    } catch {
      if (active.current) {
        setSubmission('idle')
        notify({ message: REQUEST_ERROR, variant: 'error' })
      }
    } finally {
      pending.current = false
    }
  }

  if (submission === 'success') {
    return (
      <main aria-labelledby="resident-success-title" className="mx-auto flex min-h-dvh w-full max-w-md flex-col items-center justify-center px-6 py-8 text-center">
        <div role="status" aria-live="polite" aria-atomic="true" className="flex w-full flex-col items-center">
          <div aria-hidden="true" className="flex size-28 items-center justify-center rounded-full bg-[var(--vip-success)] sm:size-32">
            <Check className="size-16 text-white" strokeWidth={3} />
          </div>
          <h1 id="resident-success-title" className="mt-6 text-2xl font-semibold tracking-tight">
            Pranešimas gautas
          </h1>
        </div>
        <WolfMascot size={280} className="mt-8" />
        <div className="mt-6"><VipTopLogo /></div>
      </main>
    )
  }

  return (
    <main
      aria-labelledby="resident-request-title"
      className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-6 pt-8 pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:pt-14"
    >
      <div className="mb-6 flex flex-col items-center gap-4">
        <VilniusLogo />
        <VipTopLogo />
      </div>
      <h1 id="resident-request-title" className="break-words text-xl leading-snug font-semibold tracking-tight">
        {missing ? 'Konteineris nerastas' : 'Prašyti šiukšlių išvežimo'}
      </h1>

      {!missing && (!current ? (
        <p role="status" className="mt-8 flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle aria-hidden="true" className="size-4 motion-safe:animate-spin" />
          Kraunama…
        </p>
      ) : current.error === 'failed' ? (
        <div className="mt-8 space-y-5">
          <p role="alert" className="text-sm text-destructive">{REQUEST_ERROR}</p>
          <Button variant="outline" className="min-h-12 w-full" onClick={() => setRevision((value) => value + 1)}>
            Bandyti dar kartą
          </Button>
        </div>
      ) : bin && (
        <>
          <div className="mt-6">
            <LocationMap latitude={bin.latitude} longitude={bin.longitude} interactive={false} canvasClassName="h-48 sm:h-56" />
          </div>
          <dl className="mt-6 space-y-4">
            <div className="space-y-1">
              <dt className="text-sm text-muted-foreground">Adresas</dt>
              <dd className="break-words text-lg font-medium">{formatValue(bin.address)}</dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm text-muted-foreground">Konteinerio numeris</dt>
              <dd className="break-words text-lg font-medium">{formatValue(bin.inventory_number)}</dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm text-muted-foreground">Atliekų tipas</dt>
              <dd className="break-words text-lg font-medium">{bin.waste_type == null ? 'N/A' : wasteLabel(bin.waste_type)}</dd>
            </div>
          </dl>

          {bin.latest_service && (
            <div className="flex flex-1 items-center py-6">
              <aside className="flex w-full items-start gap-3 rounded-lg border border-border bg-card p-4 text-foreground">
                <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-[var(--vip-info)]" />
                <p className="min-w-0 text-sm leading-relaxed">
                  <span className="block font-medium">Paskutinis aptarnavimas atliktas</span>
                  <time dateTime={bin.latest_service.date.split('T')[0]} className="block break-words">
                    {bin.latest_service.date.split('T')[0]}
                  </time>
                </p>
              </aside>
            </div>
          )}

          <div className={`mt-auto${bin.latest_service ? '' : ' pt-6'}`}>
            <div role="status" aria-live="polite" aria-atomic="true">
              {submission === 'pending' && <span className="sr-only">Kraunama…</span>}
            </div>
            <Button
              className="min-h-12 w-full text-base"
              disabled={submission === 'pending'}
              aria-busy={submission === 'pending'}
              onClick={submit}
            >
              {submission === 'pending' && <LoaderCircle aria-hidden="true" className="size-4 motion-safe:animate-spin" />}
              Siųsti
            </Button>
          </div>
        </>
      ))}
    </main>
  )
}
