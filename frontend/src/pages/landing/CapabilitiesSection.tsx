import headImage from '../../assets/images/capability-head.jpg'
import summaryImage from '../../assets/images/capability-summary.jpg'
import trackingImage from '../../assets/images/capability-tracking.jpg'
import Reveal from './Reveal'

const CAPABILITIES = [
  {
    num: '01',
    title: '기준은 하나, HEAD',
    description:
      '승인된 산출물만 기준이 됩니다. 수정본이 아무리 많아도 팀이 참조하는 문서는 언제나 하나입니다.',
    points: ['승인 전 제출본은 팀 내부에만', '버전·소유 팀·공개 범위 기록'],
    image: headImage,
  },
  {
    num: '02',
    title: '변경은 3줄로',
    description:
      '긴 회의록도, 스무 장짜리 설계서도 그대로 전달하지 않습니다. 영향받는 팀이 알아야 할 것만 세 줄로 정리합니다.',
    points: ['AI 요약 + 근거 구간 표시', 'HEAD 덮어쓰기·개인정보 자동 감지'],
    image: summaryImage,
  },
  {
    num: '03',
    title: '확인까지 남는다',
    description:
      '알림을 보내고 끝나지 않습니다. 누가 읽었고 누가 아직 작업 중인지, 이틀이 지난 알림이 무엇인지 계속 남습니다.',
    points: ['팀별 확인 응답 기록', '2일 경과 자동 리마인드'],
    image: trackingImage,
  },
]

function CapabilitiesSection() {
  return (
    <section id="capabilities" className="relative py-24 md:py-36">
      <div className="mx-auto w-full max-w-[1280px] px-5 md:px-10">
        <div className="grid gap-6 lg:grid-cols-12 lg:gap-8">
          <span className="landing-kicker lg:col-span-4">Capabilities</span>
          <Reveal className="lg:col-span-8">
            <h2 className="text-[clamp(1.9rem,3.8vw,3.1rem)] font-light leading-[1.14] tracking-[-0.04em] text-foreground-50">
              조용하지만 빠짐없는 <span className="text-foreground-400">세 가지</span>
            </h2>
            <p className="mt-5 max-w-lg text-[15px] leading-[1.85] text-foreground-400">
              기준을 세우고, 변경을 요약하고, 확인을 남깁니다. 이 세 단계만 지켜도 회의는 절반으로
              줄어듭니다.
            </p>
          </Reveal>
        </div>

        <div className="mt-16 flex flex-col md:mt-24">
          {CAPABILITIES.map((item, i) => (
            <article
              key={item.num}
              className="grid gap-8 border-t border-foreground-50/[0.08] py-14 md:py-20 lg:grid-cols-12 lg:items-center lg:gap-8"
            >
              <Reveal className="flex flex-col lg:col-span-5">
                <span className="font-label text-[13px] tabular-nums tracking-[0.16em] text-foreground-500">
                  {item.num} / 03
                </span>
                <h3 className="mt-5 text-[clamp(1.6rem,2.6vw,2.2rem)] font-light leading-[1.2] tracking-[-0.03em] text-foreground-50">
                  <span className="text-primary-400">{item.title.slice(0, 1)}</span>
                  {item.title.slice(1)}
                </h3>
                <p className="mt-5 max-w-md text-[15px] leading-[1.85] text-foreground-400">
                  {item.description}
                </p>
                <ul className="mt-7 flex flex-wrap gap-x-5 gap-y-2">
                  {item.points.map((point) => (
                    <li
                      key={point}
                      className="flex items-center gap-2 whitespace-nowrap text-[13px] text-foreground-300"
                    >
                      <span className="h-1 w-1 shrink-0 bg-primary-400" aria-hidden />
                      {point}
                    </li>
                  ))}
                </ul>
              </Reveal>
              <Reveal
                delay={100}
                className={`lg:col-span-7 ${i % 2 === 1 ? 'lg:order-first lg:pe-10' : 'lg:ps-10'}`}
              >
                <div className="relative aspect-[16/10] w-full overflow-hidden rounded-[2px] bg-background-900">
                  <img
                    src={item.image}
                    alt={item.title}
                    className="absolute inset-0 h-full w-full object-cover object-center"
                  />
                </div>
              </Reveal>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export default CapabilitiesSection
