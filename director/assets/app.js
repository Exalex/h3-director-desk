/* ============ 导演台 app.js — 核心框架 ============ */
"use strict";

const API = {
  async j(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) {
      const t = await r.text().catch(() => "");
      throw new Error(`${r.status} ${t.slice(0, 200)}`);
    }
    return r.json();
  },
  get(u) { return this.j(u); },
  post(u, body) {
    return this.j(u, { method: "POST", headers: { "Content-Type": "application/json" },
                       body: JSON.stringify(body || {}) });
  },
};

// media path -> absolute browser URL
const MEDIA = (p) => p ? `/api/media?path=${encodeURIComponent(p)}` : "";

const $ = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function toast(msg, kind = "info") {
  const w = $("#toast-wrap");
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = msg;
  w.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

/* ---------------- global state ---------------- */
const S = {
  director: null,     // /api/director payload (summary etc.)
  projectPath: "projects/odyssey/ep01.json",
  activeStage: "bible",
  progress: null,   // per-stage readiness + next-step advice
  config: { comfy: "http://127.0.0.1:8188" },
};

/* ---------------- stage registry ---------------- */
const STAGES = [
  { id: "bible",   num: "01", name: "设定 · Bible",      stateOf: () => p("bible") },
  { id: "board",   num: "02", name: "分镜表 · Board",    stateOf: () => S.director && S.director.summary ? `×${S.director.summary.n_shots}` : "" },
  { id: "check",   num: "03", name: "自检 · Check",      stateOf: () => p("check") },
  { id: "cards",   num: "04", name: "角色卡 · Cards",    stateOf: () => p("cards") },
  { id: "scene",   num: "05", name: "场景卡 · Scene",    stateOf: () => p("scene") },
  { id: "prompts", num: "06", name: "提示词 · Prompts",  stateOf: () => p("prompts") },
  { id: "deploy",  num: "07", name: "部署 · ComfyUI",    stateOf: () => p("deploy") },
  { id: "gen",     num: "08", name: "生成 · Generate",   stateOf: () => p("gen") },
  { id: "qc",      num: "09", name: "质检 · QC",         stateOf: () => p("qc") },
  { id: "final",   num: "10", name: "成片 · Assemble",   stateOf: () => p("final") },
];
const STAGE_RENDER = {};   // id -> fn(bodyEl)
const STATECH = { done: "✓", warn: "!", pending: "" };
function p(id) { return (S.progress && S.progress.stages) ? (S.progress.stages[id] || "pending") : "pending"; }

/* ---------------- nav ---------------- */
function buildNav() {
  const nav = $("#stages");
  nav.innerHTML = "";
  for (const st of STAGES) {
    const el = document.createElement("div");
    el.className = "stage" + (st.id === S.activeStage ? " active" : "");
    el.dataset.id = st.id;
    const stt = st.stateOf();
    const mark = stt === "done" ? '<span class="s-state pass">✓</span>'
                : stt === "warn" ? '<span class="s-state fail">!</span>' : "";
    el.innerHTML = `<span class="s-num">${st.num}</span>
                    <span class="s-name">${st.name}</span>${mark}`;
    el.onclick = () => go(st.id);
    nav.appendChild(el);
  }
  renderAdvice();
}

// Jellyfish-style single next-step CTA + progress dots
function renderAdvice() {
  const bar = $("#advice-bar"), body = $("#advice-body");
  if (!body) return;
  if (!S.progress) { bar.style.display = "none"; return; }
  bar.style.display = "";
  const seq = ["bible","board","check","cards","scene","prompts","deploy","gen","qc","final"];
  const dots = seq.map(s => `<span class="ap ${p(s)}" title="${s}"></span>`).join("");
  const a = S.progress.advice || { target: "", label: "就绪", note: "" };
  body.innerHTML = `
    <div class="advice-prog">${dots}</div>
    <div class="advice-btns">
      <button class="btn-sm" id="advice-go">${esc(a.label || "下一步")}</button>
      <span class="advice-note">${esc(a.note || "")}</span>
    </div>`;
  $("#advice-go").onclick = () => { if (a.target && STAGE_RENDER[a.target]) go(a.target); };
}

async function go(id) {
  S.activeStage = id;
  $$(".stage").forEach(e => e.classList.toggle("active", e.dataset.id === id));
  const st = STAGES.find(x => x.id === id);
  $("#stage-badge").textContent = st.num;
  $("#stage-title").textContent = st.name.replace(/^.*?·\s*/, "");
  const body = $("#stage-body");
  body.innerHTML = `<div class="empty">载入 ${st.name} …</div>`;
  try {
    if (STAGE_RENDER[id]) {
      await STAGE_RENDER[id](body);
    } else {
      body.innerHTML = `<div class="empty">「${st.name}」尚未实现。</div>`;
    }
  } catch (e) {
    console.error(e);
    body.innerHTML = `<div class="empty" style="color:var(--bad)">载入失败: ${esc(e.message)}</div>`;
  }
}

function pbody() { return $("#stage-body"); }

/* ---------------- header actions ---------------- */
function setActions(html) { $("#work-actions").innerHTML = html; }

/* ---------------- monitor ---------------- */
let MON_TAB = "chars";
async function refreshMonitor() {
  const panes = $("#mon-panes");
  const d = S.director;
  // video: pick final candidate
  const videoMap = window._finalVideo || "";
  const vid = $("#mon-video");
  if (videoMap) { vid.src = videoMap; vid.style.display = "block"; $("#empty-player").style.display = "none"; }
  else { vid.style.display = "none"; $("#empty-player").style.display = "flex"; }

  if (!d || !d.summary) { panes.innerHTML = `<div class="empty-note">暂无项目数据</div>`; return; }
  const s = d.summary;
  if (MON_TAB === "chars") {
    if (!s.characters?.length) { panes.innerHTML = `<div class="empty-note">无角色卡</div>`; return; }
    panes.innerHTML = `<div class="mon-grid">` + s.characters.map(c =>
      `<div class="mon-card"><img src="${MEDIA(c.image_path)}" onerror="this.style.visibility='hidden'">
        <div class="lbl"><b>${esc(c.name)}</b><span class="mut">${esc((c.do_not_change||[]).join(" · "))}</span></div></div>`
    ).join("") + `</div>`;
  } else if (MON_TAB === "scenes") {
    if (!s.scenes?.length) { panes.innerHTML = `<div class="empty-note">无场景卡</div>`; return; }
    panes.innerHTML = `<div class="mon-grid">` + s.scenes.map(sc =>
      `<div class="mon-card"><img src="${MEDIA(sc.image_path)}" onerror="this.style.visibility='hidden'">
        <div class="lbl"><b>${esc(sc.name)}</b></div></div>`).join("") + `</div>`;
  } else if (MON_TAB === "shots") {
    panes.innerHTML = `<div class="mon-shots">` + (s.shots || []).map(sh =>
      `<div class="shot-thumb" onclick="playShotClip('${sh.id}')">
         <div class="top"><span class="id">${sh.id}</span><span class="mode">${sh.mode}</span></div>
         <div class="muted" style="font-size:11px">${esc((sh.desc||"").slice(0,80))}</div>
         <div class="mut" style="font-size:10.5px;margin-top:3px">${sh.duration_s}s · edit ${sh.edit_target_s}s · ${sh.hook}</div>
       </div>`).join("") + `</div>`;
  } else if (MON_TAB === "tasks") {
    refreshTasks(panes);
  }
}

function playShotClip(id) {
  // try common clip location
  const base = (S.director?.output_dir || "") + "/" + id + ".mp4";
  const vid = $("#mon-video");
  vid.src = MEDIA(base); vid.style.display = "block";
  $("#empty-player").style.display = "none";
  vid.play().catch(() => {});
}

async function refreshTasks(panes) {
  panes = panes || $("#mon-panes");
  let tasks;
  try { tasks = (await API.get("/api/tasks")).tasks || []; } catch (e) { tasks = []; }
  if (!tasks.length) { panes.innerHTML = `<div class="empty-note">暂无后台任务</div>`; return; }
  panes.innerHTML = tasks.map(t =>
    `<div class="task" data-tid="${t.id}">
       <div class="t-head"><b>${esc(t.title)}</b><span class="status ${t.status}">${t.status}</span></div>
       <div class="bar"><i style="width:${pct(t)}%"></i></div>
       <div class="log"></div>
     </div>`).join("");
}
const pct = (t) => t.total ? Math.round((t.cur || 0) / t.total * 100) : (t.status === "done" ? 100 : 8);

/* detail of a task (poll fills log) */
async function monitorTask(tid) {
  try {
    const t = await API.get("/api/task/" + tid);
    const el = $(`.task[data-tid="${tid}"]`);
    if (!el) return;
    const logEl = $(".log", el);
    if (logEl) logEl.textContent = (t.log || []).join("\n");
    const bar = $(".bar>i", el); if (bar) bar.style.width = pct(t) + "%";
    if (t.status === "done") {
      el.querySelector(".t-head .status").textContent = "done ✓";
      el.classList.add("done");
      // auto-play result if it's a clip
      if (t.result && t.result.clip) { window._finalVideo = MEDIA(t.result.clip); refreshMonitor(); }
      if (t.kind === "series" && t.result) {
        const records = Array.isArray(t.result) ? t.result : (t.result.records || []);
        const ep = records.find(r => r.episode);
        if (ep) { window._finalVideo = MEDIA(ep.episode); refreshMonitor(); }
      }
    } else if (t.status === "error") {
      el.querySelector(".t-head .status").textContent = "✕ " + (t.error || "error");
    }
  } catch (e) { /* ignore */ }
}

/* ---------------- boot ---------------- */
async function boot() {
  buildNav();
  // project select
  try {
    const ps = (await API.get("/api/projects")).projects || [];
    const sel = $("#project-select");
    sel.innerHTML = ps.map(p => `<option value="${p}">${p}</option>`).join("");
    S.projectPath = S.projectPath && ps.includes(S.projectPath) ? S.projectPath : (ps[0] || "");
    sel.value = S.projectPath;
    sel.onchange = async () => {
      S.projectPath = sel.value;
      window._finalVideo = "";
      await loadDirector();
      await go(S.activeStage);
    };
  } catch (e) { console.error(e); }

  // monitor tabs
  $$(".mon-tab").forEach(b => b.onclick = () => {
    $$(".mon-tab").forEach(x => x.classList.remove("active"));
    b.classList.add("active"); MON_TAB = b.dataset.tab; refreshMonitor();
  });
  $("#btn-collapse").onclick = () => {
    const m = $("#monitor"); m.classList.toggle("collapsed");
    $("#btn-collapse").textContent = m.classList.contains("collapsed") ? "«" : "»";
  };
  // config drawer
  $("#btn-config").onclick = () => openDrawer(true);
  $("#btn-drawer-close").onclick = () => openDrawer(false);
  $("#drawer-mask").onclick = () => openDrawer(false);
  $("#btn-save-config").onclick = async () => {
    S.config.comfy = $("#cfg-comfy").value.trim();
    $("#cfg-status").textContent = "配置已保存（生效需重启后端 --comfy，或手动指定）。";
    toast("配置已保存", "ok");
    openDrawer(false);
  };
  $("#btn-save-llm").onclick = async () => {
    try {
      const r = await API.post("/api/config/llm", {
        provider: $("#cfg-llm-provider").value.trim(),
        name: $("#cfg-llm-name").value.trim(),
        base_url: $("#cfg-llm-base").value.trim(),
        model: $("#cfg-llm-model").value.trim(),
        display_name: $("#cfg-llm-display").value.trim(),
        api_key: $("#cfg-llm-key").value,
      });
      $("#llm-status").textContent = `已保存：${r.display_name}`;
      toast("LLM Provider 已保存", "ok");
    } catch (e) { toast("LLM 配置保存失败: " + e.message, "bad"); }
  };
  // new-project modal
  $("#btn-new-project").onclick = () => openNewProject();
  $("#np-close").onclick = () => closeNewProject();
  $("#np-mask").onclick = () => closeNewProject();
  $$(".np-method").forEach(b => b.onclick = () => {
    $$(".np-method").forEach(x => x.classList.remove("active"));
    b.classList.add("active");
    $("#np-spsec-wrap").style.display = "";
  });
  $("#np-create").onclick = () => submitNewProject();
  // chat iteration
  $("#btn-chat-iter").onclick = () => openChatIter();
  $("#chat-close").onclick = () => closeChatIter();
  $("#chat-mask").onclick = () => closeChatIter();
  $("#chat-send").onclick = () => sendChatIter();
  $("#chat-feedback").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatIter(); }
  });

  await loadDirector();
  await go(S.activeStage);
  // poll tasks while on monitor or gen stage
  setInterval(async () => {
    if (MON_TAB === "tasks") refreshMonitor();
    // poll running tasks
    try {
      const ts = (await API.get("/api/tasks")).tasks || [];
      ts.filter(t => t.status === "running").forEach(t => monitorTask(t.id));
    } catch (e) {}
  }, 1800);
}

