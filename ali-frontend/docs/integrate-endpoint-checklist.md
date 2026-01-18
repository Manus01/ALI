# How to Integrate a New Endpoint in 10 Minutes

This checklist helps you integrate any Brand Monitoring endpoint consistently using the Integration Accelerator pattern.

---

## Prerequisites

- [ ] Endpoint exists in the backend (`brand_monitoring.py`)
- [ ] Endpoint is registered in `endpoints.ts` (check integration status)
- [ ] You know which feature module it belongs to

---

## Step 1: Update Endpoint Registry (1 minute)

Mark the endpoint as integrated in `src/lib/brand-monitoring/endpoints.ts`:

```typescript
checkForDeepfake: {
  method: 'POST',
  path: '/brand-monitoring/deepfake-check',
  module: 'Threats',
  integrated: true, // ✅ Changed from false
  description: 'AI analysis for potential synthetic/deepfake media',
},
```

---

## Step 2: Add TypeScript Types (2 minutes)

If the types don't exist, add them to `src/lib/brand-monitoring/types.ts`:

```typescript
// Request type (if POST/PUT)
export interface DeepfakeCheckRequest {
  content: {
    title?: string;
    url: string;
    content_snippet?: string;
    media_url?: string;
  };
}

// Response type
export interface DeepfakeCheckResponse {
  is_likely_synthetic: boolean;
  confidence: number;
  indicators: string[];
  analysis: string;
  recommended_action?: string;
}
```

> **Tip**: Match the Pydantic models in the backend for consistency.

---

## Step 3: Create API Function (2 minutes)

Create or update `src/lib/brand-monitoring/modules/{module}/api.ts`:

```typescript
import { brandMonitoringApi } from '../../client';
import { BRAND_MONITORING_ENDPOINTS } from '../../endpoints';
import type { Result } from '../../../api-client';
import type { DeepfakeCheckRequest, DeepfakeCheckResponse } from '../../types';

export async function checkForDeepfake(
  request: DeepfakeCheckRequest
): Promise<Result<DeepfakeCheckResponse>> {
  const { path } = BRAND_MONITORING_ENDPOINTS.checkForDeepfake;
  
  return brandMonitoringApi.post<DeepfakeCheckResponse>(path, {
    body: request,
    config: {
      timeout: 60000, // Optional: longer timeout for AI processing
    },
  });
}
```

---

## Step 4: Create Hook/Composable (3 minutes)

For React, create `hooks.ts`:

```typescript
import { useState, useCallback } from 'react';
import { RequestState } from '../../../api-client';
import { checkForDeepfake } from './api';
import type { DeepfakeCheckResponse } from '../../types';

export function useDeepfakeCheck() {
  const [state, setState] = useState<RequestState<DeepfakeCheckResponse>>(
    RequestState.idle()
  );

  const check = useCallback(async (content: DeepfakeCheckRequest['content']) => {
    setState(RequestState.loading());
    const result = await checkForDeepfake({ content });
    setState(RequestState.fromResult(result));
  }, []);

  const reset = useCallback(() => {
    setState(RequestState.idle());
  }, []);

  return { state, check, reset };
}
```

For Vue/Svelte, create equivalent composable/store following the same pattern.

---

## Step 5: Export from Module Index (1 minute)

Update `src/lib/brand-monitoring/modules/{module}/index.ts`:

```typescript
export { checkForDeepfake } from './api';
export { useDeepfakeCheck } from './hooks';
```

---

## Step 6: Use in Component (1 minute)

```tsx
import { useDeepfakeCheck } from '@/lib/brand-monitoring/modules/threats';
import { renderRequestState } from '@/lib/api-client';

function DeepfakeChecker({ mention }) {
  const { state, check } = useDeepfakeCheck();

  return (
    <>
      <button onClick={() => check(mention)}>
        Check for Deepfake
      </button>
      
      {renderRequestState(state, {
        loading: () => <Spinner />,
        success: (data) => <DeepfakeResult result={data} />,
        error: (err) => <ErrorMessage message={err.message} />,
      })}
    </>
  );
}
```

---

## Quick Reference

### Result Type Pattern
```typescript
const result = await api.get<MyType>('/path');

if (result.ok) {
  // result.data is MyType
  console.log(result.data);
} else {
  // result.error is ApiError
  console.error(result.error.message);
  
  if (result.error.retriable) {
    // Can retry
  }
}
```

### RequestState Pattern
```typescript
// States: 'idle' | 'loading' | 'success' | 'error' | 'empty'

// Check status
if (state.status === 'success') {
  console.log(state.data);
}

// Use factory
setState(RequestState.loading());
setState(RequestState.success(data));
setState(RequestState.error(error));
setState(RequestState.fromResult(result));
```

### Path Parameters
```typescript
// For endpoints like /brand-monitoring/competitors/{name}
await api.delete('/brand-monitoring/competitors/{name}', {
  pathParams: { name: 'CompetitorCo' },
});
```

### Query Parameters
```typescript
await api.get('/brand-monitoring/mentions', {
  queryParams: { 
    max_results: 20,
    topic: 'sustainability',
  },
});
```

---

## Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `UNAUTHORIZED` | Token expired | User will be auto-redirected to login |
| `VALIDATION_ERROR` | Invalid request body | Check request matches Pydantic model |
| `NOT_FOUND` | Wrong endpoint path | Verify path in endpoint registry |
| `TIMEOUT` | Long-running request | Increase timeout in config |
| `NETWORK_ERROR` | Connection failed | Check internet, retry if `retriable: true` |

---

## Checklist Summary

- [ ] Update endpoint registry (`integrated: true`)
- [ ] Add TypeScript types if missing
- [ ] Create API function with `brandMonitoringApi`
- [ ] Create hook using `RequestState`
- [ ] Export from module index
- [ ] Use in component with `renderRequestState`
- [ ] Test happy path and error cases

**Estimated Time: 10 minutes** ⏱️
