import logo from '@/assets/vilnius-logo.webp'
import { cn } from '@/lib/utils'

export function VilniusLogo({ className }: { className?: string }) {
  return (
    <img
      src={logo}
      alt="Vilniaus logotipas"
      width={960}
      height={960}
      className={cn('block size-24 max-w-full shrink-0 object-contain', className)}
    />
  )
}
