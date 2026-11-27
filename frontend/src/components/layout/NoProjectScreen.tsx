import { useQuery } from '@tanstack/react-query'

import { authQueries } from '../../api/auth'
import { PROJECT_CREATOR_LEVELS } from '../../api/organizations'
import CreateProjectForm from '../CreateProjectForm'
import DepartmentsPanel from '../DepartmentsPanel'

interface NoProjectScreenProps {
  onLogout: () => void
}

// 참여 중인 프로젝트가 없을 때. MANAGER·ADMIN 은 여기서 첫 프로젝트를, ADMIN 은 부서도 만든다
function NoProjectScreen({ onLogout }: NoProjectScreenProps) {
  const { data: user } = useQuery(authQueries.me())
  const canCreateProject = !!user && PROJECT_CREATOR_LEVELS.includes(user.user_type)
  const isAdmin = user?.user_type === 'ADMIN'

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-4 py-12 text-center">
      <p className="overline">no project</p>
      <h1 className="font-heading text-[24px] font-light text-foreground-50">
        {canCreateProject ? '첫 프로젝트를 만들어 주세요' : '참여 중인 프로젝트가 없습니다'}
      </h1>
      <p className="text-[13.5px] text-foreground-500">
        {canCreateProject
          ? '프로젝트를 만들면 오너가 되어 팀과 멤버를 구성할 수 있습니다.'
          : '프로젝트 오너에게 멤버 추가를 요청해 주세요.'}
      </p>

      {canCreateProject && (
        <div className="panel mt-4 w-full max-w-[420px] p-6">
          <CreateProjectForm />
        </div>
      )}

      {isAdmin && (
        <div className="panel mt-2 w-full max-w-[420px] p-6">
          <p className="mb-3 text-left text-[14px] text-foreground-100">회사 부서</p>
          <DepartmentsPanel canCreate />
        </div>
      )}

      <button
        type="button"
        onClick={onLogout}
        className="mt-4 h-9 cursor-pointer rounded-md border border-background-600/80 px-4 text-[13px] text-foreground-200 transition hover:bg-background-800/60"
      >
        로그아웃
      </button>
    </div>
  )
}

export default NoProjectScreen
