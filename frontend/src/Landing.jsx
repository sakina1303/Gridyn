import React, { useState } from 'react'
import './landing.css'

const chapters = [
  {
    number: '01', label: 'Model the site', title: 'Start with a physical boundary.',
    copy: 'Declare grid limits, solar capacity, storage, and flexible loads. Every interval is represented in explicit kW and kWh.',
    question: 'What assets and constraints are actually in scope?',
    output: 'A site model with named limits and service windows.',
  },
  {
    number: '02', label: 'Read the evidence', title: 'See what the data can support.',
    copy: 'Generate a clearly marked synthetic study or inspect timestamped site readings. Missing signals remain visible instead of being filled with invented certainty.',
    question: 'Which signals are observed, synthetic, or absent?',
    output: 'A signal inventory and claim-specific readiness states.',
  },
  {
    number: '03', label: 'Test the response', title: 'Ask for a sustained response.',
    copy: 'Compare a baseline with a joint schedule across the response and recovery window. Asset service and critical load stay inside the physical model.',
    question: 'How much response is feasible for this duration?',
    output: 'A directional envelope with recovery requirements.',
  },
  {
    number: '04', label: 'Validate the result', title: 'Replay before you report.',
    copy: 'The optimizer proposes a schedule; the simulator checks it independently. The report keeps status, provenance, failed cases, and limits together.',
    question: 'Can the schedule survive physical replay?',
    output: 'A traceable result, or an explicit failure state.',
  },
]

const researchAreas = [
  ['01', 'Site setup', 'Declare grid import and export limits, PV, battery, EV, pump, and conservative HVAC constraints.'],
  ['02', 'Data readiness', 'Separate observed, synthetic, inferred, and unknown signals before making a claim.'],
  ['03', 'Energy overview', 'Inspect the site model, baseline, available assets, and the status of the latest run.'],
  ['04', 'Flexibility', 'Examine upward and downward response, duration, recovery, and operational limits.'],
  ['05', 'Forecasts', 'Compare methods on held-out data; show missing inputs and unavailable methods.'],
  ['06', 'Optimization', 'Propose a schedule, then independently replay it against physical and service constraints.'],
  ['07', 'Scenario lab', 'Compare no action, rules, optimization, and stress-aware candidates on declared scenarios.'],
  ['08', 'Experiments', 'Run reproducible synthetic protocols and inspect separate public-data benchmarks.'],
  ['09', 'Research report', 'Keep methods, provenance, failures, limitations, and next measurements in one trace.'],
]

const researchDetails = [
  {
    title: 'Site setup', state: 'Configuration available in the research code',
    question: 'What can the site physically do?',
    inputs: 'Site timezone; grid import and export limits; PV capacity; battery capacity, power, efficiency and SOC; EV, pump and HVAC service windows.',
    result: 'A typed site model with explicit kW, kWh and 15-minute intervals. The public site has no configured real site.',
  },
  {
    title: 'Data readiness', state: 'Dataset dependent',
    question: 'Which claims does the available data support?',
    inputs: 'Timestamped load, PV, battery SOC, EV, pump, HVAC and tariff signals, with source and missingness recorded.',
    result: 'Claim-specific readiness and observed, synthetic, inferred or unknown provenance. No real-site dataset is connected to this website.',
  },
  {
    title: 'Energy overview', state: 'No public site run',
    question: 'What is happening inside the declared boundary?',
    inputs: 'A site model, dataset and completed simulation run.',
    result: 'Baseline, asset inventory, grid flows, physical balance and run status. Numerical site results remain unavailable here.',
  },
  {
    title: 'Flexibility', state: 'Synthetic research implemented',
    question: 'How much can demand move, in which direction, and for how long?',
    inputs: 'Baseline, response window, asset limits, service needs and recovery period.',
    result: 'Separate upward and downward envelopes with duration, recovery and feasibility. No single flexibility score or field claim.',
  },
  {
    title: 'Forecasts', state: 'Synthetic and public-data checks',
    question: 'How well can the next load and PV intervals be anticipated?',
    inputs: 'Historical observations, issue time, held-out future and a declared method.',
    result: 'Method comparison with error and availability states. Public-data checks are separate from site-specific validation.',
  },
  {
    title: 'Optimization', state: 'Candidate schedules require replay',
    question: 'Can a proposed schedule meet an objective without breaking constraints?',
    inputs: 'Objective, forecasts, grid limits, asset limits and service requirements.',
    result: 'Solver status, schedule, feasibility and independent physical validation. A failed run is reported as a failure.',
  },
  {
    title: 'Scenario lab', state: 'Synthetic comparison',
    question: 'How do decisions change under stress?',
    inputs: 'No action, rule-based, optimization and uncertainty-aware candidates under declared demand, PV and data scenarios.',
    result: 'Side-by-side outcomes and failure states. The site does not claim operational performance from synthetic scenarios.',
  },
  {
    title: 'Experiments', state: 'Reproducible research',
    question: 'Does the method hold up across repeatable tests?',
    inputs: 'Fixed seeds, protocols, synthetic disturbances and separately sourced public benchmark data.',
    result: 'Per-case outcomes, provenance and failed cases. Observed public data supports forecasting checks, not measured site flexibility.',
  },
  {
    title: 'Research report', state: 'Generated after a research run',
    question: 'What can be stated and reproduced?',
    inputs: 'Run ID, dataset ID, methods, validated outputs and limitations.',
    result: 'Traceable metrics, evidence labels, failures, next measurements and reproducibility information. No report is fabricated for this website.',
  },
]

