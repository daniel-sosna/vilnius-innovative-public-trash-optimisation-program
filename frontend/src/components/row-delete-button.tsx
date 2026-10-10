import type { ComponentProps } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type RowDeleteButtonProps = Omit<
  ComponentProps<typeof Button>,
  'children' | 'variant' | 'size' | 'asChild'
> & { recordName: string }

export function RowDeleteButton({ recordName, className, ...props }: RowDeleteButtonProps) {
  return (
    <Button
      {...props}
      type={props.type ?? 'button'}
      variant="ghost"
      size="sm"
      className={cn('text-destructive hover:bg-destructive/10 hover:text-destructive', className)}
    >
      Ištrinti<span className="sr-only">: {recordName}</span>
    </Button>
  )
}
