/* Proof Ledger style: editorial verification tooling, warm paper, verdigris proof marks, evidence-first hierarchy. */
import { useMemo, useState } from "react";
import { Activity, ArrowUpRight, Check, ChevronRight, CircleAlert, Copy, FileCode2, GitCommitHorizontal, LockKeyhole, Play, ShieldCheck, Terminal, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const checks = [
  { id: "01", name: "Impact plan", detail: "12 files mapped to 5 deterministic checks", status: "pass", time: "0.08s" },
  { id: "02", name: "Unit tests", detail: "42 passed · 0 failed", status: "pass", time: "0.84s" },
  { id: "03", name: "Secret scan", detail: "No high-confidence secrets detected", status: "pass", time: "0.12s" },
  { id: "04", name: "Policy gate", detail: "Evidence complete · default policy", status: "pass", time: "0.03s" },
];

const changedFiles = [
  { path: "src/proofsmith/policy.py", stat: "+18 −4", label: "core" },
  { path: "tests/test_core.py", stat: "+31 −0", label: "test" },
  { path: ".github/workflows/ci.yml", stat: "+6 −1", label: "ci" },
];

function StatusMark({ status }: { status: "pass" | "review" | "blocked" }) {
  return status === "pass" ? (
    <span className="stamp stamp-pass"><Check size={13} strokeWidth={3} /> PASS</span>
  ) : status === "review" ? (
    <span className="stamp stamp-review"><CircleAlert size={13} /> REVIEW</span>
  ) : (
    <span className="stamp stamp-blocked"><X size={13} /> BLOCKED</span>
  );
}

export default function Home() {
  const [activeCheck, setActiveCheck] = useState(0);
  const [copied, setCopied] = useState(false);
  const active = useMemo(() => checks[activeCheck], [activeCheck]);

  const copyCommand = () => {
    navigator.clipboard?.writeText("proofsmith bundle examples/verification-input.json --output .proofsmith");
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <div className="app-shell">
      <aside className="rail">
        <div className="brand-lockup">
          <img src="/manus-storage/proofsmith-mark_5c3ff058.png" alt="" className="brand-mark" />
          <span className="brand-name">ProofSmith</span>
        </div>
        <div className="rail-rule" />
        <nav className="rail-nav" aria-label="Primary navigation">
          <a className="rail-link active" href="#overview"><Activity size={17} /><span>Run overview</span></a>
          <a className="rail-link" href="#evidence"><ShieldCheck size={17} /><span>Evidence</span></a>
          <a className="rail-link" href="#changed"><FileCode2 size={17} /><span>Changed files</span></a>
        </nav>
        <div className="rail-bottom">
          <div className="tiny-label">LOCAL-FIRST</div>
          <p>Nothing leaves your machine unless you choose to publish the bundle.</p>
          <div className="rail-version"><span className="dot" /> v0.1.0-alpha</div>
        </div>
      </aside>

      <main className="main-canvas">
        <header className="topbar">
          <div className="crumbs"><span>WORKSPACE</span><ChevronRight size={13} /><strong>demo-repository</strong><ChevronRight size={13} /><span>RUN 0007</span></div>
          <div className="top-actions"><span className="mono muted">rev 7f3a2c1</span><Button size="sm" className="run-button"><Play size={14} fill="currentColor" /> Run proof</Button></div>
        </header>

        <section className="hero-grid" id="overview">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-line" /> VERIFICATION REPORT <span className="eyebrow-dot" /></div>
            <h1>Turn a diff<br /><em>into evidence.</em></h1>
            <p className="hero-lede">A deterministic proof run for the code you are about to ship. Every decision has a trace, every pass has an artifact.</p>
            <div className="hero-meta"><span className="meta-chip"><GitCommitHorizontal size={15} /> demo-commit-7f3a2c1</span><span className="meta-chip"><LockKeyhole size={14} /> local-only</span></div>
          </div>
          <div className="hero-art" aria-label="Abstract evidence map illustration">
            <img src="/manus-storage/proofsmith-hero_8f87bd7d.png" alt="Abstract evidence map with connected verification checkpoints" />
            <div className="hero-art-label"><span>PROOF / 07</span><strong>Replay-safe<br />evidence bundle</strong></div>
          </div>
        </section>

        <section className="status-strip">
          <div className="status-primary"><div className="status-seal"><Check size={25} strokeWidth={2.5} /></div><div><div className="tiny-label">FINAL STATUS</div><div className="status-title">Verified for review</div></div></div>
          <div className="status-stat"><span className="tiny-label">CHECKS</span><strong>04 <small>/ 04</small></strong></div>
          <div className="status-stat"><span className="tiny-label">DURATION</span><strong>1.07 <small>sec</small></strong></div>
          <div className="status-stat"><span className="tiny-label">BUNDLE HASH</span><strong className="mono hash">a41b…e902</strong></div>
          <StatusMark status="pass" />
        </section>

        <div className="content-grid">
          <section id="evidence" className="timeline-panel">
            <div className="section-heading"><div><div className="tiny-label">EVIDENCE SPINE</div><h2>What the run proved</h2></div><span className="mono muted">4 observations</span></div>
            <div className="timeline">
              {checks.map((check, index) => (
                <button key={check.id} className={cn("timeline-row", activeCheck === index && "selected")} onClick={() => setActiveCheck(index)}>
                  <span className="timeline-node"><span>{check.id}</span></span>
                  <span className="timeline-copy"><strong>{check.name}</strong><small>{check.detail}</small></span>
                  <span className="timeline-time mono">{check.time}</span><Check className="timeline-check" size={16} />
                </button>
              ))}
            </div>
            <div className="active-detail"><div className="detail-kicker"><span className="dot" /> SELECTED EVIDENCE</div><div className="detail-main"><strong>{active.name}</strong><span>{active.detail}</span></div><ArrowUpRight size={17} /></div>
          </section>

          <section id="changed" className="files-panel">
            <div className="section-heading"><div><div className="tiny-label">CHANGE SURFACE</div><h2>Files in scope</h2></div><span className="count-badge">3 files</span></div>
            <div className="file-list">{changedFiles.map((file) => <div className="file-row" key={file.path}><FileCode2 size={17} /><div className="file-copy"><strong>{file.path}</strong><span>{file.label}</span></div><span className="file-stat mono">{file.stat}</span></div>)}</div>
            <div className="impact-card"><img src="/manus-storage/proofsmith-evidence-map_ed073b89.png" alt="Evidence map texture" /><div className="impact-overlay"><div className="tiny-label">IMPACT CONFIDENCE</div><strong>High</strong><span>All changed paths mapped</span></div></div>
          </section>
        </div>

        <section className="command-card">
          <div className="command-icon"><Terminal size={19} /></div><div className="command-copy"><div className="tiny-label">REPLAY THIS PROOF</div><code>proofsmith bundle examples/verification-input.json --output .proofsmith</code></div><Button onClick={copyCommand} variant="outline" size="sm" className="copy-button"><Copy size={14} /> {copied ? "Copied" : "Copy command"}</Button>
        </section>

        <footer className="footer-note"><span>ProofSmith is open source under Apache-2.0.</span><span className="footer-links"><a href="https://github.com/Alqudimi/proofsmith">GitHub <ArrowUpRight size={13} /></a><a href="#evidence">Read the evidence model <ArrowUpRight size={13} /></a></span></footer>
      </main>
    </div>
  );
}
