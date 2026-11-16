// SAMPLE CONTENT. Every post, list, project, address and title below is invented placeholder text,
// written to show the shape of the site. Nothing is quoted from real books, records or songs.
// Replace freely; the page reads everything from here.

export const SAMPLE_NOTE = 'Sample content';

export const SUBTITLE = {
  day: 'Coffee, the morning paper, a record on low.',
  night: 'Records, whisky, and the hours after closing.',
};

export const STOP_NAMES = {
  bar: 'The bar', records: 'Records', hifi: 'Turntable', table: 'Kitchen table', window: 'Window', stairs: 'Stairs',
};
export const STOP_SHORT = { bar: 'Bar', records: 'Records', hifi: 'Hi-fi', table: 'Table', window: 'Window', stairs: 'Stairs' };

// ---------------------------------------------------------------- records = posts (titles are printed on the 3D sleeves)
export const POSTS = [
  {
    slug: 'first-pressing', cat: 'DN-1001', title: 'First Pressing', sub: 'an opening set, slightly warped', date: '2 November 2026', mins: 4,
    intro: 'Every collection starts with a record you cannot quite explain owning. This is that one: the first post, pressed in a small run, and played anyway.',
    sides: [
      { name: 'Side A', tracks: [['Why a bar', '1:10'], ['What is on the shelves', '0:55'], ['House rules', '0:40']],
        text: ['I wanted somewhere on the web that worked like a small listening bar: you come in, somebody else has already chosen the record, and the polite thing is to sit through the whole side.',
               'So the shelf is the archive. The sleeves that stand a little proud of the others are posts. The books are reading lists, the bottles are projects, and the note on the counter will tell you who runs the place.'] },
      { name: 'Side B', tracks: [['What I will write about', '1:05'], ['What I will not', '0:20']],
        text: ['Expect software that had to survive real users, old maps and the people who drew them, novels that took a month and records that took a year. Expect very few opinions about frameworks.',
               'The needle is down. Everything here is sample text standing in for the real thing.'] },
    ],
  },
  {
    slug: 'side-b-is-where-the-truth-is', cat: 'DN-1002', title: 'Side B Is Where the Truth Is', sub: 'on the tracks nobody asked for', date: '19 October 2026', mins: 6,
    intro: 'The single sells the album. The second side tells you who made it. A short argument for reading a codebase, a city, or a person from the back.',
    sides: [
      { name: 'Side A', tracks: [['The single', '0:50'], ['The README', '1:20']],
        text: ['Sample paragraph. The front of anything is arranged for strangers. The landing page, the lobby, the first chapter: tidy, confident, a little rehearsed. I do not hold this against it. It is doing its job.',
               'Sample paragraph. But if I want to know how a system is really built, I open the oldest file nobody has touched in three years and read the comments. That is where the decisions are, along with the apologies.'] },
      { name: 'Side B', tracks: [['The long one at the end', '3:40'], ['Run-out groove', '0:15']],
        text: ['Sample paragraph. The second side is where a band stops trying to be liked and starts playing for itself. It is usually longer, slower, and better. Software has a second side too. It is called maintenance.'] },
    ],
  },
  {
    slug: 'a-map-of-small-hours', cat: 'DN-1003', title: 'A Map of Small Hours', sub: 'old charts, confident coastlines', date: '5 October 2026', mins: 5,
    intro: 'Old maps are wrong in instructive ways. A walk through invented islands, careful harbours and the blank interior nobody had visited yet.',
    sides: [
      { name: 'Side A', tracks: [['The coast they sailed', '1:30'], ['The interior they guessed', '2:00']],
        text: ['Sample paragraph. A sixteenth-century chart is a system diagram drawn by someone who has seen a third of the system. The coast is exact to the inlet. Inland is a rumour with a decorative border.',
               'Sample paragraph. Every architecture document I have written has an island that is not there and is missing a river that is.'] },
      { name: 'Side B', tracks: [['Compass roses', '1:00'], ['Folding it back up', '1:20']],
        text: ['Sample paragraph. The honest thing, then and now, is to mark which parts you measured and which parts you were told about late at night by someone in a harbour bar.'] },
    ],
  },
  {
    slug: 'standards-slightly-wrong', cat: 'DN-1004', title: 'Standards, Slightly Wrong', sub: 'in praise of the familiar tune', date: '21 September 2026', mins: 5,
    intro: 'Everyone plays the same thirty-two bars. The interest is in what each person does to them, and in which wrong notes they leave in on purpose.',
    sides: [
      { name: 'Side A', tracks: [['The tune everyone knows', '1:45'], ['Changes you can trust', '1:30']],
        text: ['Sample paragraph. Boring technology is a standard. You know the changes, the people you work with know the changes, and so you can listen to each other instead of the chart.',
               'Sample paragraph. The craft is in the small deviations: a substitution here, a rest there, one unexpected abstraction that turns out to be exactly right.'] },
      { name: 'Side B', tracks: [['A wrong note, kept', '1:10'], ['Last chorus', '0:50']],
        text: ['Sample paragraph. I keep a list of wrong notes I am glad I left in. It is shorter than the other list, but I read it more often.'] },
    ],
  },
  {
    slug: 'the-quiet-refactor', cat: 'DN-1005', title: 'The Quiet Refactor', sub: 'changing a thing while it is playing', date: '7 September 2026', mins: 7,
    intro: 'How to replace the engine of a system that cannot stop, written mostly for the version of me who tried to do it loudly.',
    sides: [
      { name: 'Side A', tracks: [['Nobody should notice', '2:10'], ['Strangler figs, briefly', '1:40'], ['The flag that stayed', '0:55']],
        text: ['Sample paragraph. The best migrations are the ones nobody hears about. Traffic moves a percent at a time. Dashboards stay boring. On the last day you delete a folder and go home early.',
               'Sample paragraph. The worst ones have a launch party. I have been to both kinds. The food is better at the first.'] },
      { name: 'Side B', tracks: [['Writing it down', '1:30']],
        text: ['Sample paragraph. A refactor is finished when the next person can explain why the code looks the way it does without asking you. Until then it is only moved.'] },
    ],
  },
  {
    slug: 'rain-on-b1', cat: 'DN-1006', title: 'Rain on B1', sub: 'a basement, a window, a weather report', date: '24 August 2026', mins: 3,
    intro: 'Basement rooms hear the weather before they see it. Notes from an afternoon when the only window showed ankles, umbrellas, and one very patient dog.',
    sides: [
      { name: 'Side A', tracks: [['Street level', '1:00'], ['Umbrellas, a census', '1:15']],
        text: ['Sample paragraph. From below, a city is mostly shoes. You learn to read them: the hurried ones, the ones out for no reason, the pair that stopped at the window and then thought better of it.',
               'Sample paragraph. Somebody came in, left a wet umbrella in the stand, and did not take it when they went. It is still there.'] },
      { name: 'Side B', tracks: [['Clearing', '0:45']],
        text: ['Sample paragraph. The rain stopped at four. Nobody noticed except the cat, who had been waiting for it to.'] },
    ],
  },
];

