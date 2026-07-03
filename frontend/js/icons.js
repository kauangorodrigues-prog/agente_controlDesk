// ══════════════════════════════════════════════════════════════════
// Ícones SVG (stroke) — inline, sem dependências externas
// ══════════════════════════════════════════════════════════════════
const P = 'stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"';

const PATHS = {
  dashboard: `<rect x="3" y="3" width="7" height="9" rx="1.5" ${P}/><rect x="14" y="3" width="7" height="5" rx="1.5" ${P}/><rect x="14" y="12" width="7" height="9" rx="1.5" ${P}/><rect x="3" y="16" width="7" height="5" rx="1.5" ${P}/>`,
  users: `<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" ${P}/><circle cx="9" cy="7" r="4" ${P}/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" ${P}/>`,
  target: `<circle cx="12" cy="12" r="9" ${P}/><circle cx="12" cy="12" r="5" ${P}/><circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none"/>`,
  gauge: `<path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" ${P}/><path d="m13.4 10.6 3.6-3.6" ${P}/><path d="M3.5 18a9 9 0 1 1 17 0" ${P}/>`,
  list: `<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" ${P}/>`,
  phone: `<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z" ${P}/>`,
  chart: `<path d="M3 3v18h18" ${P}/><path d="m7 14 4-4 3 3 5-6" ${P}/>`,
  trending: `<path d="m3 17 6-6 4 4 8-8" ${P}/><path d="M21 7v6h-6" ${P}/>`,
  calendar: `<rect x="3" y="4" width="18" height="18" rx="2" ${P}/><path d="M16 2v4M8 2v4M3 10h18" ${P}/>`,
  shield: `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" ${P}/><path d="m9 12 2 2 4-4" ${P}/>`,
  bell: `<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" ${P}/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" ${P}/>`,
  pause: `<rect x="6" y="4" width="4" height="16" rx="1" ${P}/><rect x="14" y="4" width="4" height="16" rx="1" ${P}/>`,
  play: `<path d="m5 3 14 9-14 9V3Z" ${P}/>`,
  refresh: `<path d="M3 12a9 9 0 0 1 15-6.7L21 8" ${P}/><path d="M21 3v5h-5" ${P}/><path d="M21 12a9 9 0 0 1-15 6.7L3 16" ${P}/><path d="M3 21v-5h5" ${P}/>`,
  logout: `<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" ${P}/><path d="m16 17 5-5-5-5M21 12H9" ${P}/>`,
  plus: `<path d="M12 5v14M5 12h14" ${P}/>`,
  trash: `<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" ${P}/>`,
  menu: `<path d="M3 12h18M3 6h18M3 18h18" ${P}/>`,
  clock: `<circle cx="12" cy="12" r="9" ${P}/><path d="M12 7v5l3 2" ${P}/>`,
  check: `<path d="M20 6 9 17l-5-5" ${P}/>`,
  x: `<path d="M18 6 6 18M6 6l12 12" ${P}/>`,
  download: `<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" ${P}/>`,
  database: `<ellipse cx="12" cy="5" rx="9" ry="3" ${P}/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" ${P}/><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" ${P}/>`,
  activity: `<path d="M22 12h-4l-3 9L9 3l-3 9H2" ${P}/>`,
  "alert-triangle": `<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" ${P}/><path d="M12 9v4M12 17h.01" ${P}/>`,
  "alert-octagon": `<path d="M7.86 2h8.28L22 7.86v8.28L16.14 22H7.86L2 16.14V7.86L7.86 2Z" ${P}/><path d="M12 8v4M12 16h.01" ${P}/>`,
  info: `<circle cx="12" cy="12" r="9" ${P}/><path d="M12 16v-4M12 8h.01" ${P}/>`,
  filter: `<path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3Z" ${P}/>`,
  layers: `<path d="m12 2 9 5-9 5-9-5 9-5Z" ${P}/><path d="m3 12 9 5 9-5M3 17l9 5 9-5" ${P}/>`,
  zap: `<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z" ${P}/>`,
  inbox: `<path d="M22 12h-6l-2 3h-4l-2-3H2" ${P}/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z" ${P}/>`,
  spark: `<path d="m12 3-1.9 5.8L4 10.6l5.2 3.4L7.7 20 12 16.4 16.3 20l-1.5-6L20 10.6l-6.1-1.8L12 3Z" ${P}/>`,
  settings: `<circle cx="12" cy="12" r="3" ${P}/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" ${P}/>`,
  server: `<rect x="2" y="3" width="20" height="8" rx="2" ${P}/><rect x="2" y="13" width="20" height="8" rx="2" ${P}/><path d="M6 7h.01M6 17h.01" ${P}/>`,
  sliders: `<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" ${P}/>`,
};

export function icon(name, cls = "") {
  const body = PATHS[name] || PATHS.info;
  return `<svg viewBox="0 0 24 24" class="${cls}" xmlns="http://www.w3.org/2000/svg" width="24" height="24">${body}</svg>`;
}

// Logo mark ATLAS — hexágono "A" estilizado em laranja
export function logoMark(size = 34) {
  return `<svg class="logo-mark" viewBox="0 0 48 48" width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="lg-atlas" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#FF8A2B"/><stop offset="1" stop-color="#E65A00"/>
      </linearGradient>
    </defs>
    <path d="M24 2 44 13.5v21L24 46 4 34.5v-21L24 2Z" fill="none" stroke="url(#lg-atlas)" stroke-width="2.5"/>
    <path d="M24 12 33 34h-4.2l-1.7-4.4h-6.2L19.2 34H15L24 12Zm0 8.8-2 5.2h4l-2-5.2Z" fill="url(#lg-atlas)"/>
  </svg>`;
}
