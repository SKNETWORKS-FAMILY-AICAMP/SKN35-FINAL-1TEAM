import { useMutation, useQueryClient } from '@tanstack/react-query'

import {
  documentQueries,
  respondToChange,
  type DocumentReview,
  type TeamResponse,
} from '../../api/documents'
import Badge from '../../components/Badge'

interface OwnerResponsePanelProps {
  review: DocumentReview
  team: string
  onNotify: (message: string) => void
}

function OwnerResponsePanel({ review, team, onNotify }: OwnerResponsePanelProps) {
  const queryClient = useQueryClient()
  const myTeam = review.teams.find((t) => t.name === team)

  const respond = useMutation({
    mutationFn: (response: TeamResponse) => respondToChange(review.id, team, response),
    onSuccess: (_, response) => {
      queryClient.invalidateQueries({ queryKey: documentQueries.review(review.id).queryKey })
      onNotify(`${team} · '${response}'로 응답했습니다. 확인 현황에 기록되었습니다.`)
    },
  })

  return (
    <section className="panel border-primary-500/25 p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-heading text-[17px] font-medium text-foreground-50">영향 팀 확인</h2>
          <p className="mt-1 text-[12.5px] text-foreground-500">
            {team} 담당자로 응답합니다. 응답은 확인 현황과 변경 알림에 바로 반영됩니다.
          </p>
        </div>
        <Badge tone="primary" icon="ri-team-line">
          {team} 담당자
        </Badge>
      </div>

      {myTeam?.state === 'done' ? (
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-md border border-accent-500/30 bg-accent-500/10 px-3.5 py-3 text-[13px] text-accent-200">
          <i className="ri-checkbox-circle-line text-[16px]" />
          {team} 확인 완료
          {myTeam.response && myTeam.response !== '확인 완료' && (
            <span className="text-foreground-400">· {myTeam.response}</span>
          )}
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => respond.mutate('확인 완료')}
            disabled={respond.isPending}
            className="flex h-10 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md bg-primary-500 px-5 font-label text-[13.5px] font-semibold text-background-950 shadow-glow transition hover:bg-primary-400"
          >
            <i className="ri-check-line text-[15px]" /> 확인 완료
          </button>
          <button
            type="button"
            onClick={() => respond.mutate('영향 없음')}
            disabled={respond.isPending}
            className="flex h-10 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md border border-background-600/80 px-5 font-label text-[13.5px] text-foreground-200 transition hover:border-background-500 hover:text-foreground-50"
          >
            <i className="ri-check-double-line text-[15px]" /> 영향 없음
          </button>
        </div>
      )}
    </section>
  )
}

export default OwnerResponsePanel
