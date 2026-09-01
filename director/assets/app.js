"use strict";

const API = {
  async j(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error(`${r.status} ${(await r.text().catch(() => "")).slice(0, 180)}`);
    return r.json();
  },
  get(url) { return this.j(url); },
  post(url, body) { return this.j(url, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body || {})}); }
};
const $ = (s, root=document) => root.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const MEDIA = p => p ? `/api/media?path=${encodeURIComponent(p)}` : "";
const dirname = p => (p || "").split("/").slice(0,-1).join("/");
function toast(message, kind="info") { const el=document.createElement("div"); el.className=`toast ${kind}`; el.textContent=message; $("#toast-wrap").appendChild(el); setTimeout(()=>el.remove(), 4000); }

const S = {projects:[], activeProject:null, activeEpisode:null, episodeDoc:null, director:null, selectedShot:"", busy:false, comfy:"http://127.0.0.1:8188", generationTasks:{}, generationPolls:{}, generationStatusTimer:null, workflowPolls:{}};
const PLAN = [
  {id:"brief", label:"制作简案", detail:"从项目概念开始"},
  {id:"assets", label:"资产", detail:"角色与场景参考"},
  {id:"storyboard", label:"分镜图", detail:"镜头结构与提示词"},
  {id:"generate", label:"视频生成", detail:"调用 ComfyUI + H3"},
  {id:"final", label:"后期合成", detail:"成片与质量检查"}
];

function activeFolder() { return S.activeEpisode ? dirname(S.activeEpisode.path) : ""; }
function assetPath(p) {
  if (!p) return "";
  return p.replace(/^gen\/[^/]+\/card_/, `${activeFolder()}/references/card_`);
}
function episodeTitle(ep) { return ep ? (ep.name || ep.folder.split("/").pop()) : "选择一集开始"; }
function projectTitle() { return S.activeProject ? S.activeProject.name : "未选择项目"; }

async function loadWorkspace() {
  try {
    const result = await API.get("/api/projects");
    S.projects = (result.projects || []).map(p => typeof p === "string" ? {path:p,name:p,folder:dirname(p),episodes:[]} : p);
    const saved = localStorage.getItem("director-project");
    const project = S.projects.find(p => p.path === saved) || S.projects[0];
    if (project) await selectProject(project.path, false);
    else renderAll();
  } catch (e) { $("#project-library").innerHTML=`<div class="library-empty">项目读取失败<br>${esc(e.message)}</div>`; toast("项目读取失败", "bad"); }
}

async function selectProject(path, remember=true) {
  const project = S.projects.find(p => p.path === path);
  if (!project) return;
  S.activeProject = project;
  if (remember) localStorage.setItem("director-project", path);
  const savedEp = localStorage.getItem(`director-episode:${path}`);
  const ep = project.episodes?.find(e => e.path === savedEp) || project.episodes?.[0];
  S.activeEpisode = ep || null; S.episodeDoc = null; S.director = null; S.selectedShot = ""; S.busy=false; $("#btn-chat-send").disabled=false; setWorkflowStatus("");
  renderAll();
  if (ep) await loadEpisode(ep.path);
}

async function selectEpisode(path) {
  if (!S.activeProject) return;
  const ep = S.activeProject.episodes.find(e => e.path === path);
  if (!ep) return;
  S.activeEpisode = ep; S.episodeDoc = null; S.director = null; S.selectedShot = ""; S.busy=false; $("#btn-chat-send").disabled=false; setWorkflowStatus("");
  localStorage.setItem(`director-episode:${S.activeProject.path}`, path);
  renderAll();
  await loadEpisode(path);
}

