import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createJiti } from '/usr/lib/node_modules/pi/node_modules/jiti/lib/jiti.mjs';
const root = path.join(os.homedir(), '.config/zellij');
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'zellij-extension-'));
const fake = path.join(dir, 'zellij');
const callLog = path.join(dir, 'calls.jsonl');
let checks = 0;
const check = (value, expected) => { assert.deepEqual(value, expected); checks++; };
try {
  fs.writeFileSync(fake, `#!/usr/bin/env python3\nimport json,os,sys\nargs=sys.argv[1:]\nwith open(os.environ['TEST_CALL_LOG'],'a') as f:f.write(json.dumps(args)+'\\n')\nif 'list-sessions' in args: print('fixture [Created 1s ago]')\nelif 'list-tabs' in args: print(json.dumps([{'tab_id':0,'position':0,'name':'1:shell','active':True}]))\nelif 'list-panes' in args: print(json.dumps([{'id':0,'tab_id':0,'tab_position':0,'tab_name':'project','title':'shell','pane_cwd':'/tmp'}]))\nelif 'run' in args: print('terminal_0')\nelif 'new-tab' in args: print('0')\n`);
  fs.chmodSync(fake, 0o755);
  Object.assign(process.env, {
    ZELLIJ: '0', ZELLIJ_SESSION_NAME: 'fixture', ZELLIJ_PANE_ID: '0',
    ZELLIJ_TRIAL_BINARY: fake, ZELLIJ_TRIAL_STATE: path.join(dir, 'state'),
    PI_ZELLIJ_NOTIFY: '0', TEST_CALL_LOG: callLog, ZELLIJ_WS_NO_SAVE: '1',
  });
  // Use the installed package's resolver rather than assuming its file layout.
  const { createRequire } = await import('node:module');
  const require = createRequire('/usr/lib/node_modules/pi/package.json');
  const load = createJiti(import.meta.url, { alias: { typebox: require.resolve('typebox') } });
  const factory = await load.import(path.join(root, 'pi/zellij.ts'), { default: true });
  const handlers = {}, commands = {}, tools = {};
  const warnings = [];
  const api = {
    on: (name, fn) => { handlers[name] = fn; },
    registerCommand: (name, spec) => { commands[name] = spec; },
    registerTool: spec => { tools[spec.name] = spec; },
    getSessionName: () => 'agent task',
  };
  factory(api);
  check(Object.keys(commands).sort(), ['zattention', 'zfleet', 'zh', 'znote', 'zpi', 'ztool', 'zv']);
  check(Object.keys(tools), ['zellij_workspace']);
  let idle = true;
  const ctx = { cwd: '/tmp', isIdle: () => idle, ui: { notify: (text, level) => { if (level === 'warning' || level === 'error') warnings.push(text); } } };
  const state = () => {
    const dir = path.join(process.env.ZELLIJ_TRIAL_STATE, 'panes');
    const files = fs.readdirSync(dir).filter(n => n.endsWith('.json'));
    return JSON.parse(fs.readFileSync(path.join(dir, files[0]), 'utf8')).terminal_0;
  };
  const emit = async (name, event = {}) => handlers[name](event, ctx);
  let branch = [{type:'message', message:{role:'user',content:'resumed prompt'}}];
  ctx.sessionManager = {getSessionFile: () => '/tmp/exact-session.jsonl', getBranch: () => branch};
  await emit('session_start'); check(state().state, 'idle');
  check(state().last_prompt, 'resumed prompt');
  check(state().session_file, '/tmp/exact-session.jsonl');
  await emit('message_end', {message:{role:'user',content:[{type:'image',data:'PRIVATE IMAGE'}, {type:'text',text:'latest\n user prompt\u001b'}]}});
  check(state().last_prompt, 'latest user prompt');
  check(typeof state().updated, 'number');
  await emit('message_end', {message:{role:'assistant',content:[{type:'text',text:'SECRET TRANSCRIPT'}]}});
  check(state().last_prompt, 'latest user prompt');
  await emit('message_end', {message:{role:'user',content:'a'.repeat(400)}});
  check(state().last_prompt.length, 240);
  branch = []; await emit('session_switch'); check(state().last_prompt, '');
  branch = [{type:'message',message:{role:'user',content:'branch prompt'}}];
  await emit('session_tree'); check(state().last_prompt, 'branch prompt');
  await emit('agent_start'); check(state().state, 'working');
  await emit('ui_prompt_start'); check(state().state, 'asking');
  idle = false; await emit('ui_prompt_end'); check(state().state, 'working');
  await emit('agent_end', { messages: [{ role: 'assistant', stopReason: 'error', errorMessage: 'SECRET TRANSCRIPT' }] });
  check(state().state, 'working'); // agent_end is not final.
  idle = true; await emit('agent_settled'); check(state().state, 'error');
  await commands.znote.handler('--literal note', ctx); check(state().note, '--literal note');
  await commands.znote.handler('manual note', ctx); check(state().note, 'manual note');
  await emit('session_info_changed', { name: 'renamed agent' });
  check(state().label, 'renamed agent'); check(state().note, 'manual note');
  await emit('agent_start');
  await emit('agent_end', { messages: [{ role: 'assistant', stopReason: 'stop', content: [{type:'text',text:'SECRET TRANSCRIPT'}] }] });
  idle = false; await emit('agent_settled'); check(state().state, 'working');
  idle = true; await emit('agent_settled'); check(state().state, 'done');
  await emit('agent_start'); await emit('agent_end', { messages: [{role:'assistant',stopReason:'aborted'}] });
  await emit('agent_settled'); check(state().state, 'idle');
  const tool = tools.zellij_workspace;
  const listed = await tool.execute('1', {action:'list'}, undefined, undefined, ctx);
  check(JSON.parse(listed.content[0].text)[0].note, 'manual note');
  await tool.execute('1', {action:'open',command:['echo','literal; no eval'],note:'new task'}, undefined, undefined, ctx);
  check(state().note, 'new task');
  await commands.zv.handler('optional initial prompt', ctx);
  await commands.zh.handler('', ctx);
  await commands.zpi.handler('', ctx);
  await commands.ztool.handler('printf hello', ctx);
  await assert.rejects(() => tool.execute('1', {action:'focus',pane:'plugin_0'}, undefined, undefined, ctx)); checks++;
  await assert.rejects(() => tool.execute('1', {action:'open'}, undefined, undefined, ctx)); checks++;
  check(JSON.stringify(state()).includes('SECRET TRANSCRIPT'), false);
  await emit('session_shutdown'); check(state().state, undefined); check(state().note, 'new task');
  // Exercise the installed SDK getter, not just a hand-written path mock.
  const { SessionManager } = await import('/usr/lib/node_modules/pi/packages/coding-agent/dist/core/session-manager.js');
  const sdk = SessionManager.create(dir, path.join(dir, 'sdk-sessions'));
  ctx.sessionManager = {getSessionFile: () => sdk.getSessionFile(), getBranch: () => []};
  await emit('session_start'); check(state().session_file, sdk.getSessionFile());
  const sdkToken = state().token;
  await emit('session_shutdown');
  check(state().session_file, sdk.getSessionFile()); check(state().owner, undefined);
  const record = JSON.parse(fs.readFileSync(path.join(process.env.ZELLIJ_TRIAL_STATE, 'agents', sdkToken + '.json'), 'utf8'));
  check(record.session_file, sdk.getSessionFile());
  const originalSdkFile = sdk.getSessionFile();
  process.env.ZELLIJ_RESTORE_TOKEN = sdkToken;
  await emit('session_start'); check(state().token, sdkToken);
  await emit('session_shutdown');
  sdk.newSession();
  await emit('session_start'); check(state().session_file, sdk.getSessionFile());
  check(state().token === sdkToken, false);
  check(JSON.parse(fs.readFileSync(path.join(process.env.ZELLIJ_TRIAL_STATE, 'agents', sdkToken + '.json'), 'utf8')).session_file, originalSdkFile);
  await emit('session_shutdown');
  const ephemeral = SessionManager.inMemory(dir);
  ctx.sessionManager = {getSessionFile: () => ephemeral.getSessionFile(), getBranch: () => []};
  await emit('session_start'); check(state().session_file, undefined);
  await emit('session_shutdown');
  check(warnings, []);
  const calls = fs.readFileSync(callLog,'utf8').trim().split('\n').map(JSON.parse);
  check(calls.some(c => c.includes('literal; no eval') && !c.includes('-c')), true);
  console.log(`${checks} extension checks passed; events/tools/commands exercised without model calls or real panes`);
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
