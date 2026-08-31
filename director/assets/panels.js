/* ============ 导演台 panels.js — 各环节导演控制面板 ============ */
"use strict";

/* ---------- 01 设定 · Bible ---------- */
STAGE_RENDER["bible"] = async (body) => {
  const d = S.director;
  if (!d || !d.summary) {
    body.innerHTML = `<div class="panel"><h3>🎬 项目设定</h3>
      <div class="empty-note">还没有项目。点左侧「＋ 新建项目」创建后，这里填写你的故事设定。</div>
      <button class="btn" onclick="window._newProj()">＋ 新建项目</button></div>`;
    window._newProj = () => openNewProject();
    setActions("");
    return;
  }
  const full = await API.get("/api/project?path=" + encodeURIComponent(S.projectPath)).catch(() => null);
  const s = d.summary;
  const f = full || {};

  setActions(`<button class="btn" id="btn-save-bible">💾 保存设定</button>`);

  const input = (id, val, ph="") => `<input id="${id}" value="${esc(val||"")}" placeholder="${esc(ph)}" style="width:100%;margin-top:4px">`;
  const ta = (id, val, ph="", rows=3) => `<textarea id="${id}" rows="${rows}" style="width:100%;margin-top:4px;background:var(--bg2);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:8px">${esc(val||"")}</textarea>`;
  const oneline = (lbl) => `width:100%;margin-top:4px;background:var(--bg2);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:6px 8px`;
  body.innerHTML = `
   <div class="panel">
     <h3>🎬 项目设定 <span class="sub">这里从第一步开始定义你的剧</span></h3>
     <div class="param-grid" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr))">
       <div class="param" style="grid-column:1/-1"><label>剧名</label>${input("b-title-in", f.title)}</div>
       <div class="param"><label>画幅</label>
         <select id="b-aspect" style="${oneline()}">${["9:16","16:9","1:1","4:3","3:4"].map(a=>`<option ${a===f.aspect?"selected":""}>${a}</option>`).join("")}</select></div>
       <div class="param"><label>一集时长 (s)</label><input id="b-dur" type="number" value="${f.duration_s??15}" style="width:100%;margin-top:4px"></div>
       <div class="param"><label>对白模式</label>
         <select id="b-dmode" style="${oneline()}">${["有对白","无对白"].map(a=>`<option ${a===f.dialogue_mode?"selected":""}>${a}</option>`).join("")}</select></div>
       <div class="param"><label>对白语言</label>${input("b-dlang", f.dialogue_language, "中文")}</div>
     </div>
     <div class="param" style="margin-top:10px"><label>What if 概念（一句话钩子）</label>${ta("b-what", f.what_if, "例如：穿越成被退婚的赘婿，开局打脸渣男全家", 2)}</div>
     <div class="param" style="margin-top:10px"><label>目标感受</label>${input("b-feel", f.target_feeling, "爽感+反转")}</div>
     <div class="param" style="margin-top:10px"><label>视觉风格 Bible（描述画面质感/摄影/色调，英文更佳）</label>${ta("b-style", f.visual_style, "cinematic, gritty realism, chiaroscuro lighting...", 4)}</div>
   </div>
   <div class="panel">
     <h3>🧭 制作流程 <span class="sub">从剧本到成片的 10 个可控制环节</span></h3>
     <div class="flow" id="b-flow"></div>
   </div>`;

  $("#btn-save-bible").onclick = async () => {
    const meta = {
      title: $("#b-title-in").value.trim() || "未命名短剧",
      aspect: $("#b-aspect").value,
      duration_s: parseFloat($("#b-dur").value) || 15,
      dialogue_mode: $("#b-dmode").value,
      dialogue_language: $("#b-dlang").value.trim() || "中文",
      what_if: $("#b-what").value,
      target_feeling: $("#b-feel").value,
      visual_style: $("#b-style").value,
    };
    try {
      await API.post("/api/stage/patch", { path: S.projectPath, field: "meta", value: meta });
      toast("设定已保存 ✓", "ok");
      await loadDirector();
      go("bible");
    } catch (e) { toast("保存失败: " + e.message, "bad"); }
  };

  const beats = [
    ["设定", "填剧名/概念/感受/视觉风格（本页）"],
    ["分镜表", "每一镜的序列/景别/角色/逐秒指令"],
    ["自检", "6 条硬规则门禁（PASS 才可进入生成）"],
    ["角色卡", "定卡：固定 seed 锁定身份一致性"],
    ["场景卡", "关键场景中帧抽帧锁定空间"],
    ["提示词", "逐镜编译 H3 规范提示词"],
    ["部署", "ComfyUI 在线状态与显存规划"],
    ["生成", "逐镜 / 整集 ComfyUI 长任务生成"],
    ["质检", "成片抽帧 + 一致性核验"],
    ["成片", "裁剪对轨 + 硬切/转场 + BGM 装配"],
  ];
  $("#b-flow").innerHTML = beats.map((b, i) =>
    `<div class="flow-item"><span class="fi-idx">${String(i+1).padStart(2,"0")}</span>
     <span class="fi-n">${b[0]}</span><span class="fi-v">${b[1]}</span></div>`).join("");
};

