import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ErrorState } from '@/components/ui/ErrorState'
import { ApiError } from '@/api/errors'
import { useAuth } from '@/auth/useAuth'
import * as usersApi from '@/api/endpoints/users'
import { signupSchema, type SignupValues } from '@/schemas/auth'
import { AuthLayout } from '../components/AuthLayout'

export function SignupPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({ resolver: zodResolver(signupSchema) })

  async function onSubmit(values: SignupValues) {
    setFormError(null)
    try {
      await usersApi.signup(values.username, values.email, values.password)
      await login(values.username, values.password)
      navigate('/')
    } catch (error) {
      setFormError(error instanceof ApiError ? error.detail : 'Signup failed')
    }
  }

  return (
    <AuthLayout title="Create an account">
      <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
        <Input placeholder="Username" {...register('username')} error={errors.username?.message} />
        <Input
          type="email"
          placeholder="Email"
          {...register('email')}
          error={errors.email?.message}
        />
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Used for your profile picture (via Gravatar) - not shown to other users.
        </p>
        <Input
          type="password"
          placeholder="Password"
          {...register('password')}
          error={errors.password?.message}
        />

        {formError && <ErrorState message={formError} />}

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          Create account
        </Button>
      </form>

      <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
        <Link to="/login" className="hover:underline">
          Already have an account? Log in
        </Link>
      </div>
    </AuthLayout>
  )
}
