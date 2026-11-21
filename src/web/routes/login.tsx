import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { AudioLines, Building2, Eye, EyeOff, Hand, Lock, LogIn, Mail, ShieldCheck, UserPlus, UserRound } from 'lucide-react';
import type { CommunicationMode } from '@/lib/support-tickets';
import type { AccountRole } from '@/lib/sanad-state';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useSanad } from '@/lib/sanad-context';
import { pageHead } from '@/lib/page-head';
const logo = { url: '/sanad-logo.png' };

export const Route = createFileRoute('/login')({
  validateSearch: (search: Record<string, unknown>): { mode?: 'signin' | 'signup' | undefined } => ({ mode: search['mode'] === 'signup' ? 'signup' : undefined }),
  head: () => pageHead('تسجيل الدخول وإنشاء حساب', 'سجّل دخولك إلى سَند أو أنشئ حسابًا تجريبيًا جديدًا.'), component: Login,
});

function Login() {
  const state = useSanad(); const navigate = useNavigate();
  const { mode } = Route.useSearch();
  const [name, setName] = useState(''); const [email, setEmail] = useState(''); const [password, setPassword] = useState('');
  const [commMode, setCommMode] = useState<CommunicationMode>('sign');
  const [account, setAccount] = useState<AccountRole>('candidate');
  const company = account === 'company';
  const [showPassword, setShowPassword] = useState(false); const [error, setError] = useState('');
  const signup = mode === 'signup';
  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return setError(company ? 'اكتب اسم الجهة.' : 'اكتب اسمك.');
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setError('اكتب بريدًا إلكترونيًا صحيحًا.');
    if (password.length < 6) return setError('كلمة المرور ٦ أحرف على الأقل.');
    state.signIn(name, email, signup && !company ? commMode : undefined, account);
    navigate({ to: company ? '/company' : '/dashboard' });
  }
  return <section className="login-page">
    <div className="login-card">
      <Link to="/" aria-label="سَند — الصفحة الرئيسية" className="login-brand"><img src={logo.url} alt="سَند — لأن صوتك يستحق أن يصل" width={96} height={56} /></Link>
      <h1 className="login-title">مرحبًا بك في سَند</h1>
      <p className="login-subtitle">{signup ? 'أنشئ حسابك للوصول إلى مساحة المرشح' : 'سجّل دخولك للمتابعة إلى مساحتك'}</p>
      <form className="login-form" onSubmit={submit} noValidate>
        <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="نوع الحساب">{([{ id: 'candidate', label: 'مرشح', Icon: UserRound }, { id: 'company', label: 'جهة توظيف', Icon: Building2 }] as const).map(({ id, label, Icon }) => <Button key={id} type="button" variant={account === id ? 'secondary' : 'outline'} role="radio" aria-checked={account === id} onClick={() => setAccount(id)}><Icon aria-hidden="true" />{label}</Button>)}</div>
        <div className="login-field"><label htmlFor="name">{company ? 'اسم الجهة' : 'الاسم'}</label>
          <div className="login-input-wrap"><Input id="name" autoComplete="name" maxLength={50} placeholder={company ? 'مثال: شركة بُعد التقنية' : 'مثال: أحمد العمري'} value={name} onChange={e => setName(e.target.value)} /><UserRound aria-hidden="true" /></div></div>
        <div className="login-field"><label htmlFor="email">البريد الإلكتروني</label>
          <div className="login-input-wrap"><Input id="email" type="email" dir="ltr" autoComplete="email" maxLength={255} placeholder="example@email.com" value={email} onChange={e => setEmail(e.target.value)} /><Mail aria-hidden="true" /></div></div>
        <div className="login-field"><label htmlFor="password">كلمة المرور</label>
          <div className="login-input-wrap"><Input id="password" type={showPassword ? 'text' : 'password'} dir="ltr" autoComplete={signup ? 'new-password' : 'current-password'} maxLength={100} placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} /><Lock aria-hidden="true" />
            <Button variant="ghost" size="icon" type="button" className="login-eye" aria-label={showPassword ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}</Button></div>
          <p className="login-hint">٦ أحرف على الأقل</p></div>
        {signup && !company && <fieldset className="login-field"><legend className="mb-2 font-medium text-sm">طريقة التواصل التي تناسبك</legend>
          <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="طريقة التواصل">{([{ id: 'sign', label: 'لغة الإشارة', hint: 'للصم وضعاف السمع', Icon: Hand }, { id: 'voice', label: 'الصوت', hint: 'للمكفوفين وضعاف البصر', Icon: AudioLines }] as const).map(({ id, label, hint, Icon }) => <Button key={id} type="button" variant="outline" role="radio" aria-checked={commMode === id} className="h-auto flex-col gap-1 py-3 aria-checked:border-primary aria-checked:bg-secondary" onClick={() => setCommMode(id)}><Icon aria-hidden="true" /><span className="font-semibold">{label}</span><span className="text-xs text-muted-foreground">{hint}</span></Button>)}</div>
          <p className="login-hint">يحدد هذا الاختيار شكل المنصة لك، ويمكنك تغييره من الإعدادات.</p></fieldset>}
        {error && <p role="alert" className="login-error">{error}</p>}
        <Button type="submit" size="lg" className="login-submit">{signup ? <UserPlus aria-hidden="true" /> : <LogIn aria-hidden="true" />}{signup ? 'إنشاء حساب' : 'تسجيل الدخول'}</Button>
        <p className="login-switch">{signup ? 'لديك حساب؟' : 'ليس لديك حساب؟'} <Button asChild variant="link" className="px-0" onClick={() => setError('')}><Link to="/login" search={{ mode: signup ? undefined : 'signup' }}>{signup ? 'تسجيل الدخول' : 'إنشاء حساب'}</Link></Button></p>
      </form>
      <p className="login-note"><ShieldCheck aria-hidden="true" />نسخة تجريبية: لا تُحفظ البيانات ولا يُنشأ حساب حقيقي.</p>
    </div>
  </section>;
}
