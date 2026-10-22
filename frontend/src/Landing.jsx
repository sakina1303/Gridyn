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
    <div className="visual-foot">The app assigns states from the selected dataset.</div>
  </div>
  if (step === 2) return <div className="journey-visual response-visual" role="img" aria-label="Schematic baseline and downward response over time, no numerical result">
    <div className="visual-caption">SCHEMATIC / RESPONSE + RECOVERY</div>
    <svg viewBox="0 0 620 300" aria-hidden="true"><path className="axis" d="M38 244H585M38 48v196"/><path className="shade" d="M60 145C132 115 170 130 226 116S304 125 353 109S452 132 560 97L560 244H60Z"/><path className="baseline" d="M60 145C132 115 170 130 226 116S304 125 353 109S452 132 560 97"/><path className="response" d="M60 145C132 115 170 130 226 116L226 178C264 173 310 182 353 170L353 109C410 144 452 132 560 97"/><path className="window" d="M226 59v185M353 59v185"/><text x="289" y="53" textAnchor="middle">RESPONSE</text><text x="453" y="210" textAnchor="middle">RECOVERY</text></svg>
    <div className="visual-foot">Illustration only · kW is calculated in the workspace.</div>
  </div>
  return <div className="journey-visual validate-visual" role="img" aria-label="Research workflow: candidate schedule, physical replay, and traceable report">
    <div className="visual-caption">METHOD / INDEPENDENT REPLAY</div>
    <div className="validation-flow"><div><span>01</span><strong>Candidate schedule</strong><small>Proposed by optimization</small></div><i aria-hidden="true">→</i><div><span>02</span><strong>Physical replay</strong><small>Balance, SOC, and service</small></div><i aria-hidden="true">→</i><div><span>03</span><strong>Research report</strong><small>Result or explicit failure</small></div></div>
    <div className="visual-foot">No equipment actuation.</div>
  </div>
}

