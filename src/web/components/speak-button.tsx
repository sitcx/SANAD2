import { Volume2 } from 'lucide-react';
import { useContext } from 'react';
import { Button } from '@/components/ui/button';
import { SanadContext } from '@/lib/sanad-state';
import { speak } from '@/lib/voice-guide';

/** Speaker button that reads a section aloud. Shown only in voice mode (blind candidates). */
export function SpeakButton({ text, label }: { text: string; label: string }) {
  const voice = useContext(SanadContext)?.communicationMode === 'voice';
  if (!voice) return null;
  return <Button type="button" size="icon" variant="outline" className="speak-button shrink-0" aria-label={`استمع: ${label}`} title={`استمع: ${label}`} onClick={() => speak(text)}><Volume2 aria-hidden="true" /></Button>;
}
