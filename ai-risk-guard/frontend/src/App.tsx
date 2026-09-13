import { useState, useEffect, useCallback } from 'react';
import { ViewId, ShieldCADState } from './types';
import { getMe } from './api/client';
import { CinematicEnvironment } from './components/landing/CinematicEnvironment';
import { TacticalNavbar } from './components/common/TacticalNavbar';
import { TacticalSidebar } from './components/common/TacticalSidebar';
import { Footer } from './components/common/Footer';
import { AccessModal } from './components/common/AccessModal';
import { DocsModal } from './components/common/DocsModal';
import { CinematicIntro } from './components/common/CinematicIntro';
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
import { View19Profile } from './components/views/View19Profile';

// Map browser path -> SPA view so OAuth callback redirects (e.g. /dashboard)
// and error redirects (/login?error=...) land on the correct view after reload.
const VIEW_PATHS: Record<ViewId, string> = {
  landing: '/',
  login: '/login',
  signup: '/signup',
  dashboard: '/dashboard',
  repositories: '/repositories',
  scanner: '/scanner',
  findings: '/findings',
  patch: '/patch',
  sandbox: '/sandbox',
  policy: '/policy',
  risk: '/risk',
  telemetry: '/telemetry',
  agents: '/agents',
  reports: '/reports',
  'report-detail': '/report-detail',
  github: '/github',
  settings: '/settings',
  status: '/status',
  profile: '/profile',
};

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
    '/status': 'status',
    '/profile': 'profile'
  };
  return map[path] ?? 'landing';
}

