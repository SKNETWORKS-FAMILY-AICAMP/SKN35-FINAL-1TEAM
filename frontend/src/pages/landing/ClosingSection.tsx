import closingImage from '../../assets/images/closing.jpg'
import CtaButtons from './CtaButtons'
import Reveal from './Reveal'

function ClosingSection() {
  return (
    <section className="relative isolate overflow-hidden pb-20 pt-28 md:pb-28 md:pt-40">
      <img
        src={closingImage}
        alt="검은 지평선 위에 놓인 하나의 유리 큐브"
        className="absolute inset-0 -z-20 h-full w-full object-cover object-center"
      />
      <div className="absolute inset-0 -z-10 bg-background-950/80" aria-hidden />
      <div className="landing-glow absolute inset-0 -z-10" aria-hidden />

      <div className="mx-auto flex w-full max-w-[1280px] flex-col items-center px-5 text-center md:px-10">
        <Reveal>
          <h2 className="max-w-[760px] font-heading text-[clamp(2rem,4.4vw,3.4rem)] font-light leading-[1.14] tracking-[-0.04em] text-foreground-50">
            팀 전체가 같은 것을 보는 상태,
            <br />
            <span className="text-foreground-400">여기서 시작합니다.</span>
          </h2>
          <p className="mx-auto mt-7 max-w-md text-[15px] leading-[1.85] text-foreground-300">
            데모 프로젝트를 열어 기준 문서와 변경 비교 화면을 바로 확인해 보세요.
          </p>
          <CtaButtons className="mt-10" />
        </Reveal>
      </div>
    </section>
  )
}

export default ClosingSection
