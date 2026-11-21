import { AudioLines, Building2, Check, Hand } from 'lucide-react';

/** Landing hero visual: Sanad connects job seekers (deaf and blind) with employers. */
const benefits = ['مطابقة المهارات', 'مقابلة بالإشارة والصوت', 'دعم بعد التوظيف'] as const;

export function HeroPreview() {
  return <figure className="hero-bridge" aria-label="سند يربط الباحثين عن عمل من الصم والمكفوفين بجهات التوظيف">
    <div className="hero-bridge-glow" aria-hidden="true" />
    <div className="hero-bridge-row" aria-hidden="true">
      <div className="hero-node">
        <span className="hero-node-icon hero-node-icon--pair"><Hand /><AudioLines /></span>
        <strong>الباحث عن عمل</strong>
        <span>أصم · كفيف</span>
      </div>
      <span className="hero-link"><i /><i /><i /></span>
      <div className="hero-node hero-node--center">
        <span className="hero-logo"><img src="/sanad-logo.png" alt="" width={86} height={50} /></span>
      </div>
      <span className="hero-link hero-link--reverse"><i /><i /><i /></span>
      <div className="hero-node">
        <span className="hero-node-icon"><Building2 /></span>
        <strong>جهة التوظيف</strong>
        <span>تستقطب الكفاءات</span>
      </div>
    </div>
    <figcaption className="hero-benefits">{benefits.map(item => <span key={item}><Check aria-hidden="true" />{item}</span>)}</figcaption>
  </figure>;
}
