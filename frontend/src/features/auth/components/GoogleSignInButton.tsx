import { GoogleIcon } from '@/components/ui/GoogleIcon'

// Plain <a>, not a router Link or fetch call: this needs a real full-page
// navigation so the browser can follow the redirect chain through Google
// and back. Same-origin in both dev (Vite proxy) and prod (the static
// site's rewrites), so a root-relative href works without knowing the API
// base URL.
export function GoogleSignInButton() {
  return (
    <a
      href="/auth/google/login"
      className="flex w-full items-center justify-center gap-3 rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
    >
      <GoogleIcon size={22} />
      Continue with Google
    </a>
  )
}
