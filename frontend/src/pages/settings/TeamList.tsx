import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { errorMessage } from '../../api/client'
import { PROJECT_ROLE_LABEL, projectQueries, updateTeamLeader } from '../../api/project'
import Badge from '../../components/Badge'
import { useCurrentUser } from '../../hooks/useAuth'

function TeamList() {
  const queryClient = useQueryClient()
  const { project, teams } = useCurrentUser()
  const { data: members = [] } = useQuery(projectQueries.members(project.project_id))
  const [error, setError] = useState('')
  const isOwner = project.my_role === 'OWNER'

  const leaderMutation = useMutation({
    mutationFn: ({ teamId, userId }: { teamId: number; userId: number }) =>
      updateTeamLeader(project.project_id, teamId, userId),
    onSuccess: () => {
      setError('')
      queryClient.invalidateQueries({ queryKey: ['projects', project.project_id] })
    },
    onError: (err) => setError(errorMessage(err, '대표 팀장을 바꾸지 못했습니다.')),
  })

  if (teams.length === 0) {
    return (
      <p className="rounded-md border border-background-700/70 px-4 py-6 text-center text-[13.5px] text-foreground-500">
        아직 팀이 없습니다.
        {isOwner ? ' 아래에서 첫 팀을 만들어 주세요.' : ' 프로젝트 오너가 팀을 만들면 표시됩니다.'}
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {error && <p className="text-[12.5px] text-red-300">{error}</p>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {teams.map((team) => {
          const teamMembers = members.filter((m) => m.project_team_id === team.project_team_id)
          // 대표 팀장은 그 팀의 LEADER(또는 OWNER) 중에서만 고를 수 있다
          const leaderCandidates = teamMembers.filter((m) => m.role !== 'MEMBER')

          return (
            <div key={team.project_team_id} className="panel p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-[15px] text-foreground-50">
                    {team.name ?? '이름 없는 팀'}
                  </p>
                  <p className="mt-0.5 text-[12.5px] text-foreground-500">
                    대표 팀장 {team.team_leader_name ?? '-'} · {team.member_count}명
                  </p>
                </div>
                {isOwner && leaderCandidates.length > 1 && (
                  <select
                    value={team.team_leader ?? ''}
                    disabled={leaderMutation.isPending}
                    onChange={(e) =>
                      leaderMutation.mutate({
                        teamId: team.project_team_id,
                        userId: Number(e.target.value),
                      })
                    }
                    aria-label={`${team.name} 대표 팀장`}
                    className="h-8 cursor-pointer rounded-md border border-background-600/70 bg-background-800/50 px-2 text-[12.5px] text-foreground-200 outline-none"
                  >
                    {leaderCandidates.map((m) => (
                      <option key={m.user_id} value={m.user_id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <ul className="mt-4 divide-y divide-background-700/60">
                {teamMembers.map((m) => (
                  <li key={m.project_member_id} className="flex items-center gap-3 py-2.5">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-primary-500/25 bg-primary-500/10 text-[12px] text-primary-200">
                      {m.name.slice(0, 1)}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13.5px] text-foreground-100">
                        {m.name}
                      </span>
                      <span className="block truncate text-[11.5px] text-foreground-500">
                        {m.email}
                      </span>
                    </span>
                    {m.is_approval === 'Y' && <Badge tone="primary">승인권자</Badge>}
                    <Badge>{PROJECT_ROLE_LABEL[m.role]}</Badge>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default TeamList
