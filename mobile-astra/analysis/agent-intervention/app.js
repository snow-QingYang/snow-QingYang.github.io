'use strict';

const fields = ['experiment', 'split', 'path', 'task'];
const controls = Object.fromEntries(fields.map(id => [id, document.getElementById(id)]));
const body = document.getElementById('case-rows');
const params = new URLSearchParams(location.search);
const pageSize = 40;
let allRows = [];
let page = 0;

for (const id of fields) {
  const value = params.get(id);
  if (value !== null && (id === 'task' || [...controls[id].options].some(o => o.value === value))) controls[id].value = value;
}

const node = (tag, text, className) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
};
const step = n => n === null ? '—' : String(n);
const pathNames = { takeover: 'VLA 后有解析动作介入', setup: '首次 VLA 前有准备', vla_only: '仅调用 VLA', manual_only: '仅解析动作', no_actions: '无物理动作' };

function cell(label) {
  const el = node('td');
  el.dataset.label = label;
  return el;
}

function rowElement(row) {
  const tr = node('tr');
  tr.dataset.experiment = row.experiment;
  tr.dataset.split = row.split;
  tr.dataset.task = row.task;
  tr.dataset.seed = row.seed;
  const id = cell('实验 / 任务 / seed');
  id.append(node('strong', `${row.experiment} · ${row.task}`), node('small', `${row.split === 'seen' ? 'Seen' : 'Unseen'} · seed ${row.seed}`));
  const result = cell('结果与路径');
  result.append(node('span', row.success ? '成功' : '未成功', row.success ? 'badge complete' : 'badge failure'), node('small', pathNames[row.path]));
  if (!row.timeline_available) result.append(node('small', '† 仅有最终评分'));
  const sequence = cell('首次 VLA → 接管 → 成功');
  sequence.append(node('span', `${step(row.first_vla_step)} → ${step(row.first_intervention_step)} → ${row.timeline_available ? step(row.first_native_success_step) : '未记录†'}`, 'number'), node('small', '数字为保存的 step 编号'));
  const evidence = cell('完成动作 / 证据');
  if (row.success) {
    evidence.append(node('code', row.last_attributed_action || '—'), node('small', row.timeline_available ? '首次原生成功所在动作' : '† 最终评分前的末次动作'));
  } else {
    evidence.append(node('span', '未达到最终成功'));
  }
  const details = node('details');
  details.append(node('summary', `查看 ${row.actions.length} 次物理动作`));
  details.addEventListener('toggle', () => {
    if (!details.open || details.dataset.loaded) return;
    const trace = row.actions.map(a => {
      const marks = [];
      if (a.step === row.first_vla_step) marks.push('首次 VLA');
      if (a.step === row.first_intervention_step) marks.push('首次接管');
      if (a.native_success === true) marks.push('原生成功');
      return `${a.step}: ${a.method}${marks.length ? '  [' + marks.join(' · ') + ']' : ''}`;
    }).join('\n');
    details.append(node('pre', trace || '没有记录物理动作。'));
    if (!row.timeline_available) details.append(node('p', '† 本局没有逐步原生成功记录；不能确定首次成功动作。', 'note'));
    details.dataset.loaded = 'true';
  });
  evidence.append(details);
  tr.append(id, result, sequence, evidence);
  return tr;
}

function render() {
  const experiment = controls.experiment.value;
  const split = controls.split.value;
  const path = controls.path.value;
  const task = controls.task.value.trim().toLowerCase();
  const rows = allRows.filter(r =>
    (experiment === 'all' || r.experiment === experiment) &&
    (split === 'all' || r.split === split) &&
    r.task.toLowerCase().includes(task) &&
    (path === 'all' ||
      (path === 'takeover_success' && r.takeover_success) ||
      (path === 'takeover_failure' && r.takeover_attempted && !r.success) ||
      (path === 'vla_only_success' && r.path === 'vla_only' && r.success) ||
      (path === 'setup_success' && r.path === 'setup' && r.success))
  );
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  page = Math.min(page, pages - 1);
  const seen = rows.filter(r => r.split === 'seen').length;
  document.getElementById('filter-count').textContent = experiment === 'E12' ? '不适用：Pure VLA 没有 Agent 接管。' : `筛选结果 ${rows.length} 局：Seen ${seen} · Unseen ${rows.length - seen}`;
  document.getElementById('filter-note').textContent = rows.some(r => !r.timeline_available) ? '† 当前筛选包含 E06：只有最终评分，无法确认接管前从未成功。' : '';
  body.replaceChildren(...rows.slice(page * pageSize, (page + 1) * pageSize).map(rowElement));
  if (!rows.length) {
    const tr = node('tr');
    const td = node('td', experiment === 'E12' ? '没有 Planner 接管轨迹。' : '没有符合条件的 episode。');
    td.colSpan = 4;
    tr.append(td);
    body.append(tr);
  }
  document.getElementById('page-status').textContent = `第 ${page + 1} / ${pages} 页`;
  document.getElementById('previous').disabled = page === 0;
  document.getElementById('next').disabled = page + 1 >= pages;
  const query = new URLSearchParams();
  for (const id of fields) {
    const value = controls[id].value.trim();
    if (value && value !== 'all' && !(id === 'path' && value === 'takeover_success')) query.set(id, value);
  }
  history.replaceState(null, '', location.pathname + (query.size ? '?' + query : '') + location.hash);
}

document.getElementById('filters').addEventListener('submit', event => event.preventDefault());
for (const id of fields) controls[id].addEventListener(id === 'task' ? 'input' : 'change', () => { page = 0; render(); });
document.getElementById('previous').addEventListener('click', () => { page--; render(); });
document.getElementById('next').addEventListener('click', () => { page++; render(); });

fetch('data.json').then(response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then(data => {
  allRows = data.experiments.flatMap(e => e.episodes);
  render();
}).catch(() => {
  document.getElementById('filter-count').textContent = '逐局数据加载失败。请刷新，或下载 CSV 查看；上方汇总表不受影响。';
});