async function loadDirector() {
  try {
    S.director = await API.get("/api/director?path=" + encodeURIComponent(S.projectPath));
    S.progress = S.director.progress || null;
    window._finalVideo = "";
    const on = S.director.comfy && S.director.comfy.online;
    $("#rail-comfy").innerHTML = `<span class="dot ${on ? "on" : "off"}"></span>Comfy${on ? " ✓" : " ✗"}`;
    buildNav();
    // auto-detect an existing final episode to show in monitor
    await probeFinalVideo();
    if (MON_TAB !== "tasks") refreshMonitor();
  } catch (e) { console.error(e); }
}

// Probe for an already-built episode: common names under gen/<proj>/
async function probeFinalVideo() {
  const dir = S.director?.output_dir;
  if (!dir) return;
  const files = (await API.get("/api/files?path=" + encodeURIComponent(dir)).catch(() => ({files:[]}))).files || [];
  for (const f of files.filter(x => x.kind === "vid" && /episode|final|desk/i.test(x.name))) {
    try {
      const r = await fetch(MEDIA(f.path), { method: "HEAD" });
      if (r.ok) { window._finalVideo = MEDIA(f.path); return; }
    } catch (e) {}
  }
}

function openDrawer(open) {
  $("#config-drawer").classList.toggle("open", open);
  $("#drawer-mask").classList.toggle("open", open);
  if (open) {
    $("#cfg-comfy").value = S.config.comfy;
    API.get("/api/config/llm").then(c => {
      $("#cfg-llm-provider").value = c.provider || "";
      $("#cfg-llm-name").value = c.name || "";
      $("#cfg-llm-base").value = c.base_url || "";
      $("#cfg-llm-model").value = c.model || "";
      $("#cfg-llm-display").value = c.display_name || "";
    }).catch(() => {});
  }
}

