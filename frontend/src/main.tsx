import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router/dom'
import { queryClient } from './api/queryClient'
import { router } from './router'
// 글꼴 Pretendard (SIL OFL 1.1). 화면에 쓰인 글자 범위의 파일만 내려받는다
import './assets/fonts/pretendard/pretendardvariable-dynamic-subset.css'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
