# 🔥 Firehorse Project Audit: Appendix
## Raw Data & Detailed Findings
## Generated: Jan 13 2026, 00:53 UTC

---

## 1. Frontend Raw Analysis

### File Structure (from /tmp/fe_analysis.txt)
```
=== FRONTEND STRUCTURE ===
Date: Tue Jan 13 00:41:54 UTC 2026

1️⃣ File structure mapping
src/App.css
src/App.tsx
src/index.css
src/main.tsx
src/assets/react.svg
src/components/Dashboard.tsx
src/components/OrdersTable.tsx
src/components/RecentActivity.tsx
src/components/RevenueChart.tsx
src/components/SystemHealthCard.tsx
src/hooks/useOrders.ts
src/services/api.ts
src/types/index.ts

Total files:
13

2️⃣ Entry point identification
=== main.tsx ===
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

=== App.tsx ===
import { ChakraProvider } from '@chakra-ui/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './components/Dashboard'
import './App.css'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider>
        <Dashboard />
      </ChakraProvider>
    </QueryClientProvider>
  )
}

export default App

3️⃣ Dependencies analysis
=== package.json dependencies ===
{
  "dependencies": {
    "@chakra-ui/react": "^2.8.0",
    "@emotion/react": "^11.11.1",
    "@emotion/styled": "^11.11.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0",
    "framer-motion": "^10.16.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.10.0"
  }
}

4️⃣ Build configuration
=== vite.config.ts ===
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})

=== tsconfig.json ===
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": false,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": false
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}

5️⃣ Build artifacts
=== dist/ directory ===
total 12K
drwxr-xr-x 2 root root 4.0K Jan 13 00:30 assets
-rw-r--r-- 1 root root  448 Jan 13 00:30 index.html
-rw-r--r-- 1 root root 1.5K Jan 13 00:26 vite.svg

6️⃣ Component audit
=== Components list ===
src/components/Dashboard.tsx
src/components/OrdersTable.tsx
src/components/RecentActivity.tsx
src/components/RevenueChart.tsx
src/components/SystemHealthCard.tsx

Total components:
5
```

---

## 2. Backend Raw Analysis

### API Structure (from /tmp/be_analysis.txt)
```
=== BACKEND STRUCTURE ===
Date: Tue Jan 13 00:42:35 UTC 2026

1️⃣ API structure mapping
total 44
drwxr-xr-x 8 root root 4096 Jan 12 23:58 .
drwxr-xr-x 1 root root 4096 Jan 13 00:30 ..
drwxr-xr-x 3 root root 4096 Jan  4 21:08 core
drwxr-xr-x 3 root root 4096 Jan  4 21:08 middleware
drwxr-xr-x 3 root root 4096 Jan  4 21:08 monitoring
drwxr-xr-x 2 root root 4096 Jan  4 21:08 prompts
drwxr-xr-x 3 root root 4096 Jan  4 21:08 services
-rw-r--r-- 1 root root 6148 Jan 12 23:58 .DS_Store
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.stats
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup2
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.broken
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.comments
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.example
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.tmp
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.1768122637
-rw-r--r-- 1 root root 6148 Jan  4 21:08 .DS_Store.backup.pooler.1768125193
