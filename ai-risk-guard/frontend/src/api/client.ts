import axios from 'axios'

export interface UserInfo {
  github_id: number;
  login: string;
  name: string;
  avatar_url: string;
}

export interface MeResponse {
  authenticated: boolean;
  user: UserInfo | null;
  installations: number;
  install_url: string;
}

export interface DashboardData {
  total_prs: number;
  total_vulnerabilities: number;
  risk_levels: { LOW: number; MEDIUM: number; HIGH: number };
  avg_risk_score: number;
  remediation_rate: number;
  cache_hit_rate: number;
  trends: { day: string; count: number }[];
  performance: Record<string, unknown>[];
  attention: AttentionFinding[];
  week_summary: { scans_7d: number; new_7d: number; open_now: number };
  repos: RepoSummary[];
}

export interface AttentionFinding {
  id: number;
  vuln_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_score: number;
  file_path: string;
  pr_number: number;
  pr_title: string;
  repo_id: number;
  repo_full_name: string;
  scan_id: number;
}

export interface RepoSummary {
  id: number;
  full_name: string;
  name?: string;
  repo_url?: string;
  last_scan?: string | null;
  open_findings?: number;
  [key: string]: unknown;
}

export interface Repo {
  id: number;
  full_name: string;
  install_id?: number;
  repo_url?: string;
  open_findings?: number;
  [key: string]: unknown;
}

export interface Scan {
  id: number;
  repo_id: number;
  pr_number: number;
  pr_title?: string;
  status?: string;
  findings_count?: number;
  scanned_at?: string;
  [key: string]: unknown;
}

export interface Finding {
  id: number;
  scan_id: number;
  vuln_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_score: number;
  file_path: string;
  line_number: number;
  status: 'open' | 'resolved' | 'dismissed';
  created_at?: string;
  pr_number?: number;
  pr_title?: string;
  repo_id?: number;
  repo_full_name?: string;
  [key: string]: unknown;
}

export interface SettingsResponse {
  settings: {
    scan_mode?: string;
    sandbox_network?: string;
    codeql_enabled?: boolean;
    [key: string]: unknown;
  };
  options: {
    scan_modes: string[];
    networks: string[];
    docker_available: boolean;
  };
}

export interface PolicyData {
  policy_name?: string;
  version?: string;
  description?: string;
  forbidden_modules?: string[];
  forbidden_functions?: string[];
  mandatory_sanitizers?: Record<string, unknown>;
  sensitive_paths?: string[];
  [key: string]: unknown;
}

export interface SandboxHealth {
  docker_available: boolean;
  image_ready: boolean;
  mode: 'docker' | 'unavailable';
}

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

function getCsrfToken(): string {
  if (typeof document === 'undefined') return ''
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

api.interceptors.request.use((config) => {
  const method = (config.method || '').toLowerCase()
  if (['post', 'put', 'patch', 'delete'].includes(method)) {
    const token = getCsrfToken()
    if (token) config.headers['X-CSRF-Token'] = token
  }
  return config
})

async function sessionAlive(): Promise<boolean> {
  try {
    const { data } = await api.get<MeResponse>('/me')
    return Boolean(data && data.authenticated)
  } catch {
    return false
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error
    if (response && response.status === 401 && !config.__sessionChecked) {
      config.__sessionChecked = true
      if (await sessionAlive()) {
        return api(config)
      }
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export async function getMe(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>('/me')
  return data
}

export async function getDashboardData(): Promise<DashboardData> {
  const { data } = await api.get<DashboardData>('/dashboard')
  return data
}

export async function getRepos(): Promise<Repo[]> {
  const { data } = await api.get<{ repos: Repo[] }>('/repos')
  return data.repos
}

export async function getFindings(params: Record<string, string | number | undefined> = {}): Promise<Finding[]> {
  const { data } = await api.get<{ findings: Finding[] }>('/findings', { params })
  return data.findings
}

export async function getScans(params: Record<string, string | number | undefined> = {}): Promise<Scan[]> {
  const { data } = await api.get<{ scans: Scan[] }>('/scans', { params })
  return data.scans
}

export async function getSettings(): Promise<SettingsResponse> {
  const { data } = await api.get<SettingsResponse>('/settings')
  return data
}

export async function updateSettings(
  settings: Record<string, string | number | boolean>
): Promise<SettingsResponse> {
  const { data } = await api.post<SettingsResponse>('/settings', settings)
  return data
}

export async function getPolicy(): Promise<PolicyData> {
  const { data } = await api.get<PolicyData>('/policy')
  return data
}

export async function getSandboxHealth(): Promise<SandboxHealth> {
  const { data } = await api.get<SandboxHealth>('/health/sandbox')
  return data
}

export async function getHealthDb(): Promise<{ status: string }> {
  const { data } = await api.get<{ status: string }>('/health/db')
  return data
}

export async function getHealthGemini(): Promise<{ status: string; configured: boolean }> {
  const { data } = await api.get<{ status: string; configured: boolean }>('/health/gemini')
  return data
}

export async function getHealthReady(): Promise<{
  status: string;
  db_writable: boolean;
  sandbox_available: boolean;
  github_configured: boolean;
}> {
  const { data } = await api.get<{
    status: string;
    db_writable: boolean;
    sandbox_available: boolean;
    github_configured: boolean;
  }>('/health/ready')
  return data
}

export { api }

export default api