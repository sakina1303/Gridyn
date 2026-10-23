import React, { useEffect, useMemo, useState } from 'react'
import { api, post } from './api/client.js'
import Landing from './Landing.jsx'

const tabs = [
  ['home', 'Overview'], ['site', 'Site setup'], ['readiness', 'Data readiness'],
  ['overview', 'Energy overview'], ['flexibility', 'Flexibility'], ['forecasts', 'Forecasts'],
  ['optimization', 'Optimization'], ['scenarios', 'Scenario lab'],
  ['experiments', 'Experiments'], ['report', 'Research report'],
]

const titles = Object.fromEntries(tabs)
const sourceLabel = value => value ? 'Synthetic' : 'Observed'
const shortId = value => value ? `${value.slice(0, 8)}…` : 'No run'
const titleCase = value => value?.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase()) || 'Unknown'

function fmt(value, digits = 2) {
  return value == null || Number.isNaN(Number(value)) ? '—' : Number(value).toFixed(digits)
}

function Notice({ children, tone = 'info' }) {
  return <div className={`notice ${tone}`}>{children}</div>
}

function Metric({ label, value, unit, note }) {
  return <div className="metric"><span>{label}</span><strong>{value}{unit && <small> {unit}</small>}</strong>{note && <em>{note}</em>}</div>
}

function Status({ children, tone = 'muted' }) {
  return <span className={`status status-${tone}`}><i aria-hidden="true" />{children}</span>
}

function EvidenceRow({ label, status, detail, tone = 'muted' }) {
  return <div className="evidence-row"><div><strong>{label}</strong><small>{detail}</small></div><Status tone={tone}>{status}</Status></div>
}

function Panel({ eyebrow, title, children, aside }) {
  return <section className="panel"><div className="panel-head"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>{aside}</div>{children}</section>
}

function LinePlot({ series, labels }) {
  const width = 760, height = 230, pad = 28
  const all = series.flatMap(item => item.values)
  if (!all.length) return <Notice>No interval data for this chart.</Notice>
  const max = Math.max(1, ...all)
  const count = Math.max(...series.map(item => item.values.length))
  const points = values => values.map((value, index) => {
    const x = pad + index * (width - 2 * pad) / Math.max(1, count - 1)
    const y = height - pad - value * (height - 2 * pad) / max
    return `${x},${y}`
  }).join(' ')
  return <div className="chart-wrap"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={labels}>
    {[0, .25, .5, .75, 1].map(fraction => <g key={fraction}><line x1={pad} x2={width - pad}
      y1={height - pad - fraction * (height - 2 * pad)} y2={height - pad - fraction * (height - 2 * pad)}
      className="grid-line" /><text x="0" y={height - pad - fraction * (height - 2 * pad) + 4}>{fmt(max * fraction, 0)}</text></g>)}
    {series.map(item => <polyline key={item.name} points={points(item.values)} fill="none" stroke={item.color}
      strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />)}
  </svg><div className="legend">{series.map(item => <span key={item.name}><i style={{ background: item.color }} />{item.name}</span>)}</div></div>
}

