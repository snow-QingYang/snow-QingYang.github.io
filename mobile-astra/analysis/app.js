"use strict";

const $ = (s) => document.querySelector(s);
const escapeHTML = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pct = (n, d) => `${(100 * n / d).toFixed(1)}%`;
const seconds = (n) => n == null ? "—" : `${n.toFixed(1)} s`;
const shortModel = (id) => id === "astra" ? "6-Astra" : "5.6-Sol";
const letters = {vla:"V", setup:"S", repair:"R", failure:"–"};
const labels = {vla:"VLA 直接完成", setup:"准备后 VLA 完成", repair:"Planner 介入后成功", failure:"未成功"};
const badge = (c) => `<span class="badge ${c}">${labels[c]}</span>`;
let data, episodeMap, matrixModel = "astra", page = 0, selectedId = null;
const pageSize = 20;
const detailCache = new Map();

const examples = [
  {id:"astra--BreadSelection--4", title:"连续 3 次 VLA，自行完成选面包", text:"3 次 rldx_arm 共执行 824 个仿真步（320 + 320 + 184），第三次返回 success=true。这里的三段是调用预算切分，动作全由 VLA 执行。"},
  {id:"astra--LoadDishwasher--3", title:"先转动底盘，再交给 VLA", text:"动作 #1–2 是 move_base，用于扩大可见区域；#3–7 连续运行 rldx_skill。#5 两件餐具已放好，#7 门关闭并成功。这是准备类，不是 VLA 停滞后的修复。"},
  {id:"astra--PanTransfer--2", title:"VLA 后接管倾倒，并恢复滑落的锅", text:"#1–4 VLA 未完成倾倒；#5 起解析抓取和搬运，#16 旋转后 vegetable_on_plate=true。回程锅滑落，#28 再抓取，最终 #48 撤离后 success=true。", replay:true},
  {id:"astra--KettleBoiling--4", title:"VLA 搬好水壶，Planner 旋转炉灶旋钮", text:"#11 VLA 已使 kettle_on_site=true，但 burner_on 仍为 false。随后经历调整与 VLA 续跑；#35–37 定位、靠近并夹紧旋钮，#38–39 旋转后 burner_on=true，任务完成。"},
  {id:"sol--StackBowlsCabinet--3", title:"一次位姿调整后，再由 VLA 完成", text:"连续 11 次 VLA 尚未完成入柜；#12 move_to 调整末端位置，随后两次 rldx_skill。#14 两个 bowl_in_cabinet 判据与撤离判据成立。共 13 次 VLA、1 次解析动作。"},
  {id:"sol--PrepareCoffee--5", title:"修正杯子位置，再按启动键并撤离", text:"VLA 和解析抓放交替尝试；#29 杯子 contact_check=true，#35 move_to 后 coffee_machine__turned_on=true，但尚未成功。#36 撤离使 gripper_button_far=true，环境才判成功。"},
];