/* ---------- 02 分镜表 · Board ---------- */
STAGE_RENDER["board"] = async (body) => {
  let full = null;
  try { full = await API.get("/api/project?path=" + encodeURIComponent(S.projectPath)); } catch (e) { full = null; }
  if (!full || !full.shots) {
    body.innerHTML = `<div class="panel"><h3>📋 分镜表</h3>
      <div class="empty-note">还没有可用的项目数据。点左侧「＋ 新建项目」创建项目后，这里就会显示分镜板并开始编辑。</div>
      <button class="btn" onclick="window._newProj()">＋ 新建项目</button></div>`;
    window._newProj = () => openNewProject();
    setActions("");
    return;
  }
  const shots = full.shots || [];
  const d = S.director;
  setActions(`<button class="btn" id="btn-add-shot">＋ 新增镜头</button>
              <button class="btn ghost" id="btn-reload-board">↻ 刷新</button>`);
  $("#btn-add-shot").onclick = () => addNewShot();
  $("#btn-reload-board").onclick = () => go("board");

  body.innerHTML = `
   <div class="stat-row">
     <div class="stat"><div class="l">总镜头</div><div class="n">${shots.length}</div></div>
     <div class="stat"><div class="l">全片时长</div><div class="n">${(full.duration_s || 0)}<small> s</small></div></div>
     <div class="stat"><div class="l">对白</div><div class="n">${(full.dialogue_mode||"-").slice(0,4)}</div></div>
     <div class="stat"><div class="l">画幅</div><div class="n">${full.aspect || "-"}</div></div>
   </div>
   <div class="panel">
     <h3>📋 分镜板 <span class="sub">点击镜头卡片展开逐秒指令</span></h3>
     <div class="board" id="board-list"></div>
   </div>`;

  const list = $("#board-list");
  list.innerHTML = shots.map(sh => {
    const ps = (sh.per_second || []).map(p =>
      `<div class="per-sec"><b>${esc(p.rng)}</b> ${esc(p.action)}
       ${p.camera ? `<br><span class="dim">camera:</span> ${esc(p.camera)}` : ""}
       ${p.spatial ? `<br><span class="dim">spatial:</span> ${esc(p.spatial)}` : ""}
       ${p.audio ? `<br><span class="dim">audio:</span> ${esc(p.audio)}` : ""}
       ${p.handoff ? `<br><span class="dim">handoff:</span> <span style="color:var(--chalk)">${esc(p.handoff)}</span>` : ""}
       </div>`).join("");
    const refs = (sh.references || []).map(r =>
      `<span class="tag amber">${esc(r.label)} · ${esc(r.retention)}</span>`).join(" ");
    return `
     <div class="shot-card" style="background:var(--panel);border:1px solid var(--line);border-radius:10px;margin-bottom:12px;overflow:hidden">
       <div class="shot-head" onclick="this.parentNode.classList.toggle('open')" style="display:flex;align-items:center;gap:12px;padding:11px 14px;cursor:pointer">
         ${sh.first_frame ? `<img src="${MEDIA(sh.first_frame)}" onerror="this.style.visibility='hidden'" style="width:34px;height:60px;object-fit:cover;border-radius:4px;border:1px solid var(--line2);flex:none">` : (sh.continuity_type==="latent_pin"||sh.continuity_type==="motion_ref" ? `<span class="tag info" style="color:var(--info)">↳ 尾帧链</span>` : `<span class="tag" style="color:var(--dim)">○ 无引用</span>`)}
         <span class="shot-id" style="font-size:15px">${sh.shot_id}</span>
         <span class="mode tag">${sh.mode}</span>
         <span class="tag">${sh.duration_s}s → edit ${sh.edit_target_s||sh.duration_s}s</span>
         <span class="tag ${sh.hook}">hook: ${sh.hook}</span>
         <span class="tag">seed ${sh.seed||"auto"}</span>
         <span class="grow"></span>
         <button class="btn-sm" onclick="event.stopPropagation();editShot('${sh.shot_id}')">✎ 编辑</button>
         <span class="dim">${(sh.continuity_type||"hard_cut")} ▸</span>
       </div>
       <div style="padding:0 14px 12px">
         <div class="desc">${esc(sh.shot_description)}</div>
         <div class="muted" style="font-size:11.5px;margin-bottom:6px">
           ${sh.continuity_handoff ? `🎬 <b>Continuity:</b> ${esc(sh.continuity_handoff)}` : ""}</div>
         <div class="mut">${refs && `<div style="margin:4px 0">${refs}</div>`}
           ${sh.dialogue?.length ? `<div><span class="dim">对白:</span> ${sh.dialogue.map(x=>esc(x.text)).join(" / ")}</div>` : ""}
           ${sh.sfx?.length ? `<div><span class="dim">SFX:</span> ${sh.sfx.map(esc).join(" · ")}</div>` : ""}
         </div>
         <details class="ps-wrap" style="margin-top:8px"><summary>逐秒指令 (${ps.length} 秒)</summary>${ps}</details>
       </div>
     </div>`;
  }).join("");
  if (!shots.length) list.innerHTML = `<div class="empty-note">该镜头无 shot 数据</div>`;
};

/* ---------- 03 自检 · Check ---------- */
STAGE_RENDER["check"] = async (body) => {
  setActions(`<button class="btn" id="btn-check">▶ 运行自检</button>`);
  body.innerHTML = `<div class="empty">点击「运行自检」执行 6 条分镜硬规则门禁。</div>
    <div class="panel" id="check-result" style="display:none"></div>`;
  $("#btn-check").onclick = async () => {
    $("#btn-check").disabled = true;
    const btn = $("#btn-check"); btn.textContent = "检查中…";
    try {
      const r = await API.get("/api/stage/check?path=" + encodeURIComponent(S.projectPath));
      const box = $("#check-result"); box.style.display = "";
      const pass = r.pass;
      box.innerHTML = `
       <h3 style="margin:0 0 8px"><span class="pill ${pass?"ok":"bad"}"></span>分镜自检 ${pass ? "PASS" : "FAIL"}
         <span class="sub">${r.n_shots} 镜</span></h3>
       ${pass
        ? `<div style="color:var(--ok)">✅ 全部通过，可进入角色卡与生成。</div>`
        : `<div style="color:var(--bad)">🔴 以下规则未通过：</div>`}
       ${(r.failures||[]).map(f=>`<div class="verdict-row"><span class="pill bad"></span>${esc(f)}</div>`).join("")}
       ${(!r.failures || !r.failures.length) ? "" : ""}`;
    } catch (e) { toast("自检失败: " + e.message, "bad"); }
    btn.disabled = false; btn.textContent = "▶ 运行自检";
  };
};