async function loadEpisode(path) {
  try {
    S.episodeDoc = await API.get(`/api/project?path=${encodeURIComponent(path)}`);
    renderAll();
    // The hardware probe can be slow while ComfyUI is starting, so it never blocks the workspace shell.
    API.get(`/api/director?path=${encodeURIComponent(path)}`).then(d => {
      if (S.activeEpisode?.path === path) {
        S.director=d;
        // The backend is the source of truth. This also repairs stale browser
        // settings left over from the old local 127.0.0.1:8188 setup.
        if (d.comfy?.base) {
          S.comfy=d.comfy.base;
          localStorage.setItem("director-comfy", S.comfy);
          const input=$("#cfg-comfy"); if (input) input.value=S.comfy;
        }
        renderAll();
      }
    }).catch(e => console.warn(e));
  } catch (e) { toast("集数读取失败: " + e.message, "bad"); }
}

function renderProjectLibrary() {
  const root=$("#project-library");
  if (!S.projects.length) { root.innerHTML='<div class="library-empty">还没有项目<br>点击“开始创作”建立第一个项目</div>'; return; }
  root.innerHTML=S.projects.map(p => {
    const active=S.activeProject?.path === p.path;
    const episodes=(p.episodes || []).map(ep => `<button class="episode-row ${S.activeEpisode?.path===ep.path?"selected":""}" data-episode="${esc(ep.path)}"><span class="episode-pin"></span><span class="episode-copy"><span class="episode-name">${esc(ep.name)}</span><span class="episode-info">${ep.shots || 0} 个镜头 · ${ep.duration_s || 0}s</span></span></button>`).join("");
    return `<div class="project-item"><button class="project-row ${active?"selected":""}" data-project="${esc(p.path)}"><span class="project-chevron">${active?"⌄":"›"}</span><span class="project-folder">◆</span><span>${esc(p.name)}</span><span class="project-meta">${p.episodes?.length || 0} 集</span></button>${active?`<div class="episode-list">${episodes || '<div class="library-empty">暂无集数</div>'}</div>`:""}</div>`;
  }).join("");
  root.querySelectorAll("[data-project]").forEach(el => el.onclick=()=>selectProject(el.dataset.project));
  root.querySelectorAll("[data-episode]").forEach(el => { el.onclick=e=>{e.stopPropagation();selectEpisode(el.dataset.episode);}; });
}

function renderCanvas() {
  const projectName=$("#canvas-project-name"), episodeName=$("#canvas-episode-name"), stage=$("#canvas-stage");
  projectName.textContent=projectTitle(); episodeName.textContent=episodeTitle(S.activeEpisode);
  if (!S.episodeDoc || !S.activeEpisode) { stage.innerHTML='<div class="canvas-empty">选择左侧项目中的一集</div>'; return; }
  const d=S.episodeDoc, chars=d.characters || [], scenes=d.scenes || [], shots=d.shots || [];
  const assets=chars.map(c => `<div class="asset-tile">${c.image_path?`<img src="${MEDIA(assetPath(c.image_path))}" alt="${esc(c.name)}">`:'<div class="asset-missing">缺少参考图</div>'}<span>${esc(c.name)}</span></div>`).join("");
  const sceneAssets=scenes.map(s => `<div class="asset-tile">${s.image_path?`<img src="${MEDIA(assetPath(s.image_path))}" alt="${esc(s.name)}">`:'<div class="asset-missing">缺少场景图</div>'}<span>${esc(s.name)}</span></div>`).join("");
  const cards=shots.map(s => `<article class="shot-card ${S.selectedShot===s.shot_id?"selected":""}" data-shot="${esc(s.shot_id)}"><div class="shot-top"><span class="shot-id">${esc(s.shot_id)}</span><span class="shot-mode">${esc(s.mode || "H3")}</span><span class="shot-time">${s.duration_s || 0}s</span></div><p class="shot-desc">${esc(s.shot_description || "等待填写镜头描述")}</p><div class="shot-foot"><span>钩子：${esc(s.hook_type || "未设定")}</span><span>剪辑点：${s.edit_target_s || 0}s</span></div></article>`).join("");
  stage.innerHTML=`<div class="canvas-grid"><article class="story-card"><div class="card-kicker"><span class="doc-symbol">▤</span><span>项目简案 · ${esc(S.activeEpisode.folder.split("/").pop())}</span></div><h1>${esc(d.title || episodeTitle(S.activeEpisode))}</h1><p class="story-summary">${esc(d.what_if || "还没有填写故事概念。")}</p><div class="story-facts"><span class="fact"><b>目标情绪</b>${esc(d.target_feeling || "待填写")}</span><span class="fact"><b>时长</b>${d.duration_s || 0}s</span><span class="fact"><b>画幅</b>${esc(d.aspect || "9:16")}</span><span class="fact"><b>对白</b>${esc(d.dialogue_mode || "未指定")}</span></div></article><section class="asset-board"><div class="section-head"><h3>资产参考</h3><span>${chars.length+scenes.length} 项</span></div><div class="asset-grid">${assets}${sceneAssets || (!assets?'<div class="library-empty">暂无资产</div>':"")}</div></section><section class="shot-board"><div class="section-head"><h3>分镜表</h3><span>${shots.length} 个镜头</span></div>${cards || '<div class="library-empty">暂无分镜</div>'}</section></div>`;
  stage.querySelectorAll("[data-shot]").forEach(el=>el.onclick=()=>{S.selectedShot=el.dataset.shot; renderCanvas();});
}

