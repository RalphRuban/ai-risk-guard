import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6">
          <div className="max-w-md w-full text-center">
            <span className="eyebrow">Something went wrong</span>
            <h1 className="k-title">An unexpected error occurred</h1>
            <p className="k-sub">
              The page failed to render. Reload to continue, or try again shortly.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-6 px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors"
            >
              Reload page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
