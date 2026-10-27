import React, { useState } from 'react'
import { auth } from './client.js'

export default function SignIn({ onBack }) {
  const [mode, setMode] = useState('sign-in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    setBusy(true); setError(''); setMessage('')
    try {
      const result = mode === 'sign-up'
        ? await auth.auth.signUp({ email, password, options: { emailRedirectTo: window.location.origin + '/?open=workspace' } })
        : await auth.auth.signInWithPassword({ email, password })
      if (result.error) throw result.error
      if (mode === 'sign-up' && !result.data.session) setMessage('Check your email to confirm your account, then sign in.')
    } catch (cause) {
      setError(cause.message || 'Sign-in failed. Please try again.')
    } finally { setBusy(false) }
  }

  return <div className="auth-shell"><div className="auth-card">
    <button className="auth-back" onClick={onBack}>← Back to Gridyn</button>
    <span className="auth-kicker">GRIDYN / PRIVATE RESEARCH WORKSPACE</span>
    <h1>{mode === 'sign-up' ? 'Create your workspace.' : 'Welcome back.'}</h1>
    <p>Save your site model, datasets, research runs, and reports in your own workspace. Gridyn remains advisory and does not control equipment.</p>
    <form onSubmit={submit}>
      <label>Email<input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required /></label>
      <label>Password<input type="password" autoComplete={mode === 'sign-up' ? 'new-password' : 'current-password'} minLength={6} value={password} onChange={event => setPassword(event.target.value)} required /></label>
      {error && <div className="auth-feedback error" role="alert">{error}</div>}
      {message && <div className="auth-feedback" role="status">{message}</div>}
      <button className="auth-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'sign-up' ? 'Create account ↗' : 'Sign in ↗'}</button>
    </form>
    <button className="auth-switch" onClick={() => { setMode(mode === 'sign-up' ? 'sign-in' : 'sign-up'); setError(''); setMessage('') }}>
      {mode === 'sign-up' ? 'Already have an account? Sign in' : 'New here? Create an account'}
    </button>
    <small>Only upload data you are authorized to share for research analysis. Field savings and reliability remain unknown.</small>
  </div></div>
}