function getOutputFiles() { return S.director?.output_dir ? (S.director.output_dir + " files") : ""; }
function planDone(id) {
  const d=S.episodeDoc, p=S.director?.progress?.stages || {};
  if (!d) return false;
  if (id === "brief") return Boolean(d.what_if && d.target_feeling);
  if (id === "assets") return Boolean((d.characters?.length || 0) + (d.scenes?.length || 0));
  if (id === "storyboard") return Boolean(d.shots?.length) && (p.check === "done" || !S.director);
  if (id === "generate") return p.gen === "done";
  if (id === "final") return p.final === "done";
  return false;
}
function currentPlanIndex() { for (let i=0;i<PLAN.length;i++) if (!planDone(PLAN[i].id)) return i; return PLAN.length-1; }
function renderPlan() {
  const done=PLAN.filter(p=>planDone(p.id)).length, idx=currentPlanIndex(), current=PLAN[idx];
  $("#plan-count").textContent=`${done}/5`; $("#plan-current").textContent=current ? `· ${current.label}` : "· 已完成"; $("#plan-state").textContent=done===5?"已完成":"进行中";
  $("#plan-list").innerHTML=PLAN.map((p,i)=>`<button class="plan-item ${i===idx?"current":""} ${planDone(p.id)?"done":""}" data-plan="${p.id}"><span class="plan-check">${planDone(p.id)?"✓":""}</span><span class="plan-label">${p.label}</span><span class="plan-meta">${planDone(p.id)?"已完成":p.detail}</span><span class="plan-open">›</span></button>`).join("");
  $("#plan-list").querySelectorAll("[data-plan]").forEach(el=>el.onclick=()=>openStage(el.dataset.plan));
}
function renderConversation() {
  const root=$("#conversation-content");
  if (!S.episodeDoc) { root.innerHTML='<div class="chat-placeholder">选择一个项目集数，开始查看制作内容。</div>'; return; }
  const d=S.episodeDoc, shot=S.selectedShot ? d.shots?.find(s=>s.shot_id===S.selectedShot) : d.shots?.[0];
  root.innerHTML=`<div class="chat-intro"><strong>请确认当前集数的制作内容。</strong><br><span class="muted">项目切换后，简案、资产、分镜和生成目录都会跟随当前集数变化。</span></div><div class="chat-block"><b>${esc(d.title || "当前集数")}</b><br>${esc(d.target_feeling || "尚未设置目标情绪")} · ${d.shots?.length || 0} 个镜头</div>${shot?`<div class="chat-block"><b>当前镜头 ${esc(shot.shot_id)}</b><br>${esc(shot.shot_description || "等待镜头描述")}</div>`:""}`;
}
function renderAll() { renderProjectLibrary(); renderCanvas(); renderPlan(); renderConversation(); $("#right-project-title").textContent=projectTitle(); $("#right-episode-title").textContent=episodeTitle(S.activeEpisode); }

