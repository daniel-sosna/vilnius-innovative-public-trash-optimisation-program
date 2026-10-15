import type { CSSProperties } from 'react'

type Props = {
  pose?: 'leaning' | 'head'
  size?: number
  wink?: boolean
  className?: string
  decorative?: boolean
  alt?: string
  assetBase?: string
}
export function WolfMascot({ pose = 'leaning', size = 160, wink = false, className = '', decorative = true, alt = 'VipTop vilkas', assetBase = `${import.meta.env.BASE_URL}brand` }: Props) {
  const base = assetBase.replace(/\/$/, '')
  const style = { '--vip-wolf-size': `${size}px` } as CSSProperties
  if (pose === 'head') return <span className={`vip-wolf vip-wolf--head ${className}`} style={style} data-wink={wink} aria-hidden={decorative || undefined}>
    <img src={`${base}/vilnius-hill-wolf.png`} width={1536} height={1024} alt={decorative ? '' : alt} loading="lazy" decoding="async" onError={event => { event.currentTarget.style.visibility = 'hidden' }} />
  </span>
  return <img className={`vip-wolf vip-wolf--leaning ${className}`} style={style} src={`${base}/wolf-leaning-frame.png`} width={1536} height={1024} alt={decorative ? '' : alt} aria-hidden={decorative || undefined} loading="lazy" decoding="async" onError={event => { event.currentTarget.style.visibility = 'hidden' }} />
}
