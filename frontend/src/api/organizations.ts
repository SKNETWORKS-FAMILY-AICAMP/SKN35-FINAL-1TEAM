import { request } from './client'

export type UserLevel = 'LIMITED' | 'MANAGER' | 'ADMIN'

// backend/app/organizations/schemas.py
export interface CompanyUser {
  user_id: number
  dept_id: number | null
  name: string
  email: string
  user_type: UserLevel
}

export function getCompanyUsers() {
  return request<{ users: CompanyUser[] }>('/companies/users')
}
