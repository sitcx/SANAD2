import { Link, useLocation } from '@tanstack/react-router';
import { BookOpen, LayoutDashboard, Mail, ShieldCheck } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { AccountMenu } from '@/components/account-menu';
const logo = { url: '/sanad-logo.png' };
import { useSanad } from '@/lib/sanad-context';
import { workspaceNavigation } from '@/lib/workspace-navigation';

export function Brand() {
  return <Link to="/" aria-label="سَند — الصفحة الرئيسية" className="shrink-0"><img className="brand-image" src={logo.url} alt="سَند — لأن صوتك يستحق أن يصل" width={118} height={68} /></Link>;
}
export function SiteHeader() {
  const state = useSanad();
  const { pathname } = useLocation();
  const isLanding = pathname === '/';
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    if (!isLanding) return;
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [isLanding]);
  return <header className={isLanding ? `site-header site-header--landing${scrolled ? ' is-scrolled' : ''}` : 'site-header'}><div className={`${isLanding ? 'landing-container' : 'site-container'} header-inner`}>
    <Brand />
    {isLanding && <nav className="landing-nav" aria-label="أقسام الصفحة"><a href="#home">الرئيسية</a><a href="#features">مميزات سَند</a><a href="#how-it-works">كيف يعمل سَند؟</a></nav>}
    {pathname !== '/' && pathname !== '/login' && <nav className="desktop-nav" aria-label="التنقل الرئيسي">
      {workspaceLinks.map(item => <Link key={item.to} className="nav-link" data-active={pathname === item.to} aria-current={pathname === item.to ? 'page' : undefined} to={item.to}><item.icon />{item.label}</Link>)}
    </nav>}
    <div className="header-actions">
      {isLanding ? <><Button variant="ghost" className="knowledge-guide" onClick={state.openGuide}><BookOpen aria-hidden="true" />الدليل المعرفي</Button><Button variant="ghost" size="icon" className="mobile-knowledge-guide" aria-label="الدليل المعرفي" title="الدليل المعرفي" onClick={state.openGuide}><BookOpen aria-hidden="true" /></Button></> : <Button variant="ghost" size="icon" aria-label="مشاهدة الدليل" title="مشاهدة الدليل" onClick={state.openGuide}><BookOpen aria-hidden="true" /></Button>}
      <AccountMenu />
    </div>
  </div></header>;
}
const workspaceLinks = workspaceNavigation.map(item => ({ ...item, icon: LayoutDashboard }));
export function Workspace({ children }: { children: ReactNode }) {
  return <div className="workspace"><div className="site-container"><div className="min-w-0 entry-animate">{children}</div></div>
  </div>;
}
export function SiteFooter() {
  return <footer className="site-footer"><div className="site-container footer-layout">
    <div className="footer-brand"><Brand /></div>
    <nav className="footer-col" aria-label="روابط سَند"><h2 className="footer-title">روابط</h2><Link to="/" hash="home">الرئيسية</Link><Link to="/" hash="features">مميزات سَند</Link><Link to="/" hash="how-it-works">كيف يعمل سَند؟</Link></nav>
    <div className="footer-col"><h2 className="footer-title">التواصل</h2><a href="mailto:sanad@gmail.com" className="footer-email"><Mail aria-hidden="true" /><span dir="ltr">sanad@gmail.com</span></a><Link to="/charter"><ShieldCheck aria-hidden="true" />الميثاق والأحكام والشروط</Link></div>
  </div></footer>;
}
export function SectionHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description?: string }) {
  return <div className="section-heading"><span className="eyebrow">{eyebrow}</span><h2>{title}</h2>{description && <p>{description}</p>}</div>;
}
export function ProgressBar({ value, label }: { value: number; label: string }) {
  return <div role="progressbar" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} className="progress-track"><div className="progress-fill" style={{ width: `${value}%` }} /></div>;
}
export function PageTitle({ title, subtitle, action }: { title: string; subtitle: string; action?: ReactNode }) {
  return <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 items-center mb-7"><div className="min-w-0"><h1 className="page-heading">{title}</h1><p className="page-subheading">{subtitle}</p></div>{action}</div>;
}