/* ---------- 04 角色卡 · Cards ---------- */
STAGE_RENDER["cards"] = async (body) => {
  const full = await API.get("/api/project?path=" + encodeURIComponent(S.projectPath)).catch(() => null);
  const chars = (full && full.characters) || [];
  setActions(`<button class="btn ghost" id="btn-refresh-cards">↻ 刷新</button>`);
  $("#btn-refresh-cards").onclick = () => go("cards");
  body.innerHTML = `
   <div class="desc">角色卡由 H3 肖像 T2V 生成后抽中帧，用于 <b>hard-cut 身份锁定</b>（固定 seed 跨镜保持同一张脸）。</div>
   <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(170px,1fr))" id="cards-grid"></div>
   <div class="panel" style="margin-top:14px"><h3>🔒 定卡规则</h3>
     <div class="muted" style="font-size:12px">
       · 每角色固定 <b>seed</b>（如 70001/70002/70003）→ 抽中帧为一致性锚点。<br>
       · 镜头引用角色卡作为 <code class="code">first_frame</code>（I2VA）→ 该镜硬切到该角色。<br>
       · <code class="code">do_not_change</code> 字段防止特征漂移（脸/发型/服装）。</div></div>`;
  const g = $("#cards-grid");
  g.innerHTML = (chars.map(c => {
    const seed = "";
    return `<div class="mon-card" style="background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden">
       <img src="${MEDIA(c.image_path)}" onerror="this.style.visibility='hidden'">
       <div class="lbl" style="padding:8px"><b style="display:block">${esc(c.name)}</b>
         <span class="mut" style="font-size:11px">${(c.do_not_change||[]).map(esc).join(" · ")}</span></div>
     </div>`;
  }).join("")) || `<div class="empty-note">无角色卡（需先生成。</div>`;
};

/* ---------- 05 场景卡 ---------- */
STAGE_RENDER["scene"] = async (body) => {
  const full = await API.get("/api/project?path=" + encodeURIComponent(S.projectPath)).catch(() => null);
  const scenes = (full && full.scenes) || [];
  body.innerHTML = `
   <div class="desc">场景卡由建立镜头抽中帧，作为跨镜<b>空间一致性</b>锚点（地标/光线基线）。</div>
   <div class="panel"><h3>🏛 场景</h3><div class="scenes" id="scene-list"></div></div>`;
  $("#scene-list").innerHTML = (scenes.map(sc =>
    `<div style="display:flex;gap:14px;align-items:center;margin-bottom:12px">
      <img style="width:110px;aspect-ratio:9/16;object-fit:cover;border-radius:8px;border:1px solid var(--line)" src="${MEDIA(sc.image_path)}" onerror="this.style.visibility='hidden'">
      <div class="grow"><b>${esc(sc.name)}</b>
       <div class="mut" style="font-size:12px;margin-top:3px">${esc(sc.description||"")}</div>
       <div style="margin-top:5px">${(sc.landmarks||[]).map(x=>`<span class="tag amber">${esc(x)}</span>`).join("")}</div>
       ${sc.light_baseline ? `<div class="dim" style="font-size:11px;margin-top:3px">light: ${esc(sc.light_baseline)}</div>`:""}
      </div></div>`).join("")) || `<div class="empty-note">无场景卡</div>`;
};

/* ---------- 06 提示词 · Prompts ---------- */
STAGE_RENDER["prompts"] = async (body) => {
  setActions(`<button class="btn" id="btn-prompts">▶ 编译提示词</button>
              <button class="btn ghost" id="btn-prompts-out">📁 落盘</button>`);
  body.innerHTML = `<div class="empty">点击「编译提示词」逐镜生成 H3 规范提示词。</div>
    <div id="prompt-results"></div>`;
  const render = async (full) => {
    $("#prompt-results").innerHTML = `
      <div class="panel"><h3>📝 逐镜 H3 提示词 <span class="sub">${full.n} 镜</span></h3>
        <div class="prompt-tabs" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px" id="ptabs"></div>
        <div id="ptab-body"></div></div>`;
    const ids = Object.keys(full.prompts);
    const tabs = $("#ptabs");
    let active = ids[0];
    const show = (id) => {
      active = id;
      $$("#ptabs .chip").forEach(c => c.classList.toggle("active", c.dataset.id === id));
      const p = full.prompts[id];
      $("#ptab-body").innerHTML =
        `<div class="tag ok">${esc(id)} · ${p.chars} chars</div>
         <div style="margin-top:8px" class="prompt-blk">${esc(full.full[id])}</div>`;
    };
    tabs.innerHTML = ids.map(id => `<span class="chip ${id===active?"active":""}" data-id="${id}" onclick="window._showP('${id}')">${id}</span>`).join("");
    window._showP = show;
    show(active);
  };
  $("#btn-prompts").onclick = async () => {
    const b = $("#btn-prompts"); b.disabled = true; b.textContent = "编译中…";
    try {
      const r = await API.get("/api/stage/prompts?path=" + encodeURIComponent(S.projectPath));
      render(r);
      toast("提示词编译完成", "ok");
    } catch (e) { toast("失败: " + e.message, "bad"); }
    b.disabled = false; b.textContent = "▶ 编译提示词";
  };
  $("#btn-prompts-out").onclick = async () => {
    try {
      await API.get("/api/stage/prompts?path=" + encodeURIComponent(S.projectPath));
      toast("已写入当前项目 prompts/", "ok");
    } catch (e) { toast("失败: " + e.message, "bad"); }
  };
};