// ---------------------------------------------------------------- the sleeve on the stand: "Now"
export const NOW = {
  album: 'After Hours', artist: 'The House Trio', month: 'November 2026', cat: 'DN-NOW',
  sides: [
    { code: 'A1', title: 'Listening', text: 'Piano trios recorded in small rooms, preferably with the audience audible. Late ballads, brushes, one cough.' },
    { code: 'A2', title: 'Working on', text: 'Making internal tools quieter: fewer dashboards, better ones. Also this room, one object at a time.' },
    { code: 'B1', title: 'Reading', text: 'A long novel about a lighthouse that is not really about a lighthouse, and a short book about maps that is entirely about maps.' },
    { code: 'B2', title: 'Practising', text: 'Ordering coffee in a second language without switching back halfway. Progress is real but slow.' },
  ],
  small: 'This sleeve is changed once a month, more or less. Sample content.',
};

// ---------------------------------------------------------------- books = reading lists (invented titles and authors)
export const SHELVES = [
  { slug: 'fiction', title: 'Fiction', note: 'Novels to read slowly, ideally on a train.',
    books: [['The Lighthouse Accountant', 'M. Arvidsen', 'Ledgers, fog, and a man who counts ships that never arrive.'],
            ['Seven Rooms Below the Station', 'Haru Okabe', 'A hotel that is always one floor deeper than the lift admits.'],
            ['Winter Tenancy', 'Clara Voss', 'Two strangers share a flat for one cold season. Very little happens, exactly.'],
            ['The Cartographer’s Daughter Keeps a Bar', 'Ines Moura', 'You can guess. It is better than you guess.']] },
  { slug: 'maps-travel', title: 'Maps & Travel', note: 'For planning trips, and for not taking them.',
    books: [['A Short History of Blank Spaces', 'T. R. Hollis', 'What mapmakers drew when they did not know, and why it mattered.'],
            ['Night Trains of the Old Continent', 'Pieter Lanting', 'Timetables, sleeping cars, dining-car menus, small disappointments.'],
            ['Harbours, Mostly', 'Ada Kerr', 'One harbour per chapter. The chapter on fog is the best.'],
            ['The Atlas in the Attic', 'Jun Seto', 'A family atlas, annotated by three generations who disagreed.']] },
  { slug: 'craft', title: 'Craft', note: 'Software, mostly the human parts of it.',
    books: [['Quiet Systems', 'Lena Marsh', 'Designing services that are dull to operate, on purpose.'],
            ['The Second Reader', 'O. Bakker', 'Writing code for the person who arrives after you.'],
            ['Small Tools, Sharp', 'D. Whitcombe', 'Command lines, notebooks, and the virtue of things that do one job.'],
            ['Incidents I Have Known', 'Ravi Menon', 'Post-mortems as short stories. Kind, funny, alarming.']] },
  { slug: 'listening', title: 'Listening', note: 'Books about records, rooms and the people who play in them.',
    books: [['The Room Is an Instrument', 'S. Aoki', 'Why the same record sounds different in a basement.'],
            ['Liner Notes, Collected', 'various hands', 'An anthology of the small essays on the backs of sleeves.'],
            ['Brushes', 'Tom Ferreira', 'A drummer’s memoir. Mostly about listening to the bass player.'],
            ['One Microphone', 'Yuki Hamada', 'Recording a trio the old way, and what gets lost when you don’t.']] },
];

