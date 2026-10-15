const logo = `${import.meta.env.BASE_URL}brand/vilnius-logo-transparent.png`
import { cn } from '@/lib/utils'

export function VilniusLogo({ className }: { className?: string }) {
  return (
    <img
      src={logo}
      alt="Vilniaus logotipas"
      width={1334}
      height={1179}
      className={cn('block h-auto w-24 max-w-full shrink-0 object-contain', className)}
    />
  )
}
