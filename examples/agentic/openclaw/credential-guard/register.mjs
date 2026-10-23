import {beforeTool, protectMessage, protectResult} from './policy.mjs';

export function registerGuard(api) {
  const files = api.pluginConfig?.credentialFiles;
  api.on('before_tool_call', event => beforeTool(event, files));
  api.registerAgentToolResultMiddleware(event => ({result: protectResult(event.result, files)}));
  api.on('tool_result_persist', event => ({message: protectMessage(event.message, files)}));
  api.on('before_message_write', event => ({message: protectMessage(event.message, files)}));
  api.on('message_sending', event => {
    const result = protectResult({content: event.content}, files);
    return typeof result.content === 'string' ? {content: result.content} : {cancel: true};
  });
}
