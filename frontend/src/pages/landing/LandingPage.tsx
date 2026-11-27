import { Link } from 'react-router'

import CapabilitiesSection from './CapabilitiesSection'
import ClosingSection from './ClosingSection'
import FaqSection from './FaqSection'
import HeroSection from './HeroSection'
import ImpactSection from './ImpactSection'
import LandingHeader from './LandingHeader'
import PlatformSection from './PlatformSection'
import PrinciplesSection from './PrinciplesSection'
import TestimonialsSection from './TestimonialsSection'

const FOOTER_LINKS = [
  { href: '#platform', label: '제품' },
  { href: '#capabilities', label: '작동 방식' },
  { href: '#faq', label: 'FAQ' },
]

const footerLinkClass =
  'whitespace-nowrap text-[13.5px] text-foreground-400 transition-colors hover:text-foreground-100'

function LandingFooter() {
  return (
    <footer className="border-t border-foreground-50/[0.08]">
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-8 px-5 py-14 md:flex-row md:items-start md:justify-between md:px-10">
        <div className="flex flex-col gap-2">
          <span className="font-heading text-[16px] font-medium tracking-[-0.02em] text-foreground-100">
            헤디
          </span>
          <p className="max-w-xs text-[13.5px] leading-relaxed text-foreground-500">
            승인된 기준 문서와 변경 확인을 한 곳에서. 헤디.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-10 gap-y-3" aria-label="푸터">
          {FOOTER_LINKS.map((link) => (
            <a key={link.href} href={link.href} className={footerLinkClass}>
              {link.label}
            </a>
          ))}
          <Link to="/login" className={footerLinkClass}>
            로그인
          </Link>
        </nav>
      </div>
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-2 border-t border-foreground-50/[0.06] px-5 py-6 text-[13.5px] text-foreground-600 sm:flex-row sm:justify-between md:px-10">
        <span>© 2026 헤디</span>
        <span>확정은 여기서, 전달은 자동으로.</span>
      </div>
    </footer>
  )
}

function LandingPage() {
  return (
    <div className="min-h-screen w-full bg-background-950 text-foreground-100">
      <LandingHeader />
      <main>
        <HeroSection />
        <PlatformSection />
        <ImpactSection />
        <CapabilitiesSection />
        <PrinciplesSection />
        <TestimonialsSection />
        <FaqSection />
        <ClosingSection />
      </main>
      <LandingFooter />
    </div>
  )
}

export default LandingPage