export function App() {
  const [currentView, setCurrentView] = useState<ViewId>(viewFromPath);
  const [introVisible, setIntroVisible] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [operatorHandle, setOperatorHandle] = useState('octocat-secops');
  const [operatorAvatar, setOperatorAvatar] = useState('');
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
          if (me.user.avatar_url) setOperatorAvatar(me.user.avatar_url);
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
  }, []);

  // Once session state is known, gate protected deep links (e.g. a reload on
  // /dashboard) behind the AccessModal instead of a silent redirect or a 401.
  useEffect(() => {
    if (!authChecked) return;
    const meta = ALL_VIEWS.find((v) => v.id === currentView);
    if (meta?.protected && !isAuthenticated) {
      setPendingRestrictedView(currentView);
      setAccessModalOpen(true);
    } else if (meta?.protected && isAuthenticated) {
      setAccessModalOpen(false);
      setPendingRestrictedView(null);
    }
  }, [authChecked, isAuthenticated, currentView]);

  // Keep currentView in sync with browser back/forward navigation and clear
  // transient OAuth params (/login?error=..., /?reason=...) once consumed.
  useEffect(() => {
    const onPopState = () => {
      setCurrentView(viewFromPath());
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has('error') || params.has('reason') || params.has('install_url')) {
      const cleanUrl = window.location.pathname + window.location.hash;
      window.history.replaceState({}, '', cleanUrl);
    }
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
      if (meta?.protected && !isAuthenticated && authChecked) {
        setPendingRestrictedView(view);
        setAccessModalOpen(true);
        return;
      }

      setCurrentView(view);
      window.history.pushState({ view }, '', VIEW_PATHS[view] ?? '/');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [isAuthenticated, authChecked]
  );

  const handleLoginSuccess = useCallback(() => {
    setIsAuthenticated(true);
    setCurrentView('dashboard');
    window.history.pushState({ view: 'dashboard' }, '', '/dashboard');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleLogout = useCallback(() => {
    window.location.href = '/auth/logout';
  }, []);

  const handleIntroComplete = useCallback(() => {
    setIntroVisible(false);
  }, []);

  // Never mount a protected view while there is no verified session — that
  // would fire 401s which race the boot guard and hard-redirect to /login.
  const activeViewMeta = ALL_VIEWS.find((v) => v.id === currentView);
  const effectiveView: ViewId = activeViewMeta?.protected && !isAuthenticated ? 'landing' : currentView;
  const isConsole = !['landing', 'login', 'signup'].includes(effectiveView);

  const viewRouter = (
    <main className="relative z-10 flex-grow">
      {effectiveView === 'landing' && (
        <View01Landing
          onNavigate={navigateTo}
          scrollProgress={scrollProgress}
          cadState={cadState}
          onCADChange={handleCADChange}
          onOpenDocs={() => setDocsModalOpen(true)}
        />
      )}

      {effectiveView === 'login' && (
        <View02Login onLoginSuccess={handleLoginSuccess} onNavigate={navigateTo} />
      )}

      {effectiveView === 'signup' && (
        <View03Signup onSignupSuccess={handleLoginSuccess} onNavigate={navigateTo} />
      )}

      {effectiveView === 'dashboard' && <View04Dashboard onNavigate={navigateTo} />}

      {effectiveView === 'repositories' && <View05Repositories onNavigate={navigateTo} />}

      {effectiveView === 'scanner' && <View06Scanner onNavigate={navigateTo} />}

      {effectiveView === 'findings' && <View07Findings onNavigate={navigateTo} />}

      {effectiveView === 'patch' && <View08Patch onNavigate={navigateTo} />}

      {effectiveView === 'sandbox' && <View09Sandbox onNavigate={navigateTo} />}

      {effectiveView === 'policy' && <View10Policy onNavigate={navigateTo} />}

      {effectiveView === 'risk' && <View11Risk onNavigate={navigateTo} />}

      {effectiveView === 'telemetry' && <View12Telemetry onNavigate={navigateTo} />}

      {effectiveView === 'agents' && <View13Agents onNavigate={navigateTo} />}

      {effectiveView === 'reports' && <View14Reports onNavigate={navigateTo} />}

      {effectiveView === 'report-detail' && <View15ReportDetail onNavigate={navigateTo} />}

      {effectiveView === 'github' && <View16GitHub onNavigate={navigateTo} />}

      {effectiveView === 'settings' && <View17Settings onNavigate={navigateTo} />}

      {effectiveView === 'status' && <View18Health onNavigate={navigateTo} />}

      {effectiveView === 'profile' && <View19Profile onNavigate={navigateTo} />}
    </main>
  );

  const footer = (
    <Footer
      onOpenDocs={() => setDocsModalOpen(true)}
      onOpenLauncher={() => setLauncherModalOpen(true)}
    />
  );

  return (
    <div className="relative min-h-screen bg-[#020B1A] text-[#D9E1EA] flex flex-col selection:bg-[#007BFF]/40 selection:text-[#5BC9FF]">
      {introVisible && (
        <CinematicIntro onComplete={handleIntroComplete} />
      )}

      {/* 8-Layer Ambient Backdrop Environment */}
      <CinematicEnvironment scrollProgress={scrollProgress} />

      {isConsole ? (
        /* Console Shell: Left Sidebar + Content Column (dashboard and all protected workstations) */
        <div className="relative z-10 flex flex-1 min-h-screen">
          <TacticalSidebar
            currentView={currentView}
            onNavigate={navigateTo}
            isAuthenticated={isAuthenticated}
            operatorHandle={operatorHandle}
            operatorAvatar={operatorAvatar}
            onOpenDocs={() => setDocsModalOpen(true)}
            onLoginClick={() => navigateTo('login')}
            onLogoutClick={handleLogout}
          />
          <div className="flex-1 min-w-0 flex flex-col">
            {viewRouter}
          </div>
        </div>
      ) : (
        /* Public Shell: Slim Top Bar + Main + Footer (landing / auth gateways) */
        <div className="relative z-10 flex-1 flex flex-col">
          <TacticalNavbar
            currentView={currentView}
            onNavigate={navigateTo}
            isAuthenticated={isAuthenticated}
            operatorHandle={operatorHandle}
            operatorAvatar={operatorAvatar}
            onLoginClick={() => navigateTo('login')}
            onLogoutClick={handleLogout}
          />
          {viewRouter}
          {footer}
        </div>
      )}

      {/* Global Modals */}
      <AccessModal
        isOpen={accessModalOpen}
        onClose={() => {
          setAccessModalOpen(false);
          setPendingRestrictedView(null);
          window.history.replaceState({}, '', VIEW_PATHS['landing']);
          setCurrentView('landing');
        }}
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
    </div>
  );
}

export default App;
