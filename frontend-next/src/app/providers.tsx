'use client'

import { ReactNode, useEffect } from 'react'
import { usePipelineStore } from '@/store/pipeline-store'
import { setMockMode as setApiMockMode } from '@/services/api'
import { apiService } from '@/services/api'

const STORAGE_KEY = 'vidiolingua_mock_mode'

export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored !== null) {
      const useRealApi = stored === 'false'
      usePipelineStore.getState().setMockMode(!useRealApi)
      setApiMockMode(!useRealApi) // false = real API, true = mock
      return
    }
    // No preference yet: if backend is reachable, default to Real API
    apiService.healthCheck().then((r) => {
      if (r.status === 'ok') {
        usePipelineStore.getState().setMockMode(false)
        setApiMockMode(false)
        localStorage.setItem(STORAGE_KEY, 'false')
      }
    })
  }, [])

  return <>{children}</>
}
