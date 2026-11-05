// Real SDK registration/catalog placement; no provider calls, private data or writes.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
export async function verifyDirectTools(packageRoot){
 const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
 const scratch=fs.mkdtempSync(path.join(os.tmpdir(),'s11-direct-tool-'));
 try{
  fs.symlinkSync(path.dirname(packageRoot),path.join(scratch,'node_modules'),'dir');
  const tools=[];
  for(const name of ['context-tool','coaching-tool']){
   fs.cpSync(path.join(root,'examples/agentic/openclaw',name),path.join(scratch,name),{recursive:true});
   const entry=(await import(pathToFileURL(path.join(scratch,name,'index.mjs')).href)).default;
   entry.register({registerTool:tool=>tools.push(tool),on(){},pluginConfig:{},logger:{info(){},warn(){}}});
  }
  assert.equal(tools.length,2);for(const t of tools)assert.equal(t.catalogMode,'direct-only');
  const dist=path.join(packageRoot,'dist');
  const mod=await import(pathToFileURL(path.join(dist,fs.readdirSync(dist).find(n=>/^tool-search-.*\.mjs$/.test(n)))).href);
  const fn=name=>Object.values(mod).find(v=>typeof v==='function'&&v.name===name);
  const catalogRef=fn('createToolSearchCatalogRef')();
  const result=fn('applyToolSearchCatalog')({tools:[...tools,{name:'tool_search',parameters:{type:'object',properties:{}},execute(){}}],
   catalogRef,config:{tools:{toolSearch:true}}});
  for(const t of tools){assert(result.tools.some(x=>x.name===t.name));assert(!catalogRef.current.entries.some(x=>x.name===t.name));}
  return {direct_tools:tools.map(t=>t.name),schema_discovery_required:false,native_catalog_verified:true,model_calls:0,calendar_writes:0};
 }finally{fs.rmSync(scratch,{recursive:true,force:true});}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))
 console.log(JSON.stringify(await verifyDirectTools(process.argv[2]??process.env.SECTION11_OPENCLAW_PACKAGE)));
