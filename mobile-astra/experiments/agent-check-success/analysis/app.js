"use strict";
const $ = (id) => document.getElementById(id);
const splitName = {seen: "Seen", unseen: "Unseen", all: "总计"};
const declarationName = {success: "声明成功", stuck: "声明 stuck", failure: "声明 failure", no_finish: "未调用 finish"};
const mark = (value) => value ? "✓" : "×";
const nativeText = (value) => value ? "成功" : "失败";
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, (char) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[char]);
const minutes = (seconds) => `${(seconds / 60).toFixed(1)} 分钟`;
let data;

function matches(row) {
  const mode = $("outcome").value;
  return mode === "all"
    || mode === "success" && row.agent_success
    || mode === "false_claim" && row.declaration === "success" && !row.agent_success
    || mode === "no_finish" && !row.finish_called
    || mode === "baseline_only" && row.baseline_success && !row.agent_success
    || mode === "agent_only" && !row.baseline_success && row.agent_success;
}

function render() {
  const query = $("search").value.trim().toLowerCase();
  const selected = $("split").value;
  let shown = 0;
  let taskCount = 0;
  const tables = [];
  for (const split of ["seen", "unseen"]) {
    if (selected !== "all" && selected !== split) continue;
    const rows = [];
    for (const task of data.tasks[split]) {
      if (!task.toLowerCase().includes(query)) continue;
      const episodes = data.episodes.filter((row) => row.split === split && row.task === task);
      if (!episodes.some(matches)) continue;
      taskCount++;
      const totals = ["baseline", "notask", "agent"].map((key) => episodes.filter((row) => row[`${key}_success`]).length);
      const cells = episodes.map((row) => {
        if (!matches(row)) return '<td><span class="muted-cell">已筛除</span></td>';
        shown++;
        const css = ["seed", row.agent_success ? "native-success" : "", row.declaration === "success" && !row.agent_success ? "false-claim" : "", !row.finish_called ? "no-finish" : ""].filter(Boolean).join(" ");
        const label = `${task}, seed ${row.seed}: E01 ${nativeText(row.baseline_success)}, E03 ${nativeText(row.notask_success)}, E06 ${nativeText(row.agent_success)}, ${declarationName[row.declaration]}`;
        return `<td><button type="button" class="${css}" data-episode="${data.episodes.indexOf(row)}" aria-label="${escapeHTML(label)}">${mark(row.baseline_success)} / ${mark(row.notask_success)} / ${mark(row.agent_success)}<small>${declarationName[row.declaration]}</small></button></td>`;
      }).join("");
      rows.push(`<tr><th scope="row">${escapeHTML(task)}</th><td class="task-count">${totals.map((count) => `${count}/5`).join(" · ")}</td>${cells}</tr>`);
    }
    if (rows.length) tables.push(`<h3>${splitName[split]}</h3><div class="table-wrap"><table class="seed-table"><thead><tr><th>任务</th><th>E01 · E03 · E06</th>${[1, 2, 3, 4, 5].map((seed) => `<th>Seed ${seed}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`);
  }
  $("status").textContent = `显示 ${taskCount} 个任务、${shown} / 160 局。绿色边框：E06 原生成功；红色：误报成功；虚线：未调用 finish。`;
  $("task-tables").innerHTML = tables.join("") || "<p>没有符合当前条件的 episode。</p>";
}

function showEpisode(row) {
  $("episode-title").textContent = `${splitName[row.split]} · ${row.task} · seed ${row.seed}`;
  const fields = [
    ["E06 完成声明", declarationName[row.declaration]],
    ["调用 finish", row.finish_called ? "是" : "否"],
    ["停止原因", row.termination_reason],
    ["E06 评分时机", "Planner 返回后查询 env.check_success"],
  ];
  const table = [["E01 · baseline", row.baseline_success, row.baseline_elapsed_s], ["E03 · No task progress", row.notask_success, row.notask_elapsed_s], ["E06 · No task progress and agent success", row.agent_success, row.elapsed_s]];
  $("episode-content").innerHTML = `<div class="table-wrap"><table><thead><tr><th>设置</th><th>原生结果</th><th>耗时</th></tr></thead><tbody>${table.map(([name, success, elapsed]) => `<tr><td>${name}</td><td>${nativeText(success)}</td><td>${minutes(elapsed)}</td></tr>`).join("")}</tbody></table></div><dl class="record">${fields.map(([key, value]) => `<dt>${key}</dt><dd>${escapeHTML(value)}</dd>`).join("")}</dl><p class="note">对照仅按任务与 seed 匹配；耗时受调度、API 等因素影响。原生结果均保留在各自 160 局分母内。</p><details><summary>结果文件 SHA-256</summary>${[["E01", row.baseline_result_sha256], ["E03", row.notask_result_sha256], ["E06", row.result_sha256]].map(([name, hash]) => `<p>${name}<code class="hash">${escapeHTML(hash)}</code></p>`).join("")}</details>`;
  $("episode-dialog").showModal();
}

$("close-dialog").addEventListener("click", () => $("episode-dialog").close());
$("task-tables").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-episode]");
  if (button) showEpisode(data.episodes[Number(button.dataset.episode)]);
});

fetch("data.json").then((response) => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then((loaded) => {
  data = loaded;
  if (data.episodes.length !== 160) throw new Error("结果数量不符");
  $("generated").textContent = data.generated_utc;
  $("paired-body").innerHTML = ["seen", "unseen", "all"].flatMap((split) => ["baseline", "notask"].map((reference) => {
    const stats = data.summary[split].paired[reference];
    return `<tr><th scope="row">${splitName[split]}</th><td>${reference === "baseline" ? "E01 · baseline" : "E03 · No task progress"}</td><td>${stats.both_success}</td><td>${stats.reference_only}</td><td>${stats.agent_only}</td><td>${stats.both_failure}</td></tr>`;
  })).join("");
  for (const id of ["split", "outcome"]) $(id).addEventListener("change", render);
  $("search").addEventListener("input", render);
  $("reset").addEventListener("click", () => {$("split").value = "all"; $("outcome").value = "all"; $("search").value = ""; render();});
  render();
}).catch((error) => {
  $("status").classList.add("error");
  $("status").textContent = `数据暂时无法加载（${error.message}）。请刷新，或下载 CSV / 阅读文字报告。`;
});