export default function Landing({ onOpenWorkspace }) {
  const [step, setStep] = useState(0)
  const current = chapters[step]

  return <div className="landing">
    <div className="landing-banner">SIMULATION-FIRST RESEARCH PROTOTYPE <span>·</span> NO PHYSICAL CONTROL</div>
    <header className="landing-nav"><a className="landing-logo" href="#top" aria-label="FlexGrid home"><Mark /><strong>FLEXGRID</strong></a><nav aria-label="Site navigation"><a href="#approach">Approach</a><a href="#experience">Experience</a><a href="#research">Research scope</a></nav><button className="landing-nav-cta" onClick={onOpenWorkspace}>Open workspace <span>↗</span></button></header>
    <main id="top">
      <section className="landing-hero" aria-labelledby="landing-title"><div className="hero-inner"><p className="landing-kicker">ENERGY FLEXIBILITY / RESEARCH LAB</p><h1 id="landing-title">Flexibility begins <em>with evidence.</em></h1><p className="hero-copy">Explore what a modeled site could provide when data are incomplete, assets interact, and every response needs a recovery plan.</p><div className="hero-actions"><a className="landing-primary" href="#experience">Explore the journey <span>↓</span></a><button className="landing-secondary" onClick={onOpenWorkspace}>Open research workspace <span>↗</span></button></div><p className="hero-note">Synthetic studies are labelled. Reliability remains unknown until tested.</p></div>
        <div className="hero-lines" aria-hidden="true"><svg viewBox="0 0 1440 250" preserveAspectRatio="none"><path d="M-30 214C300 40 445 265 760 135S1170 15 1470 165"/><path d="M-30 232C300 58 445 283 760 153S1170 33 1470 183"/><path d="M-30 250C300 76 445 301 760 171S1170 51 1470 201"/><path d="M-30 268C300 94 445 319 760 189S1170 69 1470 219"/><path d="M-30 286C300 112 445 337 760 207S1170 87 1470 237"/></svg></div>
      </section>
      <section id="approach" className="landing-approach"><div className="section-side"><span className="section-index">01 / THE QUESTION</span><p>From site physics to a claim you can inspect.</p></div><div className="section-main"><h2>How much can a site shift, <em>for how long,</em> and with what evidence?</h2><p>FlexGrid is a simulation-first advisory prototype. It brings site constraints, data quality, sustained response, and schedule validation into one research path. It reports unknowns as unknowns.</p><div className="approach-columns"><div><span>01 / INPUT</span><h3>Declare the site</h3><p>Grid, PV, battery, EV, pump, and HVAC constraints define the model boundary.</p></div><div><span>02 / EVIDENCE</span><h3>Inspect the data</h3><p>Readiness is evaluated by claim, with resolution, coverage, and missing signals visible.</p></div><div><span>03 / RESULT</span><h3>Replay the answer</h3><p>Candidate schedules are checked against physical balance and service constraints.</p></div></div></div></section>
      <section id="experience" className="landing-experience"><div className="experience-head"><div><span className="section-index">02 / PRODUCT JOURNEY</span><h2>Follow the question through.</h2></div><p>Move through four steps to see how the prototype turns a declared site into a traceable research result.</p></div><div className="journey-shell"><div className="journey-top"><span>INTERACTIVE OVERVIEW</span><span>{current.number} / 04</span></div><div className="journey-progress" aria-hidden="true"><span style={{ width: `${(step + 1) * 25}%` }} /></div><div className="journey-body" role="tabpanel" id="journey-panel" aria-label={current.label}><div className="journey-story"><span className="journey-num">{current.number}</span><p className="journey-label">{current.label}</p><h3>{current.title}</h3><p className="journey-copy">{current.copy}</p><div className="journey-meta"><div><span>THE QUESTION</span><strong>{current.question}</strong></div><div><span>THE OUTPUT</span><strong>{current.output}</strong></div></div></div><JourneyVisual step={step} /></div><div className="journey-bottom"><div className="journey-dots" role="tablist" aria-label="Journey stages">{chapters.map((chapter, index) => <button key={chapter.number} className={step === index ? 'active' : ''} role="tab" aria-controls="journey-panel" aria-selected={step === index} aria-label={`${chapter.number} ${chapter.label}`} onClick={() => setStep(index)}>{chapter.number}</button>)}</div><div className="journey-controls"><button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>← Previous</button>{step < chapters.length - 1 ? <button className="next" onClick={() => setStep(step + 1)}>Next step →</button> : <button className="next" onClick={onOpenWorkspace}>Enter workspace ↗</button>}</div></div></div><p className="experience-note">Illustrative journey. No site data or numerical result is shown here.</p></section>
      <section id="research" className="landing-research"><div className="research-copy"><span className="section-index">03 / RESEARCH SCOPE</span><h2>Built to show the limits of the answer.</h2><p>The workspace can generate synthetic studies, examine observed CSV data, assess joint flexibility, test optimization, compare stress cases, and export a traceable report.</p><p>It does not control equipment. Synthetic outcomes do not establish measured savings, grid benefit, or field reliability.</p><button className="landing-primary" onClick={onOpenWorkspace}>Open the prototype <span>↗</span></button></div><div className="research-ledger" aria-label="Research scope"><div><span>AVAILABLE NOW</span><strong>Simulation · readiness · envelope · validated schedule</strong></div><div><span>DISPLAYED AS UNKNOWN</span><strong>Calibrated response reliability · field impact</strong></div><div><span>OUT OF SCOPE</span><strong>Live control · market bidding · utility integration</strong></div></div></section>
    </main><footer className="landing-footer"><div className="landing-logo"><Mark light /><strong>FLEXGRID</strong></div><p>Simulation-first energy flexibility research prototype.</p><button onClick={onOpenWorkspace}>Research workspace ↗</button></footer>
  </div>
}
