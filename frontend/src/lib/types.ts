// Shared domain types matching the Django REST API

export type Role = 'PATIENT' | 'DOCTOR' | 'ADMIN'

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  role: Role
  role_display: string
  is_active: boolean
  must_change_password: boolean
}

export interface PublicUser {
  id: number
  username: string
  first_name: string
  last_name: string
  role_display: string
}

export interface DoctorProfile {
  id: number
  user: PublicUser
  full_name: string
  specialty: string
  hospital: string
  bio: string
  years_of_experience: number
  is_verified: boolean
}

export interface FullDoctorProfile extends DoctorProfile {
  user_id: number
  username: string
  email: string
  address: string
  phone: string
  created_at: string
  updated_at: string
}

export type ConnectionStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'BLOCKED'

export interface Connection {
  id: number
  doctor: DoctorProfile
  patient: PublicUser
  status: ConnectionStatus
  created_at: string
  updated_at: string
}

export interface Disease {
  id: number
  name_en: string
  name_vi: string
  is_active: boolean
}

export interface Symptom {
  id: number
  name_en: string
  name_vi: string
  is_active: boolean
}

export interface MedicalRecord {
  id: number
  patient: PublicUser
  doctor: PublicUser
  disease: number | null
  disease_id?: number
  disease_name: string | null
  title: string
  notes: string
  diagnosis: string
  prescription: string
  created_at: string
  updated_at: string
}

export interface VitalSign {
  id: number
  patient: PublicUser
  patient_id?: number
  temperature: number | null
  heart_rate: number | null
  blood_pressure_sys: number | null
  blood_pressure_dia: number | null
  oxygen_saturation: number | null
  recorded_at: string
  notes: string
  is_abnormal: boolean
  created_at: string
  updated_at: string
}

export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED'

export interface Alert {
  id: number
  patient: PublicUser
  created_by: PublicUser
  title: string
  message: string
  severity: AlertSeverity
  status: AlertStatus
  related_vital: number | null
  created_at: string
  resolved_at: string | null
}

export interface AuditLogEntry {
  id: number
  actor: PublicUser | null
  action: string
  content_type: number
  content_type_name: string
  object_id: number
  summary: string
  details: string
  ip_address: string | null
  created_at: string
}

export const ROLE_LABEL: Record<Role, string> = {
  PATIENT: 'Bệnh nhân',
  DOCTOR: 'Bác sĩ',
  ADMIN: 'Quản trị viên',
}