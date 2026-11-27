import { queryOptions } from '@tanstack/react-query'

import { request } from './client'

export type UserLevel = 'LIMITED' | 'MANAGER' | 'ADMIN'

// 프로젝트를 만들 수 있는 등급 (backend/app/projects/service.py 의 PROJECT_CREATOR_LEVELS)
export const PROJECT_CREATOR_LEVELS: UserLevel[] = ['MANAGER', 'ADMIN']

// backend/app/organizations/schemas.py
export interface CompanyUser {
  user_id: number
  dept_id: number | null
  name: string
  email: string
  user_type: UserLevel
}

export interface Department {
  dept_id: number
  name: string
  description: string | null
}

export interface DepartmentCreateRequest {
  name: string
  description: string
}

export function getCompanyUsers() {
  return request<{ users: CompanyUser[] }>('/companies/users')
}

export const organizationQueries = {
  users: () =>
    queryOptions({
      queryKey: ['companies', 'users'],
      queryFn: getCompanyUsers,
      select: (data) => data.users,
    }),
  departments: () =>
    queryOptions({
      queryKey: ['companies', 'departments'],
      queryFn: () => request<{ departments: Department[] }>('/companies/departments'),
      select: (data) => data.departments,
    }),
}

// 부서 생성: ADMIN 만 가능
export function createDepartment(body: DepartmentCreateRequest) {
  return request<Department>('/companies/departments', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
