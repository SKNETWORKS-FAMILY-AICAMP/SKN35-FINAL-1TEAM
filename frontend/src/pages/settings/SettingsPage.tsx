import DepartmentsPanel from '../../components/DepartmentsPanel'
import { formatDate, PROJECT_STATUS_LABEL } from '../../api/project'
import { useCurrentUser } from '../../hooks/useAuth'
import AddMemberForm from './AddMemberForm'
import CreateTeamForm from './CreateTeamForm'
import TeamList from './TeamList'

function SettingsPage() {
  const { user, project } = useCurrentUser()
  const isOwner = project.my_role === 'OWNER'
  // LEADER 는 자기 팀에 MEMBER 만 추가할 수 있다
  const canAddMembers = isOwner || project.my_role === 'LEADER'

  return (
    <div className="mx-auto w-full max-w-[1120px] space-y-12 pb-16">
      <section className="animate-fade-up">
        <p className="overline">
          조직 관리 · {PROJECT_STATUS_LABEL[project.status]} · {formatDate(project.created_at)} 시작
        </p>
        <h1 className="mt-4 font-heading text-[30px] font-light leading-[1.15] tracking-[-0.03em] text-foreground-50 md:text-[38px]">
          {project.name}
        </h1>
        <p className="mt-3 max-w-xl text-[14.5px] leading-[1.8] text-foreground-400">
          팀과 멤버를 구성합니다. 팀은 영향 팀 알림의 단위가 되고, 승인권자로 지정한 팀장이 제출본을
          승인합니다.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="font-heading text-[20px] text-foreground-50">팀 · 멤버</h2>
        <TeamList />
      </section>

      {(isOwner || canAddMembers) && (
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {isOwner && (
            <div className="panel p-6">
              <h3 className="text-[15px] text-foreground-100">팀 만들기</h3>
              <p className="mt-1 text-[12.5px] text-foreground-500">
                대표 팀장을 함께 지정합니다. 팀장은 이 프로젝트의 다른 팀에 속하지 않은 직원이어야
                합니다.
              </p>
              <div className="mt-4">
                <CreateTeamForm />
              </div>
            </div>
          )}
          {canAddMembers && (
            <div className="panel p-6">
              <h3 className="text-[15px] text-foreground-100">멤버 추가</h3>
              <p className="mt-1 text-[12.5px] text-foreground-500">
                {isOwner
                  ? '모든 팀에 팀장·팀원을 추가할 수 있습니다. 승인권자는 팀장만 지정할 수 있습니다.'
                  : '내 팀에 팀원을 추가할 수 있습니다.'}
              </p>
              <div className="mt-4">
                <AddMemberForm />
              </div>
            </div>
          )}
        </section>
      )}

      <section className="space-y-4">
        <h2 className="font-heading text-[20px] text-foreground-50">회사 부서</h2>
        <p className="text-[12.5px] text-foreground-500">
          직원은 가입할 때 이 목록에서 부서를 고릅니다.
          {user.user_type === 'ADMIN' ? '' : ' 부서 등록은 회사 관리자만 할 수 있습니다.'}
        </p>
        <DepartmentsPanel canCreate={user.user_type === 'ADMIN'} />
      </section>
    </div>
  )
}

export default SettingsPage
