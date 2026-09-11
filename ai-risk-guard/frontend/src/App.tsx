import React, { useState, useEffect, useCallback } from 'react';
import { ViewId, ShieldCADState } from './types';
import { getMe } from './api/client';
import { CinematicEnvironment } from './components/landing/CinematicEnvironment';
import { TacticalNavbar } from './components/common/TacticalNavbar';
import { Footer } from './components/common/Footer';
import { AccessModal } from './components/common/AccessModal';
import { DocsModal } from './components/common/DocsModal';
import { WorkstationLauncherModal, ALL_VIEWS } from './components/common/WorkstationLauncherModal';

// Views 01 to 18
import { View01Landing } from './components/views/View01Landing';
import { View02Login } from './components/views/View02Login';
import { View03Signup } from './components/views/View03Signup';
import { View04Dashboard } from './components/views/View04Dashboard';
import { View05Repositories } from './components/views/View05Repositories';
import { View06Scanner } from './components/views/View06Scanner';
import { View07Findings } from './components/views/View07Findings';
import { View08Patch } from './components/views/View08Patch';
import { View09Sandbox } from './components/views/View09Sandbox';
import { View10Policy } from './components/views/View10Policy';
import { View11Risk } from './components/views/View11Risk';
import { View12Telemetry } from './components/views/View12Telemetry';
import { View13Agents } from './components/views/View13Agents';
import { View14Reports } from './components/views/View14Reports';
import { View15ReportDetail } from './components/views/View15ReportDetail';
import { View16GitHub } from './components/views/View16GitHub';
import { View17Settings } from './components/views/View17Settings';
import { View18Health } from './components/views/View18Health';

// Map browser path -> SPA view so OAuth callback redirects (e.g. /dashboard)
// and error redirects (/login?error=...) land on the correct view after reload.
function viewFromPath(): ViewId {
  const { pathname, search } = window.location;
  const params = new URLSearchParams(search);
  const path = pathname.replace(/\/+$/, '') || '/';
  if (path === '/' && params.has('error')) return 'login';
  const map: Record<string, ViewId> = {
    '/': 'landing',
    '/login': 'login',
    '/signup': 'signup',
    '/dashboard': 'dashboard',
    '/repositories': 'repositories',
    '/scanner': 'scanner',
    '/findings': 'findings',
    '/patch': 'patch',
    '/sandbox': 'sandbox',
    '/policy': 'policy',
    '/risk': 'risk',
    '/telemetry': 'telemetry',
    '/agents': 'agents',
    '/reports': 'reports',
    '/report-detail': 'report-detail',
    '/github': 'github',
    '/settings': 'settings',
    '/status': 'status'
  };
  return map[path] ?? 'landing';
}

