import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Check, Info, LoaderCircle } from 'lucide-react'
import { LocationMap } from '@/components/maps/location-map'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/toast-context'
import { formatValue, wasteLabel } from '@/pages/sites/format'
import { getBin, REQUEST_ERROR, ResidentRequestError, submitResidentRequest, type PublicBin } from './api'

const SUCCESS_GIF = 'https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExbzBjbWJnMWNtZXdiYnBpbGZiNTV5NWFydGcyenUzc3N0bmkxMGplMyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xsFjLwT7NPfH2/giphy.gif'

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
  const [gifFailed, setGifFailed] = useState(false)
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
          <div aria-hidden="true" className="flex size-28 items-center justify-center rounded-full bg-green-600 sm:size-32">
            <Check className="size-16 text-white" strokeWidth={3} />
          </div>
          <h1 id="resident-success-title" className="mt-6 text-2xl font-semibold tracking-tight">
            Jau vykstame pas Jus
          </h1>
        </div>
        {!gifFailed && <img
          src={SUCCESS_GIF}
          alt=""
          className="mt-8 block h-auto w-full max-w-xs rounded-md"
          onError={() => setGifFailed(true)}
        />}
      </main>
    )
  }

  return (
    <main
      aria-labelledby="resident-request-title"
      className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-6 pt-8 pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:pt-14"
    >
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
              <aside className="flex w-full items-start gap-3 rounded-lg border border-sky-400/60 bg-sky-200/25 p-4 text-black dark:border-sky-500/60 dark:bg-sky-100/90">
                <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-sky-700" />
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
