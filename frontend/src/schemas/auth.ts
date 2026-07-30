import { z } from 'zod'

export const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})
export type LoginValues = z.infer<typeof loginSchema>

export const signupSchema = z.object({
  username: z.string().min(3, 'At least 3 characters'),
  password: z.string().min(8, 'At least 8 characters'),
})
export type SignupValues = z.infer<typeof signupSchema>

export const apiKeyLoginSchema = z.object({
  apiKey: z.string().startsWith('eak_', 'API keys start with "eak_"'),
})
export type ApiKeyLoginValues = z.infer<typeof apiKeyLoginSchema>
