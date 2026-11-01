"use strict";
const video=document.querySelector('#video'), timeline=document.querySelector('#timeline');
let data, filter='all', expanded=false, active=-1;
const escapeHTML=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty=x=>escapeHTML(JSON.stringify(x,null,2));
function render(){
  const query=document.querySelector('#search').value.toLowerCase();
  const calls=data.calls.filter(c=>(filter==='all'||c.kind===filter)&&(c.method+' '+c.label+' '+c.intent).toLowerCase().includes(query));
  document.querySelector('#count').textContent=`${calls.length} / ${data.calls.length} calls`;
  timeline.innerHTML=calls.map(c=>`<details class="call ${active===c.index?'active':''}" data-index="${c.index}" ${expanded?'open':''}><summary><span class="num">${String(c.index).padStart(2,'0')}</span><span class="call-main"><span class="method">${escapeHTML(c.method)}</span>${c.kind==='manual'?'<span class="kind manual">解析</span>':c.kind==='vla'?'<span class="kind">VLA</span>':''}<span class="call-label">${escapeHTML(c.label)}</span></span><span class="call-time">+${c.start.toFixed(1)}s</span><span class="chevron">›</span></summary><div class="detail-content"><div class="outcome">工具调用已返回 · 耗时 ${c.duration.toFixed(3)} 秒${c.step?` · 环境动作 #${c.step}<br><b>任务 success = false</b>`:''}${c.kind==='vla'?`<br>${c.outcome.chunks} chunks · ${c.outcome.steps_applied} 仿真步 · status=${escapeHTML(c.outcome.status)}`:''}${c.method==='finish'?'<br><b>finish(status=stuck) · 任务未成功</b>':''}</div>${c.intent?`<div class="detail-heading">Agent 当时的公开执行说明</div><div class="intent">${escapeHTML(c.intent)}</div>`:''}${c.videoEnd>c.videoStart?`<button class="jump" data-seek="${c.videoStart}">▶ 播放 ${c.videoStart.toFixed(2)}–${c.videoEnd.toFixed(2)}s 片段</button>`:''}<div class="detail-heading">输入参数</div><pre>${pretty(c.arguments)}</pre><div class="detail-heading">返回结果</div><pre>${pretty(c.results.length===1?c.results[0]:c.results)}</pre>${c.images.length?`<div class="images">${c.images.map((im,j)=>`<a href="${im}" target="_blank" rel="noopener"><img loading="lazy" src="${im}" alt="调用 ${c.index} 返回的相机画面 ${j+1}"></a>`).join('')}</div>`:''}</div></details>`).join('')||'<p class="empty">没有匹配的调用</p>';
}
function seek(t){
  if(!data)return;
  video.currentTime=t; video.play().catch(()=>{}); update();
  const segment=data.segments.find(s=>t>=s.start&&t<s.end);
  if(!segment)return;
  let card=timeline.querySelector(`[data-index="${segment.index}"]`);
  if(!card){filter='all';document.querySelector('#search').value='';setFilterButtons();render();card=timeline.querySelector(`[data-index="${segment.index}"]`);}
  if(card){card.open=true;scrollToCard(card);}
}
function scrollToCard(card){timeline.scrollTop+=card.getBoundingClientRect().top-timeline.getBoundingClientRect().top-12;}
function update(){
  if(!data)return;
  const t=video.currentTime;
  const segment=data.segments.find(s=>t>=s.start&&t<s.end)||data.segments[data.segments.length-1];
  const ended=video.ended||t>=data.duration-.02;
  document.querySelector('#phase-label').textContent=ended?'回放结束 · 任务未成功 · finish=stuck':`动作 #${segment.step} · ${segment.label}`;
  const next=ended?data.calls[data.calls.length-1].index:segment.index;
  const changed=active!==next;active=next;
  timeline.querySelectorAll('.call').forEach(el=>{const on=Number(el.dataset.index)===active;el.classList.toggle('active',on);if(on&&changed&&!video.paused)scrollToCard(el);});
  document.querySelectorAll('.chapters button').forEach(b=>b.classList.toggle('active',t>=Number(b.dataset.start)&&t<Number(b.dataset.end)));
}
function setFilterButtons(){document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===filter)));}
fetch('replay.json').then(r=>{if(!r.ok)throw Error('执行记录加载失败');return r.json();}).then(d=>{
  data=d;render();
  document.querySelector('#chapters').innerHTML=d.chapters.map(c=>`<button class="${c.kind}" title="${escapeHTML(c.label)}" aria-label="跳转：${escapeHTML(c.label)}" style="flex:${c.end-c.start}" data-start="${c.start}" data-end="${c.end}" data-seek="${c.start}"></button>`).join('');
  update();
}).catch(e=>{timeline.innerHTML='<p class="error">'+escapeHTML(e.message)+'</p>';});
document.addEventListener('click',event=>{const b=event.target.closest('[data-seek]');if(b)seek(Number(b.dataset.seek));});
video.addEventListener('timeupdate',update);video.addEventListener('ended',update);
document.querySelector('#speed').addEventListener('change',e=>video.playbackRate=Number(e.target.value));
document.querySelector('#search').addEventListener('input',()=>data&&render());
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;setFilterButtons();if(data)render();}));
document.querySelector('#expand').addEventListener('click',e=>{expanded=!expanded;e.target.textContent=expanded?'全部收起':'全部展开';if(data)render();});
