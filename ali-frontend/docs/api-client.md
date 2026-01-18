# API Client Library

The `apiClient` is a type-safe HTTP client for interacting with the ALI backend.

## Installation

The library is included in the frontend at `src/lib/api-client/`.

## Basic Usage

```typescript
import { apiClient } from '@/lib/api-client';

// GET request
const result = await apiClient.get('/tutorials/123');

if (result.ok) {
  console.log(result.data); // Tutorial data
} else {
  console.error(result.error.message);
}
```

---

## Result Pattern

All API calls return a `Result<T>` discriminated union:

```typescript
type Result<T> = 
  | { ok: true; data: T }
  | { ok: false; error: ApiError };

interface ApiError {
  code: string;          // e.g., 'NETWORK_ERROR', 'VALIDATION_ERROR'
  message: string;       // Human-readable message
  status?: number;       // HTTP status code
  retriable: boolean;    // Whether retry might help
  details?: unknown;     // Additional error context
}
```

### Handling Results

```typescript
const result = await apiClient.get<Tutorial>('/tutorials/123');

if (result.ok) {
  // TypeScript knows result.data is Tutorial
  setTutorial(result.data);
} else {
  // TypeScript knows result.error is ApiError
  if (result.error.retriable) {
    // Can retry the request
  }
  showError(result.error.message);
}
```

---

## Request Options

### POST with Body

```typescript
const result = await apiClient.post('/tutorials', {
  body: { title: 'New Tutorial', topic: 'Marketing' }
});
```

### Path Parameters

```typescript
const result = await apiClient.delete('/competitors/{name}', {
  pathParams: { name: 'CompetitorCo' }
});
```

### Query Parameters

```typescript
const result = await apiClient.get('/mentions', {
  queryParams: { max_results: 20, topic: 'sustainability' }
});
```

### Custom Timeout

```typescript
const result = await apiClient.post('/long-running-task', {
  body: data,
  config: { timeout: 120000 } // 2 minutes
});
```

---

## RequestState Helper

For managing loading/success/error states in components:

```typescript
import { RequestState } from '@/lib/api-client';

const [state, setState] = useState<RequestState<Data>>(RequestState.idle());

// Start loading
setState(RequestState.loading());

// Get result
const result = await apiClient.get('/data');

// Convert result to state
setState(RequestState.fromResult(result));
```

### State Values

| Value | Description |
|-------|-------------|
| `idle` | Initial state, no request made |
| `loading` | Request in progress |
| `success` | Request succeeded, data available |
| `error` | Request failed, error available |
| `empty` | Request succeeded but no data (e.g., empty list) |

### Rendering States

```tsx
import { renderRequestState } from '@/lib/api-client';

{renderRequestState(state, {
  idle: () => <InitialView />,
  loading: () => <Spinner />,
  success: (data) => <DataView data={data} />,
  error: (err) => <ErrorMessage message={err.message} />,
  empty: () => <EmptyState />,
})}
```

---

## Error Codes

| Code | Description | Retriable |
|------|-------------|-----------|
| `NETWORK_ERROR` | Connection failed | ✅ |
| `TIMEOUT` | Request timed out | ✅ |
| `RATE_LIMITED` | Too many requests | ✅ |
| `UNAUTHORIZED` | Token expired/invalid | ❌ |
| `FORBIDDEN` | No permission | ❌ |
| `NOT_FOUND` | Resource not found | ❌ |
| `VALIDATION_ERROR` | Invalid request body | ❌ |
| `SERVER_ERROR` | Backend error (5xx) | ✅ |

---

## Migration from axios

Replace `api` (axios) calls with `apiClient`:

```typescript
// Before (axios)
try {
  const res = await api.get('/tutorials/123');
  setData(res.data);
} catch (err) {
  setError(err.message);
}

// After (apiClient)
const result = await apiClient.get('/tutorials/123');
if (result.ok) {
  setData(result.data);
} else {
  setError(result.error.message);
}
```

Key differences:
- No try/catch needed
- Errors are in `.error`, not thrown
- Discriminated union for type safety
- Built-in `retriable` flag for retry logic