function openStage(id) {
  if (!S.episodeDoc) { toast("请先选择一集", "bad"); return; }
  const plan=PLAN.find(p=>p.id===id) || PLAN[0]; $("#modal-kicker").textContent=plan.label; $("#modal-title").textContent=episodeTitle(S.activeEpisode);
  const d=S.episodeDoc, body=$("#modal-body");
  if (id === "brief") body.innerHTML=`<div class="chat-block"><b>故事概念</b><br>${esc(d.what_if || "待填写")}</div><div class="chat-block"><b>目标情绪</b><br>${esc(d.target_feeling || "待填写")}</div><div class="chat-block"><b>视觉风格</b><br>${esc(d.visual_style || "待填写")}</div>`;
  else if (id === "assets") { const items=[...(d.characters||[]).map(c=>({name:c.name,path:c.image_path})),...(d.scenes||[]).map(s=>({name:s.name,path:s.image_path}))]; body.innerHTML=items.length?`<div class="modal-assets">${items.map(x=>x.path?`<div><img src="${MEDIA(assetPath(x.path))}" alt="${esc(x.name)}"><p class="form-note">${esc(x.name)}</p></div>`:`<div class="asset-missing">无参考图<div>${esc(x.name)}</div></div>`).join("")}</div>`:'<div class="library-empty">当前集数还没有角色或场景资产。</div>'; }
  else if (id === "storyboard") body.innerHTML=`<div class="modal-shot-list">${(d.shots||[]).map(s=>`<div class="modal-shot"><b>${esc(s.shot_id)}</b> · ${s.duration_s||0}s · ${esc(s.mode||"H3")}<br>${esc(s.shot_description||"暂无描述")}<br><span class="form-note">提示词文件位于 ${esc(activeFolder())}/prompts</span></div>`).join("")}</div><div class="modal-action"><button class="primary-button" id="run-prompts">重新编译本集提示词</button><span id="stage-message" class="form-note"></span></div>`;
  else if (id === "generate") body.innerHTML=`<div class="chat-block">当前 ComfyUI：<b>${esc(S.comfy)}</b><br><strong class="generation-summary" data-generation-summary>正在读取本集任务…</strong><br>任务会在后台运行，下面显示阶段进度、耗时和最新日志；生成完成后可直接在对应镜头下预览。</div><div class="modal-shot-list">${(d.shots||[]).map(s=>`<div class="modal-shot generation-row"><div class="generation-copy"><b>${esc(s.shot_id)}</b> · ${esc((s.shot_description||"").slice(0,150))}<span class="generation-status" data-shot-status="${esc(s.shot_id)}">等待提交</span><div class="generation-meter"><i data-shot-progress="${esc(s.shot_id)}"></i></div><span class="generation-meta" data-shot-meta="${esc(s.shot_id)}">尚未提交</span><details class="generation-details"><summary>查看日志</summary><pre data-shot-log="${esc(s.shot_id)}">暂无日志</pre></details><div class="generation-preview" data-shot-preview="${esc(s.shot_id)}"></div></div><button class="primary-button" style="padding:6px 10px;font-size:11px;flex:none" data-generate="${esc(s.shot_id)}">生成</button></div>`).join("")}</div>`;
  else body.innerHTML=`<div class="chat-block">后期合成会读取当前集数的独立 outputs 目录。完成所有镜头后，可以在这里继续装配和查看成片。</div><button class="primary-button" id="refresh-state">刷新生成状态</button><div class="form-note" id="stage-message">${esc(getOutputFiles())}</div><div id="output-preview" class="modal-shot-list" style="margin-top:14px"><div class="form-note">正在读取当前集视频…</div></div>`;
  $("#stage-mask").classList.add("open");
  const promptBtn=$("#run-prompts"); if(promptBtn) promptBtn.onclick=async()=>{promptBtn.disabled=true;try{await API.get(`/api/stage/prompts?path=${encodeURIComponent(S.activeEpisode.path)}`);$("#stage-message").textContent="提示词已写入当前集 prompts 目录";toast("提示词编译完成","ok");}catch(e){$("#stage-message").textContent=e.message;}finally{promptBtn.disabled=false;}};
  body.querySelectorAll("[data-generate]").forEach(btn=>btn.onclick=()=>generateShot(btn.dataset.generate,btn));
  const refresh=$("#refresh-state"); if(refresh) refresh.onclick=()=>loadEpisode(S.activeEpisode.path);
  if (id === "generate") { syncGenerationStatus(); clearInterval(S.generationStatusTimer); S.generationStatusTimer=setInterval(()=>{ if (!$("#stage-mask").classList.contains("open")) { clearInterval(S.generationStatusTimer); S.generationStatusTimer=null; return; } syncGenerationStatus(); },5000); }
  if (id === "final") loadOutputPreview();
}
function generationKey(shotId, episodePath=S.activeEpisode?.path || "") { return `${episodePath}::${shotId}`; }
function setGenerationTask(shotId, task) { S.generationTasks[generationKey(shotId)] = task; }
function elapsedText(started) { if (!started) return ""; const seconds=Math.max(0,Math.floor(Date.now()/1000-started)); return `${Math.floor(seconds/60)}分${String(seconds%60).padStart(2,"0")}秒`; }
function updateGenerationRow(shotId) {
  const statusEl=document.querySelector(`[data-shot-status="${CSS.escape(shotId)}"]`);
  const btn=document.querySelector(`[data-generate="${CSS.escape(shotId)}"]`);
  const progressEl=document.querySelector(`[data-shot-progress="${CSS.escape(shotId)}"]`), metaEl=document.querySelector(`[data-shot-meta="${CSS.escape(shotId)}"]`), logEl=document.querySelector(`[data-shot-log="${CSS.escape(shotId)}"]`);
  const previewEl=document.querySelector(`[data-shot-preview="${CSS.escape(shotId)}"]`);
  if (!statusEl || !btn) return;
  const task=S.generationTasks[generationKey(shotId)];
  if (!task) { statusEl.textContent="等待提交"; statusEl.className="generation-status"; if(progressEl)progressEl.style.width="0%"; if(metaEl)metaEl.textContent="尚未提交"; if(logEl)logEl.textContent="暂无日志"; if(previewEl)previewEl.innerHTML=""; btn.disabled=false; btn.textContent="生成"; return; }
  const progress=task.total ? ` ${task.cur || 0}/${task.total}` : "";
  const labels={running:task.pending ? "正在提交…" : (task.remote && !task.cur ? "ComfyUI 排队中" : (task.cur ? `H3 处理中${progress}…` : "已进入 ComfyUI 队列…")),done:"已完成，可播放",error:`失败：${task.error || "未知错误"}`};
  statusEl.textContent=labels[task.status] || "已提交，等待任务状态";
  statusEl.className=`generation-status ${task.status}`;
  if(progressEl) progressEl.style.width=`${task.total ? Math.min(100,Math.round((task.cur||0)/task.total*100)) : 0}%`;
  if(metaEl) { const queue=task.remote && task.queue_group === "queue_pending" && task.queue_position ? ` · 队列第 ${task.queue_position} 位` : ""; const elapsed=elapsedText(task.started); metaEl.textContent=`阶段 ${task.cur||0}/${task.total||3}${queue}${elapsed ? ` · 已耗时 ${elapsed}` : ""}`; }
  if(logEl) logEl.textContent=(task.log||[]).slice(-8).join("\n") || (task.remote ? "已从 ComfyUI 远端队列识别" : "等待后台日志");
  const outputPath=task.outputPath || task.result?.clip;
  if(previewEl) { if(task.status === "done" && outputPath) { previewEl.innerHTML=`<video class="generation-video" controls playsinline preload="metadata" src="${MEDIA(outputPath)}" title="点击播放或暂停 ${esc(shotId)} 预览"></video>`; const video=previewEl.querySelector("video"); video.onclick=()=>video.paused ? video.play() : video.pause(); } else if(task.status === "done") previewEl.innerHTML='<span class="generation-preview-note">已完成，正在准备预览…</span>'; else previewEl.innerHTML=""; }
  btn.disabled=task.status === "running";
  btn.textContent=task.status === "running" ? "生成中" : (task.status === "done" ? "重新生成" : "重试");
}
function updateGenerationSummary() {
  const el=document.querySelector("[data-generation-summary]"); if (!el) return;
  const shots=S.episodeDoc?.shots || [], tasks=shots.map(s=>S.generationTasks[generationKey(s.shot_id)]).filter(Boolean);
  const done=tasks.filter(t=>t.status === "done").length, running=tasks.filter(t=>t.status === "running" && !t.remote).length;
  const queued=tasks.filter(t=>t.status === "running" && t.remote && !t.cur).length, remoteRunning=tasks.filter(t=>t.status === "running" && t.remote && t.cur).length;
  el.textContent=`本集生成进度：已完成 ${done}/${shots.length} · 处理中 ${running+remoteRunning} · 排队 ${queued}`;
}
function updateAllGenerationRows() { (S.episodeDoc?.shots || []).forEach(s=>updateGenerationRow(s.shot_id)); updateGenerationSummary(); }
async function syncGenerationStatus() {
  if (!S.activeEpisode || !S.episodeDoc) return;
  try {
    const [fileResult, taskResult]=await Promise.all([
      API.get(`/api/files?path=${encodeURIComponent(activeFolder()+"/outputs")}`),
      API.get("/api/tasks")
    ]);
    const videos=new Map((fileResult.files||[]).filter(f=>f.kind==="vid").map(f=>[f.name.replace(/\.mp4$/i,""),f.path]));
    for (const shot of S.episodeDoc.shots || []) {
      const key=generationKey(shot.shot_id), remote=(taskResult.tasks||[]).find(t=>(t.path===S.activeEpisode.path && t.shot_id===shot.shot_id) || (!t.path && t.shot_id===shot.shot_id));
      if (remote && remote.status === "running") { setGenerationTask(shot.shot_id, remote); if (!remote.remote) startGenerationPoll(remote.id, shot.shot_id, S.activeEpisode.path); }
      else if (videos.has(shot.shot_id)) setGenerationTask(shot.shot_id, {status:"done",output:true,outputPath:videos.get(shot.shot_id)});
      else if (S.generationTasks[key]?.remote) setGenerationTask(shot.shot_id, {status:"error",error:"ComfyUI 队列中已无此任务，暂未发现本地视频"});
      else if (remote) setGenerationTask(shot.shot_id, remote);
      else if (!S.generationTasks[key]) delete S.generationTasks[key];
    }
    updateAllGenerationRows();
  } catch(e) { console.warn("generation status", e); }
}
async function loadOutputPreview() {
  const root=$("#output-preview"); if (!root) return;
  try {
    const r=await API.get(`/api/files?path=${encodeURIComponent(activeFolder()+"/outputs")}`);
    const videos=(r.files||[]).filter(f=>f.kind === "vid");
    root.innerHTML=videos.length ? videos.map(f=>`<div class="modal-shot"><b>${esc(f.name)}</b><br><video controls playsinline preload="metadata" style="width:min(260px,100%);margin-top:9px;border-radius:8px;background:#111" src="${MEDIA(f.path)}"></video></div>`).join("") : '<div class="form-note">当前集还没有可播放的视频。</div>';
  } catch(e) { root.innerHTML=`<div class="form-note">视频读取失败：${esc(e.message)}</div>`; }
}
async function generateShot(shotId, btn) {
  const key=generationKey(shotId), existing=S.generationTasks[key];
  if (existing?.status === "running") { toast(`${shotId} 正在生成中，请等待完成`, "info"); updateGenerationRow(shotId); if(existing.id) startGenerationPoll(existing.id, shotId, S.activeEpisode.path); return; }
  btn.disabled=true; btn.textContent="提交中"; setGenerationTask(shotId,{status:"running",pending:true}); updateGenerationRow(shotId);
  try {
    const r=await API.post("/api/stage/generate",{path:S.activeEpisode.path,shot_id:shotId,comfy:S.comfy});
    setGenerationTask(shotId,{id:r.task,status:"running",started:Date.now()/1000,log:[r.status === "existing" ? (r.message || "已在后台任务中") : "已提交到 ComfyUI"]}); updateGenerationRow(shotId);
    toast(r.status === "existing" ? `${shotId} 已在后台生成中` : `已提交 ${shotId} 到 ComfyUI`, "ok");
    if (r.task) startGenerationPoll(r.task, shotId, S.activeEpisode.path);
  } catch(e) { setGenerationTask(shotId,{status:"error",error:e.message}); updateGenerationRow(shotId); toast("提交失败: "+e.message,"bad"); }
}
function startGenerationPoll(id, shotId, episodePath=S.activeEpisode?.path || "") {
  const key=generationKey(shotId, episodePath);
  if (S.generationPolls[key] === id) return;
  S.generationPolls[key]=id;
  pollTask(id, shotId, episodePath);
}
async function pollTask(id, shotId, episodePath) {
  try {
    if (S.activeEpisode?.path !== episodePath) { delete S.generationPolls[generationKey(shotId, episodePath)]; return; }
    const t=await API.get(`/api/task/${id}`), current=S.generationTasks[generationKey(shotId, episodePath)];
    if (current?.id && current.id !== id) return;
    setGenerationTask(shotId,{...t,id}); updateGenerationRow(shotId);
    if(t.status === "done"){delete S.generationPolls[generationKey(shotId, episodePath)];toast(`${shotId} 生成完成，可在后期合成播放`,"ok");loadEpisode(episodePath);return;}
    if(t.status === "error"){delete S.generationPolls[generationKey(shotId, episodePath)];toast(`${shotId} 生成失败: `+(t.error||"未知错误"),"bad");return;}
    setTimeout(()=>pollTask(id,shotId,episodePath),2500);
  } catch(e){setTimeout(()=>pollTask(id,shotId,episodePath),4000);}
}
function setWorkflowStatus(text, kind="running") { const el=$("#workflow-status"); if (!el) return; el.textContent=text || ""; el.className=`workflow-status ${kind}`; }
async function pollWorkflow(id, episodePath) {
  const key=`${episodePath}::${id}`;
  try {
    if (S.activeEpisode?.path !== episodePath) { delete S.workflowPolls[key]; return; }
    const t=await API.get(`/api/task/${id}`), progress=`${t.cur || 0}/${t.total || 5}`;
    const latest=(t.log || []).slice(-1)[0] || (t.status === "running" ? "正在处理…" : "任务已结束");
    if (t.status === "running") setWorkflowStatus(`自动创作 ${progress} · ${latest}`, "running");
    if (t.status === "done") {
      delete S.workflowPolls[key]; S.busy=false; $("#btn-chat-send").disabled=false;
      const passed=t.result?.check?.pass;
      setWorkflowStatus(`自动创作完成 · ${t.result?.prompts || 0} 个提示词${passed === false ? " · 有规则待修复" : " · 可进入视频生成"}`, passed === false ? "warn" : "done");
      toast(passed === false ? "规划完成，但有分镜规则待修复" : "简案、资产、分镜和提示词已完成", passed === false ? "info" : "ok");
      await loadEpisode(episodePath);
      return;
    }
    if (t.status === "error") {
      delete S.workflowPolls[key]; S.busy=false; $("#btn-chat-send").disabled=false;
      setWorkflowStatus(`自动创作失败 · ${t.error || latest}`, "error"); toast("自动创作失败: "+(t.error || latest), "bad"); return;
    }
    setTimeout(()=>pollWorkflow(id, episodePath), 1800);
  } catch(e) { setTimeout(()=>pollWorkflow(id, episodePath), 3000); }
}
async function sendChat() {
  const input=$("#chat-input"), feedback=input.value.trim();
  if(!feedback||!S.activeEpisode||S.busy){if(!S.activeEpisode) toast("请先选择一集","bad");return;}
  const episodePath=S.activeEpisode.path; S.busy=true; $("#btn-chat-send").disabled=true; setWorkflowStatus("正在提交自动创作任务…", "running");
  try {
    const r=await API.post("/api/chat/workflow",{path:episodePath,mode:"auto",feedback});
    if(r.error) throw new Error(r.error);
    input.value=""; toast(r.status === "existing" ? "当前集已有自动创作任务，继续显示进度" : "已提交自动创作任务", "ok");
    if (r.task) { S.workflowPolls[`${episodePath}::${r.task}`]=true; pollWorkflow(r.task, episodePath); }
    else { S.busy=false; $("#btn-chat-send").disabled=false; setWorkflowStatus(r.message || "任务已提交", "running"); }
  } catch(e) { S.busy=false; $("#btn-chat-send").disabled=false; setWorkflowStatus("提交失败 · "+e.message, "error"); toast("自动创作失败: "+e.message,"bad"); }
}

