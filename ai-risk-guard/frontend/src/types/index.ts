export type ViewId =
  | 'landing'
  | 'login'
  | 'signup'
  | 'dashboard'
  | 'repositories'
  | 'findings'
  | 'policy'
  | 'risk'
  | 'agents'
  | 'reports'
  | 'report-detail'
  | 'github'
  | 'settings'
  | 'status'
  | 'profile';

export interface ViewMeta {
  id: ViewId;
  title: string;
  code: string;
  category: 'PUBLIC' | 'CORE' | 'GOVERNANCE' | 'SYSTEM';
  protected: boolean;
  description: string;
  hiddenFromNav?: boolean;
}

export type CADViewAngle = 'ISOMETRIC' | 'FRONT' | 'TOP' | 'RIGHT' | 'SECTION' | 'EXPLODED';

export interface ShieldCADState {
  viewAngle: CADViewAngle;
  wireframe: boolean;
  autoRotate: boolean;
  assemblyStage: number; // 1 to 7
}

export interface AuthState {
  isAuthenticated: boolean;
  operatorHandle: string;
  operatorRole: string;
  tokenExpiresAt?: string;
  activeWorkstation: ViewId;
}

export interface RiskFactorItem {
  id: string;
  name: string;
  weight: number;
  score: number;
  status: 'OPTIMAL' | 'MODERATE' | 'ELEVATED' | 'CRITICAL';
  description: string;
  threadColor: string;
}

export interface SecurityAgent {
  id: string;
  name: string;
  role: string;
  status: 'ACTIVE' | 'IDLE' | 'PROCESSING' | 'CONVERGING';
  load: number;
  lastHeartbeat: string;
  activeTasks: number;
  coordinates: { x: number; y: number };
}

export interface VulnerabilityFinding {
  id: string;
  cwe: string;
  name: string;
  file: string;
  line: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: number;
  riskContribution: number;
  snippet: string;
  remediationSnippet: string;
  status: 'UNPATCHED' | 'PATCH_READY' | 'VALIDATED' | 'BLOCKED';
}

export interface RepositoryItem {
  id: string;
  name: string;
  branch: string;
  status: 'PROTECTED' | 'ACTION_REQUIRED' | 'SCANNING';
  lastScan: string;
  openFindings: number;
  astHealth: number;
}

export interface SubsystemHealth {
  id: string;
  name: string;
  status: 'HEALTHY' | 'DEGRADED' | 'OPTIMAL' | 'OFFLINE';
  latency: string;
  version: string;
  uptime: string;
  details: string;
}

export interface PolicyData {
  policy_name?: string;
  version?: string;
  description?: string;
  forbidden_modules?: string[];
  forbidden_functions?: string[];
  mandatory_sanitizers?: Record<string, unknown>;
  sensitive_paths?: string[];
  restricted_function_args?: unknown[];
  mandatory_call_wrappers?: unknown[];
  forbidden_assignments?: unknown[];
  mandatory_query_params?: unknown[];
}
