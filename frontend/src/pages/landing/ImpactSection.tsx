import impactImage from '../../assets/images/impact.jpg'
import Reveal from './Reveal'

const STATS = [
  { value: '-61%', label: '다시 설명하는 시간', note: '확정된 변경이 3줄 요약으로 도착합니다.' },
  { value: '3.4x', label: '기준 반영 속도', note: '승인과 동시에 HEAD가 갱신됩니다.' },
  { value: '+68%', label: '확인 응답률', note: '아직 확인하지 않은 팀이 바로 보입니다.' },
]

function ImpactSection() {
  return (
    <section id="impact" className="relative overflow-hidden py-24 md:py-36">
      <div className="mx-auto grid w-full max-w-[1280px] items-center gap-14 px-5 md:px-10 lg:grid-cols-12 lg:gap-8">
        <Reveal className="lg:col-span-5">
          <div className="relative aspect-[4/5] max-h-[520px] w-full overflow-hidden rounded-[2px] bg-background-900">
            <img
              src={impactImage}
              alt="작은 유리 조각들이 모여 하나의 구를 이룬 모습"
              className="absolute inset-0 h-full w-full object-cover object-center"
            />
          </div>
        </Reveal>

        <div className="flex flex-col lg:col-span-7 lg:col-start-6 lg:ps-10">
          <span className="landing-kicker">Impact</span>
          <Reveal>
            <h2 className="mt-6 max-w-xl text-[clamp(1.9rem,3.6vw,3rem)] font-light leading-[1.14] tracking-[-0.04em] text-foreground-50">
              숫자로 남는 변화
            </h2>
            <p className="mt-5 max-w-md text-[15px] leading-[1.85] text-foreground-400">
              파일럿에 참여한 세 개 프로젝트의 8주 기록입니다.
            </p>
          </Reveal>

          <dl className="mt-14 flex flex-col md:mt-20">
            {STATS.map((stat, i) => (
              <Reveal key={stat.label} delay={i * 90}>
                <div className="flex flex-col gap-3 border-t border-foreground-50/10 py-8 md:py-10">
                  <div className="flex items-end justify-between gap-6">
                    <dd className="font-heading text-[clamp(2.6rem,6vw,4.6rem)] font-light leading-[0.9] tracking-[-0.05em] text-foreground-50">
                      {stat.value}
                    </dd>
                    <div className="flex max-w-[15rem] flex-col items-end gap-1 pb-1 text-right">
                      <dt className="text-[14px] font-medium text-foreground-100">{stat.label}</dt>
                      <span className="text-[13.5px] leading-relaxed text-foreground-500">
                        {stat.note}
                      </span>
                    </div>
                  </div>
                </div>
              </Reveal>
            ))}
          </dl>
        </div>
      </div>
    </section>
  )
}

export default ImpactSection