function Mark({ light = false }) {
  return <span className={`landing-mark${light ? ' light' : ''}`} aria-hidden="true"><i /><i /><i /></span>
}

function JourneyVisual({ step }) {
  if (step === 0) return <div className="journey-visual site-visual" role="img" aria-label="Schematic site model connecting grid, PV, battery, and loads">
    <div className="visual-caption">SCHEMATIC / SITE BOUNDARY</div>
    <svg viewBox="0 0 620 300" aria-hidden="true"><path className="connection" d="M94 150H235M385 150h141M310 75v150M170 250h280"/><circle className="hub" cx="310" cy="150" r="58"/><circle className="node" cx="94" cy="150" r="35"/><circle className="node" cx="526" cy="150" r="35"/><circle className="node" cx="310" cy="55" r="35"/><circle className="node" cx="310" cy="245" r="35"/><text x="310" y="155" textAnchor="middle">SITE</text><text x="94" y="155" textAnchor="middle">GRID</text><text x="526" y="155" textAnchor="middle">LOAD</text><text x="310" y="60" textAnchor="middle">PV</text><text x="310" y="250" textAnchor="middle">BATT</text></svg>
    <div className="visual-foot">Declared limits · No live connection</div>
    </div>
  if (step === 1) return <div className="journey-visual evidence-visual" role="img" aria-label="Illustrative signal inventory with unknown evidence states">
    <div className="visual-caption">ILLUSTRATIVE / EVIDENCE INVENTORY</div>
    <div className="visual-table"><div><span>GRID IMPORT</span><b>CHECK SOURCE</b></div><div><span>PV AVAILABLE</span><b>CHECK SOURCE</b></div><div><span>BATTERY SOC</span><b>UNKNOWN UNTIL SUPPLIED</b></div><div><span>ASSET SERVICE</span><b>CHECK SOURCE</b></div></div>
    <div className="visual-foot">Evidence states depend on the selected dataset.</div>
  </div>
  if (step === 2) return <div className="journey-visual response-visual" role="img" aria-label="Schematic baseline and downward response over time, no numerical result">
    <div className="visual-caption">SCHEMATIC / RESPONSE + RECOVERY</div>
    <svg viewBox="0 0 620 300" aria-hidden="true"><path className="axis" d="M38 244H585M38 48v196"/><path className="shade" d="M60 145C132 115 170 130 226 116S304 125 353 109S452 132 560 97L560 244H60Z"/><path className="baseline" d="M60 145C132 115 170 130 226 116S304 125 353 109S452 132 560 97"/><path className="response" d="M60 145C132 115 170 130 226 116L226 178C264 173 310 182 353 170L353 109C410 144 452 132 560 97"/><path className="window" d="M226 59v185M353 59v185"/><text x="289" y="53" textAnchor="middle">RESPONSE</text><text x="453" y="210" textAnchor="middle">RECOVERY</text></svg>
    <div className="visual-foot">Illustration only · no numerical site result shown.</div>
  </div>
  return <div className="journey-visual validate-visual" role="img" aria-label="Research workflow: candidate schedule, physical replay, and traceable report">
    <div className="visual-caption">METHOD / INDEPENDENT REPLAY</div>
    <div className="validation-flow"><div><span>01</span><strong>Candidate schedule</strong><small>Proposed by optimization</small></div><i aria-hidden="true">→</i><div><span>02</span><strong>Physical replay</strong><small>Balance, SOC, and service</small></div><i aria-hidden="true">→</i><div><span>03</span><strong>Research report</strong><small>Result or explicit failure</small></div></div>
    <div className="visual-foot">No equipment actuation.</div>
  </div>
}

