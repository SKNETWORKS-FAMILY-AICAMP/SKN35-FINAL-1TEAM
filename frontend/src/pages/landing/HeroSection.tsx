import heroImage from '../../assets/images/hero.jpg'
import CtaButtons from './CtaButtons'

const KEYWORDS = ['기준 문서 HEAD', '3줄 변경 요약', '팀 확인 추적']

function HeroSection() {
  return (
    <section
      aria-label="확정은 여기서, 전달은 자동으로"
      className="relative isolate flex min-h-[600px] w-full items-center overflow-hidden md:h-[min(100vh,760px)]"
    >
      <img
        src={heroImage}
        alt="어둠 속에서 겹겹이 쌓인 반투명 유리 층과 시안빛 경계"
        className="absolute inset-0 -z-20 h-full w-full object-cover object-center"
      />
      <div className="landing-veil absolute inset-0 -z-10" aria-hidden />

      <div className="mx-auto w-full max-w-[1280px] px-5 pb-16 pt-28 md:px-10 md:pb-20">
        <div className="flex w-full flex-col items-center text-center">
          <span className="landing-kicker animate-fade-up">THE COMPANY-WIDE BRAIN</span>
          <h1 className="mt-7 max-w-[900px] font-heading text-[clamp(2.5rem,6.2vw,5.1rem)] font-light leading-[1.06] tracking-[-0.045em] text-foreground-50">
            <span className="block animate-fade-up">확정은 여기서,</span>
            <span
              className="block animate-fade-up text-foreground-400"
              style={{ animationDelay: '120ms' }}
            >
              전달은 자동으로.
            </span>
          </h1>
          <p
            className="mt-7 max-w-[520px] animate-fade-up text-[16px] leading-[1.75] text-foreground-300 md:text-[17px]"
            style={{ animationDelay: '220ms' }}
          >
            승인된 산출물만 기준이 되고, 확정된 변경은 영향받는 팀에 세 줄로 도착합니다. 같은 내용을
            두 번 설명하지 않아도 됩니다.
          </p>
          <div className="mt-10 animate-fade-up" style={{ animationDelay: '320ms' }}>
            <CtaButtons />
          </div>
          <div
            className="mt-16 flex animate-fade-up flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[12.5px] uppercase tracking-[0.2em] text-foreground-500"
            style={{ animationDelay: '420ms' }}
          >
            {KEYWORDS.map((keyword, i) => (
              <span key={keyword} className="contents">
                {i > 0 && <span className="h-1 w-1 rounded-full bg-foreground-600" aria-hidden />}
                <span>{keyword}</span>
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default HeroSection
