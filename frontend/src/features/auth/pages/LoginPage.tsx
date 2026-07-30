import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ErrorState } from '@/components/ui/ErrorState'
import { ApiError } from '@/api/errors'
import { useAuth } from '@/auth/useAuth'
import { loginSchema, type LoginValues } from '@/schemas/auth'
import { AuthLayout } from '../components/AuthLayout'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) })

  async function onSubmit(values: LoginValues) {
    setFormError(null)
    try {
      await login(values.username, values.password)
      navigate('/')
    } catch (error) {
      setFormError(error instanceof ApiError ? error.detail : 'Login failed')
    }
  }

  return (
    <AuthLayout title="Log in">
      {searchParams.get('reason') === 'expired' && (
        <p className="mb-3 text-xs text-amber-600 dark:text-amber-400">Your session expired. Log in again.</p>
      )}

      <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
        <Input placeholder="Username" {...register('username')} error={errors.username?.message} />
        <Input
          type="password"
          placeholder="Password"
          {...register('password')}
          error={errors.password?.message}
        />

        {formError && <ErrorState message={formError} />}

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          Log in
        </Button>
      </form>

      <div className="mt-4 flex justify-between text-xs text-slate-500 dark:text-slate-400">
        <Link to="/signup" className="hover:underline">
          Create an account
        </Link>
        <Link to="/login/api-key" className="hover:underline">
          Log in with an API key
        </Link>
      </div>
    </AuthLayout>
  )
}
