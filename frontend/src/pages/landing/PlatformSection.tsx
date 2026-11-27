import Reveal from './Reveal'

function PlatformSection() {
  return (
    <section id="platform" className="relative border-t border-foreground-50/[0.06] py-24 md:py-36">
      <div className="mx-auto w-full max-w-[1280px] px-5 md:px-10">
        <div className="grid gap-6 lg:grid-cols-12 lg:gap-8">
          <span className="landing-kicker lg:col-span-4">Platform</span>
          <Reveal className="lg:col-span-8">
            <h2 className="text-[clamp(2rem,4.2vw,3.4rem)] font-light leading-[1.12] tracking-[-0.04em] text-foreground-50">
              하나의 기준,
              <br />
              <span className="text-foreground-400">하나의 흐름.</span>
            </h2>
          </Reveal>
        </div>

        <div className="mt-16 grid gap-10 md:mt-24 lg:grid-cols-12 lg:gap-8">
          <Reveal className="lg:col-span-4">
            <p className="max-w-sm text-[17px] leading-[1.8] text-foreground-200">
              문서는 메신저에, 결정은 회의록에, 최신본은 누군가의 데스크톱에 있습니다.
            </p>
          </Reveal>
          <Reveal delay={120} className="lg:col-span-8 lg:pl-10">
            <p className="max-w-2xl text-[15px] leading-[1.95] text-foreground-400">
              헤디는 그 흩어진 결정을 한 곳에 모읍니다. 승인된 산출물만 기준이 되고, 확정된 변경은
              영향받는 팀에 세 줄로 도착합니다. 누가 무엇을 확인했는지도 같은 화면에 남습니다.
              필요한 것은 더 많은 문서가 아니라, 모두가 같은 것을 보고 있다는 확신입니다.
            </p>
          </Reveal>
        </div>

        <Reveal delay={80} className="mt-20 md:mt-28 lg:ml-auto lg:max-w-[720px]">
          <blockquote className="border-l border-primary-500/40 pl-6 font-heading text-[clamp(1.5rem,2.8vw,2.2rem)] font-light leading-[1.4] tracking-[-0.03em] text-foreground-100">
            “결정은 한 곳에 쌓이고,
            <br />
            <span className="text-foreground-500">확인은 각자의 자리에서.</span>”
          </blockquote>
        </Reveal>
      </div>
    </section>
  )
}

export default PlatformSection
