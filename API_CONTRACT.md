# Firehorse MVP API Contract v1.0

## Base URL
- Production: `https://barsik.online/api`
- Development: `http://127.0.0.1:8000/api`

## Response Format (MANDATORY)

### Success Response
```json
{
  "success": true,
  "data": null,
  "error": null,
  "meta": {
    "timestamp": "2026-01-11T04:22:00Z",
    "version": "1.0",
    "trace_id": "uuid-string-here",
    "request_id": "req-123"
  }
}
```

### Error Response
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "User-friendly error message",
    "details": {}
  },
  "meta": {
    "timestamp": "2026-01-11T04:22:00Z",
    "version": "1.0",
    "trace_id": "uuid"
  }
}
```

## Endpoints

### 1. Core Order Management

#### POST /api/orders
Create order from webhook

**Request Body:**
```json
{
  "title": "Order title",
  "description": "Order description",
  "price": 100.0,
  "buyer_id": "buyer123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "order-uuid",
    "title": "Order title",
    "status": "queued",
    "created_at": "2026-01-11T04:22:00Z"
  },
  "error": null,
  "meta": {...}
}
```

#### GET /api/orders
List orders (pagination required)

**Query Parameters:**
- `page` (optional, default: 1)
- `limit` (optional, default: 20)
- `status` (optional)

**Response:**
```json
{
  "success": true,
  "data": {
    "orders": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "pages": 5
    }
  },
  "error": null,
  "meta": {...}
}
```

#### GET /api/orders/{id}
Get single order with details

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "order-uuid",
    "title": "Order title",
    "status": "processing",
    "price": 100.0,
    "created_at": "2026-01-11T04:22:00Z",
    "updated_at": "2026-01-11T04:22:00Z"
  },
  "error": null,
  "meta": {...}
}
```

#### PUT /api/orders/{id}
Update order status/metadata

**Request Body:**
```json
{
  "status": "completed",
  "metadata": {...}
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "order-uuid",
    "status": "completed",
    "updated_at": "2026-01-11T04:22:00Z"
  },
  "error": null,
  "meta": {...}
}
```

#### DELETE /api/orders/{id}
Cancel/delete order

**Response:**
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "id": "order-uuid"
  },
  "error": null,
  "meta": {...}
}
```

#### GET /api/orders/{id}/events
Get order timeline events

**Response:**
```json
{
  "success": true,
  "data": {
    "order_id": "order-uuid",
    "events": [
      {
        "id": "event-uuid",
        "stage": "created",
        "level": "info",
        "message": "Order created",
        "created_at": "2026-01-11T04:22:00Z"
      }
    ]
  },
  "error": null,
  "meta": {...}
}
```

### 2. Monitoring & Health

#### GET /api/health
Health check (response 200)

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database": "connected",
    "version": "1.0.0",
    "timestamp": "2026-01-11T04:22:00Z"
  },
  "error": null,
  "meta": {...}
}
```

#### GET /api/metrics
Prometheus metrics

**Response:** `text/plain` format

#### POST /webhook
Kwork webhook receiver (verify signature)

**Request Body:** Kwork webhook format

**Response:**
```json
{
  "success": true,
  "data": {
    "webhook_id": "uuid",
    "processed": true
  },
  "error": null,
  "meta": {...}
}
```

### 3. Dashboard & Analytics

#### GET /api/dashboard
Dashboard stats (orders count, totals, trends)

**Response:**
```json
{
  "success": true,
  "data": {
    "total_orders": 150,
    "pending_orders": 25,
    "completed_orders": 125,
    "total_revenue": 12500.0,
    "recent_orders": [...],
    "daily_trends": {...}
  },
  "error": null,
  "meta": {...}
}
```

#### GET /api/dashboard/stats
Detailed statistics

**Response:**
```json
{
  "success": true,
  "data": {
    "by_status": {...},
    "by_day": {...},
    "by_hour": {...},
    "average_price": 83.33
  },
  "error": null,
  "meta": {...}
}
```

## Error Codes

- `INVALID_REQUEST`: Invalid input parameters
- `NOT_FOUND`: Resource not found
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions
- `INTERNAL_SERVER_ERROR`: Server error
- `DATABASE_ERROR`: Database operation failed
- `VALIDATION_ERROR`: Data validation failed
- `RATE_LIMIT_EXCEEDED`: Too many requests
