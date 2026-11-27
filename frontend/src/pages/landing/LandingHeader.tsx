import { useEffect, useState } from 'react'
import { Link } from 'react-router'

const SECTION_LINKS = [
  { href: '#platform', label: '제품' },
  { href: '#impact', label: '도입 효과' },
  { href: '#capabilities', label: '작동 방식' },
  { href: '#faq', label: 'FAQ' },
]

const SCROLLED_OFFSET = 24

function LandingHeader() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > SCROLLED_OFFSET)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${scrolled ? 'border-b border-foreground-50/10 bg-background-950/80 backdrop-blur-xl' : 'border-b border-transparent'}`}
    >
      <div className="mx-auto flex h-[68px] w-full max-w-[1280px] items-center justify-between px-5 md:h-[76px] md:px-10">
        <Link to="/" className="flex cursor-pointer items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-sm border border-primary-400/30 bg-primary-500/10 text-primary-300">
            <i className="ri-brain-line text-[15px]" />
          </span>
          <span className="whitespace-nowrap font-heading text-[16px] font-medium tracking-[-0.02em] text-foreground-50">
            헤디
          </span>
        </Link>

        <nav className="hidden items-center gap-10 md:flex" aria-label="주요 섹션">
          {SECTION_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="whitespace-nowrap text-[14px] text-foreground-400 transition-colors hover:text-foreground-50"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            to="/login"
            className="hidden cursor-pointer whitespace-nowrap px-3 text-[13.5px] text-foreground-400 transition-colors hover:text-foreground-50 sm:block"
          >
            로그인
          </Link>
          <Link
            to="/dashboard"
            className="hidden h-9 cursor-pointer items-center whitespace-nowrap rounded-[3px] bg-foreground-50 px-4 text-[13px] font-medium text-background-950 transition hover:bg-foreground-100 sm:inline-flex"
          >
            데모 열람
          </Link>
          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="메뉴"
            aria-expanded={menuOpen}
            className="flex h-10 w-10 cursor-pointer items-center justify-center text-foreground-200 md:hidden"
          >
            <i className={`${menuOpen ? 'ri-close-line' : 'ri-menu-line'} text-xl`} />
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="border-t border-foreground-50/10 bg-background-950/95 px-5 pb-6 pt-3 backdrop-blur-xl md:hidden">
          <nav className="flex flex-col" aria-label="모바일 섹션">
            {SECTION_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className="border-b border-foreground-50/5 py-3.5 text-[15px] text-foreground-300"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <Link
            to="/dashboard"
            className="mt-5 flex h-11 w-full cursor-pointer items-center justify-center rounded-[3px] bg-foreground-50 text-[14px] font-medium text-background-950"
          >
            데모 열람
          </Link>
        </div>
      )}
    </header>
  )
}

export default LandingHeader