export function App() {
  const [currentView, setCurrentView] = useState<ViewId>(viewFromPath);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [operatorHandle, setOperatorHandle] = useState('octocat-secops');
  const [authChecked, setAuthChecked] = useState(false);

  // Modal States
  const [accessModalOpen, setAccessModalOpen] = useState(false);
  const [pendingRestrictedView, setPendingRestrictedView] = useState<ViewId | null>(null);
  const [docsModalOpen, setDocsModalOpen] = useState(false);
  const [launcherModalOpen, setLauncherModalOpen] = useState(false);

  // Verify the real GitHub OAuth session on boot.
  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((me) => {
        if (cancelled) return;
        const authed = Boolean(me.authenticated);
        setIsAuthenticated(authed);
        if (me.authenticated && me.user) {
          setOperatorHandle(me.user.login);
        }
        // If the initial path pointed at a protected view but there is no
        // session, send the user back to a public view instead of a blank gate.
        if (!authed) {
          const meta = ALL_VIEWS.find((v) => v.id === currentView);
          if (meta?.protected) setCurrentView('landing');
        }
      })
      .catch(() => {
        if (!cancelled) setIsAuthenticated(false);
      })
      .finally(() => {
        if (!cancelled) setAuthChecked(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Scroll Progress Engine (0.0 to 1.0) with rAF interpolation
  const [scrollProgress, setScrollProgress] = useState(0);

  // Shield CAD Controls State
  const [cadState, setCadState] = useState<ShieldCADState>({
    viewAngle: 'ISOMETRIC',
    wireframe: false,
    autoRotate: true,
    assemblyStage: 1
  });

  const handleCADChange = useCallback((updates: Partial<ShieldCADState>) => {
    setCadState((prev) => ({ ...prev, ...updates }));
  }, []);

  // Passive Scroll Listener for hardware-accelerated 0->1 interpolation
  useEffect(() => {
    let ticking = false;

    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
          const progress = totalHeight > 0 ? Math.min(1, Math.max(0, window.scrollY / totalHeight)) : 0;
          setScrollProgress(progress);
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [currentView]);

  // Route Guard / Workstation Navigation Handler
  const navigateTo = useCallback(
    (view: ViewId) => {
      const meta = ALL_VIEWS.find((v) => v.id === view);
      if (meta?.protected && !isAuthenticated) {
        setPendingRestrictedView(view);
        setAccessModalOpen(true);
        return;
      }

      setCurrentView(view);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [isAuthenticated]
  );

  const handleLoginSuccess = useCallback(() => {
    setIsAuthenticated(true);
    setCurrentView('dashboard');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleLogout = useCallback(() => {
    window.location.href = '/auth/logout';
  }, []);

  return (
    <div className="relative min-h-screen bg-[#02050B] text-[#D7DEE7] flex flex-col justify-between selection:bg-[#087BFF]/40 selection:text-[#65E7FF]">
      {/* 8-Layer Ambient Backdrop Environment */}
      <CinematicEnvironment scrollProgress={scrollProgress} />

      {/* Persistent 3-Module Tactical Glass Topbar */}
      <TacticalNavbar
        currentView={currentView}
        onNavigate={navigateTo}
        isAuthenticated={isAuthenticated}
        operatorHandle={operatorHandle}
        onOpenLauncher={() => setLauncherModalOpen(true)}
        onOpenDocs={() => setDocsModalOpen(true)}
        onLoginClick={() => navigateTo('login')}
        onLogoutClick={handleLogout}
      />

      {/* Main View Router */}
      <main className="relative z-10 flex-grow">
        {currentView === 'landing' && (
          <View01Landing
            onNavigate={navigateTo}
            scrollProgress={scrollProgress}
            cadState={cadState}
            onCADChange={handleCADChange}
            onOpenDocs={() => setDocsModalOpen(true)}
          />
        )}

        {currentView === 'login' && (
          <View02Login onLoginSuccess={handleLoginSuccess} onNavigate={navigateTo} />
        )}

        {currentView === 'signup' && (
          <View03Signup onSignupSuccess={handleLoginSuccess} onNavigate={navigateTo} />
        )}

        {currentView === 'dashboard' && <View04Dashboard onNavigate={navigateTo} />}

        {currentView === 'repositories' && <View05Repositories onNavigate={navigateTo} />}

        {currentView === 'scanner' && <View06Scanner onNavigate={navigateTo} />}

        {currentView === 'findings' && <View07Findings onNavigate={navigateTo} />}

        {currentView === 'patch' && <View08Patch onNavigate={navigateTo} />}

        {currentView === 'sandbox' && <View09Sandbox onNavigate={navigateTo} />}

        {currentView === 'policy' && <View10Policy onNavigate={navigateTo} />}

        {currentView === 'risk' && <View11Risk onNavigate={navigateTo} />}

        {currentView === 'telemetry' && <View12Telemetry onNavigate={navigateTo} />}

        {currentView === 'agents' && <View13Agents onNavigate={navigateTo} />}

        {currentView === 'reports' && <View14Reports onNavigate={navigateTo} />}

        {currentView === 'report-detail' && <View15ReportDetail onNavigate={navigateTo} />}

        {currentView === 'github' && <View16GitHub onNavigate={navigateTo} />}

        {currentView === 'settings' && <View17Settings onNavigate={navigateTo} />}

        {currentView === 'status' && <View18Health onNavigate={navigateTo} />}
      </main>

      {/* Global Modals */}
      <AccessModal
        isOpen={accessModalOpen}
        onClose={() => setAccessModalOpen(false)}
        onAuthenticate={() => {
          setAccessModalOpen(false);
          navigateTo('login');
        }}
        targetViewName={pendingRestrictedView || 'RESTRICTED_WORKSTATION'}
      />

      <DocsModal
        isOpen={docsModalOpen}
        onClose={() => setDocsModalOpen(false)}
      />

      <WorkstationLauncherModal
        isOpen={launcherModalOpen}
        onClose={() => setLauncherModalOpen(false)}
        currentView={currentView}
        onSelectView={navigateTo}
        isAuthenticated={isAuthenticated}
      />

      {/* Enterprise Platform Footer */}
      <Footer
        onNavigate={navigateTo}
        onOpenDocs={() => setDocsModalOpen(true)}
        onOpenLauncher={() => setLauncherModalOpen(true)}
      />
    </div>
  );
}

export default App;
