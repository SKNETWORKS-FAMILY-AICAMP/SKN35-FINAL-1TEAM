import { Link } from 'react-router'

function CtaButtons({ className = '' }: { className?: string }) {
  return (
    <div className={`flex flex-wrap items-center justify-center gap-3 ${className}`}>
      <Link
        to="/dashboard"
        className="inline-flex h-11 cursor-pointer items-center whitespace-nowrap rounded-[3px] bg-foreground-50 px-6 text-[14px] font-medium text-background-950 transition hover:bg-foreground-100"
      >
        데모 열람
      </Link>
      <Link
        to="/login"
        className="inline-flex h-11 cursor-pointer items-center whitespace-nowrap rounded-[3px] border border-foreground-50/20 px-6 text-[14px] text-foreground-100 transition hover:border-foreground-50/40 hover:bg-foreground-50/5"
      >
        로그인
      </Link>
    </div>
  )
}

export default CtaButtons
