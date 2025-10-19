import { useState, useEffect, useRef, useCallback } from 'react'

interface UseCountUpOptions {
  start?: number
  end: number
  duration?: number // milliseconds
  decimals?: number
  startOnInView?: boolean
  threshold?: number
}

/**
 * Custom hook that animates counting up from start to end value
 */
export function useCountUp({
  start = 0,
  end,
  duration = 2000,
  decimals = 0,
  startOnInView = false,
  threshold = 0.3,
}: UseCountUpOptions) {
  const [count, setCount] = useState(start)
  const [hasAnimated, setHasAnimated] = useState(false)
  const elementRef = useRef<HTMLDivElement>(null)
  const countRef = useRef(start)
  const rafRef = useRef<number | undefined>(undefined)
  const startTimeRef = useRef<number | undefined>(undefined)

  const animate = useCallback(
    (timestamp: number = performance.now()) => {
      if (!startTimeRef.current) {
        startTimeRef.current = timestamp
      }

      const progress = Math.min((timestamp - startTimeRef.current) / duration, 1)
      const currentCount = start + (end - start) * progress

      countRef.current = currentCount
      setCount(parseFloat(currentCount.toFixed(decimals)))

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      }
    },
    [start, end, duration, decimals]
  )

  useEffect(() => {
    if (!startOnInView || hasAnimated) {
      animate()
      return () => {
        if (rafRef.current) {
          cancelAnimationFrame(rafRef.current)
        }
      }
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasAnimated) {
            setHasAnimated(true)
            animate()
          }
        })
      },
      { threshold }
    )

    if (elementRef.current) {
      observer.observe(elementRef.current)
    }

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current)
      }
      observer.disconnect()
    }
  }, [animate, startOnInView, threshold, hasAnimated])

  return { count, ref: elementRef }
}
