'use strict';

const $ = (id) => document.getElementById(id);
const splitNames = {seen: 'Seen', unseen: 'Unseen', all: '总计'};
const escapeHTML = (value) => String(value).replace(/[&<>"']/g, (char) => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
let data;

function differences(episode) {
  return [episode.initial_robot_state_max_abs_diff > data.initial_state_audit.robot_state_threshold ? '初始机器人状态不同（最大差 >1e-6）' : '',
    !episode.initial_task_language_equal ? '初始任务文本不同' : ''].filter(Boolean);
}

function showEpisode(index) {
  const episode = data.episodes[index];
  if (!episode) return;
  $('episode-title').textContent = `${episode.task} · seed ${episode.seed} · ${splitNames[episode.split]}`;
  const termination = {completed: '正常完成', planner_timeout: 'Planner 超时'};
  const rows = [
    ['原生任务结果', episode.baseline_success ? '成功' : '失败', episode.nocontact_success ? '成功' : '失败'],
    ['耗时', `${episode.baseline_elapsed_s.toFixed(1)} 秒`, `${episode.nocontact_elapsed_s.toFixed(1)} 秒`],
    ['终止原因', termination[episode.baseline_termination_reason], termination[episode.nocontact_termination_reason]],
    ['末条原生 success', String(episode.baseline_final_native_success), String(episode.nocontact_final_native_success)],
  ];
  const initial = differences(episode);
  $('episode-content').innerHTML = `<div class="table"><table><thead><tr><th>记录</th><th>Baseline</th><th>NoContactGT</th></tr></thead><tbody>${rows.map((row) => `<tr><th scope="row">${escapeHTML(row[0])}</th><td>${escapeHTML(row[1])}</td><td>${escapeHTML(row[2])}</td></tr>`).join('')}</tbody></table></div>
    <p class="note">${escapeHTML(initial.length ? initial.join('；') : '初始机器人状态差值未超过 1e-6，任务文本相同。')} 未检查全部场景物体。</p>
    <p class="note">初始机器人状态最大绝对差：<code>${escapeHTML(episode.initial_robot_state_max_abs_diff.toExponential(4))}</code></p>
    <details><summary>来源与 SHA-256</summary>${['baseline', 'nocontact'].map((label) => `<h3>${label === 'baseline' ? 'Baseline' : 'NoContactGT'}</h3><p class="hash"><code>${escapeHTML(data.sources[label].run)}</code></p><dl><dt>result.json</dt><dd class="hash"><code>${escapeHTML(episode[`${label}_result_sha256`])}</code></dd><dt>states.json</dt><dd class="hash"><code>${escapeHTML(episode[`${label}_states_sha256`])}</code></dd></dl>`).join('')}</details>`;
  $('episode-dialog').showModal();
}

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
      const nocontact = episodes.filter((e) => e.nocontact_success).length;
      const delta = nocontact - baseline;
      const cells = episodes.map((e) => {
        const category = e.baseline_success === e.nocontact_success ? '' : e.nocontact_success ? 'gain' : 'loss';
        const initial = differences(e);
        const timeout = e.nocontact_termination_reason === 'planner_timeout' ? '；NoContactGT 超时失败' : '';
        const label = `${task} seed ${e.seed}：baseline ${e.baseline_success ? '成功' : '失败'}，NoContactGT ${e.nocontact_success ? '成功' : '失败'}${timeout}${initial.length ? '；' + initial.join('、') : ''}。查看详情`;
        return `<td><button type="button" class="pair ${category}" data-episode="${data.episodes.indexOf(e)}" title="${escapeHTML(label)}" aria-label="${escapeHTML(label)}">${e.baseline_success ? '✓' : '×'} → ${e.nocontact_success ? '✓' : '×'}${initial.length ? ' *' : ''}</button></td>`;
      }).join('');
      return `<tr><th scope="row">${escapeHTML(task)}</th><td>${baseline}/5</td><td>${nocontact}/5</td><td class="${delta > 0 ? 'gain-text' : delta < 0 ? 'loss-text' : ''}">${delta > 0 ? '+' : ''}${delta}</td>${cells}</tr>`;
    }).join('');
    return `<div class="task-group"><h3 id="tasks-${s}">${splitNames[s]}</h3><div class="table" tabindex="0" role="region" aria-labelledby="tasks-${s}"><table class="task-table"><thead><tr><th>任务</th><th>Baseline</th><th>NoContactGT</th><th>差值</th><th>seed 1</th><th>seed 2</th><th>seed 3</th><th>seed 4</th><th>seed 5</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
  }).join('');
  $('status').textContent = count ? `显示 ${count} 个任务 · ${count * 5} 对运行。筛选不改变上方完整实验统计。` : '没有匹配的任务。';
}

function validateData(value) {
  if (!Array.isArray(value.episodes) || value.episodes.length !== 160
      || ['seen', 'unseen'].some((s) => !Array.isArray(value.tasks[s]) || value.tasks[s].length !== 16)) throw new Error('数据不完整');
  const keys = new Set(value.episodes.map((e) => `${e.split}/${e.task}/${e.seed}`));
  if (keys.size !== 160) throw new Error('存在重复 episode');
  for (const split of ['seen', 'unseen', 'all']) {
    const episodes = value.episodes.filter((e) => split === 'all' || e.split === split);
    const summary = value.summary[split];
    if (summary.total !== episodes.length
        || summary.baseline_success !== episodes.filter((e) => e.baseline_success).length
        || summary.nocontact_success !== episodes.filter((e) => e.nocontact_success).length) throw new Error('汇总与逐局记录不一致');
  }
}

async function init() {
  try {
    const response = await fetch('data.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
    validateData(data);
    $('summary-body').innerHTML = ['seen', 'unseen', 'all'].map((s) => {
      const row = data.summary[s];
      const delta = 100 * (row.nocontact_success - row.baseline_success) / row.total;
      return `<tr><th scope="row">${splitNames[s]}</th><td>${row.baseline_success} / ${row.total} · ${(100 * row.baseline_success / row.total).toFixed(2)}%</td><td>${row.nocontact_success} / ${row.total} · ${(100 * row.nocontact_success / row.total).toFixed(2)}%</td><td>${delta < 0 ? '−' : delta > 0 ? '+' : ''}${Math.abs(delta).toFixed(2)} 个百分点</td></tr>`;
    }).join('');
    $('paired-body').innerHTML = ['seen', 'unseen', 'all'].map((s) => {
      const row = data.summary[s];
      return `<tr><th scope="row">${splitNames[s]}</th><td>${row.both_success}</td><td>${row.baseline_only}</td><td>${row.nocontact_only}</td><td>${row.neither}</td></tr>`;
    }).join('');
    $('field-body').innerHTML = Object.entries(data.protocol.removed_progress_fields_by_task).map(([task, fields]) => `<tr><th scope="row">${escapeHTML(task)}</th><td>${fields.map((field) => `<code>${escapeHTML(field)}</code>`).join(' · ')}</td></tr>`).join('');
    $('generated').textContent = new Date(data.generated_utc).toLocaleString('zh-CN', {timeZone: 'Asia/Hong_Kong', hour12: false}) + '（香港时间）';
    $('split').addEventListener('change', renderTasks);
    $('search').addEventListener('input', renderTasks);
    $('reset').addEventListener('click', () => { $('split').value = 'all'; $('search').value = ''; renderTasks(); });
    $('task-tables').addEventListener('click', (event) => {
      const button = event.target.closest('[data-episode]');
      if (button) showEpisode(Number(button.dataset.episode));
    });
    $('close-dialog').addEventListener('click', () => $('episode-dialog').close());
    renderTasks();
  } catch (error) {
    $('status').textContent = `明细加载失败：${error.message}。请刷新，或使用上方 CSV / JSON 下载。`;
  }
}
init();
