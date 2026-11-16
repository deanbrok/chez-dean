// HTML for the reading panels. One family (paper, ink, brass, small caps), a different object for each kind.
import { POSTS, NOW, SHELVES, BOTTLES, WRITING, ABOUT, COLOPHON, ODDS, PAPERBACK, CONTACT, PLACES, DOWNSTAIRS } from './content.js';

export const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sample = (t = 'sample') => `<span class="sample">${esc(t)}</span>`;
const nextLink = (group, i, n, label) => n > 1
  ? `<nav class="leaf" aria-label="More ${esc(label)}"><button data-go="${group}:${(i + n - 1) % n}">&larr; previous</button><span>${i + 1} / ${n}</span><button data-go="${group}:${(i + 1) % n}">next &rarr;</button></nav>` : '';

// slug -> {group, index} for deep links
export const SLUGS = {};
POSTS.forEach((p, i) => { SLUGS['post-' + p.slug] = ['rec', i]; });
SHELVES.forEach((s, i) => { SLUGS['reading-' + s.slug] = ['book', i]; });
BOTTLES.forEach((b, i) => { SLUGS['bottle-' + b.slug] = ['bottle', i]; });
Object.assign(SLUGS, { now: ['nowplaying'], writing: ['manuscript'], about: ['note'], colophon: ['matchbook'], odds: ['cigarbox'],
  'currently-reading': ['paperback'], contact: ['phone'], places: ['mapframe'], downstairs: ['door'] });
export function slugFor(group, i) {
  for (const [k, v] of Object.entries(SLUGS)) if (v[0] === group && (v[1] === undefined || v[1] === i)) return k;
  return '';
}

function post(i) {
  const p = POSTS[i % POSTS.length];
  return { cls: 'k-liner', label: 'Liner notes: ' + p.title, html: `
    <article class="paper">
      <div class="strip"><span>Dean&rsquo;s Records &middot; ${esc(p.cat)}</span><span>Stereo &middot; 33&#8531;</span></div>
      <h2>${esc(p.title)}</h2><p class="sub">${esc(p.sub)}</p>
      <div class="meta">${esc(p.date)} &middot; ${p.mins} min &middot; ${sample('sample post')}</div>
      <p class="intro">${esc(p.intro)}</p>
      ${p.sides.map((s) => `<h3><span>${esc(s.name)}</span><em>${s.tracks.length} ${s.tracks.length === 1 ? 'track' : 'tracks'}</em></h3>
        <ol class="tracks">${s.tracks.map((t) => `<li>${esc(t[0])}<span>${esc(t[1])}</span></li>`).join('')}</ol>
        ${s.text.map((x) => `<p>${esc(x)}</p>`).join('')}`).join('')}
      <div class="foot"><span>Notes by the proprietor</span><span>Pressed in the small hours</span></div>
      ${nextLink('rec', i, POSTS.length, 'records')}
    </article>` };
}

function now() {
  const n = NOW;
  return { cls: 'k-back', label: 'Now', html: `
    <article class="paper">
      <div class="backtop"><div><span class="kick">Now playing at Dean&rsquo;s</span><h2>${esc(n.album)}</h2><p class="sub">${esc(n.artist)}</p></div>
        <div class="cat-no">${esc(n.cat)}<br><small>${esc(n.month)}</small></div></div>
      <div class="cols">${n.sides.map((s) => `<section><h3><b>${esc(s.code)}</b> ${esc(s.title)}</h3><p>${esc(s.text)}</p></section>`).join('')}</div>
      <p class="fine">${esc(n.small)} &nbsp;${sample()}</p>
      <div class="barcode" aria-hidden="true"></div>
    </article>` };
}

function shelf(i) {
  const s = SHELVES[i % SHELVES.length];
  return { cls: 'k-card', label: 'Reading list: ' + s.title, html: `
    <article class="paper">
      <div class="cardhead"><span>Dean&rsquo;s &middot; lending shelf</span><span>No. ${i + 1}</span></div>
      <h2>${esc(s.title)}</h2><p class="sub">${esc(s.note)}</p>
      <table class="ledger"><thead><tr><th>Title</th><th>Author</th></tr></thead><tbody>
        ${s.books.map((b) => `<tr><td><b>${esc(b[0])}</b><i>${esc(b[2])}</i></td><td>${esc(b[1])}</td></tr>`).join('')}
      </tbody></table>
      <div class="stamp" aria-hidden="true">Returned</div>
      <p class="fine">Borrow freely, return eventually. Invented titles &mdash; ${sample('sample list')}</p>
      ${nextLink('book', i, SHELVES.length, 'shelves')}
    </article>` };
}

function bottle(i) {
  const b = BOTTLES[i % BOTTLES.length];
  return { cls: 'k-tag', label: 'Bottle keep: ' + b.name, html: `
    <article class="paper tag">
      <i class="hole" aria-hidden="true"></i>
      <div class="kept">Bottle keep &middot; No. ${String(i + 1).padStart(2, '0')}</div>
      <div class="for">kept for <b>Dean</b></div>
      <h2>${esc(b.name)}</h2>
      <p class="sub">${esc(b.kind)}</p>
      <dl>
        <dt>What it is</dt><dd>${esc(b.what)}</dd>
        <dt>Status</dt><dd>${esc(b.status)}</dd>
        <dt>Tasting notes</dt><dd class="notes">${esc(b.notes)}</dd>
      </dl>
      <p class="fine">${sample('sample project')}</p>
      ${nextLink('bottle', i, BOTTLES.length, 'bottles')}
    </article>` };
}

