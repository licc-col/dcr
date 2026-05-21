/**
 * server.js — DCR Visualizer API + Static Server
 * Node.js 22 + Express 5 + MongoDB 8
 */
import express from 'express';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import mongoose from 'mongoose';
import { MONGODB_URI, PORT } from '../config.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const PUBLIC = join(ROOT, 'public');

const app = express();
app.use(express.json());
app.use(express.static(PUBLIC));

// --- Database Connection ---
mongoose.connect(MONGODB_URI).then(() => console.log('Connected to MongoDB'));

// ── Models (lightweight — no full schema needed here) ────────────────────────
const Lemma = mongoose.model('Lemma', new mongoose.Schema({
  lemma: String, slug: String, grammaticalCategory: String,
  introduction: String, acepciones: mongoose.Schema.Types.Mixed,
  etymology: String, transformedHtml: String,
  authorsUsed: [String], abbrevsUsed: [String],
}, { collection: 'lemmas' }));

const Abbreviation = mongoose.model('Abbreviation', new mongoose.Schema(
  { abbrev: String, expansion: String }, { collection: 'abbreviations' }
));

const Author = mongoose.model('Author', new mongoose.Schema(
  { abbrev: String, fullInfo: String }, { collection: 'authors' }
));

// ── LEMMA endpoints ───────────────────────────────────────────────────────────

// Autocomplete: fast prefix match on lemma field
app.get('/api/autocomplete', async (req, res) => {
  const q = (req.query.q || '').trim().toUpperCase();
  if (!q) return res.json([]);
  const results = await Lemma.find(
    { lemma: { $regex: `^${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, $options: 'i' } },
    { lemma: 1, slug: 1, grammaticalCategory: 1, _id: 0 }
  ).limit(15);
  res.json(results);
});

// Search + pagination
app.get('/api/lemmas', async (req, res) => {
  const { q = '', page = 1, limit = 30, letter } = req.query;
  const pg = Math.max(1, parseInt(page));
  const lm = Math.min(100, Math.max(1, parseInt(limit)));
  const skip = (pg - 1) * lm;

  let filter = {};
  if (q.trim()) {
    filter = { lemma: { $regex: q.trim(), $options: 'i' } };
  } else if (letter) {
    filter = { lemma: { $regex: `^${letter.toUpperCase()}`, $options: 'i' } };
  }

  const [total, items] = await Promise.all([
    Lemma.countDocuments(filter),
    Lemma.find(filter, { lemma: 1, slug: 1, grammaticalCategory: 1, introduction: 1, _id: 0 })
         .sort({ lemma: 1 }).skip(skip).limit(lm),
  ]);

  res.json({ total, page: pg, pages: Math.ceil(total / lm), items });
});

// Single lemma — full data
app.get('/api/lemmas/:slug', async (req, res) => {
  const doc = await Lemma.findOne({ slug: req.params.slug.toLowerCase() }).lean();
  if (!doc) return res.status(404).json({ error: 'Lemma not found' });
  res.json(doc);
});

// Single lemma — transformed HTML only (lightweight)
app.get('/api/lemmas/:slug/html', async (req, res) => {
  const doc = await Lemma.findOne(
    { slug: req.params.slug.toLowerCase() },
    { transformedHtml: 1, lemma: 1, grammaticalCategory: 1, _id: 0 }
  ).lean();
  if (!doc) return res.status(404).json({ error: 'Not found' });
  res.json(doc);
});

// ── ABBREVIATION endpoints ────────────────────────────────────────────────────
app.get('/api/abbreviations', async (req, res) => {
  const items = await Abbreviation.find({}, { _id: 0 }).sort({ abbrev: 1 });
  res.json(items);
});

app.get('/api/abbreviations/:key', async (req, res) => {
  const key = decodeURIComponent(req.params.key);
  // Try exact match first
  let doc = await Abbreviation.findOne({ abbrev: key }, { _id: 0 }).lean();
  if (!doc) {
    // Fallback to case-insensitive match
    doc = await Abbreviation.findOne({ abbrev: { $regex: `^${key}$`, $options: 'i' } }, { _id: 0 }).lean();
  }
  if (!doc) return res.status(404).json({ error: 'Abbreviation not found' });
  res.json(doc);
});

// ── AUTHOR endpoints ──────────────────────────────────────────────────────────
app.get('/api/authors', async (req, res) => {
  const items = await Author.find({}, { _id: 0 }).sort({ abbrev: 1 });
  res.json(items);
});

app.get('/api/authors/:key', async (req, res) => {
  const key = decodeURIComponent(req.params.key);
  const doc = await Author.findOne({ abbrev: key }, { _id: 0 }).lean();
  if (!doc) {
    // Try partial match
    const partial = await Author.findOne(
      { abbrev: { $regex: key.replace(/\./g, '\\.'), $options: 'i' } },
      { _id: 0 }
    ).lean();
    if (!partial) return res.status(404).json({ error: 'Author not found' });
    return res.json(partial);
  }
  res.json(doc);
});

// ── CONTEXTUAL PAGES ──────────────────────────────────────────────────────────
app.get('/contextual/:page', (req, res) => {
  const slug = req.params.page.replace(/[^a-z0-9_-]/g, '');
  res.sendFile(join(PUBLIC, 'contextual', `${slug}.html`), err => {
    if (err) res.status(404).send('Page not found');
  });
});

// ── SPA fallback ──────────────────────────────────────────────────────────────
app.get('*path', (req, res) => {
  if (!req.path.startsWith('/api')) {
    res.sendFile(join(PUBLIC, 'index.html'));
  }
});

app.listen(PORT, () => {
  console.log(`\n🟢 DCR Visualizer at http://localhost:${PORT}\n`);
});
