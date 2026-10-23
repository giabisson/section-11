import fs from 'node:fs';
import path from 'node:path';

const SECRET_FIELD = /^(?:intervals_key|api_?key|bot_?token|access_?token|refresh_?token|id_?token|token|password|client_?secret)$/i;
const PRIVATE_NAME = /(?:^|[\\/\s"'`])(?:\.sync_config\.json|openclaw\.json(?:\.bak[^\\/\s"']*)?|auth-profiles\.json|\.env(?:\.[^\\/\s"']*)?)(?:$|[\\/\s"'`])/i;
const UNAVAILABLE = 'Credential protection is unavailable; tool output withheld. Repair the private runtime configuration.';
const MASK = '[CREDENTIAL REDACTED]';

function strings(value, found = []) {
  if (typeof value === 'string') found.push(value);
  else if (Array.isArray(value)) value.forEach(v => strings(v, found));
  else if (value && typeof value === 'object') Object.values(value).forEach(v => strings(v, found));
  return found;
}

export function loadSecrets(files) {
  if (!Array.isArray(files) || !files.length) throw new Error('Missing credential sources');
  const values = new Set();
  function visit(value) {
    if (!value || typeof value !== 'object') return;
    for (const [key, item] of Object.entries(value)) {
      if (SECRET_FIELD.test(key) && typeof item === 'string' && item.length >= 6 && !item.startsWith('${')) {
        values.add(item);
        values.add(encodeURIComponent(item));
        values.add(JSON.stringify(item).slice(1, -1));
        values.add(Buffer.from(`API_KEY:${item}`).toString('base64'));
      } else if (item && typeof item === 'object') visit(item);
    }
  }
  for (const file of files) {
    if (!path.isAbsolute(file)) throw new Error('Credential source must be absolute');
    const st = fs.lstatSync(file);
    if (!st.isFile() || st.isSymbolicLink() || (st.mode & 0o077)) throw new Error('Credential source must be a private ordinary file');
    if (st.size > 2_000_000) throw new Error('Credential source exceeds limit');
    visit(JSON.parse(fs.readFileSync(file, 'utf8')));
  }
  if (!values.size) throw new Error('No credentials resolved');
  return [...values].sort((a, b) => b.length - a.length);
}

export function redact(value, secrets, seen = new WeakMap()) {
  if (typeof value === 'string') {
    for (const secret of secrets) value = value.split(secret).join(MASK);
    return value;
  }
  if (!value || typeof value !== 'object') return value;
  if (seen.has(value)) return seen.get(value);
  if (Buffer.isBuffer(value) || ArrayBuffer.isView(value)) return value;
  const out = Array.isArray(value) ? [] : {};
  seen.set(value, out);
  for (const [key, item] of Object.entries(value)) out[redact(key, secrets)] = redact(item, secrets, seen);
  return out;
}

export function beforeTool(event, files) {
  try {
    const secrets = loadSecrets(files);
    const text = strings(event.params).join('\n');
    const paths = [...strings(event.params), ...strings(event.derivedPaths)];
    const protectedPaths = files.map(f => fs.realpathSync(f));
    const directPrivatePath = paths.some(p => {
      if (!path.isAbsolute(p)) return false;
      try { return protectedPaths.includes(fs.realpathSync(p)); } catch { return false; }
    });
    if (directPrivatePath || PRIVATE_NAME.test(text) || secrets.some(s => text.includes(s)) || /(?:^|[;|&\s])printenv(?:\s|$)|(?:^|[;|&]\s*)env\s*(?:$|[;|&])|\/proc\/[^\s]+\/environ\b/.test(text)) {
      return {block: true, blockReason: 'Credential access blocked. Use the configured Section 11 tools; they load credentials privately. Never inspect or paste credential files.'};
    }
  } catch {
    return {block: true, blockReason: UNAVAILABLE};
  }
}

export function protectResult(result, files) {
  try { return redact(result, loadSecrets(files)); }
  catch { return {content: [{type: 'text', text: UNAVAILABLE}], isError: true}; }
}

export function protectMessage(message, files) {
  try { return redact(message, loadSecrets(files)); }
  catch {
    return {role: message.role, toolCallId: message.toolCallId, toolName: message.toolName,
      timestamp: message.timestamp, content: [{type: 'text', text: UNAVAILABLE}], isError: true};
  }
}
