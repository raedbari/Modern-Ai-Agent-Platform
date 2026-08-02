const SVG_NS = 'http://www.w3.org/2000/svg';

/** Build a static, decorative SVG without injecting HTML strings. */
export function createIcon(
  className: string,
  paths: string[],
  viewBox = '0 0 24 24',
): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('class', className);
  svg.setAttribute('viewBox', viewBox);
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '2');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');

  for (const data of paths) {
    const path = document.createElementNS(SVG_NS, 'path');
    path.setAttribute('d', data);
    svg.appendChild(path);
  }
  return svg;
}

export const ICON_PATHS = {
  chat: [
    'M21 15a4 4 0 0 1-4 4H8l-5 3 1.7-5.1A7 7 0 0 1 3 12V8a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z',
    'M8 10h.01',
    'M12 10h.01',
    'M16 10h.01',
  ],
  close: ['M18 6 6 18', 'M6 6 18 18'],
  send: ['m22 2-7 20-4-9-9-4z', 'M22 2 11 13'],
  sparkle: [
    'm12 3-1.2 3.1a3 3 0 0 1-1.7 1.7L6 9l3.1 1.2a3 3 0 0 1 1.7 1.7L12 15l1.2-3.1a3 3 0 0 1 1.7-1.7L18 9l-3.1-1.2a3 3 0 0 1-1.7-1.7z',
  ],
} as const;
