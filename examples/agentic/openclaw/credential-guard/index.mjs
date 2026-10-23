import {definePluginEntry, buildJsonPluginConfigSchema} from 'openclaw/plugin-sdk/plugin-entry';
import manifest from './openclaw.plugin.json' with {type: 'json'};
import {registerGuard} from './register.mjs';

export default definePluginEntry({
  id: 'section11-credential-guard',
  name: 'Section 11 credential guard',
  configSchema: () => buildJsonPluginConfigSchema(manifest.configSchema),
  register: registerGuard
});
