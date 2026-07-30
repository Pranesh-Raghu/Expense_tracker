import { Outlet } from 'react-router-dom'
import { AuthProvider } from '@/auth/AuthProvider'
import { ToastProvider } from '@/components/ui/ToastProvider'

// Root layout route: AuthProvider needs router context (useNavigate), so it
// has to live inside the router tree rather than wrapping RouterProvider.
export function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Outlet />
      </AuthProvider>
    </ToastProvider>
  )
}
