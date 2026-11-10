'use strict';
const $ = id => document.getElementById(id);
const splitName = {seen: 'Seen', unseen: 'Unseen', all: '总计'};
const runName = {combined: '组合移除', geometry: '仅移除几何', baseline: 'Baseline'};
const pathName = {unsuccessful: '未成功', vla_only: '仅 VLA 动作', manual_then_vla_finish: '手工介入后 VLA 收尾', manual_finish: '手工动作后首次成功'};
const mark = value => value ? '✓' : '×';
const outcome = value => value ? '成功' : '失败';
const equal = value => value ? '精确相同' : '不完全相同';
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
let data;

function matches(row) {
  const ref = row[$('reference').value].success;
  const current = row.combined.success;
  const mode = $('outcome').value;
  const path = $('path').value;
  const resultMatches = mode === 'all' || mode === 'success' && current
    || mode === 'gain' && current && !ref || mode === 'loss' && !current && ref
    || mode === 'both' && current && ref || mode === 'neither' && !current && !ref;
  return resultMatches && (path === 'all' || row.combined.success_path === path);
}

function render() {
  const query = $('search').value.trim().toLowerCase();
  const selected = $('split').value;
  const reference = $('reference').value;
  let count = 0, cells = 0;
  const tables = [];
  for (const split of ['seen', 'unseen']) {
    if (selected !== 'all' && selected !== split) continue;
    const rows = [];
    for (const task of data.tasks[split]) {
      if (!task.toLowerCase().includes(query)) continue;
      const episodes = data.episodes.filter(row => row.split === split && row.task === task).sort((a, b) => a.seed - b.seed);
      if (!episodes.some(matches)) continue;
      count++;
      const refSuccesses = episodes.filter(row => row[reference].success).length;
      const currentSuccesses = episodes.filter(row => row.combined.success).length;
      const delta = currentSuccesses - refSuccesses;
      const seedCells = episodes.map(row => {
        if (!matches(row)) return '<td><span class="muted-cell">已筛除</span></td>';
        cells++;
        const ref = row[reference].success, current = row.combined.success;
        const differs = !row.initial_conditions[reference].strict_equal;
        const css = ref === current ? '' : current ? 'gain' : 'loss';
        const label = `${task}, seed ${row.seed}: ${runName[reference]} ${outcome(ref)}, 组合移除 ${outcome(current)}${differs ? '，初始记录不完全相同' : ''}`;
        return `<td><button type="button" class="seed ${css}" data-episode="${data.episodes.indexOf(row)}" aria-label="${escapeHTML(label)}">${mark(ref)} → ${mark(current)}${differs ? ' *' : ''}</button></td>`;
      }).join('');
      rows.push(`<tr><th scope="row">${escapeHTML(task)}</th><td class="task-count">${refSuccesses}/5 → ${currentSuccesses}/5</td><td class="${delta > 0 ? 'delta-positive' : delta < 0 ? 'delta-negative' : ''}">${delta > 0 ? '+' : ''}${delta}</td>${seedCells}</tr>`);
    }
    if (rows.length) tables.push(`<h3>${splitName[split]}</h3><div class="table-wrap" tabindex="0" role="region" aria-label="${splitName[split]} 逐任务结果"><table class="seed-table"><thead><tr><th>任务</th><th>${runName[reference]} → 组合移除</th><th>差值</th>${[1, 2, 3, 4, 5].map(seed => `<th>Seed ${seed}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`);
  }
  $('task-tables').innerHTML = tables.join('') || '<p>没有符合筛选条件的 episode。</p>';
  $('status').textContent = `显示 ${count} 个任务、${cells} / 160 对运行；对照组：${runName[reference]}。筛选不改变完整实验统计或每个任务的 5 局成功数。`;
}

function hashBlock(label, value) {
  return `<p>${escapeHTML(label)}<code class="hash">${escapeHTML(value)}</code></p>`;
}

function showEpisode(row) {
  const reference = $('reference').value;
  const initial = row.initial_conditions[reference];
  $('episode-title').textContent = `${splitName[row.split]} · ${row.task} · seed ${row.seed}`;
  const fields = [
    ['原生结果', 'success', outcome],
    ['成功路径', 'success_path', value => pathName[value]],
    ['VLA / 手工动作次数', null, (_, run) => `${run.vla_calls} / ${run.manual_calls}`],
    ['首次成功动作', 'first_success_action', value => value || '—'],
    ['首次成功记录 step', 'first_success_step', value => value ?? '—'],
    ['耗时', 'elapsed_s', value => value === null ? '—' : `${(value / 60).toFixed(1)} 分钟`],
    ['结束原因', 'termination_reason', value => value === 'completed' ? '正常结束' : value],
    ['末条观测 success', 'final_native_success', String],
  ];
  const runKeys = ['baseline', 'geometry', 'combined'];
  $('episode-content').innerHTML = `<div class="table-wrap"><table><thead><tr><th>记录</th>${runKeys.map(key => `<th>${runName[key]}</th>`).join('')}</tr></thead><tbody>${fields.map(([name, key, format]) => `<tr><th scope="row">${name}</th>${runKeys.map(run => `<td>${escapeHTML(format(key ? row[run][key] : null, row[run]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
  <h3>与${runName[reference]}的初始记录对照</h3><dl class="record"><dt>严格匹配</dt><dd>${equal(initial.strict_equal)}</dd><dt>机器人状态</dt><dd>${equal(initial.robot_state_exact_equal)}；最大绝对差 <code>${initial.robot_state_max_abs_diff.toExponential(4)}</code></dd><dt>任务文字</dt><dd>${equal(initial.task_language_equal)}</dd><dt>三路 RGB 文件</dt><dd>${Object.entries(initial.rgb_exact_equal).map(([camera, value]) => `${escapeHTML(camera)}：${equal(value)}`).join('<br>')}</dd><dt>相机 metadata</dt><dd>${Object.entries(initial.camera_metadata_equal).map(([camera, value]) => `${escapeHTML(camera)}：${equal(value)}`).join('<br>')}</dd></dl>
  <p class="note">“不完全相同”不自动代表场景不同；图像可仅差少量像素。完整物体初态与 RNG 状态没有记录。成功路径为实际动作分类，不代表某一步的因果贡献；耗时也受 API 与调度影响。</p>
  <details><summary>物理动作调用统计</summary>${runKeys.map(key => `<h3>${runName[key]}</h3><p>${Object.entries(row[key].action_counts).map(([action, count]) => `<code>${escapeHTML(action)}</code> × ${count}`).join('；') || '无物理动作'}</p>`).join('')}</details>
  <details><summary>结果、状态与初始证据 SHA-256</summary>${runKeys.map(key => {
    const hashes = row.initial_sha256[key];
    return `<h3>${runName[key]}</h3>${hashBlock('result.json', row[key].result_sha256)}${hashBlock('states.json', row[key].states_sha256)}${hashBlock('初始机器人状态', hashes.robot_state)}${hashBlock('初始任务文字', hashes.task_language)}${Object.entries(hashes.rgb).map(([camera, value]) => hashBlock(`初始 RGB · ${camera}`, value)).join('')}${Object.entries(hashes.camera_metadata).map(([camera, value]) => hashBlock(`初始 metadata · ${camera}`, value)).join('')}`;
  }).join('')}</details>`;
  $('episode-dialog').showModal();
}

function validate(loaded) {
  if (loaded.episodes.length !== 160 || new Set(loaded.episodes.map(row => `${row.split}/${row.task}/${row.seed}`)).size !== 160) throw new Error('明细数量或唯一性不符');
  for (const split of ['seen', 'unseen', 'all']) {
    const rows = loaded.episodes.filter(row => split === 'all' || row.split === split);
    const summary = loaded.summary[split];
    if (summary.total !== rows.length) throw new Error('汇总数量与明细不符');
    for (const run of ['baseline', 'geometry', 'combined']) {
      if (summary.successes[run] !== rows.filter(row => row[run].success).length) throw new Error('成功数与明细不符');
    }
    for (const reference of ['baseline', 'geometry']) {
      const paired = summary[`paired_${reference}`];
      const counts = [
        ['both_success', row => row.combined.success && row[reference].success],
        ['combined_only', row => row.combined.success && !row[reference].success],
        ['reference_only', row => !row.combined.success && row[reference].success],
        ['both_failure', row => !row.combined.success && !row[reference].success],
      ];
      for (const [key, predicate] of counts) if (paired[key] !== rows.filter(predicate).length) throw new Error('配对统计与明细不符');
    }
  }
}

$('close-dialog').addEventListener('click', () => $('episode-dialog').close());
$('task-tables').addEventListener('click', event => {
  const button = event.target.closest('button[data-episode]');
  if (button) showEpisode(data.episodes[Number(button.dataset.episode)]);
});
fetch('data.json').then(response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then(loaded => {
  validate(loaded);
  data = loaded;
  $('generated').textContent = data.generated_utc;
  for (const id of ['split', 'reference', 'outcome', 'path']) $(id).addEventListener('change', render);
  $('search').addEventListener('input', render);
  $('reset').addEventListener('click', () => {
    $('split').value = 'all'; $('reference').value = 'geometry'; $('outcome').value = 'all';
    $('path').value = 'all'; $('search').value = ''; render();
  });
  render();
}).catch(error => {
  $('status').classList.add('error');
  $('status').textContent = `明细加载失败（${error.message}）。可下载 CSV 或阅读文字报告。`;
});
