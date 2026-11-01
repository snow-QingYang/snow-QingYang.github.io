"use strict";
const $=selector=>document.querySelector(selector);
const video=$("#video"),timeline=$("#timeline");
const esc=value=>String(value ?? "").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const pretty=value=>esc(JSON.stringify(value,null,2));
const sec=value=>`${Number(value).toFixed(1)} s`;
const clock=value=>`${String(Math.floor(value/60)).padStart(2,"0")}:${String(Math.floor(value%60)).padStart(2,"0")}`;
let current,filter="all",expanded=false,active=null,pendingTime=0,pendingPlay=false;

function stepOf(item){return current.trace.find(step=>step.index===item.ref);}
function planOf(item){return current.plans.find(plan=>plan.index===item.ref);}
function kindOf(item){return item.type!=="step"?item.type:["vla","pick"].includes(stepOf(item).command.op)?"vla":"manual";}
function methodOf(item){return item.type==="step"?stepOf(item).command.op:item.type==="plan"?planOf(item).kind:"result.success";}
function titleOf(item){return item.type==="step"?`步骤 #${item.ref} · ${methodOf(item)}`:item.type==="plan"?`计划 #${item.ref} · ${methodOf(item)}`:"最终环境结果";}
function timeOf(item){return item.type==="step"?stepOf(item).start:item.type==="plan"?planOf(item).time:current.elapsed_s;}
function scrollToCard(card){timeline.scrollTop+=card.getBoundingClientRect().top-timeline.getBoundingClientRect().top-12;}
function images(files,label){return files.length?`<div class="images panorama">${files.map(src=>`<a href="${src}" target="_blank" rel="noopener"><img src="${src}" alt="${esc(label)}" loading="lazy"></a>`).join("")}</div>`:"";}

function bodyOf(item){
  let outcome,args,result,extra="",photos=[];
  if(item.type==="step"){
    const step=stepOf(item);
    outcome=`程序步骤 #${step.index} · 耗时 ${sec(step.duration)} · 子步骤 ok=${step.summary.ok}<br>${step.plan_index?`来自计划 #${step.plan_index}`:"固定的首次整任务 VLA"}${!item.media.length?" · 本段没有连续录像":""}`;
    args=step.command;
    result={...step.summary};delete result.step;
    extra=step.attempt_events.map(attempt=>{
      const media=item.media.find(m=>m.attempt===attempt.index);
      return `<details class="attempt-detail"><summary>Attempt ${attempt.index+1} · ${esc(attempt.result.status)} · ${attempt.result.chunks} chunks</summary>${media?`<button class="jump" data-seek="${media.videoStart}">▶ 播放这次 attempt · ${sec(media.videoStart)}</button><a class="original" href="${media.src}" target="_blank" rel="noopener">原始视频 ↗</a>`:""}<pre>${pretty(attempt.result)}</pre></details>`;
    }).join("");
    if(step.alerts.length)extra+=`<div class="detail-heading">异常事件</div><pre>${pretty(step.alerts)}</pre>`;
    photos=item.media.map(m=>m.snapshot).filter(Boolean);
  }else if(item.type==="plan"){
    const plan=planOf(item),executed=current.trace.filter(step=>step.plan_index===item.ref);
    outcome=`Planner ${plan.kind} 输出 · ${plan.program.steps.length} 个计划步骤 / ${executed.length} 个实际执行${plan.program.unrecoverable?"<br><b>unrecoverable=true</b>":""}`;
    args={after_step:plan.after_step,replan_trigger:plan.trigger};
    result=plan.program;
    extra=plan.program.steps.length?`<div class="detail-heading">计划中的步骤是否执行</div><ol class="planned-steps">${plan.program.steps.map((step,index)=>`<li><code>${esc(step.op)}</code> · ${index<executed.length?`已执行为步骤 #${executed[index].index}`:"未执行"}</li>`).join("")}</ol>`:"";
    photos=item.media.map(m=>m.src);
  }else{
    outcome=`环境 success=${current.success} · ${current.stop}`;
    args={task:current.task,seed:current.seed};
    result={success:current.success,termination_reason:current.stop,elapsed_s:current.elapsed_s,llm_calls:current.llm_calls,steps_executed:current.steps_executed,final_progress:current.final_progress};
    photos=item.media.map(m=>m.src);
  }
  const isVideo=item.media.some(m=>m.type==="video");
  return `<div class="outcome">${outcome}</div><div class="detail-heading">回放注释</div><div class="intent">${esc(item.note)}</div><button class="jump" data-seek="${item.videoStart}">▶ ${isVideo?"播放":"查看说明画面"} ${item.videoStart.toFixed(1)}–${item.videoEnd.toFixed(1)}s</button><div class="detail-heading">${item.type==="plan"?"规划所处步骤 / 重规划触发反馈":"输入参数"}</div><pre>${pretty(args)}</pre><div class="detail-heading">${item.type==="plan"?"Planner 输出的完整程序":"返回结果"}</div><pre>${pretty(result)}</pre>${extra}${photos.length?`<div class="detail-heading">${item.type==="plan"?"本次 Planner 调用前的观测":item.type==="result"?"最终观测图":"各 attempt 结束后的观测（抬手 / 撤离前）"}</div>${images(photos,titleOf(item)+" 的相机观测")}<p class="note">从左到右为 agentview_left、agentview_right、wrist。图片是静态观测。</p>`:""}`;
}

