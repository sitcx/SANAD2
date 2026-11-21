/**
 * Web accessibility assistant (browser side): extracts what is visible on the current page, in reading order,
 * and asks the Sanad API (POST /accessibility/describe) for a short Arabic spoken guide.
 * The LLM and its key live on the server only. Only visible text, labels and link paths are sent
 * (no field values, no query strings).
 */

export type PageElementKind = 'heading' | 'text' | 'button' | 'link' | 'field' | 'form' | 'image';
export type PageRegion = 'header' | 'nav' | 'main' | 'aside' | 'footer' | 'dialog' | 'other';
export type PageElement = { id: string; kind: PageElementKind; text: string; level?: number; region: PageRegion; href?: string | undefined; field_type?: string; required?: boolean | undefined; disabled?: boolean | undefined };
export type PageContent = { url: string; title: string; elements: PageElement[] };
export type PageDescription = { via: 'llm' | 'rules'; model: string | null; speech: string[]; description: { purpose: string; main_heading: string; introduction: string } };

const MAX_ELEMENTS = 400;
const MAX_TEXT = 400;
const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'CANVAS', 'VIDEO', 'AUDIO', 'IFRAME']);
const TEXT_BLOCKS = new Set(['P', 'LI', 'DD', 'DT', 'TD', 'TH', 'FIGCAPTION', 'BLOCKQUOTE', 'CAPTION', 'LEGEND', 'SUMMARY']);
const INTERACTIVE = 'a[href],button,input,select,textarea,[role="button"],[role="link"],h1,h2,h3,h4,h5,h6,[role="heading"]';
const REGION_SELECTOR = 'header,nav,main,aside,footer,dialog,[role="dialog"],[role="alertdialog"],[role="banner"],[role="navigation"],[role="main"],[role="complementary"],[role="contentinfo"]';
const REGION_BY_ROLE: Record<string, PageRegion> = { banner: 'header', navigation: 'nav', main: 'main', complementary: 'aside', contentinfo: 'footer', dialog: 'dialog', alertdialog: 'dialog' };

function clean(text: string | null | undefined): string {
  return (text ?? '').replace(/\s+/g, ' ').trim().slice(0, MAX_TEXT);
}

function hidden(el: Element): boolean {
  if (el.closest('[aria-hidden="true"],[hidden],[inert]')) return true;
  const check = (el as HTMLElement & { checkVisibility?: () => boolean }).checkVisibility;
  return typeof check === 'function' ? !check.call(el) : false;
}

function regionOf(el: Element): PageRegion {
  const landmark = el.closest(REGION_SELECTOR);
  if (!landmark) return 'other';
  const role = landmark.getAttribute('role');
  if (role && REGION_BY_ROLE[role]) return REGION_BY_ROLE[role]!;
  const tag = landmark.tagName.toLowerCase();
  return tag === 'dialog' ? 'dialog' : (['header', 'nav', 'main', 'aside', 'footer'].includes(tag) ? tag as PageRegion : 'other');
}

function nameOf(el: Element): string {
  const aria = el.getAttribute('aria-label');
  if (aria?.trim()) return clean(aria);
  const labelledBy = el.getAttribute('aria-labelledby');
  if (labelledBy) {
    const text = labelledBy.split(/\s+/).map(id => document.getElementById(id)?.textContent ?? '').join(' ');
    if (text.trim()) return clean(text);
  }
  if (el instanceof HTMLInputElement || el instanceof HTMLSelectElement || el instanceof HTMLTextAreaElement) {
    const label = el.labels?.[0]?.textContent;
    if (label?.trim()) return clean(label);
    if ('placeholder' in el && el.placeholder) return clean(el.placeholder);
    if (el instanceof HTMLInputElement && ['submit', 'button', 'reset'].includes(el.type)) return clean(el.value);
  }
  return clean(el.textContent) || clean(el.getAttribute('title'));
}

function linkPath(anchor: HTMLAnchorElement): string {
  try {
    const url = new URL(anchor.href, window.location.href);
    if (url.protocol === 'mailto:') return 'mailto';
    return url.origin === window.location.origin ? `${url.pathname}${url.hash}` : url.hostname;
  } catch { return ''; }
}

