import { useEffect } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ErrorState } from '@/components/ui/ErrorState'
import { Avatar } from '@/components/ui/Avatar'
import { useToast } from '@/components/ui/ToastProvider'
import { ApiError } from '@/api/errors'
import { useAuth } from '@/auth/useAuth'
import * as usersApi from '@/api/endpoints/users'
import type { UserUpdateInput } from '@/api/types'
import { profileSchema, type ProfileValues } from '@/schemas/auth'

export function ProfilePage() {
  const { user, refreshUser } = useAuth()
  const { showToast } = useToast()
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting: isValidating },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { username: user?.username ?? '', email: user?.email ?? '', password: '' },
  })

  useEffect(() => {
    reset({ username: user?.username ?? '', email: user?.email ?? '', password: '' })
  }, [user, reset])

  const watchedUsername = watch('username')

  const mutation = useMutation({
    mutationFn: (input: UserUpdateInput) => {
      if (!user) throw new Error('Not logged in')
      return usersApi.updateUser(user.id, input)
    },
    onSuccess: async () => {
      await refreshUser()
      queryClient.invalidateQueries({ queryKey: ['users'] })
      showToast('Profile updated', 'success')
    },
    onError: (error) => {
      showToast(error instanceof ApiError ? error.detail : 'Update failed', 'error')
    },
  })

  function onSubmit(values: ProfileValues) {
    if (!user) return
    const input: UserUpdateInput = {}
    if (values.username !== user.username) input.username = values.username
    if (values.email !== user.email) input.email = values.email
    if (values.password) input.password = values.password

    if (Object.keys(input).length === 0) {
      showToast('Nothing to update', 'info')
      return
    }

    mutation.mutate(input, { onSuccess: () => reset({ ...values, password: '' }) })
  }

  if (!user) return null

  return (
    <div className="max-w-md space-y-4">
      <h1 className="text-lg font-semibold">Profile</h1>

      <Card className="flex items-center gap-4">
        <Avatar username={watchedUsername || user.username} avatarUrl={user.avatar_url} size={56} />
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Your picture comes from{' '}
          <a href="https://gravatar.com" target="_blank" rel="noreferrer" className="underline">
            Gravatar
          </a>
          , based on your email. No email, or no Gravatar for it, falls back to your first initial.
        </p>
      </Card>

      <Card>
        <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Username</label>
            <Input {...register('username')} error={errors.username?.message} />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Email</label>
            <Input type="email" {...register('email')} error={errors.email?.message} />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
              New password
            </label>
            <Input
              type="password"
              placeholder="Leave blank to keep current password"
              {...register('password')}
              error={errors.password?.message}
            />
          </div>

          {mutation.isError && (
            <ErrorState message={mutation.error instanceof ApiError ? mutation.error.detail : 'Update failed'} />
          )}

          <Button type="submit" disabled={isValidating || mutation.isPending}>
            Save changes
          </Button>
        </form>
      </Card>
    </div>
  )
}
