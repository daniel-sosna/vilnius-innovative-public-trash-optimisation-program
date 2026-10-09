import { useEffect, useId, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ToastProvider } from '@/components/ui/toast'
import { VipTopLogo } from '@/components/viptop-logo'

const links = [
  { to: '/admin/trucks', label: 'Šiukšliavežės' },
  { to: '/admin/sites', label: 'Šiukšlių surinkimo vietos' },
]

export function AdminLayout() {
  const location = useLocation()
  const navigationId = useId()
  const toggle = useRef<HTMLButtonElement>(null)
  const [menu, setMenu] = useState({ key: location.key, open: false })
  const open = menu.key === location.key && menu.open
  function closeMenu() {
    setMenu({ key: location.key, open: false })
  }
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 640px)')
    const close = () => setMenu({ key: '', open: false })
    desktop.addEventListener('change', close)
    return () => desktop.removeEventListener('change', close)
  }, [])

  return (
    <ToastProvider>
      <div className="min-h-dvh">
        <header
          className="border-b bg-card"
          onKeyDown={(event) => {
            if (event.key === 'Escape' && open) {
              event.preventDefault()
              closeMenu()
              toggle.current?.focus()
            }
          }}
        >
          <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-4 sm:px-6">
            <Link
              to="/"
              className="flex items-center gap-2 rounded-sm font-semibold text-primary focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring"
              aria-label="VipTop – pradžia"
            >
              <VipTopLogo />
            </Link>
            <Button
              ref={toggle}
              variant="ghost"
              size="icon"
              className="ml-auto sm:hidden"
              aria-label={open ? 'Uždaryti navigaciją' : 'Atidaryti navigaciją'}
              aria-expanded={open}
              aria-controls={navigationId}
              onClick={() => setMenu({ key: location.key, open: !open })}
            >
              {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
            </Button>
            <nav
              id={navigationId}
              aria-label="Administratoriaus navigacija"
              className={`${open ? 'flex' : 'hidden'} w-full flex-col gap-4 border-t pt-4 sm:flex sm:w-auto sm:flex-row sm:border-0 sm:pt-0`}
            >
              {links.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => {
                    closeMenu()
                    if (!window.matchMedia('(min-width: 640px)').matches)
                      toggle.current?.focus()
                  }}
                  className={({ isActive }) =>
                    `rounded-sm text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring ${isActive ? 'underline decoration-primary underline-offset-8' : ''}`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">
          <Outlet />
        </main>
      </div>
    </ToastProvider>
  )
}
