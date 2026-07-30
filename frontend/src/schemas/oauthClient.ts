import { z } from 'zod'

export const registerClientSchema = z.object({
  client_name: z.string().optional(),
  client_uri: z.string().url('Must be a valid URL').optional().or(z.literal('')),
  redirect_uris: z
    .array(z.object({ value: z.string().url('Must be a valid URL') }))
    .min(1, 'At least one redirect URI is required'),
  token_endpoint_auth_method: z.enum(['none', 'client_secret_basic']),
  scope: z.string().optional(),
})

export type RegisterClientValues = z.infer<typeof registerClientSchema>