export default function Landing({ onOpenWorkspace }) {
  const [step, setStep] = useState(0)
  const [researchArea, setResearchArea] = useState(0)
  const current = chapters[step]
  const selectedResearch = researchDetails[researchArea]

  return <div className="landing">
    <div className="landing-banner">SIMULATION-FIRST RESEARCH PROTOTYPE <span>·</span> NO PHYSICAL CONTROL</div>
    <header className="landing-nav"><a className="landing-logo" href="#top" aria-label="Gridyn home"><Mark /><strong>GRIDYN</strong></a><nav aria-label="Site navigation"><a href="#approach">Approach</a><a href="#experience">Journey</a><a href="#capabilities">Research areas</a><a href="#research">Evidence</a></nav>{onOpenWorkspace ? <button className="landing-nav-cta" onClick={onOpenWorkspace}>Open workspace <span>↗</span></button> : <a className="landing-nav-cta" href="#experience">Explore Gridyn <span>↗</span></a>}</header>
    <main id="top">
      <section className="landing-hero" aria-labelledby="landing-title"><div className="hero-inner"><p className="landing-kicker">GRIDYN / ENERGY FLEXIBILITY RESEARCH</p><h1 id="landing-title">Understand your <em>power to shift.</em></h1><p className="hero-copy">Explore when and how a site could safely shift electricity use. Gridyn studies asset limits, data readiness, response duration, and recovery together.</p><div className="hero-actions">{onOpenWorkspace ? <button className="landing-primary" onClick={onOpenWorkspace}>Use the research workspace <span>↗</span></button> : <a className="landing-primary" href="#experience">Explore the journey <span>↓</span></a>}<a className="landing-secondary" href="#approach">The research question <span>↗</span></a></div><p className="hero-note">Simulation-first prototype · Synthetic studies are labelled · Field reliability remains unknown</p></div>
        <div className="hero-lines" aria-hidden="true"><svg viewBox="0 0 1440 250" preserveAspectRatio="none"><path d="M-30 214C300 40 445 265 760 135S1170 15 1470 165"/><path d="M-30 232C300 58 445 283 760 153S1170 33 1470 183"/><path d="M-30 250C300 76 445 301 760 171S1170 51 1470 201"/><path d="M-30 268C300 94 445 319 760 189S1170 69 1470 219"/><path d="M-30 286C300 112 445 337 760 207S1170 87 1470 237"/></svg></div>
      </section>
      <section id="approach" className="landing-approach"><div className="section-side"><span className="section-index">01 / THE QUESTION</span><p>From site physics to a claim you can inspect.</p></div><div className="section-main"><h2>How much can a site shift, <em>for how long,</em> and with what evidence?</h2><p>Gridyn is a simulation-first advisory prototype. It brings site constraints, data quality, sustained response, and schedule validation into one research path. It reports unknowns as unknowns.</p><div className="approach-columns"><div><span>01 / INPUT</span><h3>Declare the site</h3><p>Grid, PV, battery, EV, pump, and HVAC constraints define the model boundary.</p></div><div><span>02 / EVIDENCE</span><h3>Inspect the data</h3><p>Readiness is evaluated by claim, with resolution, coverage, and missing signals visible.</p></div><div><span>03 / RESULT</span><h3>Replay the answer</h3><p>Candidate schedules are checked against physical balance and service constraints.</p></div></div></div></section>
      <section id="experience" className="landing-experience"><div className="experience-head"><div><span className="section-index">02 / PRODUCT JOURNEY</span><h2>Follow the question through.</h2></div><p>Move through four steps to see how the prototype turns a declared site into a traceable research result.</p></div><div className="journey-shell"><div className="journey-top"><span>INTERACTIVE OVERVIEW</span><span>{current.number} / 04</span></div><div className="journey-progress" aria-hidden="true"><span style={{ width: `${(step + 1) * 25}%` }} /></div><div className="journey-body" role="tabpanel" id="journey-panel" aria-label={current.label}><div className="journey-story"><span className="journey-num">{current.number}</span><p className="journey-label">{current.label}</p><h3>{current.title}</h3><p className="journey-copy">{current.copy}</p><div className="journey-meta"><div><span>THE QUESTION</span><strong>{current.question}</strong></div><div><span>THE OUTPUT</span><strong>{current.output}</strong></div></div></div><JourneyVisual step={step} /></div><div className="journey-bottom"><div className="journey-dots" role="tablist" aria-label="Journey stages">{chapters.map((chapter, index) => <button key={chapter.number} className={step === index ? 'active' : ''} role="tab" aria-controls="journey-panel" aria-selected={step === index} aria-label={`${chapter.number} ${chapter.label}`} onClick={() => setStep(index)}>{chapter.number}</button>)}</div><div className="journey-controls"><button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>← Previous</button>{step < chapters.length - 1 ? <button className="next" onClick={() => setStep(step + 1)}>Next step →</button> : <a className="next" href="#capabilities">Research areas ↗</a>}</div></div></div><p className="experience-note">Illustrative journey. No site data or numerical result is shown here.</p></section>
      <section id="capabilities" className="landing-capabilities"><div className="capabilities-intro"><span className="section-index">03 / WHAT THE RESEARCH COVERS</span><h2>A complete view of the site, without a made-up score.</h2><p>The underlying research code keeps each question separate. Explore every area below to see its inputs, outputs, and current evidence state.</p></div><div className="capability-list">{researchAreas.map(([number, title, description], index) => <button className={`capability-item${researchArea === index ? ' selected' : ''}`} key={number} onClick={() => setResearchArea(index)} aria-pressed={researchArea === index} aria-controls="research-detail"><span>{number}</span><h3>{title}</h3><p>{description}</p><small>Explore area ↗</small></button>)}</div><div className="research-detail" id="research-detail" aria-live="polite"><div className="research-detail-heading"><span>IN THE RESEARCH WORKSPACE / {String(researchArea + 1).padStart(2, '0')}</span><strong>{selectedResearch.state}</strong></div><div className="research-detail-body"><div><h3>{selectedResearch.title}</h3><p>{selectedResearch.question}</p></div><div><span>WHAT IT NEEDS</span><p>{selectedResearch.inputs}</p><span>WHAT IT SHOWS</span><p>{selectedResearch.result}</p></div></div></div></section>
      <section id="research" className="landing-research"><div className="research-copy"><span className="section-index">04 / EVIDENCE AND LIMITS</span><h2>Built to show the limits of the answer.</h2><p>The research prototype runs synthetic site studies and checks observed public data for forecasting. Site-specific field validation has not happened yet.</p><p>It does not control equipment. Synthetic outcomes do not establish measured savings, grid benefit, or field reliability.</p><a className="landing-primary" href="https://github.com/sakina1303/Gridyn" target="_blank" rel="noreferrer">View the research code <span>↗</span></a></div><div className="research-ledger" aria-label="Research evidence"><div><span>SYNTHETIC / MODELLED</span><strong>Site simulation · flexibility envelope · schedule replay</strong></div><div><span>OBSERVED / EXTERNAL</span><strong><a href="https://springernature.figshare.com/articles/dataset/Energy_dataset_of_IIITD/6007637" target="_blank" rel="noreferrer">IIIT Delhi load ↗</a> · <a href="https://zenodo.org/records/19006030" target="_blank" rel="noreferrer">ETSIT load and PV ↗</a> forecast checks</strong></div><div><span>UNKNOWN / FIELD</span><strong>Delivered flexibility · measured savings · reliability · operator acceptance</strong></div><div><span>OUT OF SCOPE</span><strong>Live control · market bidding · utility integration</strong></div></div></section>
    </main><footer className="landing-footer"><a className="landing-logo" href="#top" aria-label="Gridyn, back to top"><Mark light /><strong>GRIDYN</strong></a><p>Understand your power to shift.</p><a href="#top">Back to top ↑</a></footer>
  </div>
}
