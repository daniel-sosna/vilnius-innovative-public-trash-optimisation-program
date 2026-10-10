import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { AlertDialog, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { CollectionMutationError, deleteBin, deleteSite, mutationError, type BinDeleteResult } from './api'

export function CollectionDeleteDialog({ id, kind, label, finalBin, onClose, onDeleted, onRefresh, restoreFocus }: {
  id: number; kind: 'site' | 'bin'; label: string; finalBin?: boolean; onClose: () => void
  onDeleted: (result?: BinDeleteResult) => void; onRefresh: () => void; restoreFocus: () => void
}) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [missing, setMissing] = useState(false)
  const submitting = useRef(false)
  const cancel = useRef<HTMLButtonElement>(null)
  const confirm = useRef<HTMLButtonElement>(null)
  async function remove() {
    if (submitting.current) return
    submitting.current = true
    setPending(true)
    setError('')
    try {
      if (kind === 'site') { await deleteSite(id); onDeleted() }
      else onDeleted(await deleteBin(id))
    } catch (failure) {
      setError(mutationError(failure))
      setMissing(failure instanceof CollectionMutationError && failure.status === 404)
    } finally {
      submitting.current = false
      setPending(false)
      window.requestAnimationFrame(() => {
        if (document.activeElement === document.body || document.activeElement?.getAttribute('role') === 'alertdialog') {
          if (confirm.current?.disabled) cancel.current?.focus()
          else confirm.current?.focus()
        }
      })
    }
  }
  return <AlertDialog open onOpenChange={(open) => { if (!open && !submitting.current) onClose() }}>
    <AlertDialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto"
      onOpenAutoFocus={(event) => { event.preventDefault(); cancel.current?.focus() }}
      onCloseAutoFocus={(event) => { event.preventDefault(); restoreFocus() }}
      onEscapeKeyDown={(event) => { if (submitting.current) event.preventDefault() }}>
      <AlertDialogHeader><AlertDialogTitle>{kind === 'site' ? 'Ištrinti surinkimo vietą?' : 'Ištrinti konteinerį?'}</AlertDialogTitle>
        <AlertDialogDescription className="break-words">
          {label}. {kind === 'site' ? 'Surinkimo vieta, visi jos konteineriai, jų aptarnavimo istorija ir gyventojų prašymai bus ištrinti visam laikui.' : 'Konteineris, jo aptarnavimo istorija ir gyventojų prašymai bus ištrinti visam laikui.'}
          {kind === 'bin' && (finalBin ? ' Tai paskutinis konteineris: bus ištrinta ir surinkimo vieta.' : ' Jei tai paskutinis likęs konteineris, bus ištrinta ir surinkimo vieta.')}
        </AlertDialogDescription></AlertDialogHeader>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      <AlertDialogFooter>
        {missing && <Button variant="outline" onClick={() => { onClose(); onRefresh() }}>Atnaujinti duomenis</Button>}
        <Button ref={cancel} variant="outline" disabled={pending} onClick={onClose}>Atšaukti</Button>
        <Button ref={confirm} variant="destructive" disabled={pending || missing} onClick={remove}>{pending ? 'Trinama…' : 'Ištrinti'}</Button>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
}