function render(){
  const query=$("#search").value.toLowerCase().trim();
  const items=current.items.filter(item=>(filter==="all"||kindOf(item)===filter)&&`${methodOf(item)} ${titleOf(item)} ${item.note} ${JSON.stringify(item.type==="step"?stepOf(item).command:item.type==="plan"?planOf(item).program:{})}`.toLowerCase().includes(query));
  $("#count").textContent=`${items.length} / ${current.items.length} 条`;
  timeline.innerHTML=items.map(item=>`<details class="call ${active===item.id?"active":""}" data-id="${item.id}" ${expanded?"open":""}><summary><span class="num">${String(current.items.indexOf(item)+1).padStart(2,"0")}</span><span class="call-main"><span class="method">${esc(methodOf(item))}</span><span class="kind ${kindOf(item)}">${{plan:"规划",manual:"显式控制",vla:"VLA",result:"结果"}[kindOf(item)]}</span><span class="call-label">${titleOf(item)}${item.type==="step"&&!item.media.length?" · 无连续录像":""}</span></span><span class="call-time">+${timeOf(item).toFixed(1)}s</span><span class="chevron">›</span></summary><div class="detail-content">${bodyOf(item)}</div></details>`).join("")||'<p class="empty">没有匹配的记录</p>';
}

function setFilterButtons(){document.querySelectorAll("[data-filter]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.filter===filter)));}

function update(t=video.currentTime){
  if(!current)return;
  const segment=current.replay.segments.find(s=>t>=s.start&&t<s.end)||current.replay.segments[current.replay.segments.length-1];
  const item=current.items.find(i=>i.id===segment.item),ended=video.ended||t>=current.replay.duration-.02;
  $("#phase-label").textContent=ended?`回放结束 · 环境${current.success?"成功":"未成功"} · ${current.stop}`:`${titleOf(item)} · ${segment.type==="video"?`VLA 录像 / attempt ${segment.attempt+1}`:item.type==="step"?"无连续录像 · 日志说明画面":"静态观测 · 4 秒说明画面"}`;
  const changed=active!==item.id;active=item.id;
  timeline.querySelectorAll(".call").forEach(card=>{
    const on=card.dataset.id===active;card.classList.toggle("active",on);
    if(on&&changed&&!video.paused)scrollToCard(card);
  });
  document.querySelectorAll(".chapters button").forEach(button=>button.classList.toggle("active",t>=Number(button.dataset.start)&&t<Number(button.dataset.end)));
}

function seek(t,play=true,open=true,writeUrl=true){
  if(!current)return;
  t=Math.max(0,Math.min(Number(t)||0,current.replay.duration-.05));
  pendingTime=t;pendingPlay=play;
  if(video.readyState>=1){
    video.currentTime=t;
    if(play)video.play().catch(()=>{});else video.pause();
    pendingPlay=false;
  }
  update(t);
  let card=timeline.querySelector(`[data-id="${active}"]`);
  if(!card){filter="all";$("#search").value="";setFilterButtons();render();card=timeline.querySelector(`[data-id="${active}"]`);}
  if(card&&open){card.open=true;scrollToCard(card);}
  if(writeUrl){const url=new URL(location.href);url.hash=`t=${t.toFixed(2)}`;history.replaceState(null,"",url);}
}

function loadHash(){
  if(!current)return;
  const hash=new URLSearchParams(location.hash.slice(1));
  if(hash.has("t")){const t=Number(hash.get("t"));if(Number.isFinite(t))seek(t,false,true,false);return;}
  const item=current.items.find(i=>i.id===hash.get("event"));
  if(item){const media=item.media[Number(hash.get("attempt"))||0];seek(media?.videoStart??item.videoStart,false,true,false);}
}

fetch("data.json?v=unified-1").then(response=>{if(!response.ok)throw Error(`HTTP ${response.status}`);return response.json();}).then(data=>{
  current=data.cases.find(c=>c.key===new URLSearchParams(location.search).get("case"))||data.cases[0];
  document.title=`GetToastedBread seed ${current.seed} · ${current.success?"成功":"失败"}回放 · Mobile Astra`;
  $("#title").textContent=`GetToastedBread · seed ${current.seed}`;
  $("#outcome").className=`badge ${current.success?"success":"failure"}`;
  $("#outcome").textContent=`环境${current.success?"成功":"未成功"} · ${current.stop}`;
  $("#page-kind").textContent=`Baiyajing · ${current.success?"成功":"失败"}案例回放`;
  $("#compare").href=`?case=${current.success?"failure":"success"}`;
  $("#compare").textContent=`对照：seed ${current.success?"3 失败":"5 成功"}回放 →`;
  $("#subtitle").textContent=`GPT-6-Sol / medium · Composite seen · ${current.llm_calls} 次 Planner 调用 · ${current.steps_executed} 个程序步骤 · ${current.actual_vla_attempts} 次 VLA attempts`;
  $("#task").textContent=`任务：启动烤面包机，待手柄弹起后，把面包送到餐桌上的盘子。${current.headline}。`;
  $("#coverage").textContent=`统一回放 ${sec(current.replay.duration)}：原始 VLA 录像 ${sec(current.media_summary.duration)}，另插入规划观测、未录像步骤和最终结果的说明画面，每张固定 4 秒。carry / put_down 及准备动作没有连续录像。说明画面的时长不代表真实耗时；完整 episode ${sec(current.elapsed_s)}。`;
  $("#end-label").textContent=`${clock(current.replay.duration)} · ${current.success?"成功":"未成功"}`;
  $("#download-video").href=current.replay.src;
  $("#case-explanation").textContent=current.explanation;
  $("#lessons").innerHTML=current.lessons.map(note=>`<li>${esc(note)}</li>`).join("");
  $("#analysis-title").textContent=current.success?"规划与恢复过程":"哪里失败了";
  $("#analysis-link").href=`../baiyajing-analysis/#case=${encodeURIComponent(current.id)}`;
  $("#criteria-body").innerHTML=Object.entries(current.final_progress).map(([key,value])=>`<tr><td><code>${esc(key)}</code></td><td>${esc(value)}</td><td>局部任务状态</td></tr>`).join("")+`<tr><td><strong>success</strong></td><td class="${current.success?"good":"bad"}"><strong>${current.success}</strong></td><td>完整环境判定</td></tr>`;
  $("#source").textContent=`数据来源：baiyajing_composite_8gpu_20261022 / GetToastedBread_s${current.seed} · ${current.replay.frames} 帧整理回放 · 原始素材和执行记录的 SHA-256 保存在 JSON 中`;
  const firstPlan=current.items.find(item=>item.type==="plan");
  $("#takeover").textContent=`▶ 从 ${clock(firstPlan.videoStart)} 看 Planner 介入`;
  $("#takeover").dataset.seek=firstPlan.videoStart;
  const milestones=[current.items.find(item=>item.id==="plan-2"),current.items.find(item=>item.type==="step"&&stepOf(item).command.op==="carry"),current.items[current.items.length-1]];
  $("#milestones").innerHTML=milestones.map(item=>`<button data-seek="${item.videoStart}">${item.type==="plan"?"重规划":item.type==="result"?"最终结果":"搬运步骤"} · ${clock(item.videoStart)}</button>`).join("");
  $("#chapters").innerHTML=current.items.map(item=>`<button class="${kindOf(item)}" title="${titleOf(item)}" aria-label="跳转：${titleOf(item)}" style="flex:${item.videoEnd-item.videoStart}" data-start="${item.videoStart}" data-end="${item.videoEnd}" data-seek="${item.videoStart}"></button>`).join("");
  render();
  $("#loading").hidden=true;$("#report").hidden=false;
  video.src=current.replay.src;video.load();
  update(0);loadHash();
}).catch(error=>{$("#loading").className="error";$("#loading").textContent=`回放加载失败：${error.message}。请刷新重试。`;});

video.addEventListener("loadedmetadata",()=>{
  video.currentTime=pendingTime;video.playbackRate=Number($("#speed").value);
  if(pendingPlay)video.play().catch(()=>{});
  pendingPlay=false;update();
});
video.addEventListener("timeupdate",()=>update());video.addEventListener("seeked",()=>update());video.addEventListener("ended",()=>update());
video.addEventListener("error",()=>{$("#playback-error").textContent="视频加载失败，请刷新或通过“下载完整回放”打开视频。";});
$("#speed").addEventListener("change",()=>video.playbackRate=Number($("#speed").value));
$("#search").addEventListener("input",()=>current&&render());
document.querySelectorAll("[data-filter]").forEach(button=>button.addEventListener("click",()=>{filter=button.dataset.filter;setFilterButtons();if(current)render();}));
$("#expand").addEventListener("click",()=>{expanded=!expanded;$("#expand").textContent=expanded?"全部收起":"全部展开";if(current)render();});
document.addEventListener("click",event=>{const button=event.target.closest("[data-seek]");if(button)seek(button.dataset.seek);});
$("#copy-link").addEventListener("click",async()=>{
  const url=new URL(location.href);url.searchParams.set("case",current.key);url.hash=`t=${video.currentTime.toFixed(2)}`;history.replaceState(null,"",url);
  try{await navigator.clipboard.writeText(url.href);$("#copy-link").textContent="已复制";}catch{$("#copy-link").textContent="当前链接在地址栏";}
});
window.addEventListener("hashchange",loadHash);