/* ---------------- new project modal ---------------- */
function activeNpMethod() {
  const a = $(".np-method.active");
  return a ? a.dataset.m : "blank";
}
function openNewProject() {
  $(".np-method[data-m='blank']").classList.add("active");
  $(".np-method[data-m='example']").classList.remove("active");
  $("#np-spsec-wrap").style.display = "";
  $("#np-e").textContent = "";
  $("#np-name").focus();
  $("#np-modal").classList.add("open");
  $("#np-mask").classList.add("open");
}
function closeNewProject() {
  $("#np-modal").classList.remove("open");
  $("#np-mask").classList.remove("open");
}
async function submitNewProject() {
  const name = $("#np-name").value.trim();
  if (!name) { toast("请先填写项目名称", "warn"); return; }
  const m = activeNpMethod();
  const btn = $("#np-create"); btn.disabled = true; btn.textContent = "创建中…";
  const progress = $("#np-progress");
  const progressLabel = $("#np-progress-label");
  const progressPct = $("#np-progress-pct");
  const progressFill = $("#np-progress-fill");
  if (progress) progress.hidden = true;
  const setProgress = (label, cur, total) => {
    if (!progress || m !== "ai") return;
    const pct = total ? Math.round(cur / total * 100) : 0;
    progressLabel.textContent = label;
    progressPct.textContent = pct + "%";
    progressFill.style.width = pct + "%";
  };
  try {
    const res = await API.post("/api/project/new", {
      name,
      template: m === "example" ? "example" : "blank",
      aspect: $("#np-aspect").value,
      duration_s: parseInt($("#np-dur").value, 10) || 15,
      seconds_per_shot: parseInt($("#np-spsec").value, 10) || 5,
    });
    if (res.error) throw new Error(res.error);
    S.projectPath = res.path;
    await refreshProjectSelect();
    await loadDirector();
    closeNewProject();
    toast("项目已创建，请输入提示词", "ok");
    openChatIter("create");
  } catch (e) { toast("创建项目出错: " + e.message, "bad"); }
  if (progress) progress.hidden = true;
  btn.disabled = false; btn.textContent = "创建项目";
}
async function refreshProjectSelect() {
  try {
    const ps = (await API.get("/api/projects")).projects || [];
    const sel = $("#project-select");
    sel.innerHTML = ps.map(p => `<option value="${p}">${p}</option>`).join("");
    sel.value = S.projectPath;
  } catch (e) {}
}

