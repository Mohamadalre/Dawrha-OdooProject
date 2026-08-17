# Recycle WMS — API Endpoints Reference

> Auto-generated reference for all HTTP endpoints in the `recycle_warehouse` module.

---

## 1. REST API (Public) — `api.py`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/recycle/products` | Public | List all active products |
| POST | `/api/recycle/orders` | Public (API Key) | Create an order from Next.js |
| GET | `/api/recycle/orders/<id>` | Public (API Key) | Get order details |

**Authentication:** API Key via `X-API-KEY` header (configured in System Parameters).

---

## 2. Attendance API — `attendance_api.py`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/login` | Public | Login with email/password, returns Bearer token |
| POST | `/api/attendance/check-in` | Bearer Token | Check in (GPS + photo optional) |
| POST | `/api/attendance/check-out` | Bearer Token | Check out |

**Authentication:** Bearer token from `/api/login`.

---

## 3. Dashboard API — `dashboard_api.py`

### 3.1 Admin Dashboard

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/recycle/dashboard-stats` | Admin | Full dashboard KPI data (period-filtered) |
| POST | `/api/recycle/registered-users` | Admin | List registered users with roles |
| POST | `/api/recycle/shift/validate-times` | Admin | Validate shift start/end times |
| POST | `/api/recycle/shift/available-employees` | Admin | Employees assignable to a shift |
| POST | `/api/recycle/shift/create` | Admin | Create a new shift |
| POST | `/api/recycle/shift/update` | Admin | Update shift name/times/tolerance |
| POST | `/api/recycle/shift/delete` | Admin | Delete a shift |
| POST | `/api/recycle/my-profile` | User | Get current user profile |
| POST | `/api/recycle/save-profile` | User | Save profile changes |

### 3.2 Manager Dashboard

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/manager/dashboard` | Manager | Manager dashboard stats (period-filtered) |
| POST | `/api/manager/employees` | Manager | List employees in warehouse |
| POST | `/api/manager/warehouse-shifts` | Manager | List shifts for warehouse |
| POST | `/api/manager/employee/update` | Manager | Update employee details |
| POST | `/api/manager/employee/create` | Manager | Create new employee + send invite |

### 3.3 Output Employee API

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/output/dashboard` | Output | Dashboard stats + pending orders |
| POST | `/api/output/orders` | Output | List orders (with optional state filter) |
| POST | `/api/output/order/<id>` | Output | Order detail with lines |
| POST | `/api/output/order/reserve` | Output | Reserve order for processing |
| POST | `/api/output/order/complete` | Output | Complete order + deduct stock + invoice |
| POST | `/api/output/order/cancel` | Output | Cancel a pending order |
| POST | `/api/output/storage-zones` | Output | List storage zones for warehouse |
| GET | `/api/output/order/<id>/print-invoice` | Output | Download invoice PDF |

### 3.4 Test/Dev Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/test/create-shipment` | Admin | Create test shipment |
| POST | `/api/test/create-order` | Admin | Create test order |
| POST | `/api/test/create-category` | Admin | Create test product category |
| POST | `/api/test/create-product` | Admin | Create test product |
| POST | `/api/output/order/create-test` | Output | Create single test order |
| POST | `/api/output/order/create-test-batch` | Output | Create batch of test orders |

### 3.5 Barcode/Receiving

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/receiving/scan-barcode` | Input | Process barcode scan for shipment |

---

## 4. Website Routes — `website.py`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | Public | Homepage |
| GET | `/about` | Public | About page |
| GET | `/jobs` | Public | Job listings |
| GET | `/jobs/<id>` | Public | Job detail |
| GET | `/jobs/apply/<id>` | User | Job application form |
| POST | `/jobs/apply/<id>/complete-profile` | User | Submit application + complete profile |
| GET | `/account` | User | User dashboard |
| GET | `/account/change-password` | User | Change password form |
| POST | `/account/save-nid` | User | Save national ID |
| POST | `/account/edit-profile` | User | Edit profile fields |
| GET | `/profile/complete` | User | Complete profile form |
| GET | `/my/jobs` | User | My job applications |
| GET | `/my/applications` | User | My applications list |
| GET | `/contact` | Public | Contact page |
| GET | `/register` | Public | Registration form |
| POST | `/verify-email` | Public | Email verification |
| POST | `/verify-email/resend` | Public | Resend verification email |
| GET | `/recycle/open-dashboard` | User | Redirect to appropriate dashboard |

---

## 5. Authentication Flow

1. **Website login:** `/web/login` → session cookie
2. **Mobile API login:** POST `/api/login` → Bearer token
3. **Dashboard access:** Session cookie required for all `/api/output/*`, `/api/manager/*`, `/api/recycle/*` endpoints
4. **REST API access:** `X-API-KEY` header for `/api/recycle/products`, `/api/recycle/orders`

---

## 6. Data Models

| Model | Description |
|-------|-------------|
| `recycle.product` | Recyclable product (name, category, prices, weight) |
| `recycle.product.category` | Product category (unique name) |
| `recycle.warehouse` | Warehouse (14 governorates, zones) |
| `recycle.zone` | Warehouse zone (receiving/sorting/storage/dispatch) |
| `recycle.stock` | Per-warehouse product stock |
| `recycle.shipment` | Incoming shipment (7 states) |
| `recycle.shipment.line` | Shipment line item |
| `recycle.order` | Customer order (pending→processing→ready→completed) |
| `recycle.order.line` | Order line item |
| `recycle.shift` | Work shift with time windows |
| `recycle.attendance` | Employee check-in/out |
| `recycle.notification` | Dashboard notification |
| `recycle.backend.sync` | NestJS backend sync |
