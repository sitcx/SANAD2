import { BriefcaseBusiness, Check, FileUser, HandMetal, LifeBuoy, Search, Video } from 'lucide-react';

/** Editable line-art icons, not flattened screenshots of the approved sections. */
export function FeatureIllustration({ kind }: { kind: 'jobs' | 'support' | 'interview' }) {
  return <div className="landing-illustration-frame" aria-hidden="true"><div className={`landing-illustration landing-illustration--${kind}`}>
    <span className="illustration-wash" />
    {kind === 'jobs' ? <>
      <FileUser className="illustration-resume" strokeWidth={1.35} />
      <span className="illustration-briefcase"><BriefcaseBusiness strokeWidth={1.7} /></span>
      <Search className="illustration-search" strokeWidth={2} />
    </> : <>
      <span className="illustration-laptop"><span className="illustration-screen">
        {kind === 'support' ? <><span className="illustration-target-wrap"><LifeBuoy className="illustration-target" strokeWidth={1.6} /></span><span className="illustration-checks">{[1, 2, 3].map(row => <span key={row}><i /><Check strokeWidth={3} /></span>)}</span></> : <HandMetal className="illustration-hand" strokeWidth={1.5} />}
      </span><span className="illustration-keyboard" /></span>
      {kind === 'interview' && <span className="illustration-camera"><Video fill="currentColor" strokeWidth={1.5} /></span>}
    </>}
  </div></div>;
}