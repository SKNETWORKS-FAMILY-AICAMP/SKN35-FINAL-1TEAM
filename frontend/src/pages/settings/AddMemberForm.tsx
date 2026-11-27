import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { errorMessage } from '../../api/client'
import { organizationQueries } from '../../api/organizations'
import {
  addProjectMembers,
  PROJECT_ROLE_LABEL,
  projectQueries,
  type ProjectMemberCreateItem,
} from '../../api/project'
import { useCurrentUser } from '../../hooks/useAuth'
import { selectClass, submitClass } from './formStyles'

type AddableRole = ProjectMemberCreateItem['role']

function AddMemberForm() {
  const queryClient = useQueryClient()
  const { project, teams } = useCurrentUser()
  const { data: users = [] } = useQuery(organizationQueries.users())
  const { data: members = [] } = useQuery(projectQueries.members(project.project_id))
  const isOwner = project.my_role === 'OWNER'

  // OWNER 는 모든 팀, LEADER 는 자기 팀에만 추가할 수 있다
  const teamOptions = isOwner
    ? teams
    : teams.filter((t) => t.project_team_id === project.my_project_team_id)

  const [teamId, setTeamId] = useState('')
  const [userId, setUserId] = useState('')
  const [role, setRole] = useState<AddableRole>('MEMBER')
  const [isApproval, setIsApproval] = useState(false)
  const [error, setError] = useState('')

  const selectedTeamId =
    teamId || (teamOptions.length === 1 ? String(teamOptions[0].project_team_id) : '')
  const memberIds = new Set(members.map((m) => m.user_id))
  const candidates = users.filter((u) => !memberIds.has(u.user_id))

  const mutation = useMutation({
    mutationFn: () =>
      addProjectMembers(project.project_id, [
        {
          user_id: Number(userId),
          project_team_id: Number(selectedTeamId),
          role,
          // 승인권자는 LEADER 만 지정할 수 있다
          is_approval: role === 'LEADER' && isApproval ? 'Y' : 'N',
        },
      ]),
    onSuccess: () => {
      setUserId('')
      setRole('MEMBER')
      setIsApproval(false)
      queryClient.invalidateQueries({ queryKey: ['projects', project.project_id] })
    },
    onError: (err) =>
      setError(errorMessage(err, '멤버를 추가하지 못했습니다. 잠시 후 다시 시도해 주세요.')),
  })

  if (teamOptions.length === 0) {
    return <p className="text-[13px] text-foreground-500">먼저 팀을 만들어 주세요.</p>
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!selectedTeamId) {
      setError('팀을 선택해 주세요.')
      return
    }
    if (!userId) {
      setError('추가할 직원을 선택해 주세요.')
      return
    }
    setError('')
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3" noValidate>
      <label className="block">
        <span className="mb-1.5 block text-[12px] text-foreground-500">팀</span>
        <select
          value={selectedTeamId}
          onChange={(e) => setTeamId(e.target.value)}
          disabled={teamOptions.length === 1}
          className={selectClass}
        >
          <option value="">팀 선택</option>
          {teamOptions.map((t) => (
            <option key={t.project_team_id} value={t.project_team_id}>
              {t.name}
            </option>
          ))}
        </select>
      </label>
      <label className="block">
        <span className="mb-1.5 block text-[12px] text-foreground-500">직원</span>
        <select value={userId} onChange={(e) => setUserId(e.target.value)} className={selectClass}>
          <option value="">
            {candidates.length === 0 ? '추가할 수 있는 직원이 없습니다' : '직원 선택'}
          </option>
          {candidates.map((u) => (
            <option key={u.user_id} value={u.user_id}>
              {u.name} · {u.email}
            </option>
          ))}
        </select>
      </label>
      {isOwner && (
        <div className="flex flex-wrap items-center gap-4">
          {(['MEMBER', 'LEADER'] as const).map((r) => (
            <label
              key={r}
              className="flex cursor-pointer items-center gap-2 text-[13px] text-foreground-300"
            >
              <input
                type="radio"
                name="member-role"
                checked={role === r}
                onChange={() => setRole(r)}
                className="h-4 w-4 cursor-pointer accent-primary-500"
              />
              {PROJECT_ROLE_LABEL[r]}
            </label>
          ))}
          {role === 'LEADER' && (
            <label className="flex cursor-pointer items-center gap-2 text-[13px] text-foreground-300">
              <input
                type="checkbox"
                checked={isApproval}
                onChange={(e) => setIsApproval(e.target.checked)}
                className="h-4 w-4 cursor-pointer accent-primary-500"
              />
              승인권자로 지정
            </label>
          )}
        </div>
      )}
      {error && <p className="text-[12px] text-red-300">{error}</p>}
      <button type="submit" disabled={mutation.isPending} className={`${submitClass} w-full`}>
        {mutation.isPending ? '추가하는 중…' : '멤버 추가'}
      </button>
    </form>
  )
}

export default AddMemberForm