export default function App() {
  const [showWorkspace, setShowWorkspace] = useState(() => window.location.hash === '#workspace')
  const [tab, setTab] = useState('home')
  const [site, setSite] = useState(null)
  const [dataset, setDataset] = useState(null)
  const [apiOnline, setApiOnline] = useState(null)
  const [scenarioLabel, setScenarioLabel] = useState('Not selected')
  const [quality, setQuality] = useState(null)
  const [observations, setObservations] = useState([])
  const [assessment, setAssessment] = useState(null)
  const [measurementSensitivity, setMeasurementSensitivity] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [forecastStudy, setForecastStudy] = useState(null)
  const [optimization, setOptimization] = useState(null)
  const [recommendation, setRecommendation] = useState(null)
  const [scenario, setScenario] = useState(null)
  const [stressOutcome, setStressOutcome] = useState(null)
  const [experiment, setExperiment] = useState(null)
  const [experimentProtocol, setExperimentProtocol] = useState('paired_missingness.json')
  const [report, setReport] = useState(null)
  const [latestRunId, setLatestRunId] = useState(null)
  const [latestVisibleRunId, setLatestVisibleRunId] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [siteForm, setSiteForm] = useState({ name: 'Synthetic campus', timezone: 'Asia/Kolkata',
    importLimit: 250, exportLimit: 40, pvCapacity: 80, battery: true, batteryCapacity: 100,
    batteryInitial: 50, batteryCharge: 25, batteryDischarge: 25 })
  const [assetForm, setAssetForm] = useState({ ev: false, evRequired: 20, evPower: 10,
    pump: false, pumpPower: 4, pumpRuntime: 1, pumpMinRun: 2,
    hvac: false, hvacMin: 2, hvacMax: 8,
    windowStart: '2026-01-01T05:00:00Z', windowEnd: '2026-01-01T12:00:00Z' })
  const [csvResolution, setCsvResolution] = useState('15')
  const [datasetForm, setDatasetForm] = useState({ start: '2026-01-01T00:00:00Z', count: 192, seed: 7,
    weather: 'clear', load: 'normal' })
  const [assessmentForm, setAssessmentForm] = useState({ start: 96, duration: 4, direction: 'down' })
  const [objective, setObjective] = useState('peak')
  const [importRate, setImportRate] = useState('')
  const [exportCredit, setExportCredit] = useState('')
  const [scenarioLimit, setScenarioLimit] = useState(200)
  const [scenarioBatteryLimit, setScenarioBatteryLimit] = useState('')

  useEffect(() => {
    const syncView = () => setShowWorkspace(window.location.hash === '#workspace')
    window.addEventListener('hashchange', syncView)
    window.addEventListener('popstate', syncView)
    return () => {
      window.removeEventListener('hashchange', syncView)
      window.removeEventListener('popstate', syncView)
    }
  }, [])

  function openWorkspace() {
    window.location.hash = 'workspace'
    setShowWorkspace(true)
    window.scrollTo({ top: 0 })
  }

  function openSite() {
    window.history.pushState(null, '', window.location.pathname + window.location.search)
    setShowWorkspace(false)
    window.scrollTo({ top: 0 })
  }

  useEffect(() => {
    let active = true
    Promise.all([api('/v1/health'), api('/v1/sites')]).then(async ([, result]) => {
      if (!active) return
      setApiOnline(true)
      const saved = localStorage.getItem('energy_lab_site_id')
      const found = result.sites.find(item => item.site_id === saved) || result.sites.at(-1)
      if (found) {
        setSite(found)
        setScenarioLimit(found.config.grid.import_limit_kw)
      }
      const savedDataset = localStorage.getItem('energy_lab_dataset_id')
      if (found && savedDataset) {
        try {
          const meta = await api(`/v1/datasets/${savedDataset}`)
          if (meta.site_id === found.site_id && active) {
            setDataset(meta)
            setScenarioLabel(localStorage.getItem('energy_lab_scenario_label') || 'Not selected')
            const observed = await api(`/v1/datasets/${savedDataset}/observations`)
            if (active) setObservations(observed.records)
          }
        } catch {
          localStorage.removeItem('energy_lab_dataset_id')
        }
      }
    }).catch(() => { if (active) setApiOnline(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    const runId = latestRunId || optimization?.run_id || assessment?.run_id
    if (tab !== 'report' || !runId) return
    let active = true
    setReport(null)
    api(`/v1/reports/${runId}`).then(value => { if (active) setReport(value) })
      .catch(() => { if (active) setReport(null) })
    return () => { active = false }
  }, [tab, latestRunId, optimization?.run_id, assessment?.run_id])

  async function run(label, task) {
    setBusy(label); setError('')
    try { await task() }
    catch (err) { setError(err.message || String(err)) }
    finally { setBusy('') }
  }

  const siteId = site?.site_id
  const datasetId = dataset?.dataset_id
  const synthetic = dataset?.synthetic
  const recordsByQuantity = useMemo(() => {
    const groups = {}
    for (const row of observations) (groups[row.quantity] ||= []).push(row)
    return groups
  }, [observations])

  async function createSite(event) {
    event.preventDefault()
    await run('Creating site', async () => {
      const payload = { name: siteForm.name, timezone: siteForm.timezone,
        grid: { import_limit_kw: Number(siteForm.importLimit), export_limit_kw: Number(siteForm.exportLimit) },
        pv: { ac_capacity_kw: Number(siteForm.pvCapacity), allow_curtailment: true },
        battery: siteForm.battery ? {
          nominal_capacity_kwh: Number(siteForm.batteryCapacity), min_soc_fraction: .1, max_soc_fraction: .9,
          initial_energy_kwh: Number(siteForm.batteryInitial), max_charge_kw: Number(siteForm.batteryCharge),
          max_discharge_kw: Number(siteForm.batteryDischarge), charge_efficiency: .9, discharge_efficiency: .9,
        } : null,
        evs: assetForm.ev ? [{ asset_id: 'ev-1', window: { start: assetForm.windowStart, end: assetForm.windowEnd },
          required_energy_kwh: Number(assetForm.evRequired), max_power_kw: Number(assetForm.evPower) }] : [],
        pumps: assetForm.pump ? [{ asset_id: 'pump-1', window: { start: assetForm.windowStart, end: assetForm.windowEnd },
          rated_power_kw: Number(assetForm.pumpPower), required_runtime_hours: Number(assetForm.pumpRuntime),
          minimum_run_intervals: Number(assetForm.pumpMinRun) }] : [],
        hvacs: assetForm.hvac ? [{ asset_id: 'hvac-1', windows: [{ start: assetForm.windowStart, end: assetForm.windowEnd }],
          min_power_kw: Number(assetForm.hvacMin), max_power_kw: Number(assetForm.hvacMax) }] : [],
      }
      const created = await post('/v1/sites', payload)
      setSite(created); localStorage.setItem('energy_lab_site_id', created.site_id)
      setScenarioLimit(created.config.grid.import_limit_kw)
      setScenarioBatteryLimit('')
      localStorage.removeItem('energy_lab_dataset_id')
      localStorage.removeItem('energy_lab_scenario_label')
      setDataset(null); setQuality(null); setObservations([]); setAssessment(null); setOptimization(null)
      setForecast(null); setForecastStudy(null); setRecommendation(null); setScenario(null); setStressOutcome(null); setMeasurementSensitivity(null); setReport(null); setLatestRunId(null); setLatestVisibleRunId(null)
      setScenarioLabel('Not selected')
      setTab('readiness')
    })
  }

  async function makeSynthetic() {
    if (!siteId) return
    await run('Generating synthetic data', async () => {
      const created = await post(`/v1/sites/${siteId}/synthetic-datasets`, {
        start_utc: datasetForm.start, interval_count: Number(datasetForm.count), seed: Number(datasetForm.seed),
        weather_scenario: datasetForm.weather, load_scenario: datasetForm.load,
      })
      setDataset(created); setQuality(null); setAssessment(null); setOptimization(null)
      setForecast(null); setForecastStudy(null); setRecommendation(null); setScenario(null); setStressOutcome(null); setMeasurementSensitivity(null); setReport(null); setLatestRunId(null); setLatestVisibleRunId(null)
      const label = `${titleCase(datasetForm.weather)} PV / ${titleCase(datasetForm.load)} load`
      setScenarioLabel(label)
      localStorage.setItem('energy_lab_scenario_label', label)
      localStorage.setItem('energy_lab_dataset_id', created.dataset_id)
      const observed = await api(`/v1/datasets/${created.dataset_id}/observations`)
      setObservations(observed.records)
    })
  }

  async function uploadCsv(event) {
    const file = event.target.files?.[0]
    if (!file || !siteId) return
    await run('Importing CSV', async () => {
      const form = new FormData(); form.append('file', file); form.append('interval_minutes', csvResolution)
      form.append('source', file.name)
      const created = await api(`/v1/sites/${siteId}/datasets`, { method: 'POST', body: form })
      const meta = await api(`/v1/datasets/${created.dataset_id}`)
      setDataset(meta); setQuality(null); setAssessment(null); setOptimization(null)
      setForecast(null); setForecastStudy(null); setRecommendation(null); setScenario(null); setStressOutcome(null); setMeasurementSensitivity(null); setReport(null); setLatestRunId(null); setLatestVisibleRunId(null)
      setScenarioLabel('Observed dataset')
      localStorage.setItem('energy_lab_scenario_label', 'Observed dataset')
      localStorage.setItem('energy_lab_dataset_id', created.dataset_id)
      const observed = await api(`/v1/datasets/${created.dataset_id}/observations`)
      setObservations(observed.records)
    })
  }

  async function validateData() {
    if (!datasetId) return
    await run('Checking data readiness', async () => {
      const brief = await post(`/v1/datasets/${datasetId}/validate`, {})
      setQuality(await api(`/v1/quality-reports/${brief.quality_report_id}`))
    })
  }

  async function assess() {
    if (!siteId || !datasetId) return
    await run('Solving joint envelope', async () => {
      const response = await post(`/v1/sites/${siteId}/flexibility-assessments`, {
        dataset_id: datasetId, start_index: Number(assessmentForm.start),
        duration_intervals: Number(assessmentForm.duration), direction: assessmentForm.direction,
      })
      setAssessment(await api(`/v1/runs/${response.run_id}`))
      setMeasurementSensitivity(null)
      setLatestRunId(response.run_id)
      setLatestVisibleRunId(response.run_id)
    })
  }

  async function inspectMeasurementSensitivity() {
    if (!assessment?.run_id) return
    await run('Testing measurement sensitivity', async () => {
      setMeasurementSensitivity(await api(`/v1/runs/${assessment.run_id}/measurement-sensitivity`))
    })
  }

  async function makeForecast() {
    if (!siteId || !datasetId) return
    await run('Issuing forecast', async () => {
      const issue = new Date(new Date(dataset.start_utc).getTime() + 24 * 60 * 60 * 1000).toISOString()
      const result = await post(`/v1/sites/${siteId}/forecasts`, { dataset_id: datasetId,
        target: 'fixed_load_kw', issue_at_utc: issue, horizon_intervals: 96, method: 'previous_day' })
      setForecast(result)
    })
  }

  async function compareForecastDecisions() {
    if (!siteId || !datasetId) return
    await run('Comparing forecast decisions', async () => {
      const count = Math.round((new Date(dataset.end_utc) - new Date(dataset.start_utc)) / 900000)
      if (count < 97) throw new Error('At least 97 consecutive 15-minute synthetic intervals are needed.')
      const issueIndex = count >= 8 * 96 ? 7 * 96 : 96
      const horizon = Math.min(96, count - issueIndex)
      const result = await post(`/v1/sites/${siteId}/forecast-decision-studies`, {
        dataset_id: datasetId, issue_index: issueIndex, horizon_intervals: horizon,
      })
      setForecastStudy(result)
      setLatestRunId(result.run_id)
      setLatestVisibleRunId(result.run_id)
    })
  }

  async function optimize() {
    if (!siteId || !datasetId) return
    await run('Optimizing schedule', async () => {
      const count = Number(dataset.interval_count || ((new Date(dataset.end_utc) - new Date(dataset.start_utc)) / 900000))
      const body = { dataset_id: datasetId, objective_profile: objective }
      if (objective === 'cost') {
        if (importRate === '' || exportCredit === '') throw new Error('Enter explicit import and export rates for a cost run.')
        body.import_tariff_inr_per_kwh = Array(count).fill(Number(importRate))
        body.export_credit_inr_per_kwh = Array(count).fill(Number(exportCredit))
      }
      const response = await post(`/v1/sites/${siteId}/optimization-runs`, body)
      const completed = await api(`/v1/runs/${response.run_id}`)
      setOptimization(completed)
      setLatestRunId(response.run_id)
      setLatestVisibleRunId(response.run_id)
      setRecommendation(completed.status === 'succeeded' ? await api(`/v1/recommendations?run_id=${response.run_id}`) : null)
    })
  }

  async function loadRecommendation() {
    if (!optimization) return
    await run('Checking recommendation', async () => {
      setRecommendation(await api(`/v1/recommendations?run_id=${optimization.run_id}`))
    })
  }

  async function compareScenario() {
    if (!siteId || !datasetId) return
    await run('Comparing scenario', async () => {
      const change = { dataset_id: datasetId, grid_import_limit_kw: Number(scenarioLimit) }
      if (scenarioBatteryLimit !== '') change.battery_max_discharge_kw = Number(scenarioBatteryLimit)
      const created = await post(`/v1/sites/${siteId}/scenarios`, change)
      const result = await post(`/v1/sites/${siteId}/scenarios/${created.scenario_id}/compare`, {})
      setScenario(result)
      setStressOutcome(null)
      setLatestVisibleRunId(result.run_id)
      setScenarioLabel(`Grid cap ${scenarioLimit} kW${scenarioBatteryLimit === '' ? '' : ` / battery ${scenarioBatteryLimit} kW`}`)
    })
  }

  async function compareStressAware() {
    if (!siteId || !scenario?.outcome?.scenario_id) return
    await run('Testing fixed schedules across stresses', async () => {
      const result = await post(`/v1/sites/${siteId}/scenarios/${scenario.outcome.scenario_id}/stress-aware-compare`, {})
      setStressOutcome(result)
    })
  }

  async function runExperiment() {
    await run('Running paired protocol', async () => {
      const seedSet = experimentProtocol === 'paired_missingness.json' ? [7] : [7, 11, 19]
      const created = await post('/v1/experiments', { protocol_id: experimentProtocol, seed_set: seedSet })
      setExperiment(await api(`/v1/experiments/${created.experiment_id}`))
    })
  }

  const qualityClaims = quality?.readiness?.claims || []
  const qualityIssues = quality?.quality?.issues || []
  const pv = (recordsByQuantity.pv_available_kw || []).map(row => row.value)
  const critical = (recordsByQuantity.critical_load_kw || []).map(row => row.value)
  const fixed = (recordsByQuantity.fixed_load_kw || []).map(row => row.value)
  const chartSeries = [
    { name: 'PV available', color: '#b8c9b9', values: pv },
    { name: 'Critical demand', color: '#baaa88', values: critical },
    { name: 'Fixed demand', color: '#80a7a2', values: fixed },
  ].filter(item => item.values.length)
  const currentRun = forecastStudy?.run_id === latestRunId ? forecastStudy
    : optimization?.run_id === latestRunId ? optimization
    : assessment?.run_id === latestRunId ? assessment : optimization || assessment
  const seriesQuality = quality?.quality?.series || []
  const seriesFor = names => seriesQuality.find(item => names.includes(item.quantity))
  const hasSignal = names => names.some(name => (recordsByQuantity[name] || []).length > 0)
  const inventory = [
    ['Site import', ['grid_import_kw']], ['PV', ['pv_available_kw', 'pv_used_kw']],
    ['Critical + fixed load', ['critical_load_kw', 'fixed_load_kw']],
    ['Battery SOC', ['battery_soc_kwh']], ['EV', ['ev_power_kw']],
    ['Pump', ['pump_power_kw']], ['HVAC', ['hvac_power_kw']],
    ['Tariff', []],
  ]
  const configuredAssets = site ? [
    site.config.pv?.ac_capacity_kw > 0 && 'PV', site.config.battery && 'Battery',
    site.config.evs?.length && 'EV', site.config.pumps?.length && 'Pump',
    site.config.hvacs?.length && 'HVAC',
  ].filter(Boolean) : []
  const operationalPass = assessment?.passes?.find(item => item.mode === 'operational')
  const latestExperimentCases = experiment?.runs?.flatMap(run => run.results || []) || []

  if (!showWorkspace) return <Landing onOpenWorkspace={openWorkspace} />

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark" aria-hidden="true"><span /><span /><span /></div><div><strong>FLEXGRID</strong><small>Research prototype</small></div></div>
      <div className="side-label">WORKSPACE / 01</div>
      <nav aria-label="Primary sections">{tabs.map(([id, label], index) => <button key={id}
        className={tab === id ? 'active' : ''} onClick={() => setTab(id)} aria-current={tab === id ? 'page' : undefined}><span className="nav-number">{String(index + 1).padStart(2, '0')}</span><span>{label}</span><b aria-hidden="true">↗</b></button>)}</nav>
      <div className="sidebar-footer"><button className="footer-link" onClick={openSite}>Back to site <span>↗</span></button><button className={tab === 'settings' ? 'footer-link active' : 'footer-link'} onClick={() => setTab('settings')}>Settings <span>↗</span></button><div className="research-status"><span className="status-dot" /> Research status <strong>Advisory · local</strong><small>No equipment control</small></div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="top-identity"><span className="eyebrow">FLEXGRID <span className="crumb">/</span> RESEARCH PROTOTYPE</span><h1>{titles[tab] || 'Settings'}</h1><p>Simulation-first advisory research workspace</p></div>
        <div className="top-actions"><Status tone={apiOnline ? 'ok' : apiOnline === false ? 'bad' : 'muted'}>{apiOnline ? latestVisibleRunId ? 'Run available' : 'Simulation not run' : apiOnline === false ? 'API unavailable' : 'Checking service'}</Status><span className={`pill ${synthetic ? 'synthetic' : ''}`}>{dataset ? `${sourceLabel(synthetic)} data` : 'No dataset'}</span></div></header>
      {error && <Notice tone="error"><strong>Could not complete the step.</strong> {error}</Notice>}
      {busy && <Notice tone="info"><span className="spinner" /> {busy}…</Notice>}
      <div className="content">
        <div className="context-strip"><div><span>ACTIVE SITE</span><strong>{site?.name || 'Not configured'}</strong></div><div><span>DATASET</span><strong>{dataset ? shortId(datasetId) : 'Not selected'}</strong></div><div><span>CURRENT SCENARIO</span><strong>{scenarioLabel}</strong></div><div><span>LATEST RUN</span><strong title={latestVisibleRunId || ''}>{shortId(latestVisibleRunId)}</strong></div></div>
        {tab === 'home' && <>
          <div className="page-intro"><div><p className="eyebrow">RESEARCH WORKSPACE / OVERVIEW</p><h2>From site evidence to validated response.</h2><p>Inspect what the model knows, run controlled synthetic studies, and keep every conclusion tied to a dataset and run.</p></div><button className="secondary" onClick={() => setTab(site ? 'readiness' : 'site')}>{site ? 'Open data readiness' : 'Configure a site'} <span>↗</span></button></div>
          <div className="overview-grid">
            <Panel eyebrow="SITE / MODEL" title="Site status" aside={<Status tone={site ? 'ok' : 'muted'}>{site ? 'Configured' : 'Not configured'}</Status>}><div className="overview-value">{site?.name || 'No site selected'}</div><p className="subtle">{site ? `${site.config.timezone} · ${configuredAssets.length ? configuredAssets.join(', ') : 'No flexible assets configured'}` : 'Define grid limits, PV, and optional flexible assets to begin.'}</p></Panel>
            <Panel eyebrow="EVIDENCE / DATA" title="Data readiness" aside={<Status tone={quality ? 'ok' : 'muted'}>{quality ? 'Assessed' : 'Not assessed'}</Status>}><div className="overview-value">{dataset ? `${sourceLabel(synthetic)} dataset` : 'No dataset'}</div><p className="subtle">{dataset ? `${dataset.interval_minutes} minute intervals · ${quality ? `${qualityIssues.length} recorded quality issues` : 'quality not assessed'}` : 'Generate a synthetic study or import observed CSV.'}</p></Panel>
            <Panel eyebrow="ASSETS / CONFIGURATION" title="Available assets"><div className="asset-list">{configuredAssets.length ? configuredAssets.map(item => <span className="asset-chip" key={item}>{item}</span>) : <span className="empty-inline">No configured assets</span>}</div><p className="subtle">Configuration is a declared model boundary, not evidence of delivered flexibility.</p></Panel>
            <Panel eyebrow="REFERENCE / B0" title="Current baseline"><div className="overview-value">{recommendation?.baseline_peak_kw == null ? 'No result available' : <>{fmt(recommendation.baseline_peak_kw)} <small>kW peak</small></>}</div><p className="subtle">B0: earliest declared EV and pump service, minimum HVAC power, battery idle.</p></Panel>
            <Panel eyebrow="JOINT RESPONSE" title="Flexibility envelope"><div className="overview-value">{operationalPass?.sustained_kw == null ? 'Simulation not run' : <>{fmt(operationalPass.sustained_kw)} <small>kW {assessment.direction}</small></>}</div><p className="subtle">{assessment ? `${assessment.duration_intervals} × 15 minute response · ${titleCase(assessment.status)}` : 'The operational response is calculated over response and recovery.'}</p></Panel>
            <Panel eyebrow="EVIDENCE / RELIABILITY" title="Reliability status"><div className="overview-value">Unknown</div><p className="subtle">No calibrated held-out reliability evidence is attached to this workspace.</p></Panel>
          </div>
          <Panel eyebrow="LATEST STUDY" title="Experiment trace" aside={<button className="text-button" onClick={() => setTab('experiments')}>Open experiments ↗</button>}><div className="trace-row"><div><span className="eyebrow">PROTOCOL</span><strong>{experiment?.protocol_id || 'No experiment run'}</strong></div><div><span className="eyebrow">CASES</span><strong>{experiment ? latestExperimentCases.length : '—'}</strong></div><div><span className="eyebrow">STATUS</span><strong>{experiment ? titleCase(experiment.status) : 'No result available'}</strong></div></div></Panel>
          {optimization && <Panel eyebrow="DECISION / ADVISORY" title="Research recommendation" aside={<button className="text-button" onClick={loadRecommendation} disabled={!!busy}>Refresh evidence ↗</button>}><p className="intro">Derived from an independently validated run. No controls are sent to equipment.</p>{recommendation ? <div className="detail-grid"><div><span>STATUS</span><strong>{titleCase(recommendation.status)}</strong></div><div><span>SIMULATED PEAK CHANGE</span><strong>{recommendation.simulated_peak_reduction_kw == null ? 'No result available' : `${fmt(recommendation.simulated_peak_reduction_kw)} kW`}</strong></div><div><span>RELIABILITY</span><strong>{titleCase(recommendation.reliability)}</strong></div></div> : <button className="secondary" onClick={loadRecommendation} disabled={!!busy}>Inspect recommendation</button>}</Panel>}
        </>}
        {tab === 'site' && <>
          <Panel eyebrow="01 / MODEL BOUNDARY" title="Define the site" aside={<span className="tag">Units are explicit</span>}>
            <p className="intro">Create a local advisory model for one site. The project name is still provisional; this name labels your site only.</p>
            <form className="form-grid" onSubmit={createSite}>
              <label className="wide">Site name<input value={siteForm.name} onChange={e => setSiteForm({ ...siteForm, name: e.target.value })} required /></label>
              <label>Site timezone<input value={siteForm.timezone} onChange={e => setSiteForm({ ...siteForm, timezone: e.target.value })} required /></label>
              <label>Grid import limit · kW<input type="number" min="0" value={siteForm.importLimit} onChange={e => setSiteForm({ ...siteForm, importLimit: e.target.value })} /></label>
              <label>Grid export limit · kW<input type="number" min="0" value={siteForm.exportLimit} onChange={e => setSiteForm({ ...siteForm, exportLimit: e.target.value })} /></label>
              <label>PV AC capacity · kW<input type="number" min="0" value={siteForm.pvCapacity} onChange={e => setSiteForm({ ...siteForm, pvCapacity: e.target.value })} /></label>
              <label className="check wide"><input type="checkbox" checked={siteForm.battery} onChange={e => setSiteForm({ ...siteForm, battery: e.target.checked })} /> Include a battery</label>
              {siteForm.battery && <><label>Battery capacity · kWh<input type="number" min="1" value={siteForm.batteryCapacity} onChange={e => setSiteForm({ ...siteForm, batteryCapacity: e.target.value })} /></label>
                <label>Initial energy · kWh<input type="number" min="0" value={siteForm.batteryInitial} onChange={e => setSiteForm({ ...siteForm, batteryInitial: e.target.value })} /></label>
                <label>Max charge · kW<input type="number" min="0" value={siteForm.batteryCharge} onChange={e => setSiteForm({ ...siteForm, batteryCharge: e.target.value })} /></label>
                <label>Max discharge · kW<input type="number" min="0" value={siteForm.batteryDischarge} onChange={e => setSiteForm({ ...siteForm, batteryDischarge: e.target.value })} /></label></>}
              <div className="wide asset-divider"><h3>Optional flexible assets</h3><p>Declared windows use UTC timestamps and must fall within the simulated study period.</p></div>
              <label>Window start · UTC<input value={assetForm.windowStart} onChange={e => setAssetForm({ ...assetForm, windowStart: e.target.value })} /></label>
              <label>Window end · UTC<input value={assetForm.windowEnd} onChange={e => setAssetForm({ ...assetForm, windowEnd: e.target.value })} /></label>
              <label className="check wide"><input type="checkbox" checked={assetForm.ev} onChange={e => setAssetForm({ ...assetForm, ev: e.target.checked })} /> Include an EV session</label>
              {assetForm.ev && <><label>EV due energy · kWh<input type="number" min="0" value={assetForm.evRequired} onChange={e => setAssetForm({ ...assetForm, evRequired: e.target.value })} /></label><label>Charger max · kW<input type="number" min="0" value={assetForm.evPower} onChange={e => setAssetForm({ ...assetForm, evPower: e.target.value })} /></label></>}
              <label className="check wide"><input type="checkbox" checked={assetForm.pump} onChange={e => setAssetForm({ ...assetForm, pump: e.target.checked })} /> Include a pump</label>
              {assetForm.pump && <><label>Pump rated power · kW<input type="number" min="0" value={assetForm.pumpPower} onChange={e => setAssetForm({ ...assetForm, pumpPower: e.target.value })} /></label><label>Required runtime · h<input type="number" min="0" step="0.25" value={assetForm.pumpRuntime} onChange={e => setAssetForm({ ...assetForm, pumpRuntime: e.target.value })} /></label><label>Minimum run · intervals<input type="number" min="1" value={assetForm.pumpMinRun} onChange={e => setAssetForm({ ...assetForm, pumpMinRun: e.target.value })} /></label></>}
              <label className="check wide"><input type="checkbox" checked={assetForm.hvac} onChange={e => setAssetForm({ ...assetForm, hvac: e.target.checked })} /> Include conservative HVAC flexibility</label>
              {assetForm.hvac && <><label>HVAC minimum · kW<input type="number" min="0" value={assetForm.hvacMin} onChange={e => setAssetForm({ ...assetForm, hvacMin: e.target.value })} /></label><label>HVAC maximum · kW<input type="number" min="0" value={assetForm.hvacMax} onChange={e => setAssetForm({ ...assetForm, hvacMax: e.target.value })} /></label></>}
              <div className="form-actions wide"><button className="primary" disabled={!!busy}>Save site</button></div>
            </form>
          </Panel>
          {site && <Panel eyebrow="CURRENT SITE" title={site.name}><div className="metric-row"><Metric label="Import limit" value={fmt(site.config.grid.import_limit_kw, 0)} unit="kW" /><Metric label="PV capacity" value={fmt(site.config.pv.ac_capacity_kw, 0)} unit="kW" /><Metric label="Timezone" value={site.config.timezone} /></div></Panel>}
        </>}
        {tab === 'readiness' && <>
          <Panel eyebrow="02 / EVIDENCE" title="Bring data into view" aside={<span className="tag">Claims are assessed separately</span>}>
            {!site ? <Notice>Create a site first.</Notice> : <><p className="intro">Generate clearly labeled synthetic truth and observations, or import your own timestamped CSV. CSV columns: <code>start,end,quantity,value,unit</code>.</p>
              <div className="split"><div className="subpanel"><h3>Generate a synthetic study</h3><div className="form-grid compact">
                <label>Start · UTC<input value={datasetForm.start} onChange={e => setDatasetForm({ ...datasetForm, start: e.target.value })} /></label>
                <label>Intervals · 15 min<input type="number" min="1" max="960" value={datasetForm.count} onChange={e => setDatasetForm({ ...datasetForm, count: e.target.value })} /></label>
                <label>Root seed<input type="number" value={datasetForm.seed} onChange={e => setDatasetForm({ ...datasetForm, seed: e.target.value })} /></label>
                <label>Weather<select value={datasetForm.weather} onChange={e => setDatasetForm({ ...datasetForm, weather: e.target.value })}><option value="clear">Clear</option><option value="cloudy">Cloudy</option><option value="monsoon_like">Monsoon-like</option></select></label>
                <label>Load<select value={datasetForm.load} onChange={e => setDatasetForm({ ...datasetForm, load: e.target.value })}><option value="normal">Normal</option><option value="high_cooling">High cooling</option><option value="low_activity">Low activity</option></select></label>
                <button className="primary" onClick={makeSynthetic} disabled={!!busy}>Generate dataset</button></div></div>
                <div className="subpanel"><h3>Import observed CSV</h3><p>Readings are normalized to UTC and canonical kW/kWh before quality checks. Files remain in this local workspace.</p><label className="upload-resolution">Declared interval<select value={csvResolution} onChange={e => setCsvResolution(e.target.value)}><option value="15">15 min</option><option value="30">30 min</option><option value="60">60 min</option></select></label><label className="upload">Choose CSV<input type="file" accept=".csv,text/csv" onChange={uploadCsv} disabled={!!busy} /></label></div></div></>}
          </Panel>
          {dataset && <Panel eyebrow="SELECTED DATASET" title={synthetic ? 'Synthetic research data' : 'Observed site data'}><div className="metric-row"><Metric label="Resolution" value={dataset.interval_minutes} unit="min" /><Metric label="Starts" value={dataset.start_utc?.slice(0, 16)} /><Metric label="Records" value={observations.length} /></div><div className="actions"><button className="primary" onClick={validateData} disabled={!!busy}>Assess readiness</button></div></Panel>}
          <Panel eyebrow="SIGNAL INVENTORY" title="What the model actually has" aside={<Status tone={dataset ? 'ok' : 'muted'}>{dataset ? `${sourceLabel(synthetic)} source` : 'No dataset'}</Status>}>
            <p className="intro">A configured asset does not imply that its telemetry was observed. Availability below reflects the selected dataset only.</p>
            <div className="evidence-grid">{inventory.map(([label, names]) => {
              const present = hasSignal(names)
              const series = seriesFor(names)
              const detail = names.length ? series ? `${fmt(series.coverage * 100, 0)}% coverage · ${series.missing_count} missing intervals` : present ? 'Available · assess readiness for coverage' : 'No corresponding data series' : 'No verified tariff attached'
              return <EvidenceRow key={label} label={label} detail={detail} status={present ? sourceLabel(synthetic) : 'Unknown'} tone={present ? synthetic ? 'synthetic' : 'ok' : 'muted'} />
            })}</div>
            <p className="footnote">Inferred signals: none in this inventory. Missing signals remain Unknown.</p>
          </Panel>
          {quality && <Panel eyebrow="CLAIM READINESS" title="What this data supports"><div className="claim-list">{qualityClaims.map(item => <div className="claim" key={item.claim}><span className={`state ${item.state}`}>{item.state.replaceAll('_', ' ')}</span><div><strong>{item.claim.replaceAll('_', ' ')}</strong><p>{item.explanation}</p>{item.next_measurement && <small>Next measurement: {item.next_measurement}</small>}</div></div>)}</div><p className="footnote">{qualityIssues.length} quality issue{qualityIssues.length === 1 ? '' : 's'} recorded. Raw values are retained.</p></Panel>}
        </>}
        {tab === 'overview' && <Panel eyebrow="03 / PHYSICAL SERIES" title="Energy overview" aside={<span className="tag">Average kW per interval</span>}>
          {!dataset ? <Notice>Select a dataset first.</Notice> : <><p className="intro">These are analyst-visible observations. The plot does not substitute missing intervals or imply measured benefits for synthetic data.</p><LinePlot series={chartSeries} labels="PV available, critical and fixed load by interval in kW" /></>}
        </Panel>}
        {tab === 'flexibility' && <>
          <Panel eyebrow="04 / JOINT RESPONSE" title="Sustained flexibility envelope"><p className="intro">The current assessment is a <strong>perfect-information synthetic oracle</strong>. It solves one joint schedule over the response and recovery horizon. Tested reliability remains unknown.</p>
            {!synthetic ? <Notice>Select a synthetic dataset to run this oracle assessment. Observed-only data is not treated as hidden truth.</Notice> : <div className="form-grid compact"><label>Start interval<input type="number" min="0" value={assessmentForm.start} onChange={e => setAssessmentForm({ ...assessmentForm, start: e.target.value })} /></label><label>Duration · intervals<input type="number" min="1" value={assessmentForm.duration} onChange={e => setAssessmentForm({ ...assessmentForm, duration: e.target.value })} /></label><label>Direction<select value={assessmentForm.direction} onChange={e => setAssessmentForm({ ...assessmentForm, direction: e.target.value })}><option value="down">Down · reduce grid import</option><option value="up">Up · increase grid import</option></select></label><button className="primary" onClick={assess} disabled={!!busy}>Assess response</button></div>}
          </Panel>
          {assessment && <Panel eyebrow="ASSESSMENT RESULT" title={assessment.status === 'succeeded' ? 'Feasible response' : 'No validated response'} aside={<Status tone={assessment.status === 'succeeded' ? 'ok' : 'bad'}>{titleCase(assessment.status)}</Status>}>
            <div className="metric-row"><Metric label="Baseline / B0" value={recommendation?.baseline_peak_kw == null ? 'No result available' : fmt(recommendation.baseline_peak_kw)} unit={recommendation?.baseline_peak_kw == null ? null : 'kW peak'} /><Metric label="Downward flexibility" value={assessment.direction === 'down' ? fmt(operationalPass?.sustained_kw) : 'Not assessed'} unit={assessment.direction === 'down' ? 'kW' : null} /><Metric label="Upward flexibility" value={assessment.direction === 'up' ? fmt(operationalPass?.sustained_kw) : 'Not assessed'} unit={assessment.direction === 'up' ? 'kW' : null} /><Metric label="Duration" value={assessment.duration_intervals ? fmt(assessment.duration_intervals * .25, 2) : 'Unknown'} unit="h" /></div>
            <div className="section-rule"><span>MODEL PASSES</span></div><div className="metric-row">{(assessment.passes || []).map(item => <Metric key={item.mode} label={item.mode} value={fmt(item.sustained_kw)} unit="kW" note={item.status} />)}<Metric label="Tested reliability" value="Unknown" note="No calibrated held-out evidence" /></div>
            {assessment.reason && <Notice tone="error">{assessment.reason}</Notice>}
            <div className="detail-grid"><div><span>RECOVERY REQUIREMENT</span><strong>{assessment.recovery_import_delta_kwh == null ? 'Unknown' : `${fmt(assessment.recovery_import_delta_kwh)} kWh import delta`}</strong></div><div><span>OPERATIONAL CONSTRAINTS</span><strong>Critical service, asset windows, grid limits, terminal SOC</strong></div><div><span>METHOD</span><strong>{assessment.method || 'Unknown'}</strong></div></div>
            {assessment.status === 'succeeded' && operationalPass?.sustained_kw > 0 && <div className="actions"><button className="secondary" onClick={inspectMeasurementSensitivity} disabled={!!busy}>Inspect next-measurement sensitivity</button></div>}
            {measurementSensitivity && <><div className="section-rule"><span>DECLARED SYNTHETIC BOUNDS</span></div><p className="footnote">{measurementSensitivity.result.ranking_basis}. {measurementSensitivity.result.limitation}. A rank here is a model diagnostic, not a sensor purchase recommendation.</p><div className="claim-list">{measurementSensitivity.result.candidates.map(item => <div className="claim" key={item.measurement}><span className="state usable_with_limitations">{item.rank == null ? 'No distinction' : `Rank ${item.rank}`}</span><div><strong>{item.measurement}</strong><p>{item.declared_range} · {item.failed_count}/{item.scenario_count} replay failures</p><small>Maximum response shortfall: {item.maximum_response_shortfall_kw == null ? 'Unknown' : `${fmt(item.maximum_response_shortfall_kw)} kW`} · Measurement burden: Unknown</small></div></div>)}</div></>}
          </Panel>}
        </>}
        {tab === 'forecasts' && <Panel eyebrow="05 / ISSUE-TIME CONTRACT" title="Forecasts"><p className="intro">Previous-day persistence uses only observations available by the issue time. A minimum of one preceding day at 15-minute resolution is needed for this view.</p>{!dataset ? <Notice>Select a dataset first.</Notice> : <><button className="primary" onClick={makeForecast} disabled={!!busy}>Forecast fixed load for day 2</button>{forecast && <><div className="metric-row top-gap"><Metric label="Model" value={forecast.forecast.method} /><Metric label="Training observations" value={forecast.forecast.training_count} /><Metric label="Issued" value={forecast.forecast.issued_at_utc?.slice(0, 16)} /></div><LinePlot series={[{ name: 'Forecast fixed load', color: '#79a7e7', values: forecast.forecast.values_kw }]} labels="Issued fixed-load forecast in kW" /></>}</>}</Panel>}
        {tab === 'optimization' && <>
          <Panel eyebrow="06 / VALIDATED SCHEDULE" title="Optimization"><p className="intro">The solver uses shared physical and service constraints. Every candidate is replayed independently before it is shown as validated. Tariff rates are required for a cost run and are never prefilled.</p>
            {!synthetic ? <Notice>Choose a synthetic dataset for a perfect-information research run.</Notice> : <div className="form-grid compact"><label>Objective<select value={objective} onChange={e => setObjective(e.target.value)}><option value="peak">Minimize grid peak</option><option value="solar_use">Minimize PV curtailment</option><option value="cost">Minimize stated cost</option></select></label>
              {objective === 'cost' && <><label>Import rate · INR/kWh<input type="number" value={importRate} onChange={e => setImportRate(e.target.value)} placeholder="Enter applicable rate" /></label><label>Export credit · INR/kWh<input type="number" value={exportCredit} onChange={e => setExportCredit(e.target.value)} placeholder="Enter applicable credit" /></label></>}
              <button className="primary" onClick={optimize} disabled={!!busy}>Solve schedule</button></div>}
          </Panel>
          {optimization && <Panel eyebrow="SOLVER RESULT" title={optimization.status === 'succeeded' ? 'Independently validated' : 'No validated schedule'} aside={<Status tone={optimization.status === 'succeeded' ? 'ok' : 'bad'}>{titleCase(optimization.status)}</Status>}>
            <div className="metric-row"><Metric label="Objective" value={fmt(optimization.objective_value)} unit={optimization.objective_unit} /><Metric label="Solver status" value={titleCase(optimization.solver_status)} /><Metric label="Termination" value={titleCase(optimization.solver_termination)} /><Metric label="Validation" value={optimization.status === 'succeeded' ? 'Passed' : 'Not passed'} /><Metric label="Runtime" value="Unknown" note="Not returned by this API" /><Metric label="Optimality gap" value="Unknown" note="Not returned by this API" /></div>
            <div className="detail-grid top-gap"><div><span>ACTIVE CONSTRAINTS</span><strong>Power balance · grid bounds · asset service · SOC</strong></div><div><span>MAX BALANCE RESIDUAL</span><strong>{optimization.max_balance_residual_kw == null ? 'Unknown' : `${fmt(optimization.max_balance_residual_kw, 6)} kW`}</strong></div><div><span>RUN ID</span><strong title={optimization.run_id}>{shortId(optimization.run_id)}</strong></div></div>
            {optimization.reason && <Notice tone={optimization.status === 'succeeded' ? 'info' : 'error'}>{optimization.reason}</Notice>}
            {optimization.grid_import_kw && <><div className="section-rule"><span>VALIDATED SCHEDULE / GRID IMPORT · kW</span></div><LinePlot series={[{ name: 'Grid import', color: '#a9c6bd', values: optimization.grid_import_kw }]} labels="Validated grid import in kilowatts by interval" />{optimization.battery_energy_kwh?.some(value => value != null) && <><div className="section-rule"><span>BATTERY ENERGY · kWh</span></div><LinePlot series={[{ name: 'Battery energy', color: '#c3aa7d', values: optimization.battery_energy_kwh.filter(value => value != null) }]} labels="Battery energy in kilowatt-hours by interval" /></>}</>}
          </Panel>}
        </>}
        {tab === 'recommendations' && <Panel eyebrow="07 / EVIDENCE CARD" title="Recommendations"><p className="intro">This page derives facts from a validated run. It does not send controls to any asset.</p>{!optimization ? <Notice>Run optimization first.</Notice> : <><button className="primary" onClick={loadRecommendation} disabled={!!busy}>Inspect recommendation</button>{recommendation && <div className="result-card"><span className={`state ${recommendation.status === 'research_candidate' ? 'usable_with_limitations' : 'insufficient'}`}>{recommendation.status.replaceAll('_', ' ')}</span><h3>{recommendation.action || recommendation.reason}</h3>{recommendation.simulated_peak_reduction_kw != null && <div className="metric-row"><Metric label="Baseline peak" value={fmt(recommendation.baseline_peak_kw)} unit="kW" /><Metric label="Optimized peak" value={fmt(recommendation.optimized_peak_kw)} unit="kW" /><Metric label="Simulated reduction" value={fmt(recommendation.simulated_peak_reduction_kw)} unit="kW" /></div>}<p className="footnote">Reliability: {recommendation.reliability || 'unknown'} · Provenance: {recommendation.provenance || 'unavailable'} · Run: {recommendation.schedule_run_id || optimization.run_id}</p></div>}</>}</Panel>}
        {tab === 'scenarios' && <>
          <Panel eyebrow="08 / CONDITIONS" title="Scenario lab"><p className="intro">Explore declared synthetic conditions, then compare B0, B1 and optimization on the same truth under changed site limits. A separate stress-aware candidate test uses declared training and evaluation stresses. Separate generated datasets are different truth cases.</p>
            <div className="scenario-presets"><button onClick={() => { setDatasetForm({ ...datasetForm, weather: 'clear', load: 'normal' }); setTab('readiness') }}>Normal conditions <span>Prepare dataset ↗</span></button><button onClick={() => { setDatasetForm({ ...datasetForm, weather: 'clear', load: 'high_cooling' }); setTab('readiness') }}>High demand <span>Prepare dataset ↗</span></button><button onClick={() => { setDatasetForm({ ...datasetForm, weather: 'cloudy', load: 'normal' }); setTab('readiness') }}>Cloudy PV <span>Prepare dataset ↗</span></button><button onClick={() => setTab('experiments')}>Missing data <span>Open paired study ↗</span></button><button onClick={compareForecastDecisions} disabled={!!busy || !synthetic}>Forecast error <span>Compare realized decisions ↗</span></button>{site?.config.battery ? <button onClick={() => { setScenarioLimit(site.config.grid.import_limit_kw); setScenarioBatteryLimit(fmt(site.config.battery.max_discharge_kw * .5, 2)) }}>Battery uncertainty <span>Prepare deterministic derating ↗</span></button> : <div>Battery uncertainty <span>Configure a battery first</span></div>}</div>
          </Panel>
          <Panel eyebrow="PAIRED / SAME TRUTH" title="Constrained grid comparison" aside={<Status tone={scenario ? 'ok' : 'muted'}>{scenario ? 'Run available' : 'Not run'}</Status>}><p className="intro">This path keeps the selected synthetic truth fixed. Grid and battery limit changes are deterministic stress cases, not calibrated uncertainty. An infeasible outcome stays visible.</p>{!synthetic ? <Notice>Select synthetic data first.</Notice> : <div className="form-grid compact"><label>Scenario import limit · kW<input type="number" min="0" value={scenarioLimit} onChange={e => setScenarioLimit(e.target.value)} /></label>{site?.config.battery && <label>Battery discharge limit · kW<input type="number" min="0" value={scenarioBatteryLimit} placeholder="Use site limit" onChange={e => setScenarioBatteryLimit(e.target.value)} /></label>}<button className="primary" onClick={compareScenario} disabled={!!busy}>Compare scenario</button></div>}
            <div className="comparison-table"><div className="table-head"><span>STRATEGY</span><span>PEAK IMPORT</span><span>STATE</span></div><div><strong>No flexibility action / B0</strong><span>{scenario?.outcome?.baseline_peak_kw == null ? 'No result available' : `${fmt(scenario.outcome.baseline_peak_kw)} kW`}</span><Status tone={scenario?.outcome?.baseline_status === 'valid' ? 'ok' : 'muted'}>{scenario ? titleCase(scenario.outcome.baseline_status) : 'Not run'}</Status></div><div><strong>Rule based / B1</strong><span>{scenario?.outcome?.rule_peak_kw == null ? 'No result available' : `${fmt(scenario.outcome.rule_peak_kw)} kW`}</span><Status tone={scenario?.outcome?.rule_status === 'valid' ? 'ok' : 'muted'}>{scenario ? titleCase(scenario.outcome.rule_status) : 'Not run'}</Status></div><div><strong>Optimization</strong><span>{scenario?.outcome?.scenario_peak_kw == null ? 'No result available' : `${fmt(scenario.outcome.scenario_peak_kw)} kW`}</span><Status tone={scenario?.outcome?.scenario_status === 'optimal_validated' ? 'ok' : 'bad'}>{scenario ? titleCase(scenario.outcome.scenario_status) : 'Not run'}</Status></div><div><strong>Stress-aware candidate</strong><span>{stressOutcome?.outcome?.reference_peak_kw == null ? 'No result available' : `${fmt(stressOutcome.outcome.reference_peak_kw)} kW`}</span><Status tone={stressOutcome?.outcome?.status === 'selected' && stressOutcome.outcome.evaluation.every(item => item.status === 'valid') ? 'ok' : stressOutcome ? 'bad' : 'muted'}>{stressOutcome ? `${titleCase(stressOutcome.outcome.status)} · ${stressOutcome.outcome.evaluation.filter(item => item.status === 'valid').length}/${stressOutcome.outcome.evaluation.length} stress pass` : 'Not run'}</Status></div></div>
            {scenario && <div className="actions"><button className="secondary" onClick={compareStressAware} disabled={!!busy}>Test stress-aware candidates</button></div>}
            {stressOutcome && <><p className="footnote">{stressOutcome.outcome.method}. {stressOutcome.outcome.evidence_label}. Selected: {stressOutcome.outcome.selected_source || 'None'}.</p><div className="claim-list">{stressOutcome.outcome.evaluation.map(item => <div className="claim" key={item.scenario_id}><span className={`state ${item.status === 'valid' ? 'usable' : 'insufficient'}`}>{item.status}</span><div><strong>{titleCase(item.scenario_id)}</strong><p>{item.peak_import_kw == null ? item.reason : `Peak import: ${fmt(item.peak_import_kw)} kW`}</p></div></div>)}</div>{stressOutcome.outcome.reason && <Notice tone="error">{stressOutcome.outcome.reason}</Notice>}</>}
            {scenario?.outcome?.baseline_status === 'infeasible' && <Notice>B0: {scenario.outcome.baseline_reason || 'The declared schedule is infeasible under this scenario.'}</Notice>}
            {scenario?.outcome?.rule_status === 'infeasible' && <Notice>B1: {scenario.outcome.rule_reason}</Notice>}
            {scenario?.outcome?.reason && <Notice tone="error">{scenario.outcome.reason}</Notice>}
            {scenario && <p className="footnote">Paired truth checksum: {scenario.outcome.truth_sha256?.slice(0, 16)}… · Peak delta: {scenario.outcome.peak_delta_kw == null ? 'Unknown' : `${fmt(scenario.outcome.peak_delta_kw)} kW`}.</p>}
          </Panel>
          <Panel eyebrow="ISSUE TIME / HELD-OUT TRUTH" title="Forecast decision value" aside={<Status tone={forecastStudy?.status === 'succeeded' ? 'ok' : 'muted'}>{forecastStudy ? titleCase(forecastStudy.status) : 'Not run'}</Status>}>
            <p className="intro">Compare previous-day persistence and a fixed-seed tree on the same synthetic future and peak objective. Forecasts see observations only up to the issue time. A seven-day history is needed for the tree; short histories remain unavailable.</p>
            {!synthetic ? <Notice>Select synthetic data first.</Notice> : <button className="secondary" onClick={compareForecastDecisions} disabled={!!busy}>Compare forecast decisions</button>}
            {forecastStudy && <><div className="comparison-table"><div className="table-head"><span>METHOD</span><span>MAE / PEAK REGRET</span><span>STATE</span></div>{forecastStudy.methods.map(item => <div key={item.method}><strong>{titleCase(item.method)}</strong><span>{item.forecast_mae_kw == null ? 'Unknown' : `${fmt(item.forecast_mae_kw)} kW`} / {item.regret == null ? 'Unknown' : `${fmt(item.regret)} kW`}</span><Status tone={item.realized_objective != null ? 'ok' : 'bad'}>{titleCase(item.solver_status)}</Status></div>)}</div><div className="claim-list top-gap">{forecastStudy.methods.map(item => <div className="claim" key={item.method}><span className={`state ${item.failure_reason ? 'insufficient' : 'usable'}`}>{item.failure_reason ? 'Unavailable' : 'Evaluated'}</span><div><strong>{titleCase(item.method)}</strong><p>{item.failure_reason || `Realized peak: ${fmt(item.realized_objective)} kW · Oracle: ${fmt(item.oracle_objective)} kW`}</p><small>Training cutoff: {item.training_end_utc || 'Unknown'}</small></div></div>)}</div><p className="footnote">{forecastStudy.limitation} Run {shortId(forecastStudy.run_id)} · Truth {forecastStudy.truth_sha256.slice(0, 16)}…</p></>}
          </Panel>
        </>}
        {tab === 'experiments' && <Panel eyebrow="09 / REPRODUCIBLE PROTOCOL" title="Experiments"><p className="intro">Run a checked-in synthetic protocol. Compare missingness, one-signal restoration or multiple observation stresses. Each variant uses paired truth; failed and abstained cases remain visible.</p><div className="form-grid compact"><label>Protocol<select value={experimentProtocol} onChange={event => { setExperimentProtocol(event.target.value); setExperiment(null) }}><option value="paired_missingness.json">Missingness and resolution</option><option value="paired_measurement_restoration.json">One-signal restoration</option><option value="paired_observation_stress.json">Missingness, bias and noise sweep</option></select></label><button className="primary" onClick={runExperiment} disabled={!!busy}>Run protocol</button></div>{experiment && <><div className="claim-list top-gap">{experiment.runs.flatMap(run => run.results.map(item => <div className="claim" key={item.observation_dataset_id}><span className={`state ${item.status === 'delivered' ? 'usable' : 'insufficient'}`}>{item.status}</span><div><strong>{item.observation_dataset_id}</strong><p>Estimated: {fmt(item.estimated_sustained_kw)} kW · Realized: {fmt(item.realized_sustained_kw)} kW · Overstatement: {fmt(item.overstatement_kw)} kW</p><small>Truth checksum: {run.truth_sha256.slice(0, 16)}…</small></div></div>))}</div>{experiment.runs.some(run => run.measurement_effects?.length) && <><div className="section-rule"><span>MEASUREMENT SENSITIVITY</span></div><p className="footnote">Synthetic, one signal at a time. “Assessment enabled” means restoring that signal allowed an estimate; it does not prove field value or rank sensor purchases. Overstatement and interval-width improvements stay Unknown when they cannot be measured.</p><div className="claim-list">{experiment.runs.flatMap(run => (run.measurement_effects || []).map(item => <div className="claim" key={`${run.run_id}-${item.quantity}`}><span className="state usable_with_limitations">Synthetic</span><div><strong>{titleCase(item.quantity)}</strong><p>Without: {titleCase(item.without_status)} · Restored: {titleCase(item.restored_status)} · Assessment enabled: {item.assessment_enabled ? 'Yes' : 'No'}</p><small>Overstatement reduction: {item.overstatement_reduction_kw == null ? 'Unknown' : `${fmt(item.overstatement_reduction_kw)} kW`} · Interval-width reduction: Unknown · Seed: {run.seed}</small></div></div>))}</div></>}</>}</Panel>}
        {tab === 'report' && <>
          <Panel eyebrow="10 / TRACEABLE EXPORT" title="Research report" aside={<Status tone={report?.synthetic ? 'synthetic' : 'muted'}>{report?.headline_label || 'No report'}</Status>}><p className="intro">Every computed metric is linked to a run, dataset, unit, and calculation. Missing analytical sections remain unavailable.</p>{!currentRun ? <Notice>Complete an assessment or optimization run first.</Notice> : <><div className="metric-row"><Metric label="Selected run" value={shortId(currentRun.run_id)} /><Metric label="Status" value={titleCase(currentRun.status)} /><Metric label="Source" value={report ? sourceLabel(report.synthetic) : 'Loading'} /></div><div className="actions"><a className="primary link-button" href={`/v1/reports/${currentRun.run_id}?format=markdown`} target="_blank" rel="noreferrer">Open Markdown report</a><a className="secondary link-button" href={`/v1/reports/${currentRun.run_id}?format=json`} target="_blank" rel="noreferrer">Open JSON</a></div></>}</Panel>
          {currentRun && <div className="report-grid">
            <Panel eyebrow="RESEARCH QUESTION" title="What can this site credibly provide?"><p className="report-copy">Estimate a feasible sustained grid response from declared assets and data, while exposing evidence gaps and uncertainty.</p></Panel>
            <Panel eyebrow="DATASET / READINESS" title="Evidence boundary"><div className="report-facts"><EvidenceRow label="Dataset" detail={report?.dataset_id || datasetId || 'Unavailable'} status={report ? sourceLabel(report.synthetic) : 'Unknown'} tone={report?.synthetic ? 'synthetic' : 'muted'} /><EvidenceRow label="Readiness" detail={quality ? `${qualityClaims.length} claim-specific assessments` : 'Assessment not run'} status={quality ? 'Assessed' : 'Unknown'} tone={quality ? 'ok' : 'muted'} /></div></Panel>
            <Panel eyebrow="COMPARATOR / B0" title="Baseline"><p className="report-copy">{report?.sections?.baseline?.definition || 'No baseline report available.'}</p><p className="footnote">A B0 peak appears only after a successful recommendation comparison.</p></Panel>
            <Panel eyebrow="ISSUE TIME / METHODS" title="Forecast & uncertainty"><div className="report-facts"><EvidenceRow label="Forecast" detail={report?.sections?.forecast_and_uncertainty?.methods ? `${report.sections.forecast_and_uncertainty.methods.length} paired methods at ${report.sections.forecast_and_uncertainty.issue_at_utc}` : forecast ? `${forecast.forecast.method} · separate session result` : 'No forecast attached to this run'} status={report?.sections?.forecast_and_uncertainty?.methods ? 'Evaluated' : forecast ? 'Session only' : 'Unknown'} tone={report?.sections?.forecast_and_uncertainty?.methods ? 'synthetic' : 'muted'} /><EvidenceRow label="Uncertainty" detail={report?.sections?.forecast_and_uncertainty?.reason || 'No calibrated evidence'} status="Unknown" /></div></Panel>
            <Panel eyebrow="RESPONSE / ENVELOPE" title="Flexibility"><div className="report-facts">{report?.sections?.envelope?.length ? report.sections.envelope.map(item => <EvidenceRow key={item.mode} label={titleCase(item.mode)} detail={item.sustained_kw == null ? 'No result available' : `${fmt(item.sustained_kw)} kW sustained`} status={titleCase(item.status)} tone={item.status === 'optimal' ? 'ok' : 'muted'} />) : <p className="report-copy">No flexibility assessment attached to this run.</p>}</div></Panel>
            <Panel eyebrow="SCHEDULE / VALIDATION" title="Optimization"><div className="report-facts"><EvidenceRow label="Solver" detail={report?.sections?.optimization?.termination || 'No optimization attached to this run'} status={report?.sections?.optimization?.status ? titleCase(report.sections.optimization.status) : 'Unknown'} tone={report?.sections?.optimization?.status === 'optimal_validated' ? 'ok' : 'muted'} /><EvidenceRow label="Objective" detail={report?.metrics?.find(item => item.name === 'optimized_objective')?.value == null ? 'No result available' : `${fmt(report.metrics.find(item => item.name === 'optimized_objective').value)} ${report.metrics.find(item => item.name === 'optimized_objective').unit}`} status={report?.metrics?.some(item => item.name === 'optimized_objective') ? 'Validated' : 'Unknown'} tone={report?.metrics?.some(item => item.name === 'optimized_objective') ? 'ok' : 'muted'} /></div></Panel>
            <Panel eyebrow="STUDIES / FAILURES" title="Experiment results"><p className="report-copy">{experiment ? `${latestExperimentCases.length} paired cases in a separate session protocol: ${experiment.protocol_id}.` : 'No experiment run in this session.'}</p>{experiment && <p className="footnote">{latestExperimentCases.filter(item => item.status !== 'delivered').length} cases abstained or failed; their states are retained.</p>}<div className="section-rule"><span>CURRENT RUN FAILURE</span></div><p className="report-copy">{report?.sections?.failed_or_infeasible || 'None recorded for this run.'}</p></Panel>
            <Panel eyebrow="ACTION / EVIDENCE" title="Recommendation"><p className="report-copy">{report?.sections?.recommendation?.action || report?.sections?.recommendation?.reason || 'No validated recommendation available.'}</p><p className="footnote">Reliability: {titleCase(report?.sections?.recommendation?.reliability)}. No equipment control.</p></Panel>
            <Panel eyebrow="MEASUREMENT / NEXT" title="Next measurements">{report?.sections?.next_measurements?.length ? <ul className="report-list">{report.sections.next_measurements.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="report-copy">No claim-specific measurement request is available for this run.</p>}{report?.sections?.measurement_sensitivity && <><p className="footnote">Synthetic model sensitivity under declared bounds. Field priority and measurement burden remain unknown.</p><ul className="report-list">{report.sections.measurement_sensitivity.result.candidates.map(item => <li key={item.measurement}>{item.rank == null ? 'No distinction' : `Rank ${item.rank}`}: {item.measurement} · {item.failed_count}/{item.scenario_count} replay failures</li>)}</ul></>}</Panel>
            <Panel eyebrow="BOUNDARY / CLAIMS" title="Limitations"><ul className="report-list">{(report?.limitations || ['No report available.']).map(item => <li key={item}>{item}</li>)}</ul></Panel>
            <Panel eyebrow="TRACE / REPLAY" title="Reproducibility"><div className="report-facts"><EvidenceRow label="Run ID" detail={currentRun.run_id} status={titleCase(currentRun.status)} /><EvidenceRow label="Dataset hash" detail={report?.dataset_hashes?.[datasetId]?.slice(0, 24) || 'Unknown'} status={report ? 'Recorded' : 'Unknown'} tone={report ? 'ok' : 'muted'} /><EvidenceRow label="Canonical model" detail={report?.canonical_model_version || 'Unknown'} status={report ? 'Recorded' : 'Unknown'} tone={report ? 'ok' : 'muted'} /></div></Panel>
          </div>}
        </>}
        {tab === 'settings' && <Panel eyebrow="WORKSPACE / SETTINGS" title="Local research configuration"><div className="detail-grid"><div><span>SERVICE</span><strong>{apiOnline ? 'Connected to local API' : 'Unavailable'}</strong></div><div><span>ACTIVE SITE</span><strong>{site?.name || 'Not configured'}</strong></div><div><span>DATA SOURCE</span><strong>{dataset ? sourceLabel(synthetic) : 'None selected'}</strong></div></div><p className="footnote">This prototype stores metadata in the local service. It does not control equipment or connect to live utility systems.</p></Panel>}
      </div>
    </main>
  </div>
}