function manuscript() {
  const w = WRITING;
  return { cls: 'k-ms', label: 'Writing', html: `
    <article class="paper">
      <div class="mshead"><span>Manuscript &middot; 400 squares</span><span>${sample()}</span></div>
      <h2>${esc(w.title)}</h2>
      <p>${esc(w.intro)}</p>
      ${w.drafts.map((d) => `<section class="draft"><h3>${esc(d.title)}</h3><div class="st">${esc(d.status)} &middot; ${esc(d.words)}</div><p>${esc(d.line)}</p></section>`).join('')}
      <h3 class="frag">From the top page</h3>
      <p class="fragment">${esc(w.fragment)}<span class="caret" aria-hidden="true"></span></p>
    </article>` };
}

function about() {
  return { cls: 'k-tent', label: 'About', html: `
    <article class="paper">
      <div class="fold" aria-hidden="true"><i class="emblem"></i></div>
      <h2>${esc(ABOUT.heading)}</h2>
      ${ABOUT.lines.map((l) => `<p>${esc(l)}</p>`).join('')}
      <p class="sign">${esc(ABOUT.sign)}</p>
      <p class="fine">${sample()}</p>
    </article>` };
}

function colophon() {
  return { cls: 'k-match', label: 'Colophon', html: `
    <article class="paper">
      <div class="cover"><i class="emblem"></i><div><b>DEAN&rsquo;S</b><span>B1 &middot; records &amp; coffee &middot; open late</span></div></div>
      <h2>How this place was made</h2>
      <dl>${COLOPHON.lines.map((l) => `<dt>${esc(l[0])}</dt><dd>${esc(l[1])}</dd>`).join('')}</dl>
      <p class="fine">${esc(COLOPHON.small)}</p>
      <div class="striker" aria-hidden="true"></div>
    </article>` };
}

function odds() {
  return { cls: 'k-cigar', label: 'Odds and ends', html: `
    <article class="paper">
      <div class="band"><span>Hecho a mano</span><b>Odds &amp; Ends</b><span>Caja No. 7</span></div>
      <p class="sub">${esc(ODDS.intro)}</p>
      <ul>${ODDS.items.map((x) => `<li><b>${esc(x[0])}</b><span>${esc(x[1])}</span>${x[2] ? (x[2][0] === '#'
        ? `<a href="${esc(x[2])}">open</a>` : `<code>${esc(x[2])}</code>`) : ''}</li>`).join('')}</ul>
      <p class="fine">Addresses are placeholders. ${sample()}</p>
    </article>` };
}

function paperback() {
  const p = PAPERBACK;
  return { cls: 'k-paperback', label: 'Currently reading', html: `
    <article class="paper">
      <div class="ribbon" aria-hidden="true"></div>
      <div class="pbtop"><span>Currently reading</span><span class="price">${esc(p.price)}</span></div>
      <h2>${esc(p.title)}</h2><p class="sub">${esc(p.author)}</p>
      <p class="blurb">${esc(p.blurb)}</p>
      <p>${esc(p.note)}</p>
      <div class="pbfoot"><span>Left open at ${esc(p.page)}</span><span>${sample()}</span></div>
    </article>` };
}

function contact(rang) {
  return { cls: 'k-ticket', label: 'Contact', html: `
    <article class="paper">
      <div class="tk-l"><span>Telephone</span><b>Contact</b><span class="no">No. 0042</span></div>
      <div class="tk-r">
        <p class="line">${esc(rang ? CONTACT.after : CONTACT.nobody)}</p>
        <table>${CONTACT.lines.map((l) => `<tr><th>${esc(l[0])}</th><td>${esc(l[1])}</td></tr>`).join('')}</table>
        <p class="fine">Write instead. Placeholders &mdash; ${sample()}</p>
      </div>
    </article>` };
}

function places() {
  return { cls: 'k-map', label: 'Places', html: `
    <article class="paper">
      <div class="cartouche"><span>A chart of</span><h2>Places</h2><span>kept by the proprietor</span></div>
      <p class="sub">${esc(PLACES.intro)}</p>
      <ol>${PLACES.places.map((p) => `<li><h3>${esc(p[0])}<small>${esc(p[1])}</small></h3><p>${esc(p[2])}</p></li>`).join('')}</ol>
      <p class="fine">${esc(PLACES.small)}</p>
      <div class="rose" aria-hidden="true"></div>
    </article>` };
}

function downstairs() {
  const d = DOWNSTAIRS;
  return { cls: 'k-down', label: 'Downstairs', html: `
    <article class="paper">
      <h2>${esc(d.title)}</h2>
      <p class="lead">${esc(d.lead)}</p>
      ${d.pieces.map((x) => `<section><h3>${esc(x.t)}</h3><p>${esc(x.p)}</p></section>`).join('')}
      <p class="fine">${esc(d.close)}</p>
    </article>` };
}

// group (rec, book, bottle, nowplaying, ...) + index -> {cls, label, html}
export function panelFor(group, i, state = {}) {
  switch (group) {
    case 'rec': return post(i);
    case 'book': return shelf(i);
    case 'bottle': return bottle(i);
    case 'nowplaying': return now();
    case 'manuscript': return manuscript();
    case 'note': return about();
    case 'matchbook': return colophon();
    case 'cigarbox': return odds();
    case 'paperback': return paperback();
    case 'phone': return contact(state.rang);
    case 'mapframe': return places();
    case 'door': return downstairs();
  }
  return null;
}
export const COUNTS = { rec: POSTS.length, book: SHELVES.length, bottle: BOTTLES.length };
