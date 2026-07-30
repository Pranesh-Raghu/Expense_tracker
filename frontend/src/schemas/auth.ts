import { z } from 'zod'

export const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})
export type LoginValues = z.infer<typeof loginSchema>

export const signupSchema = z.object({
  username: z.string().min(3, 'At least 3 characters'),
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'At least 8 characters'),
})
export type SignupValues = z.infer<typeof signupSchema>

export const apiKeyLoginSchema = z.object({
  apiKey: z.string().startsWith('eak_', 'API keys start with "eak_"'),
})
export type ApiKeyLoginValues = z.infer<typeof apiKeyLoginSchema>

// Password is optional here - leaving it blank means "don't change it".
export const profileSchema = z.object({
  username: z.string().min(3, 'At least 3 characters'),
  email: z.string().email('Enter a valid email address'),
  password: z.union([z.string().length(0), z.string().min(8, 'At least 8 characters')]).optional(),
})
export type ProfileValues = z.infer<typeof profileSchema>
