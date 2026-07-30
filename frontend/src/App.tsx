import { Outlet } from 'react-router-dom'
import { AuthProvider } from '@/auth/AuthProvider'
import { ToastProvider } from '@/components/ui/ToastProvider'
import { ThemeProvider } from '@/components/ThemeProvider'

// Root layout route: AuthProvider needs router context (useNavigate), so it
// has to live inside the router tree rather than wrapping RouterProvider.
export function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AuthProvider>
          <Outlet />
        </AuthProvider>
      </ToastProvider>
    </ThemeProvider>
  )
}
