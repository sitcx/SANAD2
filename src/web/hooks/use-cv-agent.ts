/** Loads the job agent's stored reading of the candidate's CV, and uploads a new CV to it. */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSanad } from '@/lib/sanad-context';
import { cvApi, type AgentProfile } from '@/lib/cv-api';

export function useCvAgent() {
  const state = useSanad();
  const [data, setData] = useState<AgentProfile | null>(null);
  const [error, setError] = useState('');
  const [needsCity, setNeedsCity] = useState(false);
  const pending = useRef<File | null>(null);
  const { signedIn, setCvStatus, setCvName } = state;

  const refresh = useCallback(async () => {
    const result = await cvApi.profile();
    setData(result);
    return result;
  }, []);

  useEffect(() => {
    if (!signedIn) return;
    let active = true;
    cvApi.profile().then(result => {
      if (!active) return;
      setData(result);
      setError('');
      setCvStatus(result.profile ? 'analysed' : 'uploaded');
      if (!result.profile) setCvName('');
    }).catch((err: Error) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [signedIn, setCvStatus, setCvName]);

  async function upload(file: File, city?: string) {
    pending.current = file;
    setCvName(file.name);
    setCvStatus('analysing');
    setError('');
    setNeedsCity(false);
    try {
      const result = await cvApi.upload(file, city ? { city } : undefined);
      if (result.status === 'need_info') {
        setNeedsCity(Boolean(result.missing_info?.includes('city')));
        if (!result.missing_info?.includes('city')) setError('لم نجد مهارات واضحة في السيرة. أضف قسم «المهارات» ثم ارفعها مجددًا.');
        setCvStatus('uploaded');
        return;
      }
      await refresh();
      setCvStatus('analysed');
    } catch (err) {
      setError((err as Error).message);
      setCvStatus('uploaded');
    }
  }

  return { data, error, setError, needsCity, upload, answerCity: (city: string) => { if (pending.current) void upload(pending.current, city); } };
}

