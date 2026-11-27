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

export interface Department {
  dept_id: number
  name: string
  description: string | null
}

export function getCompanyUsers() {
  return request<{ users: CompanyUser[] }>('/companies/users')
}

export function getDepartments() {
  return request<{ departments: Department[] }>('/companies/departments')
}
