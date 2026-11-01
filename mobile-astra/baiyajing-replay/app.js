"use strict";

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const json = value => esc(JSON.stringify(value,null,2));
const seconds = value => `${Number(value).toFixed(1)} s`;
const policy = step => ["vla","pick"].includes(step.command.op);
let data, current, position=0, attemptIndex=0, filter="all", mediaVersion=0;
const expanded = new Set();

function stepOf(item) { return current.trace.find(step=>step.index===item.ref); }
function planOf(item) { return current.plans.find(plan=>plan.index===item.ref); }
function kindOf(item) { return item.type!=="step"?item.type:policy(stepOf(item))?"vla":"control"; }
function itemLabel(item) {
  if(item.type==="plan") return `计划 #${item.ref} · ${planOf(item).kind}`;
  if(item.type==="result") return "最终环境判定与画面";
  const step=stepOf(item);
  return `步骤 #${step.index} · ${step.command.op}`;
}
function stamp(item) {
  if(item.type==="plan") return `+${seconds(planOf(item).time)}`;
  if(item.type==="result") return `+${seconds(current.elapsed_s)}`;
  const step=stepOf(item);
  return `+${step.start.toFixed(1)}–${step.end.toFixed(1)} s`;
}

function updateUrl(push=false) {
  const url=new URL(location.href);
  url.searchParams.set("case",current.key);
  url.hash=new URLSearchParams({event:current.items[position].id,attempt:String(attemptIndex)}).toString();
  history[push?"pushState":"replaceState"](null,"",url);
}

