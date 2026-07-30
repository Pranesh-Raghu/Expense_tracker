import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ErrorState } from '@/components/ui/ErrorState'
import { ApiError } from '@/api/errors'
import { useAuth } from '@/auth/useAuth'
import { apiKeyLoginSchema, type ApiKeyLoginValues } from '@/schemas/auth'
import { AuthLayout } from '../components/AuthLayout'

export function ApiKeyLoginPage() {
  const { loginWithApiKey } = useAuth()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ApiKeyLoginValues>({ resolver: zodResolver(apiKeyLoginSchema) })

  async function onSubmit(values: ApiKeyLoginValues) {
    setFormError(null)
    try {
      await loginWithApiKey(values.apiKey)
      navigate('/')
    } catch (error) {
      setFormError(error instanceof ApiError ? error.detail : 'That API key is not valid')
    }
  }

  return (
    <AuthLayout title="Log in with an API key">
      <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
        <Input placeholder="eak_..." {...register('apiKey')} error={errors.apiKey?.message} />

        {formError && <ErrorState message={formError} />}

        <Button type="submit" className="w-full" disabled={isSubmitting}>
          Log in
        </Button>
      </form>

      <div className="mt-4 text-xs text-slate-500 dark:text-slate-400">
        <Link to="/login" className="hover:underline">
          Log in with a password instead
        </Link>
      </div>
    </AuthLayout>
  )
}