/** Visible content of the page in DOM (reading) order. */
export function extractPageContent(root: Element = document.body): PageContent {
  const elements: PageElement[] = [];
  let last = '';
  const add = (el: Element, item: Omit<PageElement, 'id' | 'region'>) => {
    if (!item.text && item.kind !== 'field') return;
    if (item.kind === 'text' && item.text === last) return;
    last = item.text;
    elements.push({ id: `e${elements.length + 1}`, region: regionOf(el), ...item });
  };
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, {
    acceptNode: node => {
      const el = node as Element;
      if (SKIP.has(el.tagName.toUpperCase()) || hidden(el)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  let node = walker.nextNode();
  while (node && elements.length < MAX_ELEMENTS) {
    const el = node as Element;
    const tag = el.tagName.toUpperCase();
    const role = el.getAttribute('role');
    let consumed = true;   // true: the element's text is taken as a whole, so its children are skipped
    if (/^H[1-6]$/.test(tag) || role === 'heading') {
      add(el, { kind: 'heading', text: nameOf(el), level: Number(el.getAttribute('aria-level') ?? tag.slice(1)) || 2 });
    } else if (tag === 'BUTTON' || role === 'button' || (el instanceof HTMLInputElement && ['submit', 'button', 'reset'].includes(el.type))) {
      add(el, { kind: 'button', text: nameOf(el), disabled: (el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true' || undefined });
    } else if ((tag === 'A' && (el as HTMLAnchorElement).href) || role === 'link') {
      add(el, { kind: 'link', text: nameOf(el), href: el instanceof HTMLAnchorElement ? linkPath(el) : undefined });
    } else if ((el instanceof HTMLInputElement && el.type !== 'hidden') || el instanceof HTMLSelectElement || el instanceof HTMLTextAreaElement) {
      add(el, { kind: 'field', text: nameOf(el), field_type: el instanceof HTMLInputElement ? el.type : tag.toLowerCase(), required: el.required || undefined, disabled: el.disabled || undefined });
    } else if (tag === 'IMG') {
      add(el, { kind: 'image', text: clean(el.getAttribute('alt')) });
    } else if (tag === 'FORM') {
      add(el, { kind: 'form', text: clean(el.getAttribute('aria-label')) || clean(el.querySelector('legend')?.textContent) });
      consumed = false;
    } else if (TEXT_BLOCKS.has(tag) && !el.querySelector(INTERACTIVE)) {
      add(el, { kind: 'text', text: clean(el.textContent) });
    } else {
      // Text written directly inside a container (div/span), without its children's text.
      const own = clean([...el.childNodes].filter(child => child.nodeType === Node.TEXT_NODE).map(child => child.textContent).join(' '));
      if (own) add(el, { kind: 'text', text: own });
      consumed = false;
    }
    node = consumed ? skipSubtree(walker) : walker.nextNode();
  }
  return { url: window.location.pathname, title: clean(document.title).slice(0, 200), elements };
}

function skipSubtree(walker: TreeWalker): Node | null {
  let next = walker.nextSibling();
  while (!next) {
    const parent = walker.parentNode();
    if (!parent) return null;
    next = walker.nextSibling();
  }
  return next;
}

function apiBase(): string {
  return ((import.meta.env['VITE_SANAD_API_URL'] as string | undefined) || 'http://localhost:8010').replace(/\/+$/, '');
}

/** Ask the Sanad API to describe the current page. Throws on network/API errors (the caller falls back). */
export async function describeCurrentPage(signal?: AbortSignal): Promise<PageDescription> {
  const page = extractPageContent();
  if (!page.elements.length) throw new Error('empty page');
  const response = await fetch(`${apiBase()}/accessibility/describe`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(page), signal: signal ?? null,
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const reply = await response.json() as PageDescription;
  if (!Array.isArray(reply.speech) || !reply.speech.length) throw new Error('empty description');
  return reply;
}
