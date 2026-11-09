'use strict';
const $ = id => document.getElementById(id);
const splitName = {seen:'Seen', unseen:'Unseen', all:'总计'};
const mark = value => value ? '✓' : '×';
const outcome = value => value ? '成功' : '失败';
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data;
function differs(row) {return row.initial_robot_state_max_abs_diff > 1e-6 || !row.initial_task_language_equal;}
function matches(row) {
  const mode = $('outcome').value;
  return mode === 'all' || mode === 'success' && row.nomemory_success
    || mode === 'baseline_only' && row.baseline_success && !row.nomemory_success
    || mode === 'nomemory_only' && !row.baseline_success && row.nomemory_success
    || mode === 'both' && row.baseline_success && row.nomemory_success
    || mode === 'neither' && !row.baseline_success && !row.nomemory_success;
}
function render() {
  const query = $('search').value.trim().toLowerCase(), selected = $('split').value;
  let count = 0, cells = 0;
  const tables = [];
  for (const split of ['seen','unseen']) {
    if (selected !== 'all' && selected !== split) continue;
    const rows = [];
    for (const task of data.tasks[split]) {
      if (!task.toLowerCase().includes(query)) continue;
      const episodes = data.episodes.filter(r => r.split === split && r.task === task);
      if (!episodes.some(matches)) continue;
      count++;
      const b = episodes.filter(r => r.baseline_success).length, n = episodes.filter(r => r.nomemory_success).length;
      const seedCells = episodes.map(row => {
        if (!matches(row)) return '<td><span class="muted-cell">已筛除</span></td>';
        cells++;
        const css = row.baseline_success === row.nomemory_success ? '' : row.nomemory_success ? 'gain' : 'loss';
        const label = `${task}, seed ${row.seed}: baseline ${outcome(row.baseline_success)}, NoMemory ${outcome(row.nomemory_success)}${differs(row) ? '，初态或任务文本存在差异' : ''}`;
        return `<td><button type="button" class="seed ${css}" data-episode="${data.episodes.indexOf(row)}" aria-label="${escapeHTML(label)}">${mark(row.baseline_success)} → ${mark(row.nomemory_success)}${differs(row) ? ' *' : ''}</button></td>`;
      }).join('');
      rows.push(`<tr><th scope="row">${escapeHTML(task)}</th><td class="task-count">${b}/5 → ${n}/5</td><td class="${n>b?'delta-positive':n<b?'delta-negative':''}">${n>b?'+':''}${n-b}</td>${seedCells}</tr>`);
    }
    if (rows.length) tables.push(`<h3>${splitName[split]}</h3><div class="table-wrap" tabindex="0" role="region" aria-label="${splitName[split]} 逐任务结果"><table class="seed-table"><thead><tr><th>任务</th><th>Baseline → NoMemory</th><th>差值</th>${[1,2,3,4,5].map(s=>`<th>Seed ${s}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`);
  }
  $('task-tables').innerHTML = tables.join('') || '<p>没有符合筛选条件的 episode。</p>';
  $('status').textContent = `显示 ${count} 个任务、${cells} / 160 对运行。筛选不改变完整实验统计或每个任务的 5 局成功数。`;
}
function showEpisode(row) {
  $('episode-title').textContent = `${splitName[row.split]} · ${row.task} · seed ${row.seed}`;
  const fields = [['原生结果','success',outcome], ['耗时','elapsed_s',v=>`${(v/60).toFixed(1)} 分钟`], ['结束原因','termination_reason',v=>v==='completed'?'正常结束':'Planner 超时'], ['末条观测 success','final_native_success',String]];
  $('episode-content').innerHTML = `<div class="table-wrap"><table><thead><tr><th>记录</th><th>Baseline</th><th>NoMemory</th></tr></thead><tbody>${fields.map(([name,key,fn])=>`<tr><th scope="row">${name}</th><td>${escapeHTML(fn(row[`baseline_${key}`]))}</td><td>${escapeHTML(fn(row[`nomemory_${key}`]))}</td></tr>`).join('')}</tbody></table></div>
  <p>初始机器人状态最大绝对差：<code>${row.initial_robot_state_max_abs_diff.toExponential(4)}</code>；任务文本${row.initial_task_language_equal?'相同':'不同'}。</p><p class="note">仅比较保存的机器人状态和任务文本，未验证全部场景物体或 VLA 动作采样一致。耗时也受 API 与调度影响。</p><details><summary>结果与状态文件 SHA-256</summary>${['baseline','nomemory'].map(name=>`<h3>${name==='baseline'?'Baseline':'NoMemory'}</h3>${['result','states'].map(kind=>`<p>${kind}.json<code class="hash">${escapeHTML(row[`${name}_${kind}_sha256`])}</code></p>`).join('')}`).join('')}</details>`;
  $('episode-dialog').showModal();
}
$('close-dialog').addEventListener('click',()=> $('episode-dialog').close());
$('task-tables').addEventListener('click',event=>{const button=event.target.closest('button[data-episode]');if(button)showEpisode(data.episodes[Number(button.dataset.episode)]);});
fetch('data.json').then(response=>{if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json();}).then(loaded=>{
  data=loaded;
  if(data.episodes.length!==160 || new Set(data.episodes.map(r=>`${r.split}/${r.task}/${r.seed}`)).size!==160)throw new Error('明细数量或唯一性不符');
  for(const split of ['seen','unseen','all']){const rows=data.episodes.filter(r=>split==='all'||r.split===split),s=data.summary[split];if(s.total!==rows.length||s.baseline_success!==rows.filter(r=>r.baseline_success).length||s.nomemory_success!==rows.filter(r=>r.nomemory_success).length)throw new Error('汇总与明细不符');}
  $('paired-body').innerHTML=['seen','unseen','all'].map(split=>{const s=data.summary[split];return `<tr><th scope="row">${splitName[split]}</th><td>${s.both_success}</td><td>${s.baseline_only}</td><td>${s.nomemory_only}</td><td>${s.neither}</td></tr>`;}).join('');
  $('generated').textContent=data.generated_utc;
  for(const id of ['split','outcome'])$(id).addEventListener('change',render);
  $('search').addEventListener('input',render);
  $('reset').addEventListener('click',()=>{$('split').value='all';$('outcome').value='all';$('search').value='';render();});
  render();
}).catch(error=>{$('status').classList.add('error');$('status').textContent=`明细加载失败（${error.message}）。可下载 CSV 或阅读文字报告。`;});
