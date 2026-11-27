import Reveal from './Reveal'

const PRINCIPLES = [
  {
    title: '승인 없는 확정은 없다',
    body: '제출, 검토, 승인, 반영. 네 단계를 건너뛴 변경은 기준이 되지 않습니다.',
  },
  {
    title: '요약은 검증을 통과해야 한다',
    body: 'AI가 만든 3줄 요약은 원문 구간과 대조를 통과한 뒤에만 발송됩니다.',
  },
  {
    title: '권한 밖은 보이지 않는다',
    body: '팀 내부 문서는 팀 안에서만, 외부 공유 문서는 정해진 범위에서만 열립니다.',
  },
  {
    title: '모든 판단에 근거가 남는다',
    body: '누가 언제 무엇을 승인했는지 감사 로그로 남아 나중에 되짚을 수 있습니다.',
  },
]

function PrinciplesSection() {
  return (
    <section className="relative overflow-hidden border-t border-foreground-50/[0.06] py-24 md:py-36">
      <div className="landing-glow pointer-events-none absolute inset-0" aria-hidden />
      <div className="relative mx-auto w-full max-w-[1280px] px-5 md:px-10">
        <div className="flex max-w-xl flex-col gap-5">
          <span className="landing-kicker">Why it works</span>
          <Reveal>
            <h2 className="text-[clamp(1.9rem,3.6vw,2.9rem)] font-light leading-[1.16] tracking-[-0.04em] text-foreground-50">
              왜 이 방식이 오래가는가
            </h2>
            <p className="mt-5 text-[15px] leading-[1.85] text-foreground-400">
              기능이 아니라 규칙이기 때문입니다. 네 가지 원칙이 문서마다 동일하게 적용됩니다.
            </p>
          </Reveal>
        </div>

        <div className="mt-16 grid gap-x-12 md:mt-24 md:grid-cols-2">
          {PRINCIPLES.map((item, i) => (
            <Reveal key={item.title} delay={i * 80}>
              <div className="flex flex-col gap-3 border-t border-foreground-50/10 py-8 md:py-10">
                <div className="flex items-baseline justify-between gap-4">
                  <h3 className="font-heading text-[19px] font-normal tracking-[-0.02em] text-foreground-50">
                    {item.title}
                  </h3>
                  <span className="font-label text-[12px] tabular-nums text-foreground-600">
                    0{i + 1}
                  </span>
                </div>
                <p className="max-w-md text-[14.5px] leading-[1.85] text-foreground-400">
                  {item.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

export default PrinciplesSection
