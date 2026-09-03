# Health Care Monitor

Nền tảng theo dõi sức khỏe bệnh nhân và bác sĩ — base local development.

## Stack

- Backend: Django 5.1 + Django REST Framework + SimpleJWT (refresh rotation + blacklist)
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS (UI tiếng Việt)
- Database: MySQL 8.4
- Runtime: Docker Compose, đúng 3 services (`frontend`, `backend`, `database`)

> 📘 Người dùng Docker? Xem **[README-TRIEN-KHAI-DOCKER.md](README-TRIEN-KHAI-DOCKER.md)** —
> hướng dẫn từng bước cài Docker trên máy tính mới nguyên, triển khai, và giải thích toàn bộ mã nguồn.

Đã bao gồm: auth theo vai trò (PATIENT/DOCTOR/ADMIN), hồ sơ & tìm kiếm bác sĩ,
kết nối bác sĩ–bệnh nhân (request/approve), bệnh án, sinh hiệu, cảnh báo tự động,
audit log bất biến, chatbot định hướng triệu chứng (mock khi Ollama chưa sẵn sàng),
catalog 59 bệnh / 377 triệu chứng song ngữ.

## Chạy bằng Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1 (Vite proxy: http://localhost:5173/api/v1)
- Health check: http://localhost:8000/api/v1/health/

### Lần đầu: migrate + seed + catalog

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py import_catalog
docker compose exec backend python manage.py seed_demo
```

## Chạy local không dùng Docker

### Yêu cầu hệ thống

- Windows 10/11, PowerShell
- Python 3.12 hoặc mới hơn
- MySQL Server 8.0+ đang chạy tại `localhost:3306`
- Node.js 20+ và npm
- Ollama (tùy chọn, chỉ cần cho chatbot dùng LLM local)

Kiểm tra cài đặt:

```powershell
python --version
node --version
npm.cmd --version
mysql --version
```

### Cài MySQL

Cài MySQL Server, sau đó mở MySQL Shell hoặc MySQL Command Line Client và chạy:

```sql
CREATE DATABASE healthcare CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'healthcare'@'localhost' IDENTIFIED BY 'healthcare';
GRANT ALL PRIVILEGES ON healthcare.* TO 'healthcare'@'localhost';
FLUSH PRIVILEGES;
```

Nếu đã có database/user, không cần tạo lại. Backend mặc định dùng đúng cấu hình:
`healthcare / healthcare / localhost / 3306`.

### Cài và chạy backend

```powershell
cd H:\web-y-te\backend
python -m pip install -r requirements.txt

$env:DJANGO_DEBUG="1"
$env:DJANGO_SECRET_KEY="local-dev-key-change-me"
$env:DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1"
$env:MYSQL_DATABASE="healthcare"
$env:MYSQL_USER="healthcare"
$env:MYSQL_PASSWORD="healthcare"
$env:MYSQL_HOST="localhost"
$env:MYSQL_PORT="3306"

python manage.py migrate
python manage.py import_catalog
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

Giữ cửa sổ backend đang chạy. API: `http://localhost:8000/api/v1`.

### Cài và chạy frontend

Mở PowerShell thứ hai:

```powershell
cd H:\web-y-te\frontend
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Mở `http://localhost:5173`. Dùng `npm.cmd` trên Windows nếu PowerShell chặn
`npm.ps1` do Execution Policy.

Tài khoản demo:

| Tài khoản | Mật khẩu | Vai trò |
|---|---|---|
| `admin` | `admin-secure-pass-2026` | ADMIN |
| `dr.nguyen` | `Test1234!` | DOCTOR |
| `dr.le` | `Test1234!` | DOCTOR |
| `patient.tran` | `Test1234!` | PATIENT |

### Ollama local (tùy chọn)

Cài Ollama, tải model fine-tuned, rồi đặt biến môi trường trước khi chạy backend:

```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_MODEL="ten-model-fine-tuned"
$env:OLLAMA_TIMEOUT="60"
```

Chatbot gửi trực tiếp tin nhắn, lịch sử hội thoại, bệnh án, sinh hiệu và cảnh báo
của tài khoản hiện tại cho LLM. Backend không dùng danh sách từ khóa để diễn giải
triệu chứng. Khi Ollama không sẵn sàng, chatbot trả phản hồi dự phòng chung.

