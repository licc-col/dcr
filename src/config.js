import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

export const CDROM_HTML_DIR = join(ROOT, 'CD-ROM', 'html');
export const CDROM_PRESENTA_DIR = join(ROOT, 'CD-ROM', 'ayuda', 'presenta');
export const PUBLIC_CONTEXTUAL_DIR = join(ROOT, 'public', 'contextual');

export const MONGODB_URI = 'mongodb://127.0.0.1:27017/dcr';
export const PORT = 3000;
