import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Navbar from './Navbar'
import Footer from './Footer'
import { getUser } from '../api/client'

export default function Layout() {
  const location = useLocation()
  const [auth, setAuth] = useState({ authenticated: false, user: null })
  const [checking, setChecking] = useState(true)

  const isHero = location.pathname === '/'

  const fetchAuth = () => {
    getUser()
      .then((data) => setAuth({ authenticated: data.authenticated, user: data.user || null }))
      .catch(() => setAuth({ authenticated: false, user: null }))
      .finally(() => setChecking(false))
  }

  useEffect(() => {
    fetchAuth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

  if (isHero) {
    return <Outlet />
  }

  if (checking) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ backgroundColor: 'var(--bg)' }}
      >
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent animate-spin" style={{ borderColor: 'var(--accent) var(--line) var(--line) var(--line)' }} />
      </div>
    )
  }

  if (auth.authenticated) {
    return (
      <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--bg)' }}>
        <Navbar auth={auth} />
        <main className="flex-grow">
          <Outlet />
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--bg)' }}>
      <Navbar auth={auth} />
      <main className="flex-grow">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}