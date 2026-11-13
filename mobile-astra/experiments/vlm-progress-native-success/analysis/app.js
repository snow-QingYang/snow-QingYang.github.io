'use strict';
const $ = id => document.getElementById(id);
const names = {current: 'E10', baseline: 'E01 baseline', no_progress: 'E03 无进度'};
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data;

function showEpisode(index) {
  const row = data.episodes[index], ref = $('reference').value;
  const current = row.current;
  $('detail').hidden = false;
  $('detail-title').textContent = `${row.task} · seed ${row.seed}`;
  $('detail-body').innerHTML = `<p>${names.current}：<strong>${current.success ? '成功' : '失败'}</strong>；${names[ref]}：${row[ref].success ? '成功' : '失败'}。</p>
    <dl class="record"><dt>终态视觉判断</dt><dd>${escapeHTML(current.visual_completion)}</dd>
    <dt>Agent finish</dt><dd>${escapeHTML(current.finish_status || '未调用')}</dd>
    <dt>动作与耗时</dt><dd>VLA ${current.vla_calls} 次，其他动作 ${current.manual_calls} 次；${current.elapsed_s.toFixed(1)} 秒</dd>
    <dt>VLM 请求</dt><dd>${current.judge_calls} 次；请求前取消 ${current.cancelled_judgments} 次</dd>
    <dt>成功后的动作</dt><dd>${current.actions_after_first_success ?? '未记录原生成功'}</dd>
    <dt>原生结果 SHA-256</dt><dd><code>${escapeHTML(current.result_sha256)}</code></dd></dl>
    <p><a href="episodes/${encodeURIComponent(row.task)}_s${row.seed}.json" download>下载本局配对记录 JSON</a> · <a href="../#downloads">完整审计包</a></p>
    <p class="note">配对按任务和 seed 对齐；本次导出未完整核验对照组初态一致性，也未固定 VLA 随机采样。</p>`;
  $('detail').scrollIntoView({behavior: 'smooth', block: 'nearest'});
}

function render() {
  const ref = $('reference').value, split = $('split').value;
  const query = $('task').value.trim().toLowerCase();
  const mode = $('outcome').value, visual = $('visual').value;
  let visible = 0;
  const matches = row => (!split || row.split === split) && (!query || row.task.toLowerCase().includes(query))
    && (!visual || row.current.visual_completion === visual)
    && (!mode || (mode === 'success' && row.current.success) || (mode === 'failure' && !row.current.success)
        || (mode === 'gain' && row.current.success && !row[ref].success)
        || (mode === 'loss' && !row.current.success && row[ref].success));
  let html = '';
  for (const group of ['seen', 'unseen']) {
    if (split && split !== group) continue;
    const rows = [];
    for (const task of data.tasks[group]) {
      const episodes = data.episodes.filter(row => row.split === group && row.task === task);
      if (!episodes.some(matches)) continue;
      const before = episodes.filter(row => row[ref].success).length;
      const after = episodes.filter(row => row.current.success).length;
      const cells = episodes.map(row => {
        if (!matches(row)) return '<td class="muted-cell">已筛除</td>';
        visible++;
        const a = row[ref].success, b = row.current.success;
        const status = a === b ? '' : b ? 'gain' : 'loss';
        const title = `${task} seed ${row.seed}，${names[ref]} ${a ? '成功' : '失败'}，E10 ${b ? '成功' : '失败'}`;
        return `<td><button class="seed ${status}" type="button" data-episode="${data.episodes.indexOf(row)}" aria-label="${escapeHTML(title)}">${a ? '✓' : '×'} → ${b ? '✓' : '×'}</button></td>`;
      }).join('');
      rows.push(`<tr><th scope="row">${escapeHTML(task)}</th><td>${before}/5 → ${after}/5</td>${cells}</tr>`);
    }
    if (rows.length) html += `<h3>${group === 'seen' ? 'Seen' : 'Unseen'}</h3><div class="table-wrap"><table><thead><tr><th>任务</th><th>${escapeHTML(names[ref])} → E10</th>${[1,2,3,4,5].map(seed => `<th>Seed ${seed}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  }
  $('task-tables').innerHTML = html || '<p>没有符合条件的 episode。</p>';
  $('status').textContent = `显示 ${visible} / 160 对运行。单元格为对照组 → E10；筛选不改变完整统计。`;
  $('paired').innerHTML = `<div class="table-wrap"><table><thead><tr><th>任务组</th><th>两组成功</th><th>仅 E10 成功</th><th>仅对照成功</th><th>两组失败</th></tr></thead><tbody>${['seen','unseen','all'].map(group => {
    const p = data.summary[group].paired[ref];
    return `<tr><th>${group === 'all' ? '总计' : group}</th><td>${p.both_success}</td><td>${p.current_only}</td><td>${p.reference_only}</td><td>${p.both_failure}</td></tr>`;
  }).join('')}</tbody></table></div>`;
  $('detail').hidden = true;
}

fetch('data.json').then(response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}).then(value => {
  data = value;
  for (const id of ['reference', 'split', 'task', 'outcome', 'visual']) $(id).addEventListener('input', render);
  $('task-tables').addEventListener('click', event => {
    const button = event.target.closest('[data-episode]');
    if (button) showEpisode(Number(button.dataset.episode));
  });
  $('close-detail').addEventListener('click', () => { $('detail').hidden = true; });
  render();
}).catch(error => {
  $('status').textContent = `数据加载失败：${error.message}。可直接下载 CSV 或 JSON。`;
});