function table(headers, rows) {
  return `<table class="summary-table"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(cell=>`<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function renderOverview() {
  const models = Object.entries(data.models);
  const splits = ["seen", "unseen"].map(split=>({
    id: split,
    label: split === "seen" ? "Seen" : "Unseen",
    models: models.map(([id,m])=>{
      const episodes = data.episodes.filter(e=>e.model===id && e.split===split);
      const categories = Object.fromEntries(["vla","setup","repair","failure"].map(c=>[c,episodes.filter(e=>e.category===c).length]));
      return {id, name:m.name, episodes, categories, total:episodes.length, success:episodes.filter(e=>e.success).length};
    })
  }));
  $("#findings").innerHTML = splits.map(split=>{
    const astra = split.models.find(m=>m.id==="astra"), sol = split.models.find(m=>m.id==="sol");
    const difference = 100 * (astra.success/astra.total - sol.success/sol.total);
    return `<div class="finding"><b>${split.label} · Astra ${astra.success}/${astra.total} vs Sol ${sol.success}/${sol.total}</b><span>Astra ${pct(astra.success,astra.total)} · Sol ${pct(sol.success,sol.total)} · ${difference===0?"成功率相同":`Astra 高 ${difference.toFixed(1)} 个百分点`}</span></div>`;
  }).join("");
  $("#success-table").innerHTML = table(["模型", "Seen", "Unseen", "Overall"], models.map(([id,m])=>[
    `<span class="row-label">${shortModel(id)}</span><small>xhigh</small>`,
    ...[m.summary.by_split.seen,m.summary.by_split.unseen,m.summary].map(s=>`<span class="rate">${pct(s.success,s.total)}</span><small>${s.success}/${s.total}</small>`)
  ]));
  $("#stage-table").innerHTML = splits.map(split=>`<div class="split-summary"><h3>${split.label}<span>每模型 ${split.models[0].total} 局</span></h3>${table(["成功路径", "Astra", "Sol"], ["vla","setup","repair"].map(c=>[
    `<span class="badge ${c}">${labels[c]}</span>`, ...split.models.map(m=>`<button class="number-button" data-filter-model="${m.id}" data-filter-split="${split.id}" data-filter-category="${c}">${m.categories[c]}</button><small>${pct(m.categories[c],m.total)} / 本组运行</small>`)
  ]))}${split.models.map(m=>`<div class="bar-row"><span>${m.id === "astra" ? "Astra" : "Sol"}</span><div class="stacked-bar" role="group" aria-label="${m.name} · ${split.label} 的 ${m.total} 次运行构成">${["vla","setup","repair","failure"].map(c=>`<button class="${c}" type="button" data-filter-model="${m.id}" data-filter-split="${split.id}" data-filter-category="${c}" style="width:${100*m.categories[c]/m.total}%" aria-label="${m.name} · ${split.label} · ${labels[c]} ${m.categories[c]} 局" title="${split.label} · ${labels[c]} ${m.categories[c]}"></button>`).join("")}</div></div>`).join("")}</div>`).join("");
  $("#completion-table").innerHTML = splits.map(split=>`<div class="split-summary"><h3>${split.label}</h3>${table(["首次成功所在动作", "Astra", "Sol"], [["vla","VLA 完成最后一步"],["manual","解析动作完成最后一步"]].map(([actor,label])=>[
    label, ...split.models.map(m=>m.episodes.filter(e=>e.category==="repair" && e.completion_actor===actor).length)
  ]))}</div>`).join("");
  $("#paired").innerHTML = `<div class="paired-grid">${[["both","两者均成功"],["astra_only","仅 Astra 成功"],["sol_only","仅 Sol 成功"],["neither","两者均失败"]].map(([id,label])=>`<button data-filter-paired="${id}"><b>${data.paired[id]}</b>${label}</button>`).join("")}</div>`;
  $("#failure-table").innerHTML = table(["停止方式", "Astra", "Sol"], [
    ["主动结束 · finish=stuck", ...models.map(([,m])=>m.summary.stops.stuck)],
    ["无 finish · 达到 100 响应上限", ...models.map(([,m])=>m.summary.stops.turn_limit)],
    ["失败总数", ...models.map(([,m])=>`<strong>${m.summary.categories.failure}</strong>`)]
  ]);
  $("#time-table").innerHTML = table(["成功路径", "Astra", "Sol"], ["vla","setup","repair"].map(c=>[
    labels[c], ...models.map(([,m])=>`${seconds(m.summary.median_by_category[c])}<small>n=${m.summary.categories[c]||0}</small>`)
  ]));
  const methods = ["move_to","move_delta","navigate_to","move_base","scripted_grasp","set_gripper","rotate_pitch","release"];
  $("#method-table").innerHTML = table(["方法", "Astra", "Sol"], methods.map(method=>[
    `<button class="text-button" data-method-search="${method}"><code>${method}</code></button>`, ...models.map(([id])=>{
      const used = data.episodes.filter(e=>e.model===id && e.category==="repair" && e.manual_methods[method]);
      return `${used.length} / ${used.reduce((s,e)=>s+e.manual_methods[method],0)}`;
    })
  ]));
  $("#example-grid").innerHTML = examples.map(ex=>{
    const e = episodeMap.get(ex.id);
    return `<article class="example"><div class="example-head"><span>${data.models[e.model].name} · ${e.split === "seen" ? "Seen" : "Unseen"}</span>${badge(e.category)}</div><h3>${ex.title}</h3><div class="mini-stats">${e.task} · seed ${e.seed} · VLA ${e.vla_calls} / 解析 ${e.manual_calls} · ${seconds(e.elapsed_s)}</div><p>${ex.text}</p><div class="example-foot"><button class="text-button" data-case="${e.id}">查看动作证据 →</button>${ex.replay?'<a href="../pan-transfer/">视频与全部工具调用 →</a>':""}</div></article>`;
  }).join("");
  $("#generated").textContent = new Date(data.generated_utc).toLocaleString("zh-CN", {timeZone:"Asia/Hong_Kong",hour12:false}) + " UTC+8";
}

function renderMatrix() {
  document.querySelectorAll("[data-matrix-model]").forEach(b=>b.setAttribute("aria-pressed", String(b.dataset.matrixModel===matrixModel)));
  $("#matrix").innerHTML = ["seen","unseen"].map(split=>{
    const summary = data.models[matrixModel].summary.by_split[split];
    return `<div><div class="matrix-title">${split === "seen" ? "Seen" : "Unseen"}<span>${summary.success}/80 · ${pct(summary.success,80)}</span></div>${data.tasks[split].map(task=>`<div class="task-row"><span class="task-name">${task}</span><div class="seed-group">${[1,2,3,4,5].map(seed=>{
      const e = episodeMap.get(`${matrixModel}--${task}--${seed}`);
      const title = `${data.models[matrixModel].name} · ${task} · seed ${seed}：${labels[e.category]}；${e.vla_calls} VLA / ${e.manual_calls} 解析动作`;
      return `<button class="seed ${e.category}" data-case="${e.id}" aria-label="${title}" title="${title}">${letters[e.category]}</button>`;
    }).join("")}</div></div>`).join("")}</div>`;
  }).join("");
}

function filteredEpisodes() {
  const search = $("#search").value.toLowerCase().trim();
  const values = Object.fromEntries(["model","split","category","paired"].map(k=>[k,$(`#filter-${k}`).value]));
  return data.episodes.filter(e=>{
    if(values.model!=="all" && e.model!==values.model) return false;
    if(values.split!=="all" && e.split!==values.split) return false;
    if(values.category==="success" ? !e.success : values.category!=="all" && e.category!==values.category) return false;
    if(values.paired!=="all" && e.paired!==values.paired) return false;
    return `${e.task} ${e.seed} ${Object.keys(e.manual_methods).join(" ")} ${Object.keys(e.vla_methods).join(" ")}`.toLowerCase().includes(search);
  });
}

function renderCases() {
  const items = filteredEpisodes();
  page = Math.min(page, Math.max(0, Math.ceil(items.length/pageSize)-1));
  const slice = items.slice(page*pageSize,(page+1)*pageSize);
  $("#case-count").textContent = `${items.length} / 320`;
  $("#cases-body").innerHTML = slice.map(e=>`<tr><td><button class="text-button" data-case="${e.id}">${e.task} · s${e.seed}</button><small>${e.split === "seen" ? "Seen" : "Unseen"}</small></td><td>${shortModel(e.model)}</td><td>${badge(e.category)}${e.category==="failure"?`<small>${e.stop==="stuck"?"finish=stuck":"100 响应上限"}</small>`:""}</td><td>${e.vla_calls} / ${e.manual_calls}</td><td>${e.first_success_step ? `<code>#${e.first_success_step} ${e.last_method}</code>`:"—"}</td><td>${seconds(e.elapsed_s)}</td><td><button class="text-button" data-case="${e.id}">详情 →</button></td></tr>`).join("") || '<tr><td colspan="7" class="empty">没有匹配的案例，试试调整筛选条件。</td></tr>';
  $("#page-label").textContent = items.length ? `第 ${page*pageSize+1}–${Math.min((page+1)*pageSize,items.length)} 条，共 ${items.length} 条` : "0 条";
  $("#prev-page").disabled = page===0;
  $("#next-page").disabled = (page+1)*pageSize>=items.length;
}

function setFilters(values={}) {
  $("#search").value = values.search || "";
  for(const key of ["model","split","category","paired"]) $(`#filter-${key}`).value = values[key] || (key==="category"?"success":"all");
  page = 0;
  renderCases();
}

function showCase(id) {
  if(!episodeMap.has(id)) return;
  const next = `#case=${encodeURIComponent(id)}`;
  if(location.hash===next) loadCase(id);
  else location.hash = next;
}

function attributionText(e, d) {
  if(e.category==="vla") return `成功前的 ${e.vla_calls} 个环境动作全部是 VLA 调用。第 #${e.first_success_step} 个动作 ${e.last_method} 后，环境首次返回 success=true。读取图像、定位、记忆和记录结果的工具调用仍可能存在。`;
  if(e.category==="setup") {
    const prep = d.trace.filter(a=>a.kind==="manual").map(a=>`#${a.step} ${a.method}`).join("、");
    return `先执行 ${prep}，之后连续 ${e.vla_calls} 次 VLA 调用；非 VLA 动作仅位于首次 VLA 之前。第 #${e.first_success_step} 个动作后成功。`;
  }
  if(e.category==="repair") return `在 ${e.initial_vla_calls} 次 VLA 尝试后，第 #${e.first_intervention_step} 个动作开始出现 VLA 之后的 Planner 介入。成功前共 ${e.vla_calls} 次 VLA、${e.manual_calls} 次解析动作；第 #${e.first_success_step} 个动作 ${e.last_method} 后首次 success=true，最后一步由${e.completion_actor==="vla"?" VLA":"解析动作"}完成。`;
  return `整个 episode 没有记录到环境 success=true。共有 ${e.vla_calls} 次 VLA 与 ${e.manual_calls} 次解析动作；${e.first_intervention_step?`第 #${e.first_intervention_step} 个动作起出现 VLA 后的 Planner 介入。`:""}停止方式为${e.stop==="stuck"?" Agent 调用 finish(status=stuck)":"无 finish 且达到 100 个模型响应上限"}。`;
}

async function loadCase(id) {
  if(!episodeMap.has(id)) return;
  selectedId = id;
  $("#copy-link").textContent = "复制链接";
  $("#case-detail").innerHTML = '<p role="status" id="detail-title">正在加载动作证据…</p>';
  const dialog = $("#case-dialog");
  if(!dialog.open) dialog.showModal();
  document.body.style.overflow = "hidden";
  dialog.scrollTop = 0;
  try {
    if(!detailCache.has(id)) {
      const response = await fetch(`cases/${encodeURIComponent(id)}.json`);
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      detailCache.set(id, await response.json());
    }
    if(selectedId!==id) return;
    const d = detailCache.get(id), e = episodeMap.get(id);
    const ex = examples.find(x=>x.id===id);
    $("#case-detail").innerHTML = `
      <div class="detail-heading"><h2 id="detail-title">${e.task} · seed ${e.seed}</h2>${badge(e.category)}</div>
      <div class="detail-subtitle">${data.models[e.model].name} · xhigh · ${e.split === "seen" ? "Seen" : "Unseen"} · 环境判定 ${e.success?"成功":"未成功"}</div>
      <div class="task-instruction">${escapeHTML(e.task_language)}</div>
      <div class="detail-stats"><div><b>${e.vla_calls} / ${e.manual_calls}</b><span>VLA / 解析动作</span></div><div><b>${e.tool_calls}</b><span>全部工具调用（transcript）</span></div><div><b>${e.turns} / 100</b><span>模型响应计数</span></div><div><b>${seconds(e.elapsed_s)}</b><span>episode 墙钟耗时</span></div></div>
      <div class="evidence"><p><strong>归类依据：</strong>${attributionText(e,d)}</p>${ex?`<p><strong>案例解读：</strong>${ex.text}</p>`:""}<p class="note">调用数截止首次成功（失败则取全程）；解析动作数包含准备动作。这里的 step 是环境动作编号，不是仿真步。</p></div>
      <div class="detail-links">${id==="astra--PanTransfer--2"?'<a href="../pan-transfer/">观看视频与全部 79 次工具调用 →</a>':""}<a href="cases/${encodeURIComponent(id)}.json" download>下载本例证据 JSON</a><button class="text-button" data-case="${e.model==="astra"?"sol":"astra"}--${e.task}--${e.seed}">查看另一模型同 seed →</button></div>
      ${d.finish_summary?`<details class="detail-summary"><summary>Agent 结束时的报告（原文；环境判定优先）</summary><blockquote>${escapeHTML(d.finish_summary)}</blockquote></details>`:'<p class="note">本例没有 finish summary；不能据缺少 Agent 总结判断是否成功。</p>'}
      <div class="trace-tools"><h3>环境动作轨迹 <span class="subtle">${d.trace.length} 个动作</span></h3><label class="subtle" for="trace-filter">显示</label><select id="trace-filter"><option value="all">全部动作</option><option value="manual">仅解析动作</option><option value="changes">仅判据变化 / 成功</option><option value="vla">仅 VLA</option></select><button id="expand-trace" type="button">展开参数</button></div>
      <div class="trace-summary" aria-label="动作类型时间顺序">${d.trace.map(a=>`<span class="trace-dot ${a.kind==="vla"?"vla":"repair"}" title="#${a.step} ${a.method}">${a.step}</span>`).join("")}</div>
      <p class="note">蓝色为 VLA，绿色为解析控制。参数使用实际保存的 command；返回结果只展示动作执行字段。展开可看完整任务判据，灰字为相对前一步的变化。</p>
      <div id="trace-list" style="margin-top:13px"></div>
      <details class="source-details"><summary>初末判据、工具计数与来源校验</summary><h4>初始任务判据</h4><pre>${escapeHTML(JSON.stringify(d.initial_progress,null,2))}</pre><h4>最终任务判据</h4><pre>${escapeHTML(JSON.stringify(d.final_progress,null,2))}</pre><h4>transcript 中具名工具的完成记录</h4><pre>${escapeHTML(JSON.stringify(d.tool_counts,null,2))}</pre><p class="note">这里只汇总具名工具；SDK 的全部工具调用数还可能包含本地命令等事件，因此不强制与该表之和相等。</p><h4>原始来源及 SHA-256</h4><pre>${escapeHTML(JSON.stringify(d.source,null,2))}</pre><p>result.termination_reason = ${escapeHTML(d.termination_reason)}</p></details>`;
    renderTrace();
    $("#trace-filter").addEventListener("change", renderTrace);
    $("#expand-trace").addEventListener("click",()=>{
      const all = [...document.querySelectorAll(".trace-step")];
      const open = all.some(el=>!el.open);
      all.forEach(el=>el.open=open);
      $("#expand-trace").textContent = open?"收起参数":"展开参数";
    });
  } catch(error) {
    if(selectedId===id) $("#case-detail").innerHTML = `<div class="error" id="detail-title">证据加载失败：${escapeHTML(error.message)}。请刷新后重试。</div>`;
  }
}

function renderTrace() {
  const d = detailCache.get(selectedId), filter = $("#trace-filter").value;
  const actions = d.trace.filter(a=> filter==="all" || (filter==="changes" ? Object.keys(a.changes).length || a.success : a.kind===filter));
  $("#expand-trace").textContent = "展开参数";
  $("#trace-list").innerHTML = actions.map(a=>{
    const changes = Object.entries(a.changes).map(([key,value])=>`${key}: ${JSON.stringify(value.before)} → ${JSON.stringify(value.after)}`).join(" · ");
    return `<details class="trace-step ${a.success?"step-success":""}"><summary><span class="step-number">#${a.step}</span><code>${a.method}</code><span class="badge ${a.kind==="vla"?"vla":"repair"}">${a.kind==="vla"?"VLA":"解析"}</span>${a.success?'<span class="badge repair">success=true</span>':""}<small>${seconds(a.elapsed_s)}</small></summary><div class="step-body"><h4>实际调用参数</h4><pre>${escapeHTML(JSON.stringify(a.args,null,2))}</pre><h4>执行结果字段</h4><pre>${escapeHTML(JSON.stringify(a.result,null,2))}</pre><h4>动作之后的任务判据 · success=${a.success}</h4><pre>${escapeHTML(JSON.stringify(a.progress,null,2))}</pre></div>${changes?`<div class="step-change">${escapeHTML(changes)}</div>`:""}</details>`;
  }).join("") || '<p class="empty">这个筛选下没有动作记录。</p>';
}

function onHash() {
  const value = new URLSearchParams(location.hash.slice(1)).get("case");
  if(value && episodeMap.has(value)) loadCase(value);
  else if($("#case-dialog").open) $("#case-dialog").close();
}

document.addEventListener("click", (event)=>{
  const target = event.target.closest("button[data-case],button[data-matrix-model],button[data-filter-category],button[data-filter-paired],button[data-method-search]");
  if(!target || !data) return;
  if(target.dataset.case) return showCase(target.dataset.case);
  if(target.dataset.matrixModel) { matrixModel=target.dataset.matrixModel; renderMatrix(); return; }
  if(target.dataset.filterCategory) setFilters({model:target.dataset.filterModel,split:target.dataset.filterSplit,category:target.dataset.filterCategory});
  if(target.dataset.filterPaired) setFilters({category:"all",paired:target.dataset.filterPaired});
  if(target.dataset.methodSearch) setFilters({category:"repair",search:target.dataset.methodSearch});
  $("#case-browser").scrollIntoView({behavior:"smooth",block:"start"});
});

$("#close-dialog").addEventListener("click",()=>$("#case-dialog").close());
$("#case-dialog").addEventListener("close",()=>{
  selectedId = null;
  document.body.style.overflow = "";
  if(location.hash.startsWith("#case=")) history.replaceState(null,"",location.pathname+location.search);
});
$("#compare-case").addEventListener("click",()=>{
  const e = episodeMap.get(selectedId);
  if(e) showCase(`${e.model==="astra"?"sol":"astra"}--${e.task}--${e.seed}`);
});
$("#copy-link").addEventListener("click",async()=>{
  try { await navigator.clipboard.writeText(location.href); $("#copy-link").textContent="已复制"; }
  catch { $("#copy-link").textContent="链接在地址栏"; }
});
$("#print").addEventListener("click",()=>window.print());
$("#prev-page").addEventListener("click",()=>{page--;renderCases();});
$("#next-page").addEventListener("click",()=>{page++;renderCases();});
$("#reset-filters").addEventListener("click",()=>setFilters());
$("#search").addEventListener("input",()=>{page=0;renderCases();});
for(const key of ["model","split","category","paired"]) $(`#filter-${key}`).addEventListener("change",()=>{page=0;renderCases();});
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
