"use strict";

const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const json = (value) => esc(JSON.stringify(value, null, 2));
const pct = (value, total) => `${(100 * value / total).toFixed(1)}%`;
const seconds = (value) => value == null ? "—" : `${Number(value).toFixed(1)} s`;
const labels = {initial:"初始整任务 VLA", planned:"修复 · vla/pick 程序", mixed:"修复 · 含显式控制", failure:"未成功"};
const letters = {initial:"V", planned:"P", mixed:"M", failure:"–"};
const origins = {initial:"固定的首次整任务执行", planner:"Planner 程序", fallback:"执行器自动 fallback"};
const isVla = (step) => ["vla", "pick"].includes(step.command.op);
const badge = (category) => `<span class="badge ${category}">${labels[category]}</span>`;
const pageSize = 20;
let data, episodeMap, page = 0, selectedId = null;
const detailCache = new Map();

const examples = [
  {id:"ScrubCuttingBoard--1", title:"首次整任务 VLA 完成刷洗", text:"只有一个固定的完整任务步骤，没有调用 Planner。58 个 chunks（464 控制步）后出现 env_success；最终接触计时为 6，横向刷洗范围为 0.2408，夹爪也已撤离。"},
  {id:"LoadDishwasher--1", title:"餐具已经放好，Planner 只要求关门", text:"初始 VLA 执行 120 个 chunks 后 idle，两件餐具的放置判据已成立，但门没有关闭。Planner 输出 Close the dishwasher door.；第二个程序步骤仅执行 13 个 chunks，就完成了整项任务。"},
  {id:"GetToastedBread--5", title:"VLA 操作烤面包机，再显式搬运放下", text:"初次 VLA 未压下手柄。修复阶段先用 VLA 操作手柄，再通过 pick 抓取吐司；重新规划抓取后，carry 把吐司带到餐桌上的盘子旁，put_down 放下。最终共 6 个程序步骤、2 次 Planner 调用。"},
  {id:"MakeIceLemonade--2", title:"多次重规划，把柠檬和冰分别放进杯子", text:"初始整任务 VLA 在 240 个 chunks 后 progress_stall。修复中经历靠近失败、动作预算用尽和底盘漂移，Planner 随后分别安排取柠檬、入杯、加冰。第 8 步用 51 个 chunks 完成任务；程序只有 vla，但包含 4 次 Planner 调用。"},
  {id:"PanTransfer--1", title:"不允许碰食物的判据已触发，自动重试仍失败", text:"初始 VLA 后 _robot_touched_food=true，食物未到盘子、锅也未回炉灶。Planner 多次返回空 steps，执行器随后自动生成了 6 个整任务 fallback。最后盘子落地、Planner 标记 unrecoverable，整局以 object_on_floor 结束。"},
  {id:"ScrubCuttingBoard--2", title:"局部接触不等于刷洗完成，最终超时", text:"初始 VLA 用完 250 个 chunks，接触计时为 2、刷洗范围仅 0.0953。经过重规划和反复操作，结束时接触计时为 3，刷洗范围仍为 0.0953，任务未成功；共 16 步、9 次 Planner 调用，最终耗尽 3600 秒预算。"},
];

