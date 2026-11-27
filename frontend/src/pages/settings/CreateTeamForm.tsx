import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { errorMessage } from '../../api/client'
import { organizationQueries } from '../../api/organizations'
import { createProjectTeam, projectQueries } from '../../api/project'
import { useCurrentUser } from '../../hooks/useAuth'
import { inputClass, selectClass, submitClass } from './formStyles'

// backend/app/projects/schemas.py 의 ProjectTeamCreateRequest
const MAX_TEAM_NAME_LENGTH = 50

function CreateTeamForm() {
  const queryClient = useQueryClient()
  const { project } = useCurrentUser()
  const { data: users = [] } = useQuery(organizationQueries.users())
  const { data: members = [] } = useQuery(projectQueries.members(project.project_id))
  const [name, setName] = useState('')
  const [leaderId, setLeaderId] = useState('')
  const [isApproval, setIsApproval] = useState(false)
  const [error, setError] = useState('')

  // 이미 이 프로젝트의 팀에 속한 직원은 팀장이 될 수 없다
  const memberIds = new Set(members.map((m) => m.user_id))
  const candidates = users.filter((u) => !memberIds.has(u.user_id))

  const mutation = useMutation({
    mutationFn: () =>
      createProjectTeam(project.project_id, {
        name: name.trim(),
        team_leader: Number(leaderId),
        is_approval: isApproval ? 'Y' : 'N',
      }),
    onSuccess: () => {
      setName('')
      setLeaderId('')
      setIsApproval(false)
      queryClient.invalidateQueries({ queryKey: ['projects', project.project_id] })
    },
    onError: (err) =>
      setError(errorMessage(err, '팀을 만들지 못했습니다. 잠시 후 다시 시도해 주세요.')),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('팀 이름을 입력해 주세요.')
      return
    }
    if (!leaderId) {
      setError('대표 팀장을 선택해 주세요.')
      return
    }
    setError('')
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3" noValidate>
      <label className="block">
        <span className="mb-1.5 block text-[12px] text-foreground-500">팀 이름</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={MAX_TEAM_NAME_LENGTH}
          placeholder="예: 기획팀"
          className={inputClass}
        />
      </label>
      <label className="block">
        <span className="mb-1.5 block text-[12px] text-foreground-500">대표 팀장</span>
        <select
          value={leaderId}
          onChange={(e) => setLeaderId(e.target.value)}
          className={selectClass}
        >
          <option value="">직원 선택</option>
          {candidates.map((u) => (
            <option key={u.user_id} value={u.user_id}>
              {u.name} · {u.email}
            </option>
          ))}
        </select>
      </label>
      <label className="flex cursor-pointer items-center gap-2 text-[13px] text-foreground-300">
        <input
          type="checkbox"
          checked={isApproval}
          onChange={(e) => setIsApproval(e.target.checked)}
          className="h-4 w-4 cursor-pointer accent-primary-500"
        />
        대표 팀장을 승인권자로 지정
      </label>
      {error && <p className="text-[12px] text-red-300">{error}</p>}
      <button type="submit" disabled={mutation.isPending} className={`${submitClass} w-full`}>
        {mutation.isPending ? '만드는 중…' : '팀 만들기'}
      </button>
    </form>
  )
}

export default CreateTeamForm
