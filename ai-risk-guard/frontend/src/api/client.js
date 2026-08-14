import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

function getCsrfToken() {
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

async function sessionAlive() {
  try {
    const { data } = await api.get('/me')
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
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export async function getDashboard() {
  const { data } = await api.get('/dashboard')
  return data
}

export async function getUser() {
  const { data } = await api.get('/me')
  return data
}

export async function getRepos() {
  const { data } = await api.get('/repos')
  return data.repos
}

export async function getRepo(repoId) {
  const { data } = await api.get(`/repos/${repoId}`)
  return data
}

export async function getRepoScans(repoId) {
  const { data } = await api.get(`/repos/${repoId}/scans`)
  return data.scans
}

export async function getRepoFindings(repoId) {
  const { data } = await api.get(`/repos/${repoId}/findings`)
  return data
}

export async function enableCodeql(repoId) {
  const { data } = await api.post(`/repos/${repoId}/codeql`)
  return data
}

export async function getAllFindings(params = {}) {
  const { data } = await api.get('/findings', { params })
  return data.findings
}

export async function getAllScans(params = {}) {
  const { data } = await api.get('/scans', { params })
  return data.scans
}

export async function updateFindingStatus(findingId, status) {
  const { data } = await api.post(`/findings/${findingId}/status`, { status })
  return data
}

export async function getScan(scanId) {
  const { data } = await api.get(`/scans/${scanId}`)
  return data.scan
}

export async function getScanFindings(scanId) {
  const { data } = await api.get(`/scans/${scanId}/findings`)
  return data.findings
}

export async function revalidateScan(scanId) {
  const { data } = await api.post(`/scans/${scanId}/revalidate`)
  return data
}

export async function getPolicy() {
  const { data } = await api.get('/policy')
  return data
}

export async function getSandboxHealth() {
  const { data } = await api.get('/health/sandbox')
  return data
}

export async function getSettings() {
  const { data } = await api.get('/settings')
  return data
}

export async function updateSettings(settings) {
  const { data } = await api.post('/settings', settings)
  return data
}

export async function getDbHealth() {
  const { data } = await api.get('/health/db')
  return data
}

export async function getGeminiHealth() {
  const { data } = await api.get('/health/gemini')
  return data
}

export async function submitFeedback(vulnType, outcome, context = {}) {
  const { data } = await api.post('/feedback', {
    vuln_type: vulnType,
    outcome,
    repo_id: context.repo_id,
    pr_number: context.pr_number,
    scan_id: context.scan_id,
  })
  return data
}

export default api