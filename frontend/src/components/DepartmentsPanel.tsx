import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import { errorMessage } from '../api/client'
import { createDepartment, organizationQueries } from '../api/organizations'

// backend/app/organizations/schemas.py 의 DepartmentCreateRequest
const MAX_NAME_LENGTH = 50
const MAX_DESCRIPTION_LENGTH = 255

const inputClass =
  'h-10 w-full rounded-md border border-background-600/70 bg-background-800/50 px-3 text-[13.5px] text-foreground-100 outline-none transition focus:border-primary-500/60'

interface DepartmentsPanelProps {
  // 부서 생성은 ADMIN 만 가능
  canCreate: boolean
}

// 직원 가입은 부서가 하나 이상 있어야 열린다 (가입 시 부서를 고르기 때문)
function DepartmentsPanel({ canCreate }: DepartmentsPanelProps) {
  const queryClient = useQueryClient()
  const { data: departments = [], isPending } = useQuery(organizationQueries.departments())
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => createDepartment({ name: name.trim(), description: description.trim() }),
    onSuccess: () => {
      setName('')
      setDescription('')
      queryClient.invalidateQueries({ queryKey: organizationQueries.departments().queryKey })
    },
    onError: (err) =>
      setError(errorMessage(err, '부서를 만들지 못했습니다. 잠시 후 다시 시도해 주세요.')),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !description.trim()) {
      setError('부서 이름과 설명을 입력해 주세요.')
      return
    }
    setError('')
    mutation.mutate()
  }

  return (
    <div className="space-y-4 text-left">
      {!isPending && departments.length === 0 && (
        <p className="rounded-md border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-[12.5px] text-amber-200">
          등록된 부서가 없어 직원이 가입할 수 없습니다.
          {canCreate ? ' 부서를 먼저 등록해 주세요.' : ' 회사 관리자에게 문의해 주세요.'}
        </p>
      )}

      {departments.length > 0 && (
        <ul className="divide-y divide-background-700/70 rounded-md border border-background-700/70">
          {departments.map((dept) => (
            <li key={dept.dept_id} className="flex items-baseline gap-3 px-4 py-3">
              <span className="text-[14px] text-foreground-100">{dept.name}</span>
              {dept.description && (
                <span className="truncate text-[12.5px] text-foreground-500">
                  {dept.description}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {canCreate && (
        <form onSubmit={handleSubmit} className="space-y-2" noValidate>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_2fr_auto]">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={MAX_NAME_LENGTH}
              placeholder="부서 이름"
              aria-label="부서 이름"
              className={inputClass}
            />
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={MAX_DESCRIPTION_LENGTH}
              placeholder="설명 (예: 서비스 기획)"
              aria-label="부서 설명"
              className={inputClass}
            />
            <button
              type="submit"
              disabled={mutation.isPending}
              className="h-10 cursor-pointer whitespace-nowrap rounded-md border border-background-600/80 px-4 text-[13.5px] text-foreground-100 transition hover:bg-background-800/60 disabled:cursor-default disabled:opacity-60"
            >
              부서 추가
            </button>
          </div>
          {error && <p className="text-[12px] text-red-300">{error}</p>}
        </form>
      )}
    </div>
  )
}

export default DepartmentsPanel
