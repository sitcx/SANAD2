import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SanadContext } from '@/lib/sanad-state';
import { SanadProvider, useSanad } from '@/lib/sanad-context';
import { useContext } from 'react';

describe('Shared candidate context identity', () => {
  it('preserves the context identity across initial evaluations before disposal', async () => {
    // Evaluate the actual browser-safe module with the shared hot data supplied
    // by Vite; Vitest's own module runner intentionally has no hot data.
    const { readFile } = await import('node:fs/promises');
    const { transpileModule, ScriptTarget, ModuleKind } = await import('typescript');
    const React = await import('react');
    const source = await readFile('src/lib/sanad-state.ts', 'utf8');
    const transformed = transpileModule(source, { compilerOptions: { target: ScriptTarget.ESNext, module: ModuleKind.ESNext } }).outputText;
    const evaluate = new Function('React', 'hot', `${transformed
      .replace(/import\s*\{\s*createContext\s*\}\s*from\s*['"]react['"];?/, 'const { createContext } = React;')
      .replace('export const SanadContext', 'const SanadContext')
      .replaceAll('import.meta.hot', 'hot')}\nreturn SanadContext;`);
    const hot = { data: {} as { sanadContext?: typeof SanadContext } };
    const first = evaluate(React, hot);
    expect(hot.data.sanadContext).toBe(first);
    expect(evaluate(React, hot)).toBe(first);
    expect(evaluate(React, hot)).toBe(first);
    expect(evaluate(React, undefined)).not.toBe(first);
  });
  it('connects separately imported consumers to the same provider', () => {
    const { result } = renderHook(() => ({
      publicConsumer: useSanad(),
      independentConsumer: useContext(SanadContext),
    }), { wrapper: SanadProvider });
    expect(result.current.independentConsumer).toBe(result.current.publicConsumer);
    act(() => result.current.publicConsumer.signIn('أحمد'));
    expect(result.current.independentConsumer?.signedIn).toBe(true);
    expect(result.current.independentConsumer?.candidateName).toBe('أحمد');
  });
  it('isolates candidate data between separate mounted providers', () => {
    const first = renderHook(() => useSanad(), { wrapper: SanadProvider });
    const second = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => first.result.current.setSentAnswers(['إجابة معتمدة في الجلسة الأولى']));
    expect(first.result.current.sentAnswers).toEqual(['إجابة معتمدة في الجلسة الأولى']);
    expect(second.result.current.sentAnswers).toEqual([]);
  });
});