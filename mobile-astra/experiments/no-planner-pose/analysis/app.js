'use strict';
const $ = id => document.getElementById(id);
const splitName = {seen: 'Seen', unseen: 'Unseen', all: '总计'};
const runName = {no_pose: 'E09 · 不提供位姿', combined: 'E08 · 提供位姿', baseline: 'E01 · Baseline'};
const pathName = {unsuccessful: '未成功', vla_only: '仅 VLA 动作', manual_then_vla_finish: '手工介入后 VLA 收尾', manual_finish: '手工动作后首次成功'};
const mark = value => value ? '✓' : '×';
const outcome = value => value ? '成功' : '失败';
const equal = value => value ? '精确相同' : '不完全相同';
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
let data;

function matches(row) {
  const ref = row[$('reference').value].success;
  const current = row.no_pose.success;
  const mode = $('outcome').value;
  const path = $('path').value;
  const resultMatches = mode === 'all' || mode === 'success' && current
    || mode === 'gain' && current && !ref || mode === 'loss' && !current && ref
    || mode === 'both' && current && ref || mode === 'neither' && !current && !ref;
  return resultMatches && (path === 'all' || row.no_pose.success_path === path);
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
      const currentSuccesses = episodes.filter(row => row.no_pose.success).length;
      const delta = currentSuccesses - refSuccesses;
      const seedCells = episodes.map(row => {
        if (!matches(row)) return '<td><span class="muted-cell">已筛除</span></td>';
        cells++;
        const ref = row[reference].success, current = row.no_pose.success;
        const differs = !row.initial_conditions[reference].observed_inputs_equal;
        const css = ref === current ? '' : current ? 'gain' : 'loss';
        const label = `${task}, seed ${row.seed}: ${runName[reference]} ${outcome(ref)}, ${runName.no_pose} ${outcome(current)}${differs ? '，初始保存记录不完全相同' : ''}`;
        return `<td><button type="button" class="seed ${css}" data-episode="${data.episodes.indexOf(row)}" aria-label="${escapeHTML(label)}">${mark(ref)} → ${mark(current)}${differs ? ' *' : ''}</button></td>`;
      }).join('');
      rows.push(`<tr><th scope="row">${escapeHTML(task)}</th><td class="task-count">${refSuccesses}/5 → ${currentSuccesses}/5</td><td class="${delta > 0 ? 'delta-positive' : delta < 0 ? 'delta-negative' : ''}">${delta > 0 ? '+' : ''}${delta}</td>${seedCells}</tr>`);
    }
    if (rows.length) tables.push(`<h3>${splitName[split]}</h3><div class="table-wrap" tabindex="0" role="region" aria-label="${splitName[split]} 逐任务结果"><table class="seed-table"><thead><tr><th>任务</th><th>${runName[reference]} → E09</th><th>差值</th>${[1, 2, 3, 4, 5].map(seed => `<th>Seed ${seed}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`);
  }
  $('task-tables').innerHTML = tables.join('') || '<p>没有符合筛选条件的 episode。</p>';
  $('status').textContent = `显示 ${count} 个任务、${cells} / 160 对运行；对照组：${runName[reference]}。筛选不改变完整实验统计或每个任务的 5 局成功数。`;
}

function renderSummaries() {
  $('paired-tables').innerHTML = ['combined', 'baseline'].map(reference => `<h3>与 ${runName[reference]} 对照</h3><div class="table-wrap"><table><thead><tr><th>任务组</th><th>两组成功</th><th>仅 E09 成功</th><th>仅对照组成功</th><th>两组失败</th></tr></thead><tbody>${['seen', 'unseen', 'all'].map(split => {
    const paired = data.summary[split][`paired_${reference}`];
    return `<tr><th scope="row">${splitName[split]}</th><td>${paired.both_success}</td><td>${paired.no_pose_only}</td><td>${paired.reference_only}</td><td>${paired.both_failure}</td></tr>`;
  }).join('')}</tbody></table></div>`).join('');
  $('path-table').innerHTML = `<div class="table-wrap"><table><thead><tr><th>任务组</th><th>仅 VLA 动作</th><th>手工介入后 VLA 收尾</th><th>手工动作后首次成功</th><th>总成功</th></tr></thead><tbody>${['seen', 'unseen', 'all'].map(split => {
    const rows = data.episodes.filter(row => split === 'all' || row.split === split);
    return `<tr><th scope="row">${splitName[split]}</th>${['vla_only', 'manual_then_vla_finish', 'manual_finish'].map(path => `<td>${rows.filter(row => row.no_pose.success && row.no_pose.success_path === path).length}</td>`).join('')}<td>${rows.filter(row => row.no_pose.success).length}</td></tr>`;
  }).join('')}</tbody></table></div>`;
  $('initial-table').innerHTML = `<div class="table-wrap"><table><thead><tr><th>对照组</th><th>任务文字相同</th><th>三张 RGB 文件相同</th><th>相机 metadata 相同</th><th>以上全部相同</th></tr></thead><tbody>${['combined', 'baseline'].map(reference => {
    const initial = data.episodes.map(row => row.initial_conditions[reference]);
    const sameRGB = value => Object.values(value.rgb_exact_equal).every(Boolean);
    const sameCamera = value => Object.values(value.camera_metadata_equal).every(Boolean);
    return `<tr><th scope="row">${runName[reference]}</th><td>${initial.filter(value => value.task_language_equal).length}/160</td><td>${initial.filter(sameRGB).length}/160</td><td>${initial.filter(sameCamera).length}/160</td><td>${initial.filter(value => value.observed_inputs_equal).length}/160</td></tr>`;
  }).join('')}</tbody></table></div>`;
  const audit = data.context_audit;
  const formatCount = value => Number(value).toLocaleString('en-US');
  $('context-audit').innerHTML = `<div class="table-wrap"><table><thead><tr><th>实际记录核查</th><th>结果</th></tr></thead><tbody><tr><th scope="row">已完成 MCP 工具调用</th><td>${formatCount(audit.completed_mcp_calls)} 次</td></tr><tr><th scope="row">正常观测返回 / 保存状态</th><td>${formatCount(audit.observation_returns)} / ${formatCount(audit.saved_snapshots)}</td></tr><tr><th scope="row">${audit.hidden_feedback_fields_checked} 个隐藏反馈字段命中</th><td>${audit.hidden_feedback_field_occurrences}</td></tr><tr><th scope="row">几何查询 / 文件读取、列表、搜索 / 原生 shell</th><td>${audit.geometry_tool_calls} / ${audit.file_read_list_search_calls} / ${audit.native_command_calls}</td></tr><tr><th scope="row">空记忆读取记录 / 原生评分一致</th><td>${audit.empty_memory_read_logs}/160 / ${audit.native_scoring_consistent}/160</td></tr><tr><th scope="row">success_criteria 文件</th><td>${audit.success_criteria_files}</td></tr></tbody></table></div><p>${formatCount(audit.saved_empty_states)} 条保存记录的机器人 state 均为空；其中 ${formatCount(audit.saved_normal_empty_results)} 条正常动作结果为空、${audit.saved_initial_null_results} 条初始记录无动作结果。另有 <strong>${audit.saved_cancelled_results} 条预算结束时的 tool_cancelled 标记</strong>，不属于正常完成的观测返回，不能说所有保存结果都为空。</p><p class="note">字段审计排除 Agent 自己的命令参数与 finish 声明；MCP 框架自身的传输状态 / 调用耗时不作为机器人动作反馈统计。实际轨迹中未见其他读取入口被使用，不代表 OS 层已禁止这些入口。</p>`;
}

function hashBlock(label, value) {
  return `<p>${escapeHTML(label)}<code class="hash">${escapeHTML(value ?? '未记录')}</code></p>`;
}

function showEpisode(row) {
  const reference = $('reference').value;
  const initial = row.initial_conditions[reference];
  $('episode-title').textContent = `${splitName[row.split]} · ${row.task} · seed ${row.seed}`;
  const fields = [
    ['原生结果', 'success', outcome],
    ['成功路径', 'success_path', value => pathName[value] || value],
    ['VLA / 手工动作次数', null, (_, run) => `${run.vla_calls} / ${run.manual_calls}`],
    ['首次成功动作', 'first_success_action', value => value || '—'],
    ['首次成功图像索引', 'first_success_step', value => value ?? '—'],
    ['耗时', 'elapsed_s', value => value == null ? '—' : `${(value / 60).toFixed(1)} 分钟`],
    ['结束原因', 'termination_reason', value => value === 'completed' ? '正常结束' : value || '—'],
    ['末条观测 success', 'final_native_success', String],
  ];
  const runKeys = ['baseline', 'combined', 'no_pose'];
  $('episode-content').innerHTML = `<div class="table-wrap"><table><thead><tr><th>记录</th>${runKeys.map(key => `<th>${runName[key]}</th>`).join('')}</tr></thead><tbody>${fields.map(([name, key, format]) => `<tr><th scope="row">${name}</th>${runKeys.map(run => `<td>${escapeHTML(format(key ? row[run][key] : null, row[run]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
  <h3>与 ${runName[reference]} 的初始记录对照</h3><dl class="record"><dt>以下记录合并比较</dt><dd>${equal(initial.observed_inputs_equal)}</dd><dt>机器人位姿</dt><dd>不可比较：E09 的机器人 state 按设计为空。</dd><dt>任务文字</dt><dd>${equal(initial.task_language_equal)}</dd><dt>三路 RGB 文件</dt><dd>${Object.entries(initial.rgb_exact_equal).map(([camera, value]) => `${escapeHTML(camera)}：${equal(value)}`).join('<br>')}</dd><dt>内部相机 metadata</dt><dd>${Object.entries(initial.camera_metadata_equal).map(([camera, value]) => `${escapeHTML(camera)}：${equal(value)}`).join('<br>')}</dd></dl>
  <p class="note">这里只比较保存的任务 / RGB / metadata；不证明全部物体和机器人初态相同。metadata 没有作为 Agent 输入。成功路径按实际命令分类，不代表某一步的因果贡献；耗时为事后统计，也受 API 与调度影响。</p>
  <details><summary>物理动作调用统计</summary>${runKeys.map(key => `<h3>${runName[key]}</h3><p>${Object.entries(row[key].action_counts).map(([action, count]) => `<code>${escapeHTML(action)}</code> × ${count}`).join('；') || '无物理动作'}</p>`).join('')}</details>
  <details><summary>结果、状态与初始证据 SHA-256</summary>${runKeys.map(key => {
    const hashes = row.initial_sha256[key];
    return `<h3>${runName[key]}</h3>${hashBlock('result.json', row[key].result_sha256)}${hashBlock('states.json', row[key].states_sha256)}${hashBlock('初始任务文字', hashes.task_language)}${Object.entries(hashes.rgb).map(([camera, value]) => hashBlock(`初始 RGB · ${camera}`, value)).join('')}${Object.entries(hashes.camera_metadata).map(([camera, value]) => hashBlock(`初始 metadata · ${camera}`, value)).join('')}`;
  }).join('')}</details>`;
  $('episode-dialog').showModal();
}

function validate(loaded) {
  if (loaded.episodes.length !== 160 || new Set(loaded.episodes.map(row => `${row.split}/${row.task}/${row.seed}`)).size !== 160) throw new Error('明细数量或唯一性不符');
  const expected = {seen: [17, 27, 34], unseen: [10, 14, 21], all: [27, 41, 55]};
  for (const split of ['seen', 'unseen', 'all']) {
    const rows = loaded.episodes.filter(row => split === 'all' || row.split === split);
    const summary = loaded.summary[split];
    if (summary.total !== rows.length || rows.length !== (split === 'all' ? 160 : 80)) throw new Error('汇总数量与明细不符');
    for (const [index, run] of ['no_pose', 'combined', 'baseline'].entries()) {
      if (summary.successes[run] !== rows.filter(row => row[run].success).length || summary.successes[run] !== expected[split][index]) throw new Error('成功数与已发布统计不符');
    }
    for (const reference of ['combined', 'baseline']) {
      const paired = summary[`paired_${reference}`];
      const counts = [
        ['both_success', row => row.no_pose.success && row[reference].success],
        ['no_pose_only', row => row.no_pose.success && !row[reference].success],
        ['reference_only', row => !row.no_pose.success && row[reference].success],
        ['both_failure', row => !row.no_pose.success && !row[reference].success],
      ];
      for (const [key, predicate] of counts) if (paired[key] !== rows.filter(predicate).length) throw new Error('配对统计与明细不符');
    }
  }
  for (const split of ['seen', 'unseen']) {
    if (loaded.tasks[split].length !== 16) throw new Error('任务数量不符');
    for (const task of loaded.tasks[split]) {
      const seeds = loaded.episodes.filter(row => row.split === split && row.task === task).map(row => row.seed).sort((a, b) => a - b);
      if (seeds.join(',') !== '1,2,3,4,5') throw new Error('任务 seed 不完整');
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
    $('split').value = 'all'; $('reference').value = 'combined'; $('outcome').value = 'all';
    $('path').value = 'all'; $('search').value = ''; render();
  });
  renderSummaries();
  render();
}).catch(error => {
  $('status').classList.add('error');
  $('status').textContent = `明细加载失败（${error.message}）。可下载 CSV 或阅读文字报告。`;
});
