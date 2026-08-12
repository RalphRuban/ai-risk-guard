import { useState, useEffect, useRef } from 'react'

export default function useCountUp(end, duration = 2000) {
  const [count, setCount] = useState(0)
  const startRef = useRef(null)

  useEffect(() => {
    if (end === 0) {
      setCount(0)
      return
    }

    startRef.current = performance.now()

    const frame = (now) => {
      const elapsed = now - startRef.current
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.floor(eased * end))
      if (progress < 1) {
        requestAnimationFrame(frame)
      }
    }

    requestAnimationFrame(frame)
  }, [end, duration])

  return count
}
