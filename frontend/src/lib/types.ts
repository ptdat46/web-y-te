// Shared domain types matching the Django REST API

export type Role = 'PATIENT' | 'DOCTOR' | 'ADMIN'

export interface User {
  id: number
  avatar_url?: string
  username: string
  email: string
  first_name: string
  last_name: string
  role: Role
  role_display: string
  is_active: boolean
  must_change_password: boolean
  email_verified: boolean
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
  address?: string
  bio: string
  years_of_experience: number
  is_verified: boolean
  academic_title?: string
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
  weight_kg?: number | null
  blood_glucose?: number | null
  recorded_at: string
  notes: string
  is_abnormal: boolean
  created_at: string
  updated_at: string
}

export interface PatientProfile {
  id?: number
  user?: User
  phone?: string
  address?: string
  date_of_birth?: string | null
  gender?: string
  emergency_contact?: string
  blood_type?: string
  allergies?: string
  underlying_conditions?: string
  current_medications?: string
  avatar_url?: string
  updated_at?: string
}

export interface HealthFile {
  id: number
  name: string
  original_name?: string
  file_name?: string
  file_url?: string
  url?: string
  category?: string
  description?: string
  size?: number
  uploaded_at?: string
  created_at?: string
}

export interface Medication {
  id: number
  name: string
  dosage?: string
  frequency?: string
  instructions?: string
  start_date?: string
  end_date?: string | null
  reminder_time?: string | null
  reminder_enabled?: boolean
  reminder_times?: string[]
  is_active?: boolean
  taken_today?: boolean
}

export interface Appointment {
  id: number
  doctor?: DoctorProfile | PublicUser
  patient?: PublicUser
  scheduled_at: string
  duration_minutes?: number
  reason?: string
  notes?: string
  status: string
  location?: string
}

export interface ChatRoom {
  id: number
  name?: string
  doctor?: DoctorProfile | PublicUser
  patient?: PublicUser
  last_message?: ChatMessage
  updated_at?: string
}

export interface ChatMessage {
  id: number
  room?: number
  sender?: PublicUser
  content: string
  attachment?: string | null
  attachment_url?: string | null
  created_at: string
}

export interface Notification {
  id: number
  notification_type: 'ALERT' | 'MEDICAL_RECORD' | 'CONNECTION' | 'SYSTEM'
  notification_type_label: string
  title: string
  message: string
  link: string
  is_read: boolean
  created_at: string
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

export interface PatientSummary {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
  full_name: string
  vitals_count: number
  records_count: number
  open_alerts_count: number
  latest_vital_at: string | null
}

export interface PatientSummaryBlock {
  vitals_count: number
  records_count: number
  open_alerts_count: number
  latest_vital_at: string | null
}

export interface PatientDetail {
  patient: PublicUser
  summary: PatientSummaryBlock
  latest_vital: VitalSign | null
  recent_alerts: Alert[]
  recent_records: MedicalRecord[]
}

export const ROLE_LABEL: Record<Role, string> = {
  PATIENT: 'Bệnh nhân',
  DOCTOR: 'Bác sĩ',
  ADMIN: 'Quản trị viên',
}