/* ---------- 07 部署 · ComfyUI ---------- */
STAGE_RENDER["deploy"] = async (body) => {
  setActions(`<button class="btn ghost" id="btn-deploy-refresh">↻ 刷新状态</button>
              <button class="btn" id="btn-deploy-plan">📐 渲染规划</button>`);
  body.innerHTML = `<div class="panel"><h3>🖥 ComfyUI 服务</h3><div id="comfy-info" class="empty">检测中…</div></div>
    <div class="panel"><h3>⚡ 加速服务 (spark2 :8123) <span class="sub">Sol-Attn 加速 · 约 2.3× · 纯文生图</span></h3>
      <div id="accel-info" class="empty">检测中…</div></div>
    <div class="panel"><h3>📐 显存 / 时长规划 <span class="sub">plan</span></h3>
      <div class="param-grid" style="margin-bottom:10px">
        <div class="param"><label>显存 (GB)</label><input id="plan-vram" type="number" value="130"></div>
        <div class="param"><label>画幅</label><select id="plan-aspect"><option>9:16</option><option>16:9</option><option>4:3</option><option>1:1</option></select></div>
        <div class="param"><label>单镜秒</label><input id="plan-sec" type="number" value="5"></div>
        <div class="param"><label>质量</label><select id="plan-q"><option value="fast">fast</option><option value="balanced">balanced</option><option value="quality">quality</option></select></div>
      </div>
      <pre class="prompt-blk" id="plan-out" style="min-height:60px">（点击「渲染规划」）</pre></div>`;

  const refreshComfy = async () => {
    const h = await API.get("/api/hardware").catch(() => null);
    const el = $("#comfy-info");
    const al = $("#accel-info");
    if (!h) { el.className = "empty"; el.textContent = "无法连接后端";
      if (al) { al.className = "empty"; al.textContent = "无法连接后端"; }
      return; }
    // accelerate service status
    if (al) {
      const a = h.accel;
      if (a && a.online) {
        al.className = "";
        al.innerHTML = `<div class="stat-row">
          <div class="stat"><div class="l">状态</div><div class="n"><span style="color:var(--ok)">在线 ⚡</span></div></div>
          <div class="stat"><div class="l">地址</div><div class="n" style="font-size:15px">${esc(a.base.replace("http://",""))}</div></div>
          <div class="stat"><div class="l">加速</div><div class="n" style="font-size:15px;color:var(--acc)">Sol-Attn</div></div>
          <div class="stat"><div class="l">适用</div><div class="n" style="font-size:13px;color:var(--chalk)">纯文生图 T2V</div></div>
        </div>
        <div class="muted" style="font-size:11px">带角色卡首帧的 I2V 镜头仍走 ComfyUI（加速服务无图生图）。</div>`;
      } else {
        al.className = "";
        al.innerHTML = `<div class="stat-row">
          <div class="stat"><div class="l">状态</div><div class="n" style="color:var(--bad)">离线</div></div>
          <div class="stat"><div class="l">地址</div><div class="n" style="font-size:13px">${esc((a && a.base)||"-")}</div></div>
          <div class="stat" style="flex:2"><div class="l">提示</div><div class="v" style="color:var(--mut)">加速服务连通后，生成环节可选它提速；当前离线不影响 ComfyUI 流程。</div></div></div>`;
      }
    }
    if (h.online && h.system_stats) {
      const sys = h.system_stats.system;
      const dev = h.system_stats.devices?.[0] || {};
      const gb = (n) => (n/1e9).toFixed(0);
      el.className = "";
      el.innerHTML = `<div class="stat-row">
        <div class="stat"><div class="l">状态</div><div class="n"><span style="color:var(--ok)">在线</span></div></div>
        <div class="stat"><div class="l">地址</div><div class="n" style="font-size:15px">${esc(h.base.replace("http://",""))}</div></div>
        <div class="stat"><div class="l">显存</div><div class="n">${gb(dev.vram_total)}<small> GB</small></div></div>
        <div class="stat"><div class="l">空闲显存</div><div class="n">${gb(dev.vram_free)}<small> GB</small></div></div>
        <div class="stat"><div class="l">设备</div><div class="n" style="font-size:15px">${esc(dev.name?.split(" ")[0]||"-")}</div></div>
        <div class="stat"><div class="l">Comfy 版本</div><div class="n" style="font-size:15px">${esc(sys.comfyui_version||"-")}</div></div>
      </div>`;
    } else {
      el.className = ""; el.innerHTML = `<div class="stat-row">
        <div class="stat"><div class="l">状态</div><div class="n" style="color:var(--bad)">离线</div></div>
        <div class="stat"><div class="l">地址</div><div class="n" style="font-size:14px">${esc(h.base)}</div></div>
        <div class="stat" style="flex:2"><div class="l">错误</div><div class="v" style="color:var(--bad)">${esc(h.error||"不可达")}</div></div></div>`;
    }
  };
  $("#btn-deploy-refresh").onclick = refreshComfy;
  $("#btn-deploy-plan").onclick = async () => {
    const v = $("#plan-vram").value, asp = $("#plan-aspect").value,
          sec = $("#plan-sec").value, q = $("#plan-q").value;
    const r = await API.get(`/api/stage/plan?vram=${v}&aspect=${asp}&seconds=${sec}&quality=${q}`);
    $("#plan-out").textContent = r.plan;
  };
  await refreshComfy();
};

