'use strict';

const $ = (id) => document.getElementById(id);
const splitNames = {seen: 'Seen', unseen: 'Unseen', all: '总计'};
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, (char) => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
let data;

function renderTasks() {
  const query = $('search').value.trim().toLowerCase();
  const split = $('split').value;
  let count = 0;
  $('task-tables').innerHTML = ['seen', 'unseen'].filter((s) => split === 'all' || s === split).map((s) => {
    const tasks = data.tasks[s].filter((task) => task.toLowerCase().includes(query));
    count += tasks.length;
    if (!tasks.length) return '';
    const rows = tasks.map((task) => {
      const episodes = data.episodes.filter((e) => e.split === s && e.task === task).sort((a, b) => a.seed - b.seed);
      const baseline = episodes.filter((e) => e.baseline_success).length;
      const da3 = episodes.filter((e) => e.da3_success).length;
      const delta = da3 - baseline;
      const cells = episodes.map((e) => {
        const category = e.baseline_success === e.da3_success ? '' : e.da3_success ? 'gain' : 'loss';
        const label = `seed ${e.seed}：baseline ${e.baseline_success ? '成功' : '失败'}，DA3 ${e.da3_success ? '成功' : '失败'}`;
        return `<td><span class="pair ${category}" role="img" title="${label}" aria-label="${label}">${e.baseline_success ? '✓' : '×'} → ${e.da3_success ? '✓' : '×'}</span></td>`;
      }).join('');
      return `<tr><th scope="row">${escapeHTML(task)}</th><td>${baseline}/5</td><td>${da3}/5</td><td class="${delta > 0 ? 'gain-text' : delta < 0 ? 'loss-text' : ''}">${delta > 0 ? '+' : ''}${delta}</td>${cells}</tr>`;
    }).join('');
    return `<div class="task-group"><h3 id="tasks-${s}">${splitNames[s]}</h3><div class="table"><table class="task-table" aria-labelledby="tasks-${s}"><thead><tr><th>任务</th><th>Baseline</th><th>DA3</th><th>差值</th><th>seed 1</th><th>seed 2</th><th>seed 3</th><th>seed 4</th><th>seed 5</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
  }).join('');
  $('status').textContent = count ? `显示 ${count} 个任务 · ${count * 5} 对运行。筛选不改变上方完整实验统计。` : '没有匹配的任务。';
}

async function init() {
  try {
    const response = await fetch('data.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
    if (data.episodes.length !== 160 || ['seen', 'unseen'].some((s) => data.tasks[s].length !== 16)) throw new Error('数据不完整');
    $('paired-body').innerHTML = ['seen', 'unseen', 'all'].map((s) => {
      const row = data.summary[s];
      return `<tr><th scope="row">${splitNames[s]}</th><td>${row.both_success}</td><td>${row.baseline_only}</td><td>${row.da3_only}</td><td>${row.neither}</td></tr>`;
    }).join('');
    $('generated').textContent = new Date(data.generated_utc).toLocaleString('zh-CN', {timeZone: 'Asia/Hong_Kong', hour12: false}) + '（香港时间）';
    $('split').addEventListener('change', renderTasks);
    $('search').addEventListener('input', renderTasks);
    $('reset').addEventListener('click', () => { $('split').value = 'all'; $('search').value = ''; renderTasks(); });
    renderTasks();
  } catch (error) {
    $('status').textContent = `明细加载失败：${error.message}。请刷新，或使用上方 CSV / JSON 下载。`;
  }
}
init();