// ---------------------------------------------------------------- bottle keep = projects
export const BOTTLES = [
  { slug: 'this-room', name: 'This Room', kind: 'A personal website, built as a place', status: 'Open · two-thirds full',
    what: 'A small basement bar in 3D, modelled and lit in Blender, served as a static page. Each object opens a part of the site.',
    notes: 'Walnut, warm valves, a trace of cigar box. Long finish.' },
  { slug: 'queue-weather', name: 'Queue Weather', kind: 'A rate-limiter simulator', status: 'Open · half full',
    what: 'Watch requests arrive like weather and try different limiters against them: token buckets, sliding windows, polite refusals.',
    notes: 'Dry. Faint ozone. Surprisingly good with graphs.' },
  { slug: 'margin', name: 'Margin', kind: 'A reading journal', status: 'Sealed · not yet opened',
    what: 'A tiny app for keeping the sentences you underline, with the page number and the weather that day.',
    notes: 'Paper, pencil shavings, the smell of a second-hand shop.' },
  { slug: 'night-ferry', name: 'Night Ferry', kind: 'A small game, abandoned twice', status: 'Nearly empty · kept for sentiment',
    what: 'A slow game about running the bar on a ferry that crosses the same strait every night. One deck, one record player.',
    notes: 'Salt, diesel, a sweetness that fades too quickly.' },
];

// ---------------------------------------------------------------- the manuscript on the kitchen table
export const WRITING = {
  title: 'Writing',
  intro: 'Work in progress. Drafts live here until they are either finished or quietly moved to the drawer downstairs.',
  drafts: [
    { title: 'Notes on a Stopped Clock', status: 'second draft', words: '2,400 words', line: 'An essay about systems that are correct exactly twice a day.' },
    { title: 'The Owner Has Stepped Out', status: 'first draft', words: '900 words', line: 'A short story. A bar, a record still turning, a customer who stays.' },
    { title: 'How We Name Things', status: 'outline', words: 'outline only', line: 'On variable names, street names and the names of cats.' },
  ],
  fragment: 'The record had reached the quiet track near the end of the side, the one nobody ever requests, and he was about to get up and turn it over when he noticed that the second glass on the counter',
};

// ---------------------------------------------------------------- the tent card on the counter: About
export const ABOUT = {
  heading: 'Back in a minute.',
  lines: [
    'This is Dean’s. Sit anywhere; the stool in the middle is the good one.',
    'I am a software engineer. By day I build the quiet tools other teams depend on; by night I collect records, old maps and novels I mean to finish.',
    'This room is my corner of the internet. The records on the shelf are things I have written. The books are reading lists. The bottles behind the bar are projects, kept with a name tag like a regular’s bottle.',
    'If the phone rings, you may answer it.',
  ],
  sign: '— D.',
};