/* ---------------- conversational iteration ---------------- */
let CHAT_WELCOME_SHOWN = false;
let CHAT_MODE = "iterate";
function openChatIter(mode = "iterate") {
  CHAT_MODE = mode;
  const body = $("#chat-body");
  body.innerHTML = "";
  if (!CHAT_WELCOME_SHOWN) {
    addChatMsg("ai", `怎么用（每一轮都在这个框里说话）：\n` +
      `新项目第一步：把故事想法 / 语料 / 背景 / 风格粘进下面输入框点发送，AI 会基于它生成一集短剧的完整分镜骨架。\n` +
      `之后每一轮：直接在框里告诉我哪里有问题（例如"第3镜太慢，把反派改阴郁些""加一镜打脸"），AI 会自动改好并保存，导演台各环节实时刷新，你不用填任何字段。`);
    CHAT_WELCOME_SHOWN = true;
  }
  $("#chat-modal").classList.add("open");
  $("#chat-mask").classList.add("open");
  $("#chat-feedback").value = "";
  $("#chat-feedback").placeholder = mode === "create" ? "请输入这个新项目的提示词：故事、人物、场景、动作、台词、风格……" : "告诉 AI 要怎么修改当前项目……";
  setTimeout(() => $("#chat-feedback").focus(), 80);
}
function closeChatIter() {
  $("#chat-modal").classList.remove("open");
  $("#chat-mask").classList.remove("open");
}
function addChatMsg(kind, text) {
  const body = $("#chat-body");
  const el = document.createElement("div");
  el.className = "chat-msg " + kind;
  if (kind === "ai") el.innerHTML = `<div class="who">🎬 AI 导演</div>` + esc(text);
  else el.textContent = text;
  body.appendChild(el);
  body.scrollTop = body.scrollHeight;
  return el;
}
async function sendChatIter() {
  const fb = $("#chat-feedback").value.trim();
  if (!fb) return;
  if (!S.projectPath) { addChatMsg("err", "还没有项目。先点「＋ 新建项目」创建项目，再回来对话迭代。"); return; }
  addChatMsg("user", fb);
  $("#chat-feedback").value = "";
  const btn = $("#chat-send"); btn.disabled = true;
  const typing = addChatMsg("ai", "");
  typing.innerHTML = `<div class="who">🎬 AI 导演</div><span class="chat-typing chat-dots">AI 在改写分镜</span>`;
  try {
    const r = await API.post("/api/chat/iter", {
      path: S.projectPath,
      mode: CHAT_MODE,
      feedback: fb,
    });
    typing.remove();
    if (r.error) {
      addChatMsg("err", r.error + (r.error.includes("LLM key") ? "" : ""));
      if (/LLM key|key/.test(r.error)) {
        addChatMsg("ai", "要启动对话式迭代，请在后端配置 LLM key（OPENAI_API_KEY 或 DEEPSEEK_API_KEY），然后重启后端。配置好我就按轮次自动改分镜。");
      }
    } else {
      const s = r.summary || {};
      addChatMsg("done", `✅ 第 ${s.round || "?"} 轮已保存\n` +
        `剧名：${esc(r.project.title)}\n镜头数：${s.n_shots} · 角色：${s.cha} · 场景：${s.scenes}`);
      // refresh all stage data so the board/monitor reflect the new JSON
      await loadDirector();
      if (STAGE_RENDER[S.activeStage]) go(S.activeStage);
    }
  } catch (e) {
    typing.remove();
    addChatMsg("err", "调用出错: " + e.message);
  }
  btn.disabled = false;
  $("#chat-feedback").focus();
}

document.addEventListener("DOMContentLoaded", boot);
