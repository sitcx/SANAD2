import { Link, useNavigate } from '@tanstack/react-router';
import { ChevronDown, ClipboardList, LogOut, Moon, Save, Settings, Sun, Target, UserRound } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { useSanad } from '@/lib/sanad-context';

export function AccountMenu() {
  const state = useSanad();
  const navigate = useNavigate();
  const [panel, setPanel] = useState<'profile' | 'settings' | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  if (!state.signedIn) return null;
  function openProfile() {
    setName(state.candidateName); setEmail(state.candidateEmail); setError(''); setPanel('profile');
  }
  function saveProfile(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return setError('اكتب اسمك.');
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setError('اكتب بريدًا إلكترونيًا صحيحًا.');
    state.updateProfile(name, email); setPanel(null);
  }
  function signOut() {
    void navigate({ to: '/', replace: true }); state.signOut();
  }
  return <>
    <DropdownMenu dir="rtl"><DropdownMenuTrigger asChild>
      <Button variant="secondary" className="account-trigger" title={`مرحبًا، ${state.candidateName}`}><UserRound aria-hidden="true" /><span>مرحبًا، {state.candidateName}</span><ChevronDown aria-hidden="true" /></Button>
    </DropdownMenuTrigger><DropdownMenuContent align="end" sideOffset={8} className="w-52">
      <DropdownMenuItem onSelect={() => void navigate({ to: '/coach' })}><Target aria-hidden="true" />ابدأ التدريب</DropdownMenuItem>
      <DropdownMenuItem onSelect={() => void navigate({ to: '/applications' })}><ClipboardList aria-hidden="true" />تتبع تقديماتي</DropdownMenuItem>
      <DropdownMenuItem onSelect={openProfile}><UserRound aria-hidden="true" />تعديل الملف الشخصي</DropdownMenuItem>
      <DropdownMenuItem onSelect={() => setPanel('settings')}><Settings aria-hidden="true" />الإعدادات</DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem onSelect={signOut}><LogOut aria-hidden="true" />تسجيل الخروج</DropdownMenuItem>
    </DropdownMenuContent></DropdownMenu>
    <Dialog open={panel !== null} onOpenChange={open => { if (!open) setPanel(null); }}><DialogContent dir="rtl">
      <DialogTitle>{panel === 'profile' ? 'الملف الشخصي' : 'الإعدادات'}</DialogTitle>
      <DialogDescription>نسخة تجريبية؛ تبقى التغييرات في الجلسة الحالية فقط.</DialogDescription>
      {panel === 'profile' ? <form onSubmit={saveProfile} className="space-y-4" noValidate>
        <div className="space-y-2"><label htmlFor="profile-name">الاسم</label><Input id="profile-name" autoComplete="name" maxLength={50} value={name} onChange={event => setName(event.target.value)} /></div>
        <div className="space-y-2"><label htmlFor="profile-email">البريد الإلكتروني</label><Input id="profile-email" type="email" dir="ltr" autoComplete="email" maxLength={255} value={email} onChange={event => setEmail(event.target.value)} /></div>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <Button type="submit"><Save aria-hidden="true" />حفظ التغييرات</Button>
      </form> : <div className="space-y-4">
        <div className="flex items-center justify-between gap-3"><span className="flex items-center gap-2 text-sm">{state.darkMode ? <Moon aria-hidden="true" className="size-4" /> : <Sun aria-hidden="true" className="size-4" />}الوضع {state.darkMode ? 'الداكن' : 'الفاتح'}</span><Switch aria-label="التبديل بين الوضع الفاتح والداكن" checked={state.darkMode} onCheckedChange={state.setDarkMode} /></div>
        <label className="flex items-start gap-3"><Checkbox checked={state.trainingConsent} onCheckedChange={value => state.setTrainingConsent(value === true)} /><span>موافقة اختيارية على تدريب نماذج سَند</span></label>
        <p className="text-sm text-muted-foreground">مستقلة عن الشروط ويمكن سحبها في أي وقت؛ لا يبدأ جمع بيانات أو تدريب في هذه التجربة.</p>
        <Button asChild variant="link" className="px-0"><Link to="/charter" onClick={() => setPanel(null)}>الميثاق والأحكام والشروط</Link></Button>
      </div>}
    </DialogContent></Dialog>
  </>;
}