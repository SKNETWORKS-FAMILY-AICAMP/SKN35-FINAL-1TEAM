import type { ReactNode } from 'react'

export type BadgeTone = 'primary' | 'accent' | 'warning' | 'neutral'

const TONE_CLASS: Record<BadgeTone, string> = {
  primary: 'text-primary-300 border-primary-500/25',
  accent: 'text-accent-400 border-accent-500/25',
  warning: 'bg-amber-400/10 text-amber-300 border-amber-400/25',
  neutral: 'bg-background-700/60 text-foreground-300 border-background-600/70',
}

interface BadgeProps {
  children: ReactNode
  tone?: BadgeTone
  icon?: string
  dot?: boolean
  className?: string
}

function Badge({ children, tone = 'neutral', icon, dot = false, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border font-label font-medium tracking-wide h-6 px-2 text-[12px] ${TONE_CLASS[tone]} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {icon && (
        <span className="flex h-3.5 w-3.5 items-center justify-center">
          <i className={`${icon} text-[13px] leading-none`} />
        </span>
      )}
      {children}
    </span>
  )
}

export default Badge