### Kiểm tra local

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/health/
cd H:\web-y-te\backend
python manage.py test accounts doctors chatbot core
cd H:\web-y-te\frontend
npm.cmd run build
```

Seed tạo tài khoản demo (chỉ dữ liệu giả, không dữ liệu thật):

| Account      | Password              | Vai trò |
|--------------|-----------------------|---------|
| `admin`      | `admin-secure-pass-2026` | ADMIN |
| `dr.nguyen`  | `Test1234!`           | DOCTOR (Tim mạch) |
| `dr.le`      | `Test1234!`           | DOCTOR (Thần kinh) |
| `patient.tran` | `Test1234!`         | PATIENT |

> Lưu ý: ngoài `admin`, các user khác do seed tạo. Đăng ký public chỉ tạo tài khoản PATIENT.

## API chính (`/api/v1`)

### Auth
- `POST /auth/register/` — username, email, password, first_name, last_name
- `POST /auth/login/` — trả `{user, access}`; refresh token đặt trong HttpOnly cookie
- `POST /auth/refresh/` — đọc cookie, rotation + blacklist, trả access mới
- `POST /auth/logout/`, `GET /auth/me/`

### Catalog (public)
- `GET /catalog/diseases/?search=`, `GET /catalog/symptoms/?search=`

### Doctors & connections
- `GET /doctors/?search=` — thư mục công khai (không lộ email/phone)
- `POST /doctors/me/` — bác sĩ tạo hồ sơ của mình
- `POST /connections/` — bệnh nhân gửi yêu cầu `{doctor_id, patient_id}`
- `GET /connections/?status=`, `POST /connections/{id}/respond/` (APPROVED/REJECTED)

### Bệnh án & theo dõi (object-level permission)
- `GET/POST /records/`, `GET/POST /vitals/`, `GET /alerts/`, `PATCH /alerts/{id}/status/`
- Bệnh nhân chỉ xem dữ liệu của mình; bác sĩ chỉ xem bệnh nhân đã kết nối (APPROVED); admin xem tất cả
- Vitals bất thường (nhiệt >38.5°/<35°, nhịp tim >120/<50, huyết áp >180/90, SpO₂ <90) tự tạo alert

### Admin
- `GET /audit-logs/?action=&actor=&content_type=` — nhật ký kiểm toán (ADMIN)

### Chatbot
- `POST /chat/conversations/`, `GET /chat/conversations/{id}/`
- `POST /chat/conversations/{id}/send/` — `{message}`; gửi tin nhắn và dữ liệu sức khỏe liên quan cho LLM
- Gọi Ollama nếu cấu hình; ngược lại dùng phản hồi dự phòng chung

## Cấu hình Ollama (tùy chọn)

Backend đọc env: `OLLAMA_BASE_URL` (local mặc định `http://localhost:11434`),
`OLLAMA_MODEL` (mặc định `qwen2.5:7b`), `OLLAMA_TIMEOUT` (giây). Ollama chạy ngoài Compose
để giữ đúng 3 container; khi chưa có model, chatbot vẫn hoạt động bằng mock reply.

## Tests

```bash
docker compose exec backend python manage.py test accounts doctors chatbot core
# Tests: register/login, role, connection approval, object permission, LLM routing, mock fallback
```

Frontend: `cd frontend && npm run build` (typecheck qua `npx tsc --noEmit`).

## Cấu trúc

```
backend/
  accounts/    custom User, auth views/serializers, seed_demo
  catalog/     Disease/Symptom + import_catalog (CSV)
  doctors/     DoctorProfile, DoctorPatientConnection, permissions
  care/        MedicalRecord, VitalSign, Alert, AuditLog
  chatbot/     Conversations, Ollama provider + mock fallback
  core/        health endpoint, URL wiring tests
  config/      settings (JWT, CORS, MySQL), urls
frontend/
  src/lib/     api client (auto-refresh), auth context, types
  src/components/ Layout (sidebar theo vai trò), UI primitives
  src/pages/   Login, Register, Dashboard, Vitals, Records, Alerts, Doctors, Connections, Audit, Chatbot
docker-compose.yml   3 services + MySQL volume
```

## Lưu ý y tế

Đây là nền tảng kỹ thuật, không phải công cụ chẩn đoán. Không dùng dữ liệu bệnh nhân thật
trong môi trường local. Trước production cần consent, retention, backup mã hóa, HTTPS,
MFA, object-level authorization thẩm định và chính sách tuân thủ dữ liệu y tế (ví dụ
quy định về dữ liệu sức khỏe tại Việt Nam nếu áp dụng).
