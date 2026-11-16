// 所有接口内容以文本节点显示，密钥不进入网页存储或下载文件。
const $ = s => document.querySelector(s);
const form=$('#diagnose-form'), symptom=$('#symptom'), content=$('#result-content');
const submit=$('#submit'), status=$('#result-status'), trace=$('#trace');
let cases=[], lastPayload=null, running=false;
const labels={congestion:'拥塞迹象',path_change:'路径变化',rate_drop:'链路速率下降',device:'设备异常',wifi:'无线侧异常',insufficient:'证据不足',normal:'未见支持所述故障的证据'};
const states={supported:'得到支持',weakened:'受到削弱',uncertain:'仍不确定'};
async function api(path, options){const r=await fetch(path,options);const data=await r.json();if(!r.ok)throw Error(data.error||'服务请求失败');return data;}
const post=(path,data)=>api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function block(title,values){const b=el('section',undefined,'result-block');b.append(el('h3',title));if(Array.isArray(values)){const list=el('ul');values.forEach(x=>list.append(el('li',x)));b.append(list);}else b.append(el('p',values));return b;}
symptom.addEventListener('input',()=>$('#count').textContent=symptom.value.length);
function selectCase(id){if(running)return;const c=cases.find(x=>x.id===id);if(!c)return;$('#case-select').value=id;symptom.value=c.symptom;$('#count').textContent=symptom.value.length;document.querySelectorAll('.case').forEach(n=>n.classList.toggle('active',n.dataset.id===id));drawTopology(c);}
function drawTopology(c){
  const box=$('#topology');box.replaceChildren(el('p',`${c.id} · 模拟拓扑示意（不表示实时状态；是否经过汇聚B需查询路径）`));
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 520 190');svg.setAttribute('role','img');svg.setAttribute('aria-label','宿舍终端经接入交换机和汇聚到校园出口的模拟拓扑');
  const points=[[50,90],[170,90],[310,45],[310,140],[465,90]],edges=[[0,1,'接入'],[1,2,'L1'],[2,4,'L2'],[1,3,'L4'],[3,4,'L3']];
  edges.forEach(([a,b,name])=>{const l=document.createElementNS(ns,'line');['x1','y1','x2','y2'].forEach((k,i)=>l.setAttribute(k,[...points[a],...points[b]][i]));l.setAttribute('stroke','#526a5d');svg.append(l);const t=document.createElementNS(ns,'text');t.setAttribute('x',(points[a][0]+points[b][0])/2);t.setAttribute('y',(points[a][1]+points[b][1])/2-7);t.setAttribute('fill','#9baaa4');t.setAttribute('font-size','10');t.textContent=name;svg.append(t);});
  c.topology.nodes.forEach((name,i)=>{const circle=document.createElementNS(ns,'circle');circle.setAttribute('cx',points[i][0]);circle.setAttribute('cy',points[i][1]);circle.setAttribute('r','7');circle.setAttribute('fill','#c6ef72');svg.append(circle);const t=document.createElementNS(ns,'text');t.setAttribute('x',points[i][0]);t.setAttribute('y',points[i][1]+25);t.setAttribute('text-anchor','middle');t.setAttribute('fill','#eaf0e9');t.setAttribute('font-size','10');t.textContent=name;svg.append(t);});box.append(svg);
}
function renderTrace(events){trace.replaceChildren();events.forEach((e,i)=>{if(e.kind==='tool'){const d=el('details',undefined,'trace-item');d.append(el('summary',`${i+1}. ${e.message}`),el('pre',JSON.stringify({input:e.arguments,output:e.output},null,2)));trace.append(d);}else trace.append(el('div',`${i+1}. ${e.message}`,'trace-item'));});}
function renderResult(payload){
  lastPayload=payload;content.replaceChildren();
  if(payload.status!=='ok'){content.append(el('p',payload.error,'error'));status.textContent='未形成有效结论';return;}
  const r=payload.result;status.textContent='调查完成 · 请核验';
  content.append(block(labels[r.category]||r.category,r.summary));
  const hypotheses=block('候选假设与证据');r.hypotheses.forEach(h=>{const item=el('div',undefined,'hypothesis');item.append(el('strong',`${h.name} · ${states[h.status]}`),el('p',h.reason),el('p','支持：'+(h.supporting_evidence.join('、')||'尚无引用')+'；反对/限制：'+(h.opposing_evidence.join('、')||'尚无引用'),'evidence-link'));hypotheses.append(item);});content.append(hypotheses);
  content.append(block('行动建议',r.recommendations),block('限制与不确定性',r.limitations));
  if(payload.group==='A'){const raw=el('details',undefined,'trace-item');raw.append(el('summary','查看A组直接获得的原始数据（R编号，非工具调用）'),el('pre',JSON.stringify(payload.evidence,null,2)));content.append(raw);}
  content.append(el('p',`组别 ${payload.group} · ${payload.model} · ${payload.elapsed_seconds}秒 · ${payload.run_id}`,'run-meta'));
  content.append(el('p','原始CSV与工具记录已保存到 '+payload.output_dir,'run-meta'));
  const download=el('button','下载本次调查记录','download');download.type='button';download.onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(lastPayload,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download=payload.run_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};content.append(download);
  content.append(el('p','网络数据全部为人工模拟；工具调用真实执行。程序校验结构和证据编号，但不保证模型判断一定正确。','disclaimer'));
}
form.addEventListener('submit',async e=>{
  e.preventDefault();if(running)return;
  running=true;submit.disabled=true;$('#case-select').disabled=true;$('#group-select').disabled=true;status.textContent='调查中';submit.firstElementChild.textContent='正在调查…';lastPayload=null;content.replaceChildren(el('p','DeepSeek 正在选择工具。可在下方查看实时调用记录。','subtle'));trace.replaceChildren();
  const start=Date.now();const timer=setInterval(()=>$('#elapsed').textContent=`已等待 ${Math.floor((Date.now()-start)/1000)} 秒`,1000);
  try{const job=await post('/api/diagnose',{symptom:symptom.value.trim(),case_id:$('#case-select').value,group:$('#group-select').value});
    while(true){const state=await api('/api/jobs/'+job.job_id);renderTrace(state.events||[]);if(state.status==='done'){renderResult(state.payload);break;}if(state.status==='error')throw Error(state.error);await new Promise(r=>setTimeout(r,1500));}
  }catch(err){content.replaceChildren(el('p',err.message,'error'));status.textContent='调查未完成';}
  finally{clearInterval(timer);$('#elapsed').textContent=`本次 ${Math.floor((Date.now()-start)/1000)} 秒`;running=false;submit.disabled=false;$('#case-select').disabled=false;$('#group-select').disabled=false;submit.firstElementChild.textContent='生成调查建议';}
});
$('#case-select').onchange=e=>selectCase(e.target.value);
$('#key-form').onsubmit=async e=>{e.preventDefault();try{await post('/api/config',{api_key:$('#api-key').value.trim()});$('#api-key').value='';$('#config-message').textContent='已配置；密钥未写入文件。';await health();}catch(err){$('#config-message').textContent=err.message;}};
async function health(){try{const h=await api('/api/health');$('#connection').textContent='DeepSeek · '+h.model;$('#key-state').textContent=h.configured?'已配置':'待输入密钥';if(!h.configured)$('.model-config').open=true;}catch{$('#connection').textContent='服务未连接';}}
async function init(){try{const data=await api('/api/cases');cases=data.cases;$('#case-list').replaceChildren();cases.forEach(c=>{const option=el('option',c.id+' · '+c.symptom);option.value=c.id;$('#case-select').append(option);const button=el('button',undefined,'case');button.type='button';button.dataset.id=c.id;button.append(el('span',c.id+' / SIMULATED','case-number'),el('strong',c.title),el('p',c.symptom));button.onclick=()=>selectCase(c.id);$('#case-list').append(button);});selectCase(cases[0].id);}catch(err){$('#case-list').textContent=err.message;}await health();}
init();
