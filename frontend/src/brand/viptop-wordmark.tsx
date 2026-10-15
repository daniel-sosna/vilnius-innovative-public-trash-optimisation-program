import type { CSSProperties } from 'react'

type Props = { className?: string; size?: number; inverse?: boolean }
export function VipTopWordmark({ className = '', size = 32, inverse = false }: Props) {
  return <span role="img" aria-label="VipTop" className={`vip-wordmark${inverse ? ' vip-wordmark--inverse' : ''} ${className}`} style={{ '--vip-logo-size': `${size}px` } as CSSProperties}>
    Vip<span className="vip-wordmark__top">Top</span>
  </span>
}