function table(headers, rows) {
  return `<table class="summary-table"><thead><tr>${headers.map(cell=>`<th>${cell}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(cell=>`<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function renderOverview() {
  const s = data.summary;
  $("#success-table").innerHTML = table(["结果来源", "Seen", "Unseen", "Overall"], [
    ["本地运行", s.by_split.seen, s.by_split.unseen, s],
    ["仓库报告", data.reference.seen, data.reference.unseen, data.reference.overall],
  ].map(([name,...counts])=>[`<span class="row-label">${name}</span>`, ...counts.map(c=>`<span class="rate">${pct(c.success,c.total)}</span><small>${c.success}/${c.total}</small>`)]));
  $("#stage-table").innerHTML = table(["执行阶段", "成功 / 进入此阶段"], [
    ["初次完整任务 VLA", `<button class="number-button" data-category="initial">28 / 160</button><small>17.5%</small>`],
    ["初次未完成后 Planner 修复", `<button class="number-button" data-category="repair">33 / 132</button><small>25.0%</small>`],
    ["其中：vla/pick 程序", `<button class="number-button" data-category="planned">20</button>`],
    ["其中：含显式控制", `<button class="number-button" data-category="mixed">13</button>`],
  ]);
  const stopLabels = {env_success:"完整任务成功", idle:"动作静止 / 无有效变化", progress_stall:"判据进展停滞", budget:"该次 chunk 预算用尽", object_fell:"检测到物体丢失"};
  $("#initial-stops").innerHTML = table(["首次 attempt 状态", "含义", "数量"], ["env_success","idle","progress_stall","budget","object_fell"].map(key=>[`<code>${key}</code>`,stopLabels[key],s.initial_statuses[key]]));
  $("#split-stages").innerHTML = table(["路径", "Seen", "Unseen"], ["initial","planned","mixed","failure"].map(category=>[
    badge(category), ...["seen","unseen"].map(split=>`<button class="number-button" data-category="${category}" data-split="${split}">${s.by_split[split].categories[category]}</button>`),
  ]));
  const methods = {vla:"执行文本子任务",pick:"由 VLA 抓取",carry:"持物导航",put_down:"降至支撑面后松手",retract:"撤离手臂",release:"降低手臂后松手",goto:"导航到目标"};
  $("#methods-table").innerHTML = table(["op", "执行器用途", "步骤 / 涉及 episode"], Object.entries(methods).map(([op,description])=>[
    `<button class="text-button" data-method="${op}"><code>${op}</code></button>`,description,`${s.methods[op]} / ${data.episodes.filter(e=>e.methods[op]).length}`,
  ]));
  $("#time-table").innerHTML = table(["路径", "中位数", "样本数"], ["initial","planned","mixed","failure"].map(category=>[badge(category),seconds(s.median_elapsed[category]),s.categories[category]]));
  $("#example-grid").innerHTML = examples.map(ex=>{
    const e = episodeMap.get(ex.id);
    return `<article class="example"><div class="example-head"><span>${e.split === "seen"?"Seen":"Unseen"}</span>${badge(e.category)}</div><h3>${ex.title}</h3><div class="mini-stats">${e.task} · seed ${e.seed}<br>${e.llm_calls} 次 Planner · ${e.steps_executed} 个程序步骤 · ${seconds(e.elapsed_s)}</div><p>${ex.text}</p><div class="example-foot"><button class="text-button" data-case="${e.id}">查看程序与执行证据 →</button></div></article>`;
  }).join("");
  $("#generated").textContent = `统计生成于 ${new Date(data.generated_utc).toLocaleString("zh-CN",{timeZone:"Asia/Hong_Kong",hour12:false})} UTC+8`;
}

function renderMatrix() {
  $("#matrix").innerHTML = ["seen","unseen"].map(split=>{
    const s = data.summary.by_split[split];
    return `<div><div class="matrix-title">${split === "seen"?"Seen":"Unseen"}<span>${s.success}/${s.total} · ${pct(s.success,s.total)}</span></div>${data.tasks[split].map(task=>`<div class="task-row"><span class="task-name">${task}</span><div class="seed-group">${[1,2,3,4,5].map(seed=>{
      const e = episodeMap.get(`${task}--${seed}`);
      const title = `${task} · seed ${seed}：${labels[e.category]}；Planner ${e.llm_calls} 次，程序 ${e.steps_executed} 步；${e.stop}`;
      return `<button class="seed ${e.category}" data-case="${e.id}" aria-label="${esc(title)}" title="${esc(title)}">${letters[e.category]}</button>`;
    }).join("")}</div></div>`).join("")}</div>`;
  }).join("");
}

function filteredEpisodes() {
  const search = $("#search").value.toLowerCase().trim();
  const split = $("#filter-split").value, category = $("#filter-category").value, stop = $("#filter-stop").value;
  return data.episodes.filter(e=>{
    if(split !== "all" && e.split !== split) return false;
    if(stop !== "all" && e.stop !== stop) return false;
    if(category === "success" && !e.success) return false;
    if(category === "repair" && !["planned","mixed"].includes(e.category)) return false;
    if(!["all","success","repair"].includes(category) && e.category !== category) return false;
    return `${e.task} ${e.seed} ${Object.keys(e.methods).join(" ")}`.toLowerCase().includes(search);
  });
}

function renderCases() {
  const items = filteredEpisodes();
  page = Math.min(page, Math.max(0, Math.ceil(items.length / pageSize)-1));
  $("#case-count").textContent = `${items.length} / 160`;
  $("#cases-body").innerHTML = items.slice(page * pageSize,(page+1) * pageSize).map(e=>`<tr><td><button class="text-button" data-case="${e.id}">${e.task} · s${e.seed}</button><small>${e.split === "seen"?"Seen":"Unseen"}</small></td><td>${badge(e.category)}${e.success?"":`<small>${e.stop}</small>`}</td><td>${e.llm_calls}</td><td>${e.steps_executed}${e.fallback_steps?`<small>含 ${e.fallback_steps} 步 fallback</small>`:""}</td><td>${e.actual_vla_attempts}</td><td>${seconds(e.elapsed_s)}</td><td><button class="text-button" data-case="${e.id}">详情 →</button></td></tr>`).join("") || '<tr><td colspan="7" class="empty">没有匹配的案例，试试调整筛选条件。</td></tr>';
  $("#page-label").textContent = items.length ? `第 ${page*pageSize+1}–${Math.min((page+1)*pageSize,items.length)} 条，共 ${items.length} 条` : "0 条";
  $("#prev-page").disabled = page===0;
  $("#next-page").disabled = (page+1)*pageSize>=items.length;
}

function setFilters(values={}) {
  $("#search").value = values.search || "";
  for(const key of ["split","category","stop"]) $(`#filter-${key}`).value = values[key] || (key === "category"?"success":"all");
  page = 0;
  renderCases();
}

function attribution(e) {
  if(e.category === "initial") return `首次固定的完整任务 VLA 在 ${e.initial_chunks} 个 chunks 后报告 env_success，整个 episode 只有 1 个程序步骤，Planner 调用为 0。执行器的准备动作和状态检查仍存在。`;
  if(e.success) return `首次完整任务 VLA 以 ${esc(e.initial_status)} 结束，未完成任务。随后调用 Planner ${e.llm_calls} 次，最终环境判成功。${e.category === "planned"?"实际执行的程序仅使用 vla/pick，子任务内容与执行条件由 Planner 指定；其内部仍有自动准备动作。":`实际执行过 ${e.explicit_steps} 个显式非 VLA 程序步骤，其余 ${e.vla_program_steps} 步为 vla/pick。`}最后一个程序步骤为 ${esc(e.last_op)}；本分类表示执行路径，不证明某一步是成功的必要原因。`;
  return `最终环境 success=false，终止标签为 ${esc(e.stop)}。首次 VLA 以 ${esc(e.initial_status)} 结束；之后共调用 Planner ${e.llm_calls} 次。${e.fallback_steps?`执行器自动生成并执行了 ${e.fallback_steps} 个 fallback 步骤，这些不能当作 Planner 写出的程序。`:"实际执行的后续步骤来自 Planner 程序。"}步骤 ok 或 attempt done 只说明局部检查通过，不能作为整局成功。`;
}

function showCase(id) {
  if(!episodeMap.has(id)) return;
  const hash = `#case=${encodeURIComponent(id)}`;
  if(location.hash === hash) loadCase(id);
  else location.hash = hash;
}

async function loadCase(id) {
  if(!episodeMap.has(id)) return;
  selectedId = id;
  $("#copy-link").textContent = "复制链接";
  $("#case-detail").innerHTML = '<p role="status" id="detail-title">正在加载程序与执行证据…</p>';
  const dialog = $("#case-dialog");
  if(!dialog.open) dialog.showModal();
  document.body.style.overflow = "hidden";
  dialog.scrollTop = 0;
  try {
    if(!detailCache.has(id)) {
      const response = await fetch(`cases/${encodeURIComponent(id)}.json`);
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      detailCache.set(id,await response.json());
    }
    if(selectedId !== id) return;
    const d = detailCache.get(id), e = episodeMap.get(id), ex = examples.find(item=>item.id===id);
    $("#case-detail").innerHTML = `
      <div class="detail-heading"><h2 id="detail-title">${e.task} · seed ${e.seed}</h2>${badge(e.category)}</div>
      <div class="detail-subtitle">Baiyajing · GPT-6-Sol / medium · ${e.split === "seen"?"Seen":"Unseen"} · 环境 success=${e.success} · ${e.stop}</div>
      <div class="task-instruction">${esc(e.task_language)}</div>
      <div class="detail-stats"><div><b>${e.llm_calls}</b><span>Planner 调用</span></div><div><b>${e.steps_executed}</b><span>已执行程序步骤</span></div><div><b>${e.actual_vla_attempts}</b><span>实际 VLA attempts</span></div><div><b>${seconds(e.elapsed_s)}</b><span>episode 墙钟耗时</span></div></div>
      <div class="evidence"><p><strong>归类依据：</strong>${attribution(e)}</p>${ex?`<p><strong>案例解读：</strong>${ex.text}</p>`:""}<p class="note">累计 ${e.vla_chunks.toLocaleString()} 个 VLA chunks = ${e.vla_env_steps.toLocaleString()} 个 VLA 控制步；不包含导航、调整手臂等执行器控制步。</p></div>
      <div class="detail-links"><a href="cases/${encodeURIComponent(id)}.json" download>下载本例完整证据 JSON</a></div>
      ${d.alerts.length?`<details class="alert-box"><summary>物体丢失 / 执行异常事件 · ${d.alerts.length} 条</summary><pre>${json(d.alerts)}</pre></details>`:""}
      <section class="programs"><h3>Planner 输出的程序 <span class="subtle">${d.plans.length} 次调用</span></h3><p class="note">展示实际输出的 steps 和 unrecoverable 字段。计划中的步骤不保证全部执行；每张卡片列出它实际执行到的步骤。时间为本 episode 开始后的秒数。</p>${d.plans.map(plan=>{
        const executed = d.trace.filter(step=>step.plan_index===plan.index);
        return `<details class="program-card" id="plan-${plan.index}"><summary><strong>计划 #${plan.index}</strong> · ${plan.kind} · ${seconds(plan.time)} · 在步骤 #${plan.after_step} 后 · ${plan.program.steps?.length || 0} 个计划步骤</summary><p>已执行：${executed.length?executed.map(step=>`#${step.index} ${esc(step.command.op)}`).join("、"):"没有执行此计划中的步骤"}${plan.trigger?`<br>重规划触发记录：${esc(plan.trigger)}`:""}</p><pre>${json(plan.program)}</pre></details>`;
      }).join("") || '<p class="case-summary-note">没有调用 Planner。首次完整任务 VLA 已成功。</p>'}</section>
      <div class="trace-tools"><h3>实际执行步骤 <span class="subtle">${d.trace.length} 步</span></h3><label class="subtle" for="trace-filter">显示</label><select id="trace-filter"><option value="all">全部步骤</option><option value="vla">vla / pick 程序</option><option value="explicit">显式非 VLA 程序</option><option value="fallback">自动 fallback</option><option value="changes">判据变化 / 环境成功</option></select><button id="expand-trace">展开全部参数</button></div>
      <div class="trace-summary" aria-label="程序步骤顺序">${d.trace.map(step=>`<span class="trace-dot ${step.origin === "initial"?"initial":isVla(step)?"planned":"mixed"}" title="#${step.index} ${esc(step.command.op)} · ${origins[step.origin]}">${step.index}</span>`).join("")}</div>
      <p class="note"># 是程序步骤编号，不是仿真步。蓝色是初次整任务，绿色是后续 vla/pick，紫色是显式控制。标为 fallback 的步骤来自执行器。参数、attempt 返回、步骤结果与任务判据均可展开。</p>
      <p class="result-note">原始 attempt 的 checks 是当时保存的快照，env_success 可能先于 checks 更新，因此两者可能同时出现 env_success 和 checks['success']=false。整局以 result.json 的 success 为准。视频 / 图片文件名仅作为原始记录标识，本分析页不提供这些素材。</p>
      <div id="trace-list"></div>
      <details class="source-details"><summary>初末任务判据、计数与来源校验</summary><h4>初始任务判据</h4><pre>${json(d.initial_progress)}</pre><h4>最终任务判据</h4><pre>${json(d.final_progress)}</pre><h4>实际执行方法计数</h4><pre>${json(e.methods)}</pre><p>终止标签：${esc(e.stop)} · 环境 success=${e.success}<br>attempt 事件 ${e.attempt_events} 条，其中 ${e.actual_vla_attempts} 次 chunks &gt; 0；其余包括靠近失败、条件已满足或零 chunk 截止等记录。</p><h4>原始来源及 SHA-256</h4><pre>${json(d.source)}</pre></details>`;
    renderTrace();
    $("#trace-filter").addEventListener("change",renderTrace);
    $("#expand-trace").addEventListener("click",()=>{
      const items = [...document.querySelectorAll(".trace-step")], open = items.some(el=>!el.open);
      items.forEach(el=>el.open=open);
      $("#expand-trace").textContent = open?"收起全部参数":"展开全部参数";
    });
  } catch(error) {
    if(selectedId === id) $("#case-detail").innerHTML = `<div class="error" id="detail-title">证据加载失败：${esc(error.message)}。请刷新重试。</div>`;
  }
}

function renderTrace() {
  const d = detailCache.get(selectedId), filter = $("#trace-filter").value;
  const actions = d.trace.filter(step=> filter === "all" || (filter === "vla" && isVla(step)) || (filter === "explicit" && !isVla(step)) || (filter === "fallback" && step.origin === "fallback") || (filter === "changes" && (Object.keys(step.changes).length || step.env_success_observed || (d.success && step.index === d.trace.length))));
  $("#expand-trace").textContent = "展开全部参数";
  $("#trace-list").innerHTML = actions.map(step=>{
    const finalSuccess = d.success && step.index === d.trace.length;
    const observed = step.env_success_observed;
    const result = {...step.summary};
    delete result.step;
    delete result.progress_after;
    const changes = Object.entries(step.changes).map(([key,value])=>`${key}: ${JSON.stringify(value.before)} → ${JSON.stringify(value.after)}`).join(" · ");
    return `<details class="trace-step ${observed || finalSuccess?"step-success":""}" data-step="${step.index}"><summary><span class="step-number">#${step.index}</span><code>${esc(step.command.op)}</code><span class="origin-tag">${step.origin === "planner"?`计划 #${step.plan_index}`:origins[step.origin]}</span>${observed?'<span class="badge planned">env_success</span>':finalSuccess?'<span class="badge planned">最终环境成功</span>':`<span class="origin-tag">子步骤 ok=${step.summary.ok}</span>`}<small>${seconds(step.duration)}</small></summary><div class="step-body"><p class="note">开始 ${seconds(step.start)} → 结束 ${seconds(step.end)} · 原始事件 #${step.event_start}–${step.event_end}${step.plan_index?` · <button class="text-button" data-plan="${step.plan_index}">查看计划 #${step.plan_index}</button>`:""}</p><h4>实际执行参数</h4><pre>${json(step.command)}</pre><h4>该步骤的 attempt 事件 · ${step.attempt_events.length} 条</h4>${step.attempt_events.map(attempt=>`<div class="attempt"><h4>Attempt ${attempt.index+1} · ${esc(attempt.result.status)} · ${attempt.result.chunks || 0} chunks</h4><p>记录时间 ${seconds(attempt.time)}${attempt.result.chunks?` · ${attempt.result.chunks*8} 个 VLA 控制步`:" · 未执行 VLA chunk"}</p><pre>${json(attempt.result)}</pre></div>`).join("") || '<p class="case-summary-note">没有 attempt 事件；查看下方步骤结果。条件已满足而跳过的执行可能只记录在 summary.attempts。</p>'}<h4>步骤结果（原始 step_end.summary，参数和 progress 单独列出）</h4><pre>${json(result)}</pre><h4>步骤结束后的任务判据</h4><pre>${json(step.summary.progress_after)}</pre>${finalSuccess?'<p class="case-summary-note"><strong>这是最后一个程序步骤；该 episode 的最终环境 success=true。</strong>执行器内部也可能进行放手 / 撤离；不据此推断某个底层动作的独立贡献。</p>':""}</div>${changes?`<div class="step-change">${esc(changes)}</div>`:""}</details>`;
  }).join("") || '<p class="empty">这个筛选下没有步骤记录。</p>';
}

