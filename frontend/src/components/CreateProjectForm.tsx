import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'

import { errorMessage } from '../api/client'
import { createProject } from '../api/project'
import { useSelectProject } from '../hooks/useAuth'

// backend/app/projects/schemas.py 의 ProjectCreateRequest
const MAX_PROJECT_NAME_LENGTH = 100

interface CreateProjectFormProps {
  onCreated?: () => void
}

// 만든 프로젝트로 전환한 뒤, 팀을 바로 꾸릴 수 있게 조직 관리 화면으로 보낸다
function CreateProjectForm({ onCreated }: CreateProjectFormProps) {
  const navigate = useNavigate()
  const selectProject = useSelectProject()
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => createProject(name.trim()),
    onSuccess: (project) => {
      selectProject(project.project_id)
      onCreated?.()
      navigate('/settings')
    },
    onError: (err) =>
      setError(errorMessage(err, '프로젝트를 만들지 못했습니다. 잠시 후 다시 시도해 주세요.')),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) {
      setError('프로젝트 이름을 입력해 주세요.')
      return
    }
    setError('')
    mutation.mutate()
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 text-left" noValidate>
      <label className="block">
        <span className="mb-1.5 block text-[12px] text-foreground-500">프로젝트 이름</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={MAX_PROJECT_NAME_LENGTH}
          placeholder="예: 쇼핑몰 구축"
          autoFocus
          className="h-10 w-full rounded-md border border-background-600/70 bg-background-800/50 px-3 text-[13.5px] text-foreground-100 outline-none transition focus:border-primary-500/60"
        />
      </label>
      {error && (
        <p className="flex items-center gap-1.5 rounded-md border border-red-400/30 bg-red-400/10 px-2.5 py-2 text-[12px] text-red-200">
          <i className="ri-error-warning-line text-[13px]" /> {error}
        </p>
      )}
      <button
        type="submit"
        disabled={mutation.isPending}
        className="h-10 w-full cursor-pointer whitespace-nowrap rounded-md bg-foreground-50 text-[13.5px] font-medium text-background-950 transition hover:bg-foreground-100 disabled:cursor-default disabled:opacity-60"
      >
        {mutation.isPending ? '만드는 중…' : '프로젝트 만들기'}
      </button>
    </form>
  )
}

export default CreateProjectForm