function bindUi() {
  $("#btn-new-project").onclick=()=>$("#new-mask").classList.add("open"); $("#new-close").onclick=()=>$("#new-mask").classList.remove("open");
  $("#btn-refresh-projects").onclick=()=>loadWorkspace(); $("#btn-project-library").onclick=()=>$("#project-library").scrollTo({top:0,behavior:"smooth"});
  $("#btn-skill").onclick=()=>{openUtility("Skill", "Skill 入口保留在工作台侧栏。后续可在这里挂载剧本检查、资产锁定和批处理能力。")}; $("#btn-comfy-flow").onclick=()=>openUtility("ComfyUI 工作流", `当前连接地址：${S.comfy}\n\n导演台运行在 5800H，ComfyUI/H3 可以运行在局域网 GPU 主机。`);
  $("#btn-config").onclick=()=>$("#config-mask").classList.add("open"); $("#config-close").onclick=()=>$("#config-mask").classList.remove("open"); $("#config-save").onclick=()=>{S.comfy=$("#cfg-comfy").value.trim()||S.comfy;localStorage.setItem("director-comfy",S.comfy);$("#config-mask").classList.remove("open");toast("连接配置已保存","ok");};
  $("#modal-close").onclick=()=>$("#stage-mask").classList.remove("open"); ["#stage-mask","#new-mask","#config-mask"].forEach(s=>$(s).addEventListener("click",e=>{if(e.target===$(s))$(s).classList.remove("open");})); $("#new-create").onclick=createProject; $("#btn-chat-send").onclick=sendChat; $("#chat-input").addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key==="Enter")sendChat();});
  S.comfy=localStorage.getItem("director-comfy")||S.comfy;$("#cfg-comfy").value=S.comfy;
}
function openUtility(title,text){$("#modal-kicker").textContent="工作台工具";$("#modal-title").textContent=title;$("#modal-body").innerHTML=`<div class="chat-block" style="white-space:pre-line">${esc(text)}</div>`;$("#stage-mask").classList.add("open");}
async function createProject(){const name=$("#new-name").value.trim();if(!name){toast("请填写项目名称","bad");return;}const btn=$("#new-create");btn.disabled=true;try{const r=await API.post("/api/project/new",{name,template:$("#new-template").value});$("#new-mask").classList.remove("open");await loadWorkspace();const p=S.projects.find(x=>x.folder===r.dir);if(p)await selectProject(p.path);toast("项目已创建","ok");}catch(e){toast("创建失败: "+e.message,"bad");}finally{btn.disabled=false;}}
async function checkComfy(){try{const h=await API.get("/api/hardware");if(h.base){S.comfy=h.base;localStorage.setItem("director-comfy",S.comfy);const input=$("#cfg-comfy");if(input)input.value=S.comfy;}const online=h.online;$("#comfy-dot").className=`status-dot ${online?"on":"off"}`;$("#comfy-label").textContent=online?"ComfyUI 在线":"ComfyUI 离线";}catch(e){$("#comfy-label").textContent="ComfyUI 未知";}}
bindUi(); renderAll(); loadWorkspace(); checkComfy();
