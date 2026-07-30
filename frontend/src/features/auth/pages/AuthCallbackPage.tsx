import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Spinner } from '@/components/ui/Spinner'
import { ErrorState } from '@/components/ui/ErrorState'
import { useAuth } from '@/auth/useAuth'
import { AuthLayout } from '../components/AuthLayout'

// Lands here after /auth/google/callback (backend) redirects the browser
// back with a freshly-minted JWT as a query param - picks it up and hands
// off to the normal auth state, same shape as a password login from here.
export function AuthCallbackPage() {
  const [searchParams] = useSearchParams()
  const { loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const ranOnce = useRef(false)

  useEffect(() => {
    if (ranOnce.current) return
    ranOnce.current = true

    const token = searchParams.get('token')
    if (!token) {
      setError('No token in callback URL')
      return
    }

    loginWithToken(token)
      .then(() => navigate('/', { replace: true }))
      .catch(() => setError('Could not complete sign-in'))
  }, [searchParams, loginWithToken, navigate])

  return (
    <AuthLayout title="Signing you in…">
      {error ? <ErrorState message={error} /> : <Spinner />}
    </AuthLayout>
  )
}
