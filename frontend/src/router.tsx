import { createBrowserRouter } from 'react-router-dom'
import { App } from './App'
import { RequireAuth } from '@/auth/RequireAuth'
import { RequireAdmin } from '@/auth/RequireAdmin'
import { AppShell } from '@/components/layout/AppShell'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { SignupPage } from '@/features/auth/pages/SignupPage'
import { ApiKeyLoginPage } from '@/features/auth/pages/ApiKeyLoginPage'
import { AuthCallbackPage } from '@/features/auth/pages/AuthCallbackPage'
import { DashboardPage } from '@/features/expenses/pages/DashboardPage'
import { ExpenseDetailPage } from '@/features/expenses/pages/ExpenseDetailPage'
import { ReportsPage } from '@/features/reports/pages/ReportsPage'
import { ApiKeysPage } from '@/features/settings/pages/ApiKeysPage'
import { ProfilePage } from '@/features/settings/pages/ProfilePage'
import { SessionsPage } from '@/features/settings/pages/SessionsPage'
import { OAuthClientsPage } from '@/features/admin/pages/OAuthClientsPage'
import { TokenToolsPage } from '@/features/admin/pages/TokenToolsPage'
import { AdminUsersPage } from '@/features/admin/pages/AdminUsersPage'

// /oauth/authorize (the consent screen) stays server-rendered Jinja
// (templates/login.html) - it deliberately has no route here so the SPA
// never shadows it.
export const router = createBrowserRouter([
  {
    element: <App />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
      { path: '/login/api-key', element: <ApiKeyLoginPage /> },
      // Not /auth/callback: /auth/* is reserved for the backend rewrite
      // (see vite.config.ts / the static site's routes) - that prefix
      // never reaches the SPA at all, so a route there would 404 against
      // the API instead of rendering this page.
      { path: '/login/callback', element: <AuthCallbackPage /> },
      {
        path: '/',
        element: (
          <RequireAuth>
            <AppShell>
              <DashboardPage />
            </AppShell>
          </RequireAuth>
        ),
      },
      {
        path: '/expenses/:id',
        element: (
          <RequireAuth>
            <AppShell>
              <ExpenseDetailPage />
            </AppShell>
          </RequireAuth>
        ),
      },
      {
        path: '/reports',
        element: (
          <RequireAuth>
            <AppShell>
              <ReportsPage />
            </AppShell>
          </RequireAuth>
        ),
      },
      {
        path: '/settings/api-keys',
        element: (
          <RequireAuth>
            <AppShell>
              <ApiKeysPage />
            </AppShell>
          </RequireAuth>
        ),
      },
      {
        path: '/settings/profile',
        element: (
          <RequireAuth>
            <AppShell>
              <ProfilePage />
            </AppShell>
          </RequireAuth>
        ),
      },
      {
        path: '/settings/sessions',
        element: (
          <RequireAuth>
            <AppShell>
              <SessionsPage />
            </AppShell>
          </RequireAuth>
        ),
      },
      {
        path: '/admin/oauth-clients',
        element: (
          <RequireAdmin>
            <AppShell>
              <OAuthClientsPage />
            </AppShell>
          </RequireAdmin>
        ),
      },
      {
        path: '/admin/tokens',
        element: (
          <RequireAdmin>
            <AppShell>
              <TokenToolsPage />
            </AppShell>
          </RequireAdmin>
        ),
      },
      {
        path: '/admin/users',
        element: (
          <RequireAdmin>
            <AppShell>
              <AdminUsersPage />
            </AppShell>
          </RequireAdmin>
        ),
      },
    ],
  },
])