// ---------------------------------------------------------------- the matchbook: colophon
export const COLOPHON = {
  lines: [
    ['Room', 'Modelled in Blender, entirely by script, by several hands working to one floor plan.'],
    ['Light', 'Baked twice, once for night and once for day, into texture atlases. Nothing is lit in your browser.'],
    ['Page', 'three.js, plain HTML and CSS, no build step. The day and night follow your own clock.'],
    ['Sound', 'Synthesised as you listen. Off unless you ask for it.'],
    ['Type', 'Playfair Display, EB Garamond and Oswald, when the network allows.'],
  ],
  small: 'Strike gently. Sample content.',
};

// ---------------------------------------------------------------- the cigar box: odds and ends
export const ODDS = {
  intro: 'Things that did not fit anywhere else, kept in the box they came in.',
  items: [
    ['Elsewhere', 'code, notes, the odd photograph', 'example.org/dean'],
    ['Feed', 'new records on the shelf, by post', 'example.org/feed.xml'],
    ['Downstairs', 'the other side of the house', '#downstairs'],
    ['Colophon', 'how the room was made', '#colophon'],
    ['A receipt', 'one coffee, one whisky, no date', null],
    ['A guitar pick', 'nobody here plays guitar', null],
  ],
};

// ---------------------------------------------------------------- the paperback on the counter
export const PAPERBACK = {
  title: 'Norwegian Wood', author: 'Haruki Murakami', price: '¥480', page: 'p. 142',
  blurb: 'Tokyo, the late sixties. A quiet student is caught between two young women: one slowly withdrawing from the world, one who walks straight into his life. Years later, a song heard by chance brings it all back.',
  note: 'Reading it again, one chapter after closing. It reads differently down here, with a record still turning. (Sample note.)',
};

// ---------------------------------------------------------------- the pay phone: contact
export const CONTACT = {
  lines: [
    ['Post', 'dean@example.com'],
    ['Elsewhere', 'example.org/dean'],
    ['Hours', 'Replies after closing, usually within the week'],
  ],
  nobody: 'You lift the receiver. Nobody is on the line.',
  after: 'The receiver is still warm. Nobody is on the line.',
};

// ---------------------------------------------------------------- the framed map: places
export const PLACES = {
  intro: 'Places I have been, or keep meaning to go back to. Distances are approximate; opinions are firm.',
  places: [
    ['Kyoto', '35°00′N 135°46′E', 'Small coffee shops with one long counter and a man who has been pouring for forty years.'],
    ['Vienna', '48°12′N 16°22′E', 'Cafés that let you stay all afternoon with one cup, a newspaper on a wooden stick.'],
    ['Trieste', '45°39′N 13°46′E', 'Wind, coffee, a city that seems to belong to three countries at once.'],
    ['Hoi An', '15°53′N 108°20′E', 'Lanterns, tailors, and the best breakfast I have ever eaten on a plastic stool.'],
    ['Lisbon', '38°43′N 9°08′W', 'Hills, trams, tiles, and a record shop that closed while I was inside it.'],
  ],
  small: 'Not to be used for navigation. Sample content.',
};

// ---------------------------------------------------------------- downstairs
export const DOWNSTAIRS = {
  title: 'Downstairs',
  lead: 'The other side of the house. Fiction, half-formed ideas, things that do not belong upstairs.',
  pieces: [
    { t: 'The Stairs', p: 'There are more of them than there should be. Nobody has counted twice and got the same number.' },
    { t: 'The Late Train', p: 'An idea for a story. A train that leaves after the last train. Only one person in the city has a ticket, and she has not decided whether to use it.' },
    { t: 'Unsent', p: 'Letters to people who would not mind receiving them, which is why they are never sent.' },
  ],
  close: 'Sample content. Mind the step.',
};

// ---------------------------------------------------------------- dry lines
export const CAT_LINES = [
  'The cat does not look up.',
  'The cat has heard this record before.',
  'The cat is not taking requests.',
  'The cat considers you, briefly, and goes back to sleep.',
  'It is the cat’s bar. You are welcome to sit.',
  'The cat would like you to know that the stool was warm before you.',
];
export const PHONE_WHISPER = 'Somewhere, a telephone.';
export const REEL_LINE = 'The tape is threaded. Not yet.';

export const HELP = {
  title: 'Pull up a stool',
  items: [
    'Move the mouse to look around a little; on a phone the room sways by itself.',
    'Click a part of the room to go there, or use the dial at the bottom, the arrow keys, 1–6, or a swipe.',
    'Small brass rings mark what opens. Records are posts, books are reading lists, bottles are projects.',
    '♪ or the record on the turntable for sound. The sun and moon follow your clock unless you change them.',
    'Esc closes a page, then takes you back to your stool.',
  ],
  small: 'All text in this room is sample content.',
};
