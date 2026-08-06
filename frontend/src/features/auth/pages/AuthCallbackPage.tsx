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
  const [searchParams, setSearchParams] = useSearchParams()
  const { loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const ranOnce = useRef(false)

  useEffect(() => {
    if (ranOnce.current) return
    ranOnce.current = true

    const token = searchParams.get('token')
    // Strip the token from the URL right away, before the async
    // loginWithToken call below - a failed sign-in must not leave the JWT
    // sitting in the address bar/browser history either. The success path
    // navigates away entirely a moment later; this covers the error path,
    // which used to leave it there indefinitely.
    setSearchParams({}, { replace: true })

    if (!token) {
      setError('No token in callback URL')
      return
    }

    loginWithToken(token)
      .then(() => navigate('/', { replace: true }))
      .catch(() => setError('Could not complete sign-in'))
  }, [searchParams, setSearchParams, loginWithToken, navigate])

  return (
    <AuthLayout title="Signing you in…">
      {error ? <ErrorState message={error} /> : <Spinner />}
    </AuthLayout>
  )
}
