import { useState } from 'react';
import { Hand, Play, Video, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerTitle, DrawerDescription } from '@/components/ui/drawer';
import { useSanad } from '@/lib/sanad-context';
import { Brand } from '@/components/sanad-layout';

export function PlatformGuide() {
  const state = useSanad();
  const [requested, setRequested] = useState(false);
  return <Drawer open={state.guideOpen} onOpenChange={open => { if (!open) state.closeGuide(); }} shouldScaleBackground={false}>
    <DrawerContent dir="rtl" className="guide-sheet"><div className="guide-inner">
      <Button variant="ghost" size="icon" className="absolute left-3 top-3" aria-label="إغلاق الدليل" onClick={state.closeGuide}><X /></Button>
      <Brand /><DrawerTitle className="text-2xl mt-4">مرحبًا بك في سَند</DrawerTitle><DrawerDescription className="mt-2">الدليل التعريفي للمنصة</DrawerDescription>
      <div className="guide-video"><span className="guide-play"><Play className="size-7" /></span><span className="text-sm mt-3">فيديو الدليل التعريفي</span><span className="text-xs text-muted-foreground flex items-center gap-2 mt-2"><Hand className="size-4" />مساحة لفيديو بلغة الإشارة ونص مكتوب</span></div>
      <p className="text-sm text-muted-foreground mt-3" role="status">{requested ? 'الفيديو لم يُضف بعد. يمكنك متابعة تجربة المنصة.' : 'سيظهر الفيديو هنا عند توفيره.'}</p>
      <div className="flex justify-center gap-3 mt-5"><Button onClick={() => setRequested(true)}><Video />مشاهدة الدليل</Button><Button variant="outline" onClick={state.closeGuide}>تخطي</Button></div>
    </div></DrawerContent>
  </Drawer>;
}