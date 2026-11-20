let embeddedFont: Promise<string> | undefined;
function getReportFont() {
  if (embeddedFont) return embeddedFont;
  embeddedFont = (async () => {
    const sheet = document.querySelector<HTMLLinkElement>('link[href*="fonts.googleapis.com/css"]');
    if (!sheet) return '';
    const response = await fetch(sheet.href);
    if (!response.ok) throw new Error('Font stylesheet unavailable');
    let css = await response.text();
    const urls = [...new Set([...css.matchAll(/url\((https:[^)]+)\)/g)].map(match => match[1]).filter((url): url is string => Boolean(url)))];
    await Promise.all(urls.map(async url => {
      const font = await fetch(url); if (!font.ok) throw new Error('Font unavailable');
      const blob = await font.blob();
      const data = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => typeof reader.result === 'string' ? resolve(reader.result) : reject(new Error('Font conversion failed')); reader.onerror = reject; reader.readAsDataURL(blob); });
      css = css.split(url).join(data);
    }));
    return css;
  })().catch(() => { embeddedFont = undefined; return ''; });
  return embeddedFont;
}
export async function downloadReportPdf(element: HTMLElement) {
  const [{ toPng }, { jsPDF }] = await Promise.all([import('html-to-image'), import('jspdf')]);
  await document.fonts.ready;
  const fontEmbedCSS = await getReportFont();
  const image = await toPng(element, { pixelRatio: 1.5, backgroundColor: getComputedStyle(element).backgroundColor, cacheBust: false, fontEmbedCSS, skipFonts: !fontEmbedCSS });
  const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const width = 190;
  const height = element.scrollHeight * width / element.scrollWidth;
  const usableHeight = 277;
  let position = 10;
  pdf.addImage(image, 'PNG', 10, position, width, height);
  for (let remaining = height - usableHeight; remaining > 0; remaining -= usableHeight) {
    position -= usableHeight; pdf.addPage(); pdf.addImage(image, 'PNG', 10, position, width, height);
  }
  pdf.save('تقرير_مقابلة_سند.pdf');
}