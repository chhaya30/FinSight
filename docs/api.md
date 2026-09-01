# API Reference

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently using API key header (to be implemented):
```
Authorization: Bearer <token>
```

## Endpoints

### Health Checks

#### GET /health
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "app": "globalrisk-ai",
  "version": "0.1.0",
  "environment": "development"
}
```

#### GET /health/db
Database connectivity check.

#### GET /health/ready
Kubernetes readiness probe.

#### GET /health/live
Kubernetes liveness probe.

---

### Companies

#### POST /companies
Create a new company.

**Request Body:**
```json
{
  "name": "Company Name",
  "sector": "Technology",
  "market_cap": 1000000.0,
  "listed_exchange": "NSE",
  "workspace_id": "uuid"
}
```

#### GET /companies
List companies with pagination.

**Query Parameters:**
- `sector` (optional): Filter by sector
- `exchange` (optional): Filter by exchange
- `search` (optional): Search by name
- `page` (default: 1): Page number
- `page_size` (default: 20): Items per page

#### GET /companies/{company_id}
Get company details with statistics.

#### PATCH /companies/{company_id}
Update company.

#### DELETE /companies/{company_id}
Delete company.

#### GET /companies/{company_id}/reports
Get all reports for a company.

#### GET /companies/sectors/list
Get list of all sectors.

#### GET /companies/exchanges/list
Get list of all exchanges.

---

### Documents

#### POST /documents/upload
Upload an annual report PDF.

**Form Data:**
- `file`: PDF file
- `company_id`: Company UUID
- `fiscal_year`: Fiscal year (integer)

#### GET /documents
List documents with filters.

**Query Parameters:**
- `company_id` (optional)
- `fiscal_year` (optional)
- `status` (optional): pending, processing, completed, failed
- `page`, `page_size`

#### GET /documents/{document_id}
Get document details.

#### GET /documents/{document_id}/status
Get processing status.

#### POST /documents/{document_id}/reprocess
Reprocess a document.

#### DELETE /documents/{document_id}
Delete a document.

---

### Risk Analysis

#### POST /analysis/extract
Extract risks from a processed report.

**Request Body:**
```json
{
  "report_id": "uuid",
  "force_reprocess": false
}
```

#### GET /analysis/{report_id}/risks
Get risks for a report.

**Query Parameters:**
- `category` (optional)
- `severity` (optional)
- `min_confidence` (optional, 0-1)
- `page`, `page_size`

#### GET /analysis/risks/{risk_id}
Get risk details.

#### GET /analysis/company/{company_id}/risks
Get all risks for a company across reports.

#### GET /analysis/categories/stats
Get risk category distribution.

**Query Parameters:**
- `company_id` (optional)
- `fiscal_year` (optional)

#### GET /analysis/severity/stats
Get severity distribution.

---

### Risks

#### GET /risks
List all risks with filters.

**Query Parameters:**
- `company_id`, `report_id`
- `category`, `severity`
- `min_confidence`
- `fiscal_year`
- `page`, `page_size`

#### GET /risks/{risk_id}
Get risk details.

#### GET /risks/{risk_id}/evolution
Get evolution history for a risk.

#### GET /risks/stats/summary
Get risk summary statistics.

#### GET /risks/stats/trends
Get risk trends over years.

**Query Parameters:**
- `company_id` (required)
- `years` (default: 5)

---

### Comparison

#### POST /comparison/compare
Compare risks between two years.

**Request Body:**
```json
{
  "company_id": "uuid",
  "year_current": 2024,
  "year_previous": 2023,
  "similarity_threshold": 0.85
}
```

#### GET /comparison/{company_id}/evolution
Get evolution between two years.

**Query Parameters:**
- `year_current` (required)
- `year_previous` (required)

#### GET /comparison/{company_id}/summary
Get evolution summary.

#### GET /comparison/{company_id}/timeline
Get risk count timeline.

**Query Parameters:**
- `category` (optional)
- `years` (default: 5)

---

### Reports & Intelligence

#### POST /reports/executive-summary
Generate executive summary.

**Request Body:**
```json
{
  "company_id": "uuid",
  "year": 2024,
  "include_evolution": true,
  "include_financial": true,
  "include_news": true
}
```

#### GET /reports/{company_id}/financial-health
Get financial health analysis.

**Query Parameters:**
- `fiscal_year` (optional)

#### POST /reports/peer-comparison
Compare with peers.

**Request Body:**
```json
{
  "company_id": "uuid",
  "peer_company_ids": ["uuid"],
  "sector": "Technology",
  "metrics": ["revenue", "profit", "net_margin"]
}
```

#### GET /reports/{company_id}/risk-explorer
Screen risks across companies.

**Query Parameters:**
- `category` (optional)
- `severity` (optional)

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error description",
  "status_code": 400
}
```

Common status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `500` - Internal Server Error

---

## Rate Limiting
To be implemented.