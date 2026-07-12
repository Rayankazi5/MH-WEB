import { useState, useCallback } from 'react'
import { api, Question, SessionStatusResponse } from '@/services/api'

type SessionState = 'idle' | 'active' | 'submitting' | 'scoring' | 'done' | 'abstained' | 'error'

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [state, setState] = useState<SessionState>('idle')
  const [result, setResult] = useState<SessionStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const startSession = useCallback(async () => {
    setState('active')
    setCurrentIndex(0)
    setError(null)
    try {
      const res = await api.patient.startSession()
      setSessionId(res.session_id)
      setQuestions(res.questions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start session')
      setState('error')
    }
  }, [])

  const submitAnswer = useCallback(
    async (rawValue: unknown, responseTimeMs: number) => {
      if (!sessionId || currentIndex >= questions.length) return
      const question = questions[currentIndex]
      try {
        await api.patient.respond(sessionId, question.key, rawValue, responseTimeMs)
        if (currentIndex < questions.length - 1) {
          setCurrentIndex(i => i + 1)
        } else {
          setState('submitting')
          await api.patient.completeSession(sessionId)
          setState('scoring')
          pollForResult(sessionId)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to submit answer')
        setState('error')
      }
    },
    [sessionId, currentIndex, questions],
  )

  const pollForResult = useCallback((sid: string) => {
    let attempts = 0
    const interval = setInterval(async () => {
      attempts++
      try {
        const status = await api.patient.sessionStatus(sid)
        if (status.status === 'scored') {
          clearInterval(interval)
          setResult(status)
          setState('done')
        } else if (status.status === 'abstained') {
          clearInterval(interval)
          setState('abstained')
        } else if (attempts > 30) {
          // 30s timeout — show done anyway
          clearInterval(interval)
          setState('done')
        }
      } catch {
        clearInterval(interval)
        setState('done')
      }
    }, 1000)
  }, [])

  const reset = useCallback(() => {
    setSessionId(null)
    setQuestions([])
    setCurrentIndex(0)
    setState('idle')
    setResult(null)
    setError(null)
  }, [])

  return {
    sessionId,
    questions,
    currentIndex,
    currentQuestion: questions[currentIndex] ?? null,
    state,
    result,
    error,
    startSession,
    submitAnswer,
    reset,
  }
}