function onHash() {
  if(!episodeMap) return;
  const id = new URLSearchParams(location.hash.slice(1)).get("case");
  if(id && episodeMap.has(id)) loadCase(id);
  else if($("#case-dialog").open) $("#case-dialog").close();
}

document.addEventListener("click",event=>{
  const target = event.target.closest("button[data-case],button[data-category],button[data-stop],button[data-method],button[data-plan]");
  if(!target || !data) return;
  if(target.dataset.case) return showCase(target.dataset.case);
  if(target.dataset.plan) {
    const plan = $(`#plan-${target.dataset.plan}`);
    if(plan) { plan.open = true; plan.scrollIntoView({block:"center",behavior:"smooth"}); }
    return;
  }
  if(target.dataset.category) setFilters({category:target.dataset.category,split:target.dataset.split});
  if(target.dataset.stop) setFilters({category:"failure",stop:target.dataset.stop});
  if(target.dataset.method) setFilters({category:"all",search:target.dataset.method});
  $("#case-browser").scrollIntoView({behavior:"smooth",block:"start"});
});

$("#close-dialog").addEventListener("click",()=>$("#case-dialog").close());
$("#case-dialog").addEventListener("close",()=>{
  selectedId = null;
  document.body.style.overflow = "";
  if(location.hash.startsWith("#case=")) history.replaceState(null,"",location.pathname+location.search);
});
$("#copy-link").addEventListener("click",async()=>{
  try { await navigator.clipboard.writeText(location.href); $("#copy-link").textContent = "已复制"; }
  catch { $("#copy-link").textContent = "链接在地址栏"; }
});
$("#print").addEventListener("click",()=>window.print());
$("#prev-page").addEventListener("click",()=>{page--;renderCases();});
$("#next-page").addEventListener("click",()=>{page++;renderCases();});
$("#reset-filters").addEventListener("click",()=>setFilters());
$("#search").addEventListener("input",()=>{if(data) {page=0;renderCases();}});
for(const key of ["split","category","stop"]) $(`#filter-${key}`).addEventListener("change",()=>{if(data) {page=0;renderCases();}});
window.addEventListener("hashchange",onHash);

(async()=>{
  try {
    const response = await fetch("data.json");
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
    episodeMap = new Map(data.episodes.map(e=>[e.id,e]));
    renderOverview(); renderMatrix(); renderCases();
    $("#loading").hidden = true;
    $("#report").hidden = false;
    onHash();
  } catch(error) {
    $("#loading").className = "error";
    $("#loading").textContent = `报告加载失败：${error.message}。请刷新，或下载上方的 CSV / Markdown 查看。`;
  }
})();