/* ---------- 08 生成 · Generate ---------- */
STAGE_RENDER["gen"] = async (body) => {
  const full = await API.get("/api/project?path=" + encodeURIComponent(S.projectPath)).catch(() => null);
  const shots = (full && full.shots) || [];
  const d = S.director;
  setActions(`<button class="btn" id="btn-gen-all">▶ 生成整集</button>
              <button class="btn ghost" id="btn-gen-refresh">↻ 状态</button>`);
  const outDir = "";
  const accelOn = d && d.comfy && d.comfy.accel && d.comfy.accel.online;
  body.innerHTML = `
   <div class="desc">逐镜生成 H3 片段（长任务）。可选择生成后端：<b>ComfyUI</b>（原版，支持图生图/角色卡首帧）或
     <b>加速服务</b>（spark2 :8123，纯文生图、约 2.3× 提速）。<span style="color:var(--chalk)">带角色卡首帧的 I2V 镜头在加速模式下会自动回退到 ComfyUI 以保身份锁定。</span></div>
   <div class="panel"><h3>🎛 生成参数</h3>
     <div class="param-grid">
       <div class="param"><label>生成后端</label>
         <select id="gen-backend">
           <option value="comfy">ComfyUI（原）</option>
           <option value="accel" ${accelOn?"":"disabled"}>加速服务 8123 ${accelOn?"✓":"(离线)"}</option>
         </select></div>
       <div class="param"><label>ComfyUI base</label><input id="gen-comfy" value="${esc(S.config.comfy)}"></div>
        <div class="param"><label>宽</label><input id="gen-w" type="number" value="768"></div>
        <div class="param"><label>高</label><input id="gen-h" type="number" value="1344"></div>
        <div class="param"><label>steps</label><input id="gen-steps" type="number" value="12"></div>
        <div class="param"><label>输出目录</label><input id="gen-out" value="${outDir}" placeholder="默认保存到当前项目 outputs/"></div>
     </div>
     ${accelOn ? "" : `<div class="hint">⚠ 加速服务当前离线（http://192.168.100.11:8123），已默认用 ComfyUI。加速服务连通后刷新本页自动可选。</div>`}
     </div>
   <div class="panel"><h3>镜头生成队列</h3><div id="gen-queue"></div></div>
   <div class="panel"><h3>运行记录</h3><div id="gen-log" class="prompt-blk" style="min-height:80px">—</div></div>`;

  const queue = $("#gen-queue");
  const renderQueue = () => {
    queue.innerHTML = shots.map(sh => {
      const exists = window._genStatus && window._genStatus[sh.id];
      return `<div class="shot-thumb" style="display:flex;gap:10px;align-items:center">
        <span class="id">${sh.id}</span>
        <span class="mode tag">${sh.mode}</span>
        <span class="tag">${sh.duration_s}s</span>
        <span class="tag">seed ${sh.seed||"auto"}</span>
        <span class="grow"></span>
        ${exists ? `<span class="tag ok">✓ ${exists}</span>` : ""}
        <button class="btn-sm" onclick="window._genOne('${sh.id}')">▶ 生成 ${sh.id}</button>
        <button class="btn-sm" onclick="playShotClip('${sh.id}')">预览</button>
      </div>`;
    }).join("") || `<div class="empty-note">无镜头</div>`;
  };
  renderQueue();

  const log = (m) => { const el = $("#gen-log"); el.textContent = (el.textContent === "—" ? "" : el.textContent) + m + "\n"; el.scrollTop = el.scrollHeight; };

  window._genOne = async (id) => {
    const sel = $("#gen-backend");
    const body2 = {
      path: S.projectPath, shot_id: id, out_dir: $("#gen-out").value.trim(),
      comfy: $("#gen-comfy").value.trim(),
      width: parseInt($("#gen-w").value, 10) || 480,
      height: parseInt($("#gen-h").value, 10) || 832,
      steps: parseInt($("#gen-steps").value, 10) || 20,
      backend: sel ? sel.value : "comfy",
    };
    S.config.comfy = body2.comfy;
    try {
      const r = await API.post("/api/stage/generate", body2);
      toast(`已提交 ${id} 生成（任务 ${r.task}）`, "info");
      log(`[${id}] submitted task ${r.task}`);
      pollGenTask(r.task, id);
    } catch (e) { toast("提交失败: " + e.message, "bad"); }
  };
  $("#btn-gen-all").onclick = async () => {
    const b = $("#btn-gen-all"); b.disabled = true; b.textContent = "提交系列任务…";
    try {
      const r = await API.post("/api/stage/series", {path: S.projectPath, out_dir: "auto"});
      toast(`已提交串行系列任务 ${r.task}`, "info");
      log(`[series] submitted task ${r.task}`);
      pollSeriesTask(r.task);
    } catch (e) { toast("提交失败: " + e.message, "bad"); }
    b.disabled = false; b.textContent = "▶ 生成整集";
  };
  window.pollSeriesTask = (tid) => {
    const iv = setInterval(async () => {
      try {
        const t = await API.get("/api/task/" + tid);
        log(`[series] ${t.status} ${t.cur || 0}/${t.total || shots.length}${t.log ? " · " + t.log[t.log.length-1] : ""}`);
        if (t.status === "done") {
          clearInterval(iv);
          const out = t.result?.out_dir || "";
          const ep = t.result?.records?.find(r => r.episode);
          toast("系列生成完成", "ok");
          if (ep?.episode) { window._finalVideo = MEDIA(ep.episode); refreshMonitor(); }
          if (out) log(`[series] spark1 archive: ${t.result.archive}`);
        } else if (t.status === "error") {
          clearInterval(iv); toast(`系列失败: ${t.error}`, "bad");
        }
      } catch (e) {}
    }, 2500);
  };
  window.pollGenTask = (tid, id) => {
    const iv = setInterval(async () => {
      try {
        const t = await API.get("/api/task/" + tid);
        log(`[${id}] ${t.status}${t.log ? " · " + t.log[t.log.length-1] : ""}`);
        if (t.status === "done") {
          clearInterval(iv);
          toast(`${id} 生成完成: ${t.result.clip}`, "ok");
          window._genStatus = window._genStatus || {};
          window._genStatus[id] = "✓ " + (t.result.clip || "").split("/").pop();
          renderQueue();
        } else if (t.status === "error") {
          clearInterval(iv); toast(`${id} 失败: ${t.error}`, "bad");
        }
      } catch (e) { /* keep polling */ }
    }, 2500);
  };
  $("#btn-gen-refresh").onclick = () => {
    API.get("/api/task/" ).then(r => {}).catch(()=>{});
    renderQueue(); toast("生成面板已刷新", "ok");
  };
};

/* ---------- 09 质检 · QC ---------- */
STAGE_RENDER["qc"] = async (body) => {
  setActions(`<button class="btn" id="btn-qc">▶ 扫描质检帧</button>`);
  body.innerHTML = `<div class="empty">点击「扫描质检帧」列出成片抽帧与 QC 资产。</div>
    <div id="qc-out"></div>`;
  $("#btn-qc").onclick = async () => {
    const dir = S.director?.output_dir || "";
    const files = (await API.get("/api/files?path=" + encodeURIComponent(dir)).catch(() => ({files:[]}))).files || [];
    const final = files.find(f => f.kind === "vid" && /episode|final|desk/i.test(f.name));
    const r = await API.get("/api/stage/qc?path=" + encodeURIComponent(S.projectPath) +
                            "&out=" + encodeURIComponent(final?.path || ""));
    const out = $("#qc-out");
    const frames = r.frames || [];
    out.innerHTML = `
      <div class="panel"><h3>🔍 质检帧 <span class="sub">${frames.length} 张</span></h3>
        <div class="media-grid">${frames.map(f =>
          `<div class="media-cell" onclick="window._qcView('${esc(f)}')">
             <img src="${MEDIA(f)}" onerror="this.style.visibility='hidden'"><div class="m-name">${esc(f.split("/").pop())}</div></div>`)
        .join("") || `<div class="empty-note">未找到质检帧</div>`}</div></div>`;
    if (r.final) {
      out.insertAdjacentHTML("afterbegin",
        `<div class="panel"><h3>🎬 待检成片</h3><video controls style="width:260px;border-radius:8px">` +
        `<source src="${MEDIA(r.final)}"></video><div class="muted" style="font-size:11px">${esc(r.final)}</div></div>`);
    }
  };
  window._qcView = (path) => { window.open(MEDIA(path), "_blank"); };
};

/* ---------- 10 成片 · Assemble ---------- */
STAGE_RENDER["final"] = async (body) => {
  setActions(`<button class="btn" id="btn-assemble">🎬 装配成片</button>
              <button class="btn ghost" id="btn-assemble-reload">↻</button>`);
  body.innerHTML = `
   <div class="desc">将每镜裁剪到 <code class="code">edit_target_s</code> 后硬切 concat，可选 BGM。读取镜头序列生成 ffmpeg 命令。</div>
   <div class="panel"><h3>装配参数</h3>
     <div class="param-grid">
        <div class="param"><label>输出文件</label><input id="asm-out" value="${S.director?.output_dir ? S.director.output_dir + "/episode.mp4" : "gen/episode.mp4"}"></div>
       <div class="param"><label>BGM (可选)</label><input id="asm-bgm" placeholder="留空"></div>
       <div class="param"><label>剪辑基准</label><select id="asm-mode"><option value="trim">按 edit_target 裁剪</option><option value="raw">原片直连</option></select></div>
     </div></div>
   <div class="panel"><h3>裁剪序列预览</h3><div id="asm-seq"></div></div>
   <div class="panel"><h3>装配日志</h3><pre class="prompt-blk" id="asm-log" style="min-height:70px">—</pre></div>`;

  // build clip sequence from ep01 shots (trim to edit_target)
  const full = await API.get("/api/project?path=" + encodeURIComponent(S.projectPath)).catch(() => null);
  const shots = (full && full.shots) || [];
  const d = S.director;
   const baseDir = S.director?.output_dir || "";
  const seq = shots.map(sh => ({
    id: sh.id,
    src: `${baseDir}/${sh.id}.mp4`,
    trim: sh.edit_target_s || sh.duration_s,
  }));
  $("#asm-seq").innerHTML = seq.map(s =>
    `<div class="flow-item"><span class="fi-idx">${s.id}</span>
     <span class="fi-n">${baseDir}/${escapeHtml(s.id)}.mp4</span>
     <span class="fi-v">→ trim ${s.trim}s</span></div>`).join("");

  $("#btn-assemble").onclick = async () => {
    // Build clip list: prefer existing *_trim*.mp4 (edit-target trimmed), else raw clip.
    const mode = $("#asm-mode").value;
    let clips;
    if (mode === "trim") {
      clips = seq.map(s => {
        const trimmed = `${s.src.replace(/\.mp4$/, "")}_trim${Math.round(s.trim)}.mp4`;
        return trimmed;   // backend checks existence; falls through per file
      });
    } else {
      clips = seq.map(s => s.src);
    }
    const out = $("#asm-out").value;
    const log = $("#asm-log");
    log.textContent = "装配中…（后台）。请稍候浏览「任务」或等待 toast。\n";
    // NOTE: assemble is synchronous on the server (ffmpeg); show busy cursor
    try {
      const r = await API.post("/api/stage/assemble", { clips, out, bgm: $("#asm-bgm").value.trim(),
                                                        mode: "hardcut" });
      log.textContent = "";
      (r.cmd_head || []).forEach(c => log.textContent += "CMD: " + c + "\n");
      if (r.error) { log.textContent += "ERROR: " + r.error + "\n"; toast("装配失败: " + r.error, "bad"); }
      else {
        log.textContent += "\n输出: " + out + (r.size ? " (" + (r.size/1e6).toFixed(1) + " MB)" : "");
        toast("装配完成" + (r.exists ? " ✓" : ""), r.exists ? "ok" : "warn");
        if (r.exists) { window._finalVideo = MEDIA(out); refreshMonitor(); }
      }
    } catch (e) { log.textContent += "ERROR: " + e.message + "\n"; toast("装配失败: " + e.message, "bad"); }
  };
  $("#btn-assemble-reload").onclick = () => go("final");
};

function escapeHtml(s){ return esc(s); }

window.escapeHtml = escapeHtml;

/* ---------- 镜头可视化编辑器 ---------- */
let EDIT_SHOTS = null;   // full shots array (mirror), EDIT_PROJECT is full doc
let EDIT_PROJECT = null;
let EDIT_IDX = -1;       // index in EDIT_SHOTS
let EDIT_PS = [];        // per_second rows

async function loadEditDoc() {
  try { return await API.get("/api/project?path=" + encodeURIComponent(S.projectPath)); }
  catch (e) { return null; }
}

function modeOptions(sel) {
  return ["T2VA","I2VA","FL2VA","L2VA","Ref2VA"].map(m =>
    `<option ${m===sel?"selected":""}>${m}</option>`).join("");
}
function hookOptions(sel) {
  const h=["visual-joke","reversal","suspense","tender","chase","reveal","callback","expression-beat"];
  return h.map(x=>`<option ${x===sel?"selected":""}>${x}</option>`).join("");
}

function editShot(id) {
  (async () => {
    const doc = await loadEditDoc();
    if (!doc) { toast("无法读取项目", "bad"); return; }
    EDIT_PROJECT = doc;
    EDIT_SHOTS = doc.shots || [];
    EDIT_IDX = EDIT_SHOTS.findIndex(s => s.shot_id === id);
    if (EDIT_IDX < 0) { toast("镜头不存在", "bad"); return; }
    renderShotEditor();
    $("#se-mask").classList.add("open");
    $("#se-modal").classList.add("open");
  })();
}
function addNewShot() {
  (async () => {
    const doc = await loadEditDoc();
    if (!doc) { toast("无法读取项目", "bad"); return; }
    EDIT_PROJECT = doc;
    EDIT_SHOTS = doc.shots || [];
    const n = EDIT_SHOTS.length + 1;
    EDIT_SHOTS.push({
      shot_id: `S${String(n).padStart(2,"0")}`,
      duration_s: 5, edit_target_s: 3,
      continuity_handoff: "（待填写）接续上一镜", fixed_landmarks: [],
      char_positions: {}, exited_chars: [], lighting_baseline: "",
      hook_type: "expression-beat",
      shot_description: "（待填写）新镜头的画面描述：场景、景别、运动。",
      per_second: [], narration: "", dialogue: [], sfx: [],
      mode: "I2VA", video_model: "H3", resolution_tier: "768P",
      aspect: doc.aspect || "9:16", references: [],
      first_frame: "", last_frame: "",
      negative: "morphing, flickering, distorted face, extra fingers, blurry, low quality, watermark, text overlay",
      continuity_type: "hard_cut", airlock_s: 0.0, seed: 0,
    });
    EDIT_IDX = EDIT_SHOTS.length - 1;
    renderShotEditor();
    $("#se-mask").classList.add("open");
    $("#se-modal").classList.add("open");
  })();
}
function renderShotEditor() {
  const sh = EDIT_SHOTS[EDIT_IDX];
  if (!sh) return;
  EDIT_PS = JSON.parse(JSON.stringify(sh.per_second || []));
  $("#se-id").textContent = sh.shot_id;
  const body = $("#se-body");
  body.innerHTML = `
    <div class="panel" style="margin:0 0 12px;padding:12px">
      <div class="param-grid" style="grid-template-columns:repeat(auto-fill,minmax(120px,1fr))">
        <div class="param"><label>镜头ID</label><input id="se-shotid" value="${esc(sh.shot_id)}"></div>
        <div class="param"><label>时长 (s)</label><input id="se-dur" type="number" value="${sh.duration_s??5}"></div>
        <div class="param"><label>剪辑到 (s)</label><input id="se-edits" type="number" value="${sh.edit_target_s||sh.duration_s||3}"></div>
        <div class="param"><label>方式 mode</label><select id="se-mode">${modeOptions(sh.mode||"I2VA")}</select></div>
        <div class="param"><label>钩子 hook</label><select id="se-hook">${hookOptions(sh.hook_type||"expression-beat")}</select></div>
        <div class="param"><label>seed (0=auto)</label><input id="se-seed" type="number" value="${sh.seed??0}"></div>
        <div class="param"><label>连续性</label><select id="se-cont">${["hard_cut","latent_pin","motion_ref"].map(c=>`<option ${c===sh.continuity_type?"selected":""}>${c}</option>`).join("")}</select></div>
        <div class="param"><label>首帧路径</label><input id="se-first" placeholder="空=自动" value="${esc(sh.first_frame||"")}"></div>
      </div>
      <div class="param"><label>画面描述 (shot_description)</label>
        <textarea id="se-desc" rows="3" style="width:100%;margin-top:5px;background:var(--bg2);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:8px">${esc(sh.shot_description||"")}</textarea></div>
      <div class="param"><label>跨镜衔接 (continuity_handoff)</label>
        <textarea id="se-handoff" rows="2" style="width:100%;margin-top:5px;background:var(--bg2);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:8px">${esc(sh.continuity_handoff||"")}</textarea></div>
      <div class="param"><label>对白 (每行一句, 说话人:台词)</label>
        <textarea id="se-dia" rows="2" style="width:100%;margin-top:5px;background:var(--bg2);color:var(--txt);border:1px solid var(--line);border-radius:6px;padding:8px">${(sh.dialogue||[]).map(x=>`${x.speaker_id||"S1"}:${(x.text||"")}`).join("\n")}</textarea></div>
      <div class="param"><label>音效 SFX (逗号分隔)</label>
        <input id="se-sfx" style="width:100%;margin-top:5px" value="${esc((sh.sfx||[]).join(", "))}"></div>
    </div>
    <div class="panel" style="margin:0 0 12px;padding:12px">
      <div class="flex" style="justify-content:space-between;margin-bottom:8px">
        <b>逐秒指令 per_second</b>
        <button class="btn-sm" id="se-add-ps">＋ 秒</button>
      </div>
      <div id="se-ps-list"></div>
    </div>
    <div class="flex" style="justify-content:flex-end;gap:8px">
      <button class="btn ghost" id="se-cancel">取消</button>
      <button class="btn" id="se-save">保存镜头</button>
    </div>`;
  $("#se-close").onclick = () => closeShotEditor();
  $("#se-cancel").onclick = () => closeShotEditor();
  $("#se-mask").onclick = () => closeShotEditor();
  $("#se-del").onclick = () => delShot();
  $("#se-add-ps").onclick = () => { EDIT_PS.push({rng:`${EDIT_PS.length}-${EDIT_PS.length+1}s`,action:"",camera:"",spatial:"",audio:"",handoff:""}); renderPSRows(); };
  $("#se-save").onclick = () => saveShotEditor();
  renderPSRows();
}
function renderPSRows() {
  const list = $("#se-ps-list");
  list.innerHTML = EDIT_PS.map((p,i)=>`
    <div class="ps-row" style="border:1px solid var(--line);border-radius:8px;padding:8px;margin-bottom:8px">
      <div class="flex" style="justify-content:space-between;margin-bottom:6px">
        <input class="ps-rng" value="${esc(p.rng)}" style="width:80px;background:var(--bg2);color:var(--txt);border:1px solid var(--line);border-radius:5px;padding:3px 6px">
        <span class="dim" style="font-size:10.5px">第 ${i+1} 秒</span>
        <button class="btn-sm danger" onclick="window._delPS(${i})">删</button>
      </div>
      ${[{k:'action',l:'动作'},{k:'camera',l:'机位'},{k:'spatial',l:'空间'},{k:'audio',l:'声音'},{k:'handoff',l:'衔接'}].map(f=>
        `<div class="flex" style="margin-bottom:4px"><span style="width:42px;flex:none;font-size:11px;color:var(--mut)">${f.l}</span>
         <input class="ps-${f.k}" value="${esc(p[f.k]||"")}" placeholder="见字段提示" style="flex:1;background:var(--bg2);color:var(--txt);border:1px solid var(--line);border-radius:5px;padding:3px 6px"></div>`).join("")}
    </div>`).join("") || `<div class="empty-note">还没有逐秒指令，点「＋ 秒」添加。</div>`;
}
window._delPS = (i) => { EDIT_PS.splice(i,1); renderPSRows(); };
function closeShotEditor() {
  $("#se-modal").classList.remove("open");
  $("#se-mask").classList.remove("open");
  EDIT_PROJECT = null; EDIT_SHOTS = null; EDIT_IDX = -1;
}
function collectPS() {
  const list = $("#se-ps-list");
  const rows = list.querySelectorAll(".ps-row");
  return Array.from(rows).map(r => ({
    rng: r.querySelector(".ps-rng").value.trim() || `${EDIT_PS[Array.from(rows).indexOf(r)]?.rng||""}`,
    action: r.querySelector(".ps-action").value, camera: r.querySelector(".ps-camera").value,
    spatial: r.querySelector(".ps-spatial").value, audio: r.querySelector(".ps-audio").value,
    handoff: r.querySelector(".ps-handoff").value,
  })).filter(p => p.action || p.camera || p.spatial || p.audio || p.handoff);
}
async function saveShotEditor() {
  const sh = EDIT_SHOTS[EDIT_IDX];
  if (!sh) return;
  sh.shot_id = $("#se-shotid").value.trim() || sh.shot_id;
  sh.duration_s = parseFloat($("#se-dur").value) || 5;
  sh.edit_target_s = parseFloat($("#se-edits").value) || sh.duration_s;
  sh.mode = $("#se-mode").value; sh.hook_type = $("#se-hook").value;
  sh.seed = parseInt($("#se-seed").value,10) || 0;
  sh.continuity_type = $("#se-cont").value;
  sh.first_frame = $("#se-first").value.trim();
  sh.shot_description = $("#se-desc").value;
  sh.continuity_handoff = $("#se-handoff").value;
  sh.sfx = $("#se-sfx").value.split(/[,，]/).map(s=>s.trim()).filter(Boolean);
  sh.dialogue = $("#se-dia").value.split("\n").map(l=>l.trim()).filter(Boolean).map(l=>{
    const i = l.indexOf(":");
    return i>0 ? {text:l.slice(i+1).trim(), speaker_id:l.slice(0,i).trim(), is_diegetic:true}
               : {text:l, speaker_id:"S1", is_diegetic:true};
  });
  sh.per_second = collectPS();
  EDIT_PROJECT.shots = EDIT_SHOTS;
  const btn = $("#se-save"); btn.disabled = true; btn.textContent = "保存中…";
  try {
    const r = await API.post("/api/stage/save_project", { path: S.projectPath, project: EDIT_PROJECT });
    toast("镜头已保存 ✓", "ok");
    closeShotEditor();
    go("board");   // re-render board
  } catch (e) { toast("保存失败: " + e.message, "bad"); }
  btn.disabled = false; btn.textContent = "保存镜头";
}
async function delShot() {
  if (!EDIT_SHOTS || EDIT_IDX < 0) return;
  if (!confirm("删除该镜头？")) return;
  EDIT_SHOTS.splice(EDIT_IDX, 1);
  EDIT_PROJECT.shots = EDIT_SHOTS;
  try {
    await API.post("/api/stage/save_project", { path: S.projectPath, project: EDIT_PROJECT });
    toast("镜头已删除", "ok");
    closeShotEditor();
    go("board");
  } catch (e) { toast("删除失败: " + e.message, "bad"); }
}
