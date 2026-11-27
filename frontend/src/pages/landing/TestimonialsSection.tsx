import Reveal from './Reveal'

const TESTIMONIALS = [
  {
    body: '설계서가 바뀌면 QA가 먼저 알아야 하는데, 늘 개발팀이 마지막에 알려줬어요. 이제 순서가 지켜집니다.',
    name: 'QA 매니저',
    org: '사내 시스템 SI 프로젝트',
  },
  {
    body: '3줄 요약이 정확해서 원문을 다시 열어보는 일이 줄었습니다.',
    name: '개발 파트장',
    org: '커머스 플랫폼',
  },
  {
    body: '확인하지 않은 팀이 숫자로 보이니, 독촉 대신 확인만 하면 됩니다.',
    name: '프로젝트 오너',
    org: '제조 SI',
  },
]

function TestimonialsSection() {
  return (
    <section className="relative py-24 md:py-36">
      <div className="mx-auto w-full max-w-[1280px] px-5 md:px-10">
        <div className="grid gap-14 lg:grid-cols-12 lg:gap-8">
          <Reveal className="flex flex-col lg:col-span-4">
            <span className="landing-kicker">In practice</span>
            <h2 className="mt-6 max-w-xs font-heading text-[clamp(1.6rem,2.6vw,2.2rem)] font-light leading-[1.2] tracking-[-0.03em] text-foreground-50">
              쓰는 사람들의 문장
            </h2>
          </Reveal>
          <Reveal delay={80} className="lg:col-span-8">
            <blockquote className="font-heading text-[clamp(1.5rem,2.8vw,2.2rem)] font-light leading-[1.42] tracking-[-0.03em] text-foreground-100">
              “회의에서 ‘그거 최신본 맞아?’라는 질문이 사라졌습니다. 기준이 하나니까요.”
            </blockquote>
            <figcaption className="mt-7 flex flex-col gap-0.5">
              <cite className="text-[14px] font-medium not-italic text-foreground-100">
                PM 리드
              </cite>
              <span className="text-[13px] text-foreground-500">디지털 에이전시</span>
            </figcaption>
          </Reveal>
        </div>

        <div className="mt-16 grid gap-x-10 md:mt-24 md:grid-cols-3">
          {TESTIMONIALS.map((item, i) => (
            <Reveal key={item.name} delay={i * 80}>
              <figure className="flex h-full flex-col justify-between border-t border-foreground-50/10 py-8">
                <blockquote className="text-[14.5px] leading-[1.85] text-foreground-300">
                  {item.body}
                </blockquote>
                <figcaption className="mt-6 flex flex-col gap-0.5">
                  <cite className="text-[13.5px] font-medium not-italic text-foreground-100">
                    {item.name}
                  </cite>
                  <span className="text-[13.5px] text-foreground-500">{item.org}</span>
                </figcaption>
              </figure>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

export default TestimonialsSection
