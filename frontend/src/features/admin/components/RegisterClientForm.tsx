import { zodResolver } from '@hookform/resolvers/zod'
import { useFieldArray, useForm } from 'react-hook-form'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { registerClientSchema, type RegisterClientValues } from '@/schemas/oauthClient'

interface RegisterClientFormProps {
  onSubmit: (values: RegisterClientValues) => void
  isPending: boolean
}

export function RegisterClientForm({ onSubmit, isPending }: RegisterClientFormProps) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterClientValues>({
    resolver: zodResolver(registerClientSchema),
    defaultValues: {
      redirect_uris: [{ value: '' }],
      token_endpoint_auth_method: 'none',
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: 'redirect_uris' })

  return (
    <form className="space-y-3" onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Client name</label>
        <Input {...register('client_name')} placeholder="My MCP client" />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Client URI</label>
        <Input {...register('client_uri')} placeholder="https://example.com" error={errors.client_uri?.message} />
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Redirect URIs</label>
        <div className="space-y-2">
          {fields.map((field, index) => (
            <div key={field.id} className="flex gap-2">
              <Input
                {...register(`redirect_uris.${index}.value`)}
                placeholder="https://example.com/callback"
                error={errors.redirect_uris?.[index]?.value?.message}
              />
              <Button type="button" variant="ghost" onClick={() => remove(index)} disabled={fields.length === 1}>
                Remove
              </Button>
            </div>
          ))}
        </div>
        {errors.redirect_uris?.message && <p className="mt-1 text-xs text-red-600">{errors.redirect_uris.message}</p>}
        <Button type="button" variant="secondary" className="mt-2" onClick={() => append({ value: '' })}>
          Add redirect URI
        </Button>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">
          Token endpoint auth method
        </label>
        <Select {...register('token_endpoint_auth_method')}>
          <option value="none">None (public client, PKCE)</option>
          <option value="client_secret_basic">Client secret basic</option>
        </Select>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-500 dark:text-slate-400">Scope</label>
        <Input {...register('scope')} placeholder="expenses:read expenses:write" />
      </div>

      <Button type="submit" className="w-full" disabled={isPending}>
        Register client
      </Button>
    </form>
  )
}