function selectCase(key, eventId="step-1", mediaIndex=0, push=false) {
  current=data.cases.find(c=>c.key===key) || data.cases[0];
  filter="all";
  expanded.clear();
  document.querySelectorAll("[data-case]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.case===current.key)));
  $("#title").textContent=`GetToastedBread · seed ${current.seed}`;
  document.title=`Baiyajing · seed ${current.seed} ${current.success?"成功":"失败"}回放 · Mobile Astra`;
  $("#outcome").className=`badge ${current.key}`;
  $("#outcome").textContent=`环境${current.success?"成功":"未成功"} · ${current.stop}`;
  $("#subtitle").textContent=`GPT-6-Sol / medium · Seen · ${current.llm_calls} 次 Planner · ${current.steps_executed} 个程序步骤 · 完整 episode ${seconds(current.elapsed_s)}`;
  $("#task").textContent=`任务：启动烤面包机，待手柄弹起后，把面包送到餐桌上的盘子。${current.headline}。`;
  $("#case-explanation").textContent=current.explanation;
  $("#lessons").innerHTML=current.lessons.map(note=>`<li>${esc(note)}</li>`).join("");
  $("#analysis-link").href=`../baiyajing-analysis/#case=${encodeURIComponent(current.id)}`;
  $("#coverage").textContent=`全部 ${current.media_summary.clips} 段 VLA 录像，共 ${seconds(current.media_summary.duration)}。10 FPS，左侧 agentview / 右侧腕部相机；步骤 ${current.media_summary.unrecorded_steps.map(n=>"#"+n).join("、")} 没有连续录像。录像时长不包含 Planner 等待与执行器动作。`;
  $("#record-count").textContent=`${current.llm_calls} 份计划输出 · ${current.steps_executed} 个实际步骤 · ${current.media_summary.clips} 段 VLA 视频 · 1 份最终结果`;
  position=Math.max(0,current.items.findIndex(item=>item.id===eventId));
  selectItem(position,mediaIndex,false,false);
  updateUrl(push);
}

function selectItem(index, mediaIndex=0, play=false, writeUrl=true) {
  position=Math.max(0,Math.min(index,current.items.length-1));
  const item=current.items[position];
  attemptIndex=Math.max(0,Math.min(mediaIndex,Math.max(0,item.media.length-1)));
  expanded.add(item.id);
  $("#current-title").textContent=itemLabel(item);
  $("#current-note").textContent=item.note;
  const facts=[];
  if(item.type==="step") {
    const step=stepOf(item);
    facts.push(`子步骤 ok=${step.summary.ok}`,step.plan_index?`来自计划 #${step.plan_index}`:"固定的首次整任务 VLA",`${seconds(step.duration)} 墙钟耗时`);
    for(const [name,value] of Object.entries(step.changes)) facts.push(`${name}: ${value.before} → ${value.after}`);
    if(step.summary.result) for(const name of ["still_grasped","released","final_dist","obj_height"]) {
      if(name in step.summary.result) facts.push(`${name}=${step.summary.result[name]}`);
    }
  } else if(item.type==="plan") {
    const plan=planOf(item), executed=current.trace.filter(step=>step.plan_index===plan.index).length;
    facts.push(`${plan.program.steps.length} 个计划步骤`,`${executed} 个实际执行`);
    if(plan.program.unrecoverable) facts.push("unrecoverable=true");
  } else facts.push(`result.success=${current.success}`,`termination_reason=${current.stop}`);
  $("#current-facts").innerHTML=`<div class="current-facts">${facts.map(fact=>`<span class="fact">${esc(fact)}</span>`).join("")}</div>`;
  $("#position").textContent=`记录 ${position+1} / ${current.items.length}`;
  $("#prev").disabled=position===0;
  $("#next").disabled=position===current.items.length-1;
  $("#copy-link").textContent="复制当前记录链接";
  renderTimeline();
  renderMedia(play);
  if(writeUrl) updateUrl();
}

function renderMedia(play=false) {
  const item=current.items[position], media=item.media[attemptIndex], video=$("#video");
  const version=++mediaVersion;
  video.pause();
  video.removeAttribute("src");
  video.load();
  video.hidden=true;
  $("#observation").hidden=true;
  $("#gap").hidden=true;
  $("#media-link").hidden=!media;
  $("#playback-status").textContent="";
  $("#media-title").textContent=itemLabel(item);
  $("#attempt-buttons").innerHTML=item.media.filter(m=>m.type==="video").map((m,index)=>`<button data-attempt="${index}" aria-pressed="${index===attemptIndex}">Attempt ${m.attempt+1} · ${esc(m.status)} · ${seconds(m.duration)}</button>`).join("");
  if(media?.type==="video") {
    video.hidden=false;
    video.src=media.src;
    video.playbackRate=Number($("#speed").value);
    $("#media-type").textContent=`原始视频 · attempt ${media.attempt+1}`;
    $("#media-caption").textContent=`左：agentview_left；右：wrist。${media.chunks} chunks / ${media.frames} 帧 / ${seconds(media.duration)}。attempt 状态 ${media.status}，不是整局成功标签。`;
    if(play) video.play().catch(error=>{
      if(version===mediaVersion && error.name!=="AbortError") $("#playback-status").textContent="请点击视频播放按钮继续。";
    });
  } else if(media?.type==="image") {
    const image=$("#observation");
    image.src=media.src;
    image.alt=media.purpose==="planner"?`计划 #${item.ref} 的输入观测图`:`seed ${current.seed} 最终环境图像`;
    image.hidden=false;
    $("#media-type").textContent=media.purpose==="planner"?"Planner 输入观测 · 静态图":"最终观测 · 静态图";
    $("#media-caption").textContent=`从左到右：agentview_left / agentview_right / wrist。${media.purpose==="planner"?"该图在本次 Planner 调用前拍摄；右侧为随后输出的程序。":"该图在整局结束时拍摄；完整任务结果来自环境 check_success()。"}这是一张静态观测图。`;
  } else {
    $("#gap").hidden=false;
    $("#gap-text").textContent=`${stepOf(item).command.op} 是 Planner 安排的执行器步骤，原始记录未保存该段视频。`;
    $("#media-type").textContent="执行日志 · 无连续录像";
    $("#media-caption").textContent="这一步仅有执行日志。具体结果见下方解读与右侧记录，后续观测可通过“下一条”查看。";
  }
  if(media) $("#media-link").href=media.src;
}

function recordBody(item) {
  if(item.type==="plan") {
    const plan=planOf(item), executed=current.trace.filter(step=>step.plan_index===plan.index);
    return `<p class="step-note">${esc(item.note)}</p><h3>计划步骤及执行情况</h3>${plan.program.steps.length?`<ol class="plan-steps">${plan.program.steps.map((step,index)=>`<li class="${index<executed.length?"executed":"unexecuted"}"><code>${esc(step.op)}</code> · ${index<executed.length?`已执行为步骤 #${executed[index].index}`:"未执行"}</li>`).join("")}</ol>`:'<p>steps=[]，没有后续动作。</p>'}${plan.trigger?`<details class="raw"><summary>触发重规划的执行反馈</summary><pre>${esc(plan.trigger)}</pre></details>`:""}<details class="raw"><summary>Planner 实际输出的完整程序 JSON</summary><pre>${json(plan.program)}</pre></details><p class="note">仅展示程序字段；右上时间是计划输出被记录的时刻。左侧图片是本次调用前的观测。</p><button class="record-action" data-view="${item.id}">查看规划输入图像</button>`;
  }
  if(item.type==="result") return `<p class="step-note">${esc(item.note)}</p><h3>最终环境结果</h3><pre>${json({success:current.success,termination_reason:current.stop,elapsed_s:current.elapsed_s,llm_calls:current.llm_calls,steps_executed:current.steps_executed})}</pre><h3>最终局部任务判据</h3><pre>${json(current.final_progress)}</pre><p class="note">这份 progress 不包含完整成功判据；两例的上述字段相同，环境 success 不同。</p><button class="record-action" data-view="result">查看最终画面</button>`;
  const step=stepOf(item), result={...step.summary};
  delete result.step;
  delete result.progress_after;
  return `<p class="step-note">${esc(item.note)}</p><details class="raw"><summary>实际执行参数 JSON</summary><pre>${json(step.command)}</pre></details>${step.attempt_events.map(attempt=>{
    const media=item.media.find(m=>m.attempt===attempt.index), mediaIndex=item.media.indexOf(media);
    return `<details class="attempt-result"><summary>Attempt ${attempt.index+1} · ${esc(attempt.result.status)} · ${attempt.result.chunks} chunks</summary>${media?`<button class="record-action" data-view="${item.id}" data-video="${mediaIndex}">播放这次 attempt</button>`:""}<pre>${json(attempt.result)}</pre>${media?.snapshot?`<a href="${media.snapshot}" target="_blank" rel="noopener"><img src="${media.snapshot}" alt="Attempt ${attempt.index+1} 的结束观测（抬手或撤离前）" loading="lazy"></a><p class="note">本图拍摄于 VLA 段结束后、抬手 / 撤离之前。三个视角依次为 left / right / wrist。</p>`:""}</details>`;
  }).join("")}<details class="raw"><summary>步骤结果 JSON · ok 不等于整局 success</summary><pre>${json(result)}</pre></details>${step.alerts.length?`<h3>本步异常事件</h3><pre>${json(step.alerts)}</pre>`:""}<details class="raw"><summary>步骤后的局部任务判据</summary><pre>${json(step.summary.progress_after)}</pre></details>${Object.keys(step.changes).length?`<details class="raw"><summary>相对上一步的判据变化</summary><pre>${json(step.changes)}</pre></details>`:""}<button class="record-action" data-view="${item.id}">${item.media.length?"查看本步视频":"查看未录像步骤说明"}</button>`;
}

function renderTimeline() {
  document.querySelectorAll("[data-filter]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.filter===filter)));
  const items=current.items.filter(item=>filter==="all" || kindOf(item)===filter);
  $("#timeline").innerHTML=items.map(item=>{
    const selected=item.id===current.items[position].id, kind=kindOf(item);
    const description=item.type==="plan"?`${planOf(item).program.steps.length} 个计划步骤 · 点击看输入图像与程序`:item.type==="result"?`success=${current.success} · ${current.stop}`:`${stepOf(item).origin==="initial"?"首次整任务":`计划 #${stepOf(item).plan_index}`} · 子步骤 ok=${stepOf(item).summary.ok} · ${item.media.length?`${item.media.length} 段视频`:"无连续录像"}`;
    return `<details class="record ${selected?"active":""}" id="record-${item.id}" data-record="${item.id}" ${expanded.has(item.id)?"open":""}><summary data-select="${item.id}"><div class="record-main"><div class="record-label">${itemLabel(item)}<span class="kind ${kind}">${{plan:"规划",vla:"VLA",control:"显式控制",result:"结果"}[kind]}</span></div><div class="record-info">${description}</div></div><span class="record-time">${stamp(item)}</span></summary><div class="record-body">${recordBody(item)}</div></details>`;
  }).join("") || '<p class="empty">没有匹配的记录。</p>';
  $("#expand").textContent=items.every(item=>expanded.has(item.id))?"收起全部":"展开全部";
  document.querySelectorAll(".record").forEach(element=>element.addEventListener("toggle",()=>{
    if(element.open) expanded.add(element.dataset.record); else expanded.delete(element.dataset.record);
  }));
}

function jump(id) {
  filter="all";
  selectItem(current.items.findIndex(item=>item.id===id));
  const record=$(`#record-${id}`);
  if(record) $("#timeline").scrollTop=record.offsetTop-$("#timeline").offsetTop-8;
}

document.addEventListener("click",event=>{
  if(!data) return;
  const button=event.target.closest("[data-case],[data-filter],[data-attempt],[data-view],summary[data-select]");
  if(!button) return;
  if(button.dataset.case) return selectCase(button.dataset.case,"step-1",0,true);
  if(button.dataset.filter) {filter=button.dataset.filter;renderTimeline();return;}
  if(button.dataset.attempt) {selectItem(position,Number(button.dataset.attempt));return;}
  const id=button.dataset.view || button.dataset.select;
  if(id) {
    event.preventDefault();
    const same=current.items[position].id===id;
    if(button.dataset.select && same) {
      const record=$(`#record-${id}`);record.open=!record.open;
      return;
    }
    selectItem(current.items.findIndex(item=>item.id===id),Number(button.dataset.video || 0));
  }
});

$("#video").addEventListener("ended",()=>{
  const item=current?.items[position];
  if(!item || item.media[attemptIndex]?.type!=="video" || !$("#auto-next").checked) return;
  if(attemptIndex+1<item.media.length) selectItem(position,attemptIndex+1,true);
  else if(position+1<current.items.length) selectItem(position+1,0,true);
});
$("#video").addEventListener("error",()=>{
  if(!$("#video").hidden && $("#video").hasAttribute("src")) $("#playback-status").textContent="视频加载失败，请使用“打开原始素材”或刷新重试。";
});
$("#observation").addEventListener("error",()=>{
  if(!$("#observation").hidden) $("#playback-status").textContent="观测图加载失败，请刷新重试。";
});
$("#speed").addEventListener("change",()=>$("#video").playbackRate=Number($("#speed").value));
$("#prev").addEventListener("click",()=>{if(current) selectItem(position-1);});
$("#next").addEventListener("click",()=>{if(current) selectItem(position+1);});
$("#jump-planner").addEventListener("click",()=>{if(current) jump("plan-1");});
$("#jump-control").addEventListener("click",()=>{if(current) jump(`step-${current.trace.find(step=>step.command.op==="carry").index}`);});
$("#jump-result").addEventListener("click",()=>{if(current) jump("result");});
$("#expand").addEventListener("click",()=>{
  const records=[...document.querySelectorAll(".record")], open=records.some(record=>!record.open);
  records.forEach(record=>{record.open=open;if(open) expanded.add(record.dataset.record);else expanded.delete(record.dataset.record);});
  $("#expand").textContent=open?"收起全部":"展开全部";
});
$("#copy-link").addEventListener("click",async()=>{
  try {await navigator.clipboard.writeText(location.href);$("#copy-link").textContent="已复制";}
  catch {$("#copy-link").textContent="当前链接在地址栏";}
});
function readUrl() {
  if(!data) return;
  const query=new URLSearchParams(location.search), hash=new URLSearchParams(location.hash.slice(1));
  const index=Number(hash.get("attempt"));
  selectCase(query.get("case"),hash.get("event") || "step-1",Number.isInteger(index)?index:0);
}
window.addEventListener("popstate",readUrl);
window.addEventListener("hashchange",readUrl);
(async()=>{
  try {
    const response=await fetch("data.json");
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    data=await response.json();
    readUrl();
    $("#loading").hidden=true;
    $("#report").hidden=false;
  } catch(error) {
    $("#loading").className="error";
    $("#loading").textContent=`回放加载失败：${error.message}。请刷新重试。`;
  }
})();
