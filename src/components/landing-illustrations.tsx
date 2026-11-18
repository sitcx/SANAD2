import { BriefcaseBusiness, Check, FileUser, HandMetal, MoveUpRight, Search, Target, Video } from 'lucide-react';

/** Editable line-art icons, not flattened screenshots of the approved sections. */
export function FeatureIllustration({ kind }: { kind: 'jobs' | 'coach' | 'interview' }) {
  return <div className="landing-illustration-frame" aria-hidden="true"><div className={`landing-illustration landing-illustration--${kind}`}>
    <span className="illustration-wash" />
    {kind === 'jobs' ? <>
      <FileUser className="illustration-resume" strokeWidth={1.35} />
      <span className="illustration-briefcase"><BriefcaseBusiness strokeWidth={1.7} /></span>
      <Search className="illustration-search" strokeWidth={2} />
    </> : <>
      <span className="illustration-laptop"><span className="illustration-screen">
        {kind === 'coach' ? <><span className="illustration-target-wrap"><Target className="illustration-target" strokeWidth={1.6} /><MoveUpRight className="illustration-target-arrow" strokeWidth={2.3} /></span><span className="illustration-checks">{[1, 2, 3].map(row => <span key={row}><i /><Check strokeWidth={3} /></span>)}</span></> : <HandMetal className="illustration-hand" strokeWidth={1.5} />}
      </span><span className="illustration-keyboard" /></span>
      {kind === 'interview' && <span className="illustration-camera"><Video fill="currentColor" strokeWidth={1.5} /></span>}
    </>}
  </div></div>;
}