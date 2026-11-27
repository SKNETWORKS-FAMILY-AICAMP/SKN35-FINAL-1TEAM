const FAQS = [
  {
    q: '기준 문서(HEAD)가 정확히 무엇인가요?',
    a: '팀이 공식적으로 참조해야 하는 단 하나의 버전입니다. 승인된 산출물만 HEAD가 될 수 있고, 같은 문서의 이전 버전은 기록으로만 남습니다.',
  },
  {
    q: '기존에 쓰던 문서 도구를 바꿔야 하나요?',
    a: '아닙니다. 지금 쓰는 문서를 그대로 올리고 버전만 관리합니다. 워드, 피피티, 엑셀, 마크다운, PDF를 모두 다룹니다.',
  },
  {
    q: 'AI 요약이 틀리면 어떻게 되나요?',
    a: '요약은 원문 구간과 대조 검증을 통과해야만 발송됩니다. 검증에 실패한 요약은 발송되지 않고 검토자에게 원문 확인을 요청합니다.',
  },
  {
    q: '어떤 팀에 알림이 갈지는 누가 정하나요?',
    a: 'AI가 영향 팀을 먼저 제안하고, 제출자가 팀을 제외하거나 추가할 수 있습니다. 제외할 때는 사유를 남겨야 합니다.',
  },
  {
    q: '도입까지 얼마나 걸리나요?',
    a: '프로젝트 하나를 기준으로 2주 안에 첫 기준선을 세울 수 있습니다. 이후 프로젝트를 순차적으로 옮기는 것을 권합니다.',
  },
]

function FaqSection() {
  return (
    <section id="faq" className="border-t border-foreground-50/[0.06] py-24 md:py-32">
      <div className="mx-auto grid w-full max-w-[1280px] gap-10 px-5 md:px-10 lg:grid-cols-12 lg:gap-8">
        <div className="flex flex-col gap-5 lg:col-span-4">
          <span className="landing-kicker">FAQ</span>
          <h2 className="max-w-xs font-heading text-[clamp(1.6rem,2.6vw,2.2rem)] font-light leading-[1.2] tracking-[-0.03em] text-foreground-50">
            궁금한 것만 짧게
          </h2>
        </div>

        <div className="border-t border-foreground-50/10 lg:col-span-8">
          {FAQS.map((item) => (
            <details key={item.q} className="group border-b border-foreground-50/10">
              <summary className="flex cursor-pointer list-none items-center gap-6 py-6 md:py-7">
                <span className="flex-1 text-[16px] leading-snug text-foreground-200 transition-colors group-hover:text-foreground-50 md:text-[17px]">
                  {item.q}
                </span>
                <span className="flex h-6 w-6 shrink-0 items-center justify-center text-foreground-500 transition-transform duration-300 group-open:rotate-45">
                  <i className="ri-add-line text-lg" />
                </span>
              </summary>
              <div className="overflow-hidden">
                <p className="max-w-2xl pb-7 pr-10 text-[14.5px] leading-[1.9] text-foreground-400">
                  {item.a}
                </p>
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FaqSection
