import { useMemo } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Custom hook for React Router v5 that mimics React Router v6's useSearchParams
 * Returns a URLSearchParams object from the current location's search string
 */
export function useSearchParams(): URLSearchParams {
  const location = useLocation()

  return useMemo(() => {
    return new URLSearchParams(location.search)
  }, [location.search])
}
