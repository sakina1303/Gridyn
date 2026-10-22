import React, { useEffect, useMemo, useState } from 'react'
import { api, post } from './api/client.js'

const tabs = [
  ['site', 'Site setup'], ['readiness', 'Data readiness'], ['overview', 'Energy overview'],
  ['flexibility', 'Flexibility'], ['forecasts', 'Forecasts'], ['optimization', 'Optimization'],
  ['recommendations', 'Recommendations'], ['scenarios', 'Scenario lab'],
  ['experiments', 'Experiments'], ['report', 'Research report'],
]

function fmt(value, digits = 2) {
  return value == null || Number.isNaN(Number(value)) ? '—' : Number(value).toFixed(digits)
}

function Notice({ children, tone = 'info' }) {
  return <div className={`notice ${tone}`}>{children}</div>
}

function Metric({ label, value, unit, note }) {
  return <div className="metric"><span>{label}</span><strong>{value}{unit && <small> {unit}</small>}</strong>{note && <em>{note}</em>}</div>
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
  const [tab, setTab] = useState('site')
  const [site, setSite] = useState(null)
  const [dataset, setDataset] = useState(null)
  const [quality, setQuality] = useState(null)
  const [observations, setObservations] = useState([])
  const [assessment, setAssessment] = useState(null)
  const [forecast, setForecast] = useState(null)
  const [optimization, setOptimization] = useState(null)
  const [recommendation, setRecommendation] = useState(null)
  const [scenario, setScenario] = useState(null)
  const [experiment, setExperiment] = useState(null)
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

  useEffect(() => {
    api('/v1/sites').then(result => {
      const saved = localStorage.getItem('energy_lab_site_id')
      const found = result.sites.find(item => item.site_id === saved) || result.sites.at(-1)
      if (found) setSite(found)
    }).catch(() => {})
  }, [])

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
      setDataset(null); setQuality(null); setObservations([]); setAssessment(null); setOptimization(null)
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
      setOptimization(await api(`/v1/runs/${response.run_id}`))
      setRecommendation(null)
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
      const created = await post(`/v1/sites/${siteId}/scenarios`, {
        dataset_id: datasetId, grid_import_limit_kw: Number(scenarioLimit) })
      setScenario(await post(`/v1/sites/${siteId}/scenarios/${created.scenario_id}/compare`, {}))
    })
  }

  async function runExperiment() {
    await run('Running paired protocol', async () => {
      const created = await post('/v1/experiments', { protocol_id: 'paired_missingness.json', seed_set: [7] })
      setExperiment(await api(`/v1/experiments/${created.experiment_id}`))
    })
  }

  const qualityClaims = quality?.readiness?.claims || []
  const qualityIssues = quality?.quality?.issues || []
  const pv = (recordsByQuantity.pv_available_kw || []).map(row => row.value)
  const critical = (recordsByQuantity.critical_load_kw || []).map(row => row.value)
  const fixed = (recordsByQuantity.fixed_load_kw || []).map(row => row.value)
  const chartSeries = [
    { name: 'PV available', color: '#49a980', values: pv },
    { name: 'Critical demand', color: '#f5aa58', values: critical },
    { name: 'Fixed demand', color: '#79a7e7', values: fixed },
  ].filter(item => item.values.length)

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">◈</div><div><strong>ENERGY LAB</strong><small>Research workspace</small></div></div>
      <div className="side-label">WORKSPACE</div>
      <nav aria-label="Primary sections">{tabs.map(([id, label], index) => <button key={id}
        className={tab === id ? 'active' : ''} onClick={() => setTab(id)}><span className="nav-number">{String(index + 1).padStart(2, '0')}</span>{label}</button>)}</nav>
      <div className="sidebar-footer"><span className="status-dot" /> Advisory simulation<br /><small>No equipment control</small></div>
    </aside>
    <main className="main">
      <header className="topbar"><div><span className="eyebrow">SIMULATION-FIRST RESEARCH PROTOTYPE</span><h1>{tabs.find(item => item[0] === tab)?.[1]}</h1></div>
        <div className="top-actions">{dataset && <span className={`pill ${synthetic ? 'synthetic' : ''}`}>{synthetic ? 'SIMULATION DATA' : 'OBSERVED DATA'}</span>}
          {site && <span className="site-chip">{site.name}</span>}</div></header>
      {error && <Notice tone="error"><strong>Could not complete the step.</strong> {error}</Notice>}
      {busy && <Notice tone="info"><span className="spinner" /> {busy}…</Notice>}
      <div className="content">
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
                <label>Intervals · 15 min<input type="number" min="1" max="672" value={datasetForm.count} onChange={e => setDatasetForm({ ...datasetForm, count: e.target.value })} /></label>
                <label>Root seed<input type="number" value={datasetForm.seed} onChange={e => setDatasetForm({ ...datasetForm, seed: e.target.value })} /></label>
                <label>Weather<select value={datasetForm.weather} onChange={e => setDatasetForm({ ...datasetForm, weather: e.target.value })}><option value="clear">Clear</option><option value="cloudy">Cloudy</option><option value="monsoon_like">Monsoon-like</option></select></label>
                <label>Load<select value={datasetForm.load} onChange={e => setDatasetForm({ ...datasetForm, load: e.target.value })}><option value="normal">Normal</option><option value="high_cooling">High cooling</option><option value="low_activity">Low activity</option></select></label>
                <button className="primary" onClick={makeSynthetic} disabled={!!busy}>Generate dataset</button></div></div>
                <div className="subpanel"><h3>Import observed CSV</h3><p>Readings are normalized to UTC and canonical kW/kWh before quality checks. Files remain in this local workspace.</p><label className="upload-resolution">Declared interval<select value={csvResolution} onChange={e => setCsvResolution(e.target.value)}><option value="15">15 min</option><option value="30">30 min</option><option value="60">60 min</option></select></label><label className="upload">Choose CSV<input type="file" accept=".csv,text/csv" onChange={uploadCsv} disabled={!!busy} /></label></div></div></>}
          </Panel>
          {dataset && <Panel eyebrow="SELECTED DATASET" title={synthetic ? 'Synthetic research data' : 'Observed site data'}><div className="metric-row"><Metric label="Resolution" value={dataset.interval_minutes} unit="min" /><Metric label="Starts" value={dataset.start_utc?.slice(0, 16)} /><Metric label="Records" value={observations.length} /></div><div className="actions"><button className="primary" onClick={validateData} disabled={!!busy}>Assess readiness</button></div></Panel>}
          {quality && <Panel eyebrow="CLAIM READINESS" title="What this data supports"><div className="claim-list">{qualityClaims.map(item => <div className="claim" key={item.claim}><span className={`state ${item.state}`}>{item.state.replaceAll('_', ' ')}</span><div><strong>{item.claim.replaceAll('_', ' ')}</strong><p>{item.explanation}</p>{item.next_measurement && <small>Next measurement: {item.next_measurement}</small>}</div></div>)}</div><p className="footnote">{qualityIssues.length} quality issue{qualityIssues.length === 1 ? '' : 's'} recorded. Raw values are retained.</p></Panel>}
        </>}
        {tab === 'overview' && <Panel eyebrow="03 / PHYSICAL SERIES" title="Energy overview" aside={<span className="tag">Average kW per interval</span>}>
          {!dataset ? <Notice>Select a dataset first.</Notice> : <><p className="intro">These are analyst-visible observations. The plot does not substitute missing intervals or imply measured benefits for synthetic data.</p><LinePlot series={chartSeries} labels="PV available, critical and fixed load by interval in kW" /></>}
        </Panel>}
        {tab === 'flexibility' && <>
          <Panel eyebrow="04 / JOINT RESPONSE" title="Sustained flexibility envelope"><p className="intro">The current assessment is a <strong>perfect-information synthetic oracle</strong>. It solves one joint schedule over the response and recovery horizon. Tested reliability remains unknown.</p>
            {!synthetic ? <Notice>Select a synthetic dataset to run this oracle assessment. Observed-only data is not treated as hidden truth.</Notice> : <div className="form-grid compact"><label>Start interval<input type="number" min="0" value={assessmentForm.start} onChange={e => setAssessmentForm({ ...assessmentForm, start: e.target.value })} /></label><label>Duration · intervals<input type="number" min="1" value={assessmentForm.duration} onChange={e => setAssessmentForm({ ...assessmentForm, duration: e.target.value })} /></label><label>Direction<select value={assessmentForm.direction} onChange={e => setAssessmentForm({ ...assessmentForm, direction: e.target.value })}><option value="down">Down · reduce grid import</option><option value="up">Up · increase grid import</option></select></label><button className="primary" onClick={assess} disabled={!!busy}>Assess response</button></div>}
          </Panel>
          {assessment && <Panel eyebrow="ASSESSMENT RESULT" title={assessment.status === 'succeeded' ? 'Feasible response' : 'No validated response'}><div className="metric-row">{(assessment.passes || []).map(item => <Metric key={item.mode} label={item.mode} value={fmt(item.sustained_kw)} unit="kW" note={item.status} />)}<Metric label="Tested reliable" value="Unknown" note="No calibrated held-out evidence" /></div>{assessment.reason && <Notice tone="error">{assessment.reason}</Notice>}<p className="footnote">Method: {assessment.method}. Recovery import delta: {fmt(assessment.recovery_import_delta_kwh)} kWh.</p></Panel>}
        </>}
        {tab === 'forecasts' && <Panel eyebrow="05 / ISSUE-TIME CONTRACT" title="Forecasts"><p className="intro">Previous-day persistence uses only observations available by the issue time. A minimum of one preceding day at 15-minute resolution is needed for this view.</p>{!dataset ? <Notice>Select a dataset first.</Notice> : <><button className="primary" onClick={makeForecast} disabled={!!busy}>Forecast fixed load for day 2</button>{forecast && <><div className="metric-row top-gap"><Metric label="Model" value={forecast.forecast.method} /><Metric label="Training observations" value={forecast.forecast.training_count} /><Metric label="Issued" value={forecast.forecast.issued_at_utc?.slice(0, 16)} /></div><LinePlot series={[{ name: 'Forecast fixed load', color: '#79a7e7', values: forecast.forecast.values_kw }]} labels="Issued fixed-load forecast in kW" /></>}</>}</Panel>}
        {tab === 'optimization' && <>
          <Panel eyebrow="06 / VALIDATED SCHEDULE" title="Optimization"><p className="intro">The solver uses shared physical and service constraints. Every candidate is replayed independently before it is shown as validated. Tariff rates are required for a cost run and are never prefilled.</p>
            {!synthetic ? <Notice>Choose a synthetic dataset for a perfect-information research run.</Notice> : <div className="form-grid compact"><label>Objective<select value={objective} onChange={e => setObjective(e.target.value)}><option value="peak">Minimize grid peak</option><option value="solar_use">Minimize PV curtailment</option><option value="cost">Minimize stated cost</option></select></label>
              {objective === 'cost' && <><label>Import rate · INR/kWh<input type="number" value={importRate} onChange={e => setImportRate(e.target.value)} placeholder="Enter applicable rate" /></label><label>Export credit · INR/kWh<input type="number" value={exportCredit} onChange={e => setExportCredit(e.target.value)} placeholder="Enter applicable credit" /></label></>}
              <button className="primary" onClick={optimize} disabled={!!busy}>Solve schedule</button></div>}
          </Panel>
          {optimization && <Panel eyebrow="SOLVER RESULT" title={optimization.status === 'succeeded' ? 'Independently validated' : 'No validated schedule'}><div className="metric-row"><Metric label="Objective" value={fmt(optimization.objective_value)} unit={optimization.objective_unit} /><Metric label="Solver" value={optimization.solver_status} /><Metric label="Max balance residual" value={fmt(optimization.max_balance_residual_kw, 6)} unit="kW" /></div>{optimization.reason && <Notice tone="error">{optimization.reason}</Notice>}{optimization.grid_import_kw && <LinePlot series={[{ name: 'Grid import', color: '#79a7e7', values: optimization.grid_import_kw }, { name: 'Battery energy', color: '#49a980', values: optimization.battery_energy_kwh.filter(value => value != null) }]} labels="Validated grid import in kW and battery energy in kWh by interval" />}</Panel>}
        </>}
        {tab === 'recommendations' && <Panel eyebrow="07 / EVIDENCE CARD" title="Recommendations"><p className="intro">This page derives facts from a validated run. It does not send controls to any asset.</p>{!optimization ? <Notice>Run optimization first.</Notice> : <><button className="primary" onClick={loadRecommendation} disabled={!!busy}>Inspect recommendation</button>{recommendation && <div className="result-card"><span className={`state ${recommendation.status === 'research_candidate' ? 'usable_with_limitations' : 'insufficient'}`}>{recommendation.status.replaceAll('_', ' ')}</span><h3>{recommendation.action || recommendation.reason}</h3>{recommendation.simulated_peak_reduction_kw != null && <div className="metric-row"><Metric label="Baseline peak" value={fmt(recommendation.baseline_peak_kw)} unit="kW" /><Metric label="Optimized peak" value={fmt(recommendation.optimized_peak_kw)} unit="kW" /><Metric label="Simulated reduction" value={fmt(recommendation.simulated_peak_reduction_kw)} unit="kW" /></div>}<p className="footnote">Reliability: {recommendation.reliability || 'unknown'} · Provenance: {recommendation.provenance || 'unavailable'} · Run: {recommendation.schedule_run_id || optimization.run_id}</p></div>}</>}</Panel>}
        {tab === 'scenarios' && <Panel eyebrow="08 / PAIRED COMPARISON" title="Scenario lab"><p className="intro">Change a site constraint while keeping the same synthetic truth. A tighter grid limit can make the comparison infeasible; that failure remains visible.</p>{!synthetic ? <Notice>Select synthetic data first.</Notice> : <div className="form-grid compact"><label>Scenario import limit · kW<input type="number" min="0" value={scenarioLimit} onChange={e => setScenarioLimit(e.target.value)} /></label><button className="primary" onClick={compareScenario} disabled={!!busy}>Compare scenario</button></div>}{scenario && <div className="metric-row top-gap"><Metric label="B0 peak" value={fmt(scenario.outcome.baseline_peak_kw)} unit="kW" /><Metric label="Scenario peak" value={fmt(scenario.outcome.scenario_peak_kw)} unit="kW" /><Metric label="Peak delta" value={fmt(scenario.outcome.peak_delta_kw)} unit="kW" note={scenario.outcome.scenario_status} /></div>}</Panel>}
        {tab === 'experiments' && <Panel eyebrow="09 / REPRODUCIBLE PROTOCOL" title="Experiments"><p className="intro">Run the checked-in paired missingness protocol. It fixes synthetic truth for seed 7, then compares clean, gapped, and 30-minute observations. Failed and abstained cases are retained.</p><button className="primary" onClick={runExperiment} disabled={!!busy}>Run protocol</button>{experiment && <div className="claim-list top-gap">{experiment.runs.flatMap(run => run.results.map(item => <div className="claim" key={item.observation_dataset_id}><span className={`state ${item.status === 'delivered' ? 'usable' : 'insufficient'}`}>{item.status}</span><div><strong>{item.observation_dataset_id}</strong><p>Estimated: {fmt(item.estimated_sustained_kw)} kW · Realized: {fmt(item.realized_sustained_kw)} kW · Overstatement: {fmt(item.overstatement_kw)} kW</p><small>Truth checksum: {run.truth_sha256.slice(0, 16)}…</small></div></div>))}</div>}</Panel>}
        {tab === 'report' && <Panel eyebrow="10 / TRACEABLE EXPORT" title="Research report"><p className="intro">The report links its result to a run and dataset. Synthetic results are labeled on the first page. Missing or failed analytical sections remain unavailable.</p>{!optimization && !assessment ? <Notice>Complete an assessment or optimization run first.</Notice> : <><div className="metric-row"><Metric label="Selected run" value={(optimization || assessment).run_id.slice(0, 12) + '…'} /><Metric label="Status" value={(optimization || assessment).status} /><Metric label="Source" value="Synthetic" /></div><div className="actions"><a className="primary link-button" href={`/v1/reports/${(optimization || assessment).run_id}?format=markdown`} target="_blank" rel="noreferrer">Open Markdown report</a><a className="secondary link-button" href={`/v1/reports/${(optimization || assessment).run_id}?format=json`} target="_blank" rel="noreferrer">Open JSON</a></div></>}</Panel>}
      </div>
    </main>
  </div>
}
