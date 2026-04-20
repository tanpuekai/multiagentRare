(function () {
  const { useEffect, useMemo, useRef, useState } = React;
  const html = htm.bind(React.createElement);

  const ICON_PATHS = {
    plus: "M12 5v14M5 12h14",
    paste: "M8.5 3.5h6l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 7.5 19V5A1.5 1.5 0 0 1 9 3.5zM14.5 3.5V8H19M10 11.25h5.5M10 14.75h5.5M10 18.25h3.5",
    reset: "M3 12a9 9 0 1 0 3-6.708M3 4v5h5",
    pulse: "M3 12h4l2.4-4.5 4.2 9 2.3-4.5H21",
    arrowUp: "M12 19V5M6 11l6-6 6 6",
    singleModel: "M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16M10.6 9.4 12 8.2v7.6",
    close: "M6 6l12 12M18 6 6 18",
    settings: "M12 3.25h.32a1.6 1.6 0 0 1 1.58 1.37l.22 1.51c.46.14.9.33 1.31.54l1.24-.83a1.6 1.6 0 0 1 2.08.18l.23.23a1.6 1.6 0 0 1 .18 2.08l-.83 1.24c.21.41.4.85.54 1.31l1.51.22A1.6 1.6 0 0 1 20.75 12v.32a1.6 1.6 0 0 1-1.37 1.58l-1.51.22c-.14.46-.33.9-.54 1.31l.83 1.24a1.6 1.6 0 0 1-.18 2.08l-.23.23a1.6 1.6 0 0 1-2.08.18l-1.24-.83c-.41.21-.85.4-1.31.54l-.22 1.51a1.6 1.6 0 0 1-1.58 1.37H12a1.6 1.6 0 0 1-1.58-1.37l-.22-1.51a6.7 6.7 0 0 1-1.31-.54l-1.24.83a1.6 1.6 0 0 1-2.08-.18l-.23-.23a1.6 1.6 0 0 1-.18-2.08l.83-1.24a6.7 6.7 0 0 1-.54-1.31l-1.51-.22A1.6 1.6 0 0 1 3.25 12.32V12a1.6 1.6 0 0 1 1.37-1.58l1.51-.22c.14-.46.33-.9.54-1.31l-.83-1.24a1.6 1.6 0 0 1 .18-2.08l.23-.23a1.6 1.6 0 0 1 2.08-.18l1.24.83c.41-.21.85-.4 1.31-.54l.22-1.51A1.6 1.6 0 0 1 12 3.25zm0 5.15a3.6 3.6 0 1 0 0 7.2 3.6 3.6 0 0 0 0-7.2z",
    history: "M12 8v5l3 2M12 3a9 9 0 1 0 9 9",
    account: "M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-4 0-7 2-7 4.5V20h14v-1.5C19 16 16 14 12 14z",
    users: "M16 11a3 3 0 1 0-2.999-3A3 3 0 0 0 16 11zm-8 1a3 3 0 1 0-3-3 3 3 0 0 0 3 3zm0 2c-2.9 0-5 1.45-5 3.5V20h10v-2.5C13 15.45 10.9 14 8 14zm8 0c-.66 0-1.28.08-1.86.22 1.15.7 1.86 1.72 1.86 3.28V20h5v-2.1c0-2.15-2.07-3.9-5-3.9z",
    hub: "M12 3v4M5 8l3 2M19 8l-3 2M12 21v-4M5 16l3-2M19 16l-3-2M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    diagnostics: "M3 12h4l2.1-3.6 3 8.4 3.2-9.8 2 5H21",
    newChat: "M15.8 4.9A8 8 0 0 0 4.2 12.1M4.4 13.8A8 8 0 0 0 18.8 14.3M12 8.8v6.4M8.8 12h6.4",
    spark: "M12 3l1.8 4.8L18 9.6l-4.2 1.2L12 15.6l-1.8-4.8L6 9.6l4.2-1.8z",
    chevronLeft: "M15 6 9 12l6 6",
    panelToggle: "M4.5 5.5h15v13h-15zM9 5.5v13M14.5 9.25 11.5 12l3 2.75",
    logout: "M15 17l5-5-5-5M20 12H9M11 19H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5",
  };

  const AUTH_TOKEN_KEY = "raremdt.authToken";

  const SETTINGS_SECTION_COPY = {
    医生档案: {
      title: "账户设置",
      copy: "维护医生档案、所属医院与专业方向，让系统输出更贴近真实医院部署场景。",
    },
    系统设置: {
      title: "API 与智能体配置",
      copy: "管理接口、编排拓扑、默认科室与多智能体工位。",
    },
    历史记录: {
      title: "会诊历史",
      copy: "查看既往会诊摘要，并可直接回到主工作区继续查看记录。",
    },
    账户管理: {
      title: "账户管理",
      copy: "管理员可查看账户、查询概览，并增删或停用账户。",
    },
  };

  const SLASH_MENU_TREE = [
    {
      id: "taskType",
      label: "任务类型",
      hint: "快速指定输出目标",
      searchText: "诊断意见 治疗规划 康复计划 分析规划 任务类型",
      children: [
        { id: "analysisPlan", label: "请提供分析规划", tokenLabel: "任务类型·请提供分析规划" },
        { id: "diagnosticOpinion", label: "请做出诊断意见", tokenLabel: "任务类型·请做出诊断意见" },
        { id: "treatmentPlan", label: "请做出治疗规划", tokenLabel: "任务类型·请做出治疗规划" },
        { id: "rehabPlan", label: "请做出康复计划", tokenLabel: "任务类型·请做出康复计划" },
      ],
    },
    {
      id: "gender",
      label: "性别",
      hint: "患者性别",
      dividerBefore: true,
      searchText: "男 女 未知 性别",
      children: [
        { id: "male", label: "男", tokenLabel: "性别·男", value: "male" },
        { id: "female", label: "女", tokenLabel: "性别·女", value: "female" },
        { id: "unknown", label: "未知", tokenLabel: "性别·未知", value: "unknown" },
      ],
    },
    {
      id: "internal",
      label: "内科",
      hint: "10 个内科专科",
      searchText: "心内科 呼吸内科 消化内科 神经内科 肾内科 血液科 内分泌科 风湿免疫科 感染科 老年医学科",
      children: [
        { id: "cardiology", label: "心内科", tokenLabel: "内科·心内科" },
        { id: "respiratory", label: "呼吸内科", tokenLabel: "内科·呼吸内科" },
        { id: "gastro", label: "消化内科", tokenLabel: "内科·消化内科" },
        { id: "neuro", label: "神经内科", tokenLabel: "内科·神经内科" },
        { id: "renal", label: "肾内科", tokenLabel: "内科·肾内科" },
        { id: "hematology", label: "血液科", tokenLabel: "内科·血液科" },
        { id: "endocrine", label: "内分泌科", tokenLabel: "内科·内分泌科" },
        { id: "rheumatology", label: "风湿免疫科", tokenLabel: "内科·风湿免疫科" },
        { id: "infectious", label: "感染科", tokenLabel: "内科·感染科" },
        { id: "geriatrics", label: "老年医学科", tokenLabel: "内科·老年医学科" },
      ],
    },
    {
      id: "surgical",
      label: "外科",
      hint: "10 个外科专科",
      searchText: "普外科 骨科 神经外科 心胸外科 泌尿外科 肝胆外科 乳腺外科 血管外科 烧伤整形科 小儿外科",
      children: [
        { id: "general", label: "普外科", tokenLabel: "外科·普外科" },
        { id: "orthopedics", label: "骨科", tokenLabel: "外科·骨科" },
        { id: "neurosurgery", label: "神经外科", tokenLabel: "外科·神经外科" },
        { id: "thoracic", label: "心胸外科", tokenLabel: "外科·心胸外科" },
        { id: "urology", label: "泌尿外科", tokenLabel: "外科·泌尿外科" },
        { id: "hepatobiliary", label: "肝胆外科", tokenLabel: "外科·肝胆外科" },
        { id: "breast", label: "乳腺外科", tokenLabel: "外科·乳腺外科" },
        { id: "vascular", label: "血管外科", tokenLabel: "外科·血管外科" },
        { id: "plastic", label: "烧伤整形科", tokenLabel: "外科·烧伤整形科" },
        { id: "pediatric", label: "小儿外科", tokenLabel: "外科·小儿外科" },
      ],
    },
    {
      id: "age",
      label: "年龄段",
      hint: "常用年龄标签",
      searchText: "新生儿 婴儿 幼儿 学龄前 学龄期 青少年 成人 老年",
      children: [
        { id: "newborn", label: "新生儿", tokenLabel: "年龄段·新生儿" },
        { id: "infant", label: "婴儿", tokenLabel: "年龄段·婴儿" },
        { id: "toddler", label: "幼儿", tokenLabel: "年龄段·幼儿" },
        { id: "preschool", label: "学龄前", tokenLabel: "年龄段·学龄前" },
        { id: "school", label: "学龄期", tokenLabel: "年龄段·学龄期" },
        { id: "teen", label: "青少年", tokenLabel: "年龄段·青少年" },
        { id: "adult", label: "成人", tokenLabel: "年龄段·成人" },
        { id: "elderly", label: "老年", tokenLabel: "年龄段·老年" },
      ],
    },
    {
      id: "material",
      label: "资料类型",
      hint: "病史、检查、化验",
      searchText: "病史 查体 检验 影像 病理 基因 用药 家族史",
      children: [
        { id: "history", label: "病史", tokenLabel: "资料·病史" },
        { id: "exam", label: "查体", tokenLabel: "资料·查体" },
        { id: "lab", label: "检验", tokenLabel: "资料·检验" },
        { id: "imaging", label: "影像", tokenLabel: "资料·影像" },
        { id: "pathology", label: "病理", tokenLabel: "资料·病理" },
        { id: "genetics", label: "基因", tokenLabel: "资料·基因" },
        { id: "medication", label: "用药", tokenLabel: "资料·用药" },
        { id: "family", label: "家族史", tokenLabel: "资料·家族史" },
      ],
    },
    {
      id: "urgency",
      label: "紧急程度",
      hint: "会诊优先级",
      searchText: "常规 加急 危重 紧急",
      children: [
        { id: "routine", label: "常规", tokenLabel: "紧急程度·常规" },
        { id: "priority", label: "加急", tokenLabel: "紧急程度·加急" },
        { id: "critical", label: "危重", tokenLabel: "紧急程度·危重" },
      ],
    },
  ];

  const AGENT_MENU_TREE = [
    {
      id: "auto",
      label: "@Auto",
      hint: "从头到尾自动执行 planner 到 report",
      searchText: "auto 自动 全流程 planner executor decider report",
      tokenLabel: "@Auto",
      value: "auto",
    },
    {
      id: "planner",
      label: "@Planner",
      hint: "根据输入生成执行计划",
      searchText: "planner 计划 执行 workflow",
      tokenLabel: "@Planner",
      value: "planner",
    },
    {
      id: "executor",
      label: "@Executor",
      hint: "按计划执行并记录证据",
      searchText: "executor 证据 grounding 多模态 执行",
      tokenLabel: "@Executor",
      value: "executor",
    },
    {
      id: "decider",
      label: "@Decider",
      hint: "融合执行证据并形成诊断判断",
      searchText: "decider 诊断 判断 证据 融合",
      tokenLabel: "@Decider",
      value: "decider",
    },
    {
      id: "report",
      label: "@Report",
      hint: "生成带证据引用的医疗报告",
      searchText: "report report generator 报告 医疗报告 证据引用",
      tokenLabel: "@Report",
      value: "report",
    },
  ];

  function commandTreeForTrigger(trigger) {
    return trigger === "@" ? AGENT_MENU_TREE : SLASH_MENU_TREE;
  }

  function isPlannerInvocation(text) {
    return /@planner\b/i.test(String(text || ""));
  }

  function isAutoInvocation(text) {
    return /@auto\b/i.test(String(text || ""));
  }

  function isExecutorInvocation(text) {
    return /@executor\b/i.test(String(text || ""));
  }

  function isDeciderInvocation(text) {
    return /@decider\b/i.test(String(text || ""));
  }

  function isReportInvocation(text) {
    return /@(?:report\s*generator|reportgenerator|report)\b/i.test(String(text || ""));
  }

  function normalizeSearchText(value) {
    return String(value || "").toLowerCase().replace(/\s+/g, "");
  }

  function normalizeCaseBlocks(blocks) {
    const next = [];
    for (const block of blocks || []) {
      if (!block) {
        continue;
      }
      if (block.type === "token") {
        if (!block.label) {
          continue;
        }
        next.push({
          type: "token",
          label: block.label,
          text: block.text || `【${block.label}】`,
          category: block.category || "",
          value: block.value || "",
        });
        continue;
      }
      const text = String(block.text || "");
      if (!text) {
        continue;
      }
      if (next.length && next[next.length - 1].type === "text") {
        next[next.length - 1].text += text;
      } else {
        next.push({ type: "text", text });
      }
    }
    return next;
  }

  function blocksToPlainText(blocks) {
    return normalizeCaseBlocks(blocks)
      .map((block) => (block.type === "token" ? block.text : block.text))
      .join("");
  }

  function serializeCaseBlocks(blocks) {
    return JSON.stringify(normalizeCaseBlocks(blocks));
  }

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => reject(new Error(`无法读取文件 ${file?.name || ""}`.trim()));
      reader.readAsDataURL(file);
    });
  }

  function loadImageElement(dataUrl) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("无法解析上传图像。"));
      image.src = dataUrl;
    });
  }

  async function normalizeImageForAgent(file, sourceDataUrl) {
    const source = sourceDataUrl || (await readFileAsDataUrl(file));
    if (!source.startsWith("data:image/")) {
      throw new Error(`不支持的图像格式: ${file?.name || ""}`.trim());
    }
    const image = await loadImageElement(source);
    const maxEdge = 1024;
    const scale = Math.min(1, maxEdge / Math.max(image.naturalWidth || image.width, image.naturalHeight || image.height));
    const width = Math.max(1, Math.round((image.naturalWidth || image.width) * scale));
    const height = Math.max(1, Math.round((image.naturalHeight || image.height) * scale));
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("无法初始化图像标准化上下文。");
    }
    context.drawImage(image, 0, 0, width, height);
    return {
      name: file.name,
      media_type: "image/jpeg",
      data_url: canvas.toDataURL("image/jpeg", 0.92),
    };
  }

  async function serializeImageAssets(files) {
    const payloads = [];
    for (const file of Array.from(files || []).slice(0, 2)) {
      const displayDataUrl = await readFileAsDataUrl(file);
      const normalized = await normalizeImageForAgent(file, displayDataUrl);
      payloads.push({
        name: file.name,
        media_type: file.type || normalized.media_type,
        data_url: normalized.data_url,
        display_data_url: displayDataUrl,
      });
    }
    return payloads;
  }

  function imageAssetsFromSubmission(submission) {
    return Array.isArray(submission?.image_assets) ? submission.image_assets.filter((item) => item?.display_data_url || item?.data_url) : [];
  }

  function imageSrcFromAsset(asset) {
    return asset?.display_data_url || asset?.data_url || "";
  }

  function groundingPayload(record) {
    return record?.evidence?.grounding && typeof record.evidence.grounding === "object" ? record.evidence.grounding : null;
  }

  function hasGroundingEvidence(record) {
    const grounding = groundingPayload(record);
    if (!grounding) {
      return false;
    }
    const boundary = Array.isArray(grounding.boundary_points) ? grounding.boundary_points : [];
    const bbox = Array.isArray(grounding.bbox) ? grounding.bbox : Array.isArray(grounding.coarse_bbox) ? grounding.coarse_bbox : [];
    return Boolean(boundary.length || bbox.length === 4);
  }

  function overlayColor(index) {
    const palette = ["#d43f2e", "#2563eb", "#0f766e", "#b45309", "#7c3aed", "#be123c", "#0369a1"];
    return palette[index % palette.length];
  }

  function buildTurnList(session) {
    if (Array.isArray(session?.turns) && session.turns.length) {
      return session.turns;
    }
    if (session?.submission && session?.result) {
      return [
        {
          turn_id: `legacy-${session.timestamp}-${session.result.execution_mode || "result"}`,
          timestamp: session.timestamp,
          user_input: session.submission.case_summary,
          submission: session.submission,
          result: session.result,
        },
      ];
    }
    return [];
  }

  function isAutoTurn(turn) {
    return /(^|\s)@auto\b/i.test(String(turn?.user_input || ""));
  }

  function autoFinalTurnForSession(session) {
    const turns = buildTurnList(session);
    const latestTurn = turns[turns.length - 1];
    if (!isAutoTurn(latestTurn)) {
      return null;
    }
    if (latestTurn?.result?.execution_mode === "report") {
      return latestTurn;
    }
    return null;
  }

  function visibleTurnsForSession(session) {
    const turns = buildTurnList(session);
    const autoFinalTurn = autoFinalTurnForSession(session);
    if (autoFinalTurn) {
      return [autoFinalTurn];
    }
    return turns.filter((turn) => !isAutoTurn(turn) || turn?.result?.execution_mode === "report");
  }

  function latestApprovalForTurn(session, turnId) {
    const approvals = Array.isArray(session?.doctor_approvals) ? session.doctor_approvals : [];
    const matched = approvals.filter((item) => item?.turn_id === turnId);
    return matched.length ? matched[matched.length - 1] : null;
  }

  function workflowRevisionValue(result) {
    return String(result?.workflow_revision || "").trim();
  }

  function workflowEntriesForSession(session) {
    const turns = buildTurnList(session);
    const entries = [];
    let currentRevision = "";
    turns.forEach((turn, index) => {
      const mode = String(turn?.result?.execution_mode || "").trim();
      const explicitRevision = workflowRevisionValue(turn?.result);
      let revision = "";
      if (mode === "planner") {
        revision = explicitRevision || String(turn?.turn_id || `planner-${index + 1}`).trim();
        currentRevision = revision;
      } else {
        revision = explicitRevision || currentRevision;
        if (explicitRevision) {
          currentRevision = explicitRevision;
        }
      }
      entries.push({ turn, revision });
    });
    return entries;
  }

  function currentWorkflowRevision(session) {
    const entries = workflowEntriesForSession(session);
    for (let index = entries.length - 1; index >= 0; index -= 1) {
      if (entries[index]?.turn?.result?.execution_mode === "planner" && entries[index]?.revision) {
        return entries[index].revision;
      }
    }
    for (let index = entries.length - 1; index >= 0; index -= 1) {
      if (entries[index]?.revision) {
        return entries[index].revision;
      }
    }
    return "";
  }

  function workflowEntryForTurn(session, turn) {
    if (!turn) {
      return null;
    }
    const turnId = String(turn.turn_id || "");
    return workflowEntriesForSession(session).find((entry) => String(entry?.turn?.turn_id || "") === turnId) || null;
  }

  function turnWorkflowRevision(session, turn) {
    return workflowEntryForTurn(session, turn)?.revision || workflowRevisionValue(turn?.result);
  }

  function latestTurnByMode(session, mode, options = {}) {
    const { currentOnly = false, workflowRevision = null } = options;
    const entries = workflowEntriesForSession(session);
    const targetRevision = workflowRevision === null
      ? (currentOnly ? currentWorkflowRevision(session) : "")
      : String(workflowRevision || "").trim();
    for (let index = entries.length - 1; index >= 0; index -= 1) {
      const entry = entries[index];
      if (entry?.turn?.result?.execution_mode !== mode) {
        continue;
      }
      if ((currentOnly || workflowRevision !== null) && targetRevision && entry.revision !== targetRevision) {
        continue;
      }
      return entry.turn;
    }
    return null;
  }

  function latestExecutorTurn(session, options = {}) {
    return latestTurnByMode(session, "executor", options);
  }

  function hasReportTurn(session, options = {}) {
    return Boolean(latestTurnByMode(session, "report", options));
  }

  function isTurnStale(session, turn) {
    if (!turn) {
      return false;
    }
    const activeRevision = currentWorkflowRevision(session);
    const turnRevision = turnWorkflowRevision(session, turn);
    return Boolean(activeRevision && turnRevision && turnRevision !== activeRevision);
  }

  function currentCaseFeedback(session) {
    const feedback = session?.case_feedback || null;
    if (!feedback) {
      return null;
    }
    const activeRevision = currentWorkflowRevision(session);
    if (!activeRevision) {
      return feedback;
    }
    const explicitRevision = String(feedback.workflow_revision || "").trim();
    if (explicitRevision) {
      return explicitRevision === activeRevision ? feedback : null;
    }
    const latestReport = latestTurnByMode(session, "report");
    if (!latestReport) {
      return null;
    }
    return turnWorkflowRevision(session, latestReport) === activeRevision ? feedback : null;
  }

  function approvalStatusForTurn(session, turn) {
    if (!turn?.turn_id) {
      return "none";
    }
    const approval = latestApprovalForTurn(session, turn.turn_id);
    if (approval?.action === "approved") {
      return "approved";
    }
    if (approval?.action === "revision_requested") {
      return "needs_revision";
    }
    return "needs_review";
  }

  function clinicalWorkflowStages(session) {
    const activeRevision = currentWorkflowRevision(session);
    const definitions = [
      { mode: "planner", label: "Planner", copy: "制定可执行计划" },
      { mode: "executor", label: "Executor", copy: "采集可复核证据" },
      { mode: "decider", label: "Decider", copy: "形成证据化判断" },
      { mode: "report", label: "Report", copy: "交付报告 artifact" },
    ];
    return definitions.map((stage) => {
      const turn = latestTurnByMode(session, stage.mode, { currentOnly: true, workflowRevision: activeRevision });
      const latestHistoricalTurn = latestTurnByMode(session, stage.mode);
      if (!turn) {
        if (latestHistoricalTurn && activeRevision && turnWorkflowRevision(session, latestHistoricalTurn) !== activeRevision) {
          return { ...stage, turn: null, staleTurn: latestHistoricalTurn, approval: null, status: "stale" };
        }
        return { ...stage, turn: null, staleTurn: null, approval: null, status: "pending" };
      }
      const approval = latestApprovalForTurn(session, turn.turn_id);
      let status = approvalStatusForTurn(session, turn);
      if (stage.mode === "report" && currentCaseFeedback(session)) {
        status = "accepted";
      }
      return { ...stage, turn, staleTurn: null, approval, status };
    });
  }

  function workflowStageText(status) {
    if (status === "accepted") {
      return "已评分";
    }
    if (status === "stale") {
      return "已失效";
    }
    if (status === "approved") {
      return "已审批";
    }
    if (status === "needs_revision") {
      return "需修改";
    }
    if (status === "needs_review") {
      return "待复核";
    }
    return "待执行";
  }

  function knownEvidenceIdsFromRecords(records) {
    return (Array.isArray(records) ? records : [])
      .map((record, index) => numericStepId(record?.step_id, index + 1))
      .filter(Boolean)
      .map((stepId) => `E${stepId}`);
  }

  function collectEvidenceIds(value, targetSet) {
    if (Array.isArray(value)) {
      value.forEach((item) => collectEvidenceIds(item, targetSet));
      return;
    }
    if (value && typeof value === "object") {
      Object.entries(value).forEach(([key, item]) => {
        if (/evidence_ids?$|supporting_evidence_ids|refuting_evidence_ids/i.test(key)) {
          collectEvidenceIds(item, targetSet);
        } else if (typeof item === "object") {
          collectEvidenceIds(item, targetSet);
        }
      });
      return;
    }
    const text = String(value || "").trim();
    if (/^E\d+$/i.test(text)) {
      targetSet.add(text.toUpperCase());
    }
  }

  function clinicalEvidenceStats(session) {
    const executorTurn = latestExecutorTurn(session, { currentOnly: true });
    const records = executorTurn?.result?.execution_records || [];
    const evidenceIds = knownEvidenceIdsFromRecords(records);
    const grounded = records.filter(hasGroundingEvidence).length;
    const cited = new Set();
    const deciderTurn = latestTurnByMode(session, "decider", { currentOnly: true });
    const reportTurn = latestTurnByMode(session, "report", { currentOnly: true });
    collectEvidenceIds(parseObjectJson(deciderTurn?.result?.raw_provider_payload), cited);
    collectEvidenceIds(parseObjectJson(reportTurn?.result?.raw_provider_payload), cited);
    const citedKnown = evidenceIds.filter((item) => cited.has(item));
    return {
      total: evidenceIds.length,
      grounded,
      cited: citedKnown.length,
      uncited: Math.max(0, evidenceIds.length - citedKnown.length),
    };
  }

  function nextClinicalAction(session) {
    const stages = clinicalWorkflowStages(session);
    const planner = stages.find((item) => item.mode === "planner");
    const executor = stages.find((item) => item.mode === "executor");
    const decider = stages.find((item) => item.mode === "decider");
    const report = stages.find((item) => item.mode === "report");
    if (!planner?.turn) {
      return "调用 @Planner，为当前病例生成可执行诊断计划。";
    }
    if (planner.status === "needs_review") {
      return "复核 Planner 计划，逐步通过或写清楚需要 steer 的位置。";
    }
    if (planner.status === "needs_revision") {
      return "Planner 计划已有修改意见，请根据 steer 重新生成或调整计划。";
    }
    if (executor?.status === "stale") {
      return "检测到旧版 Executor 证据已被新的 Planner 计划置为失效，请重新调用 @Executor。";
    }
    if (!executor?.turn) {
      return "调用 @Executor，按已审批计划采集图像和文本证据。";
    }
    if (executor.status === "needs_review") {
      return "复核 Executor 证据，重点检查 ROI、结论和置信度是否可接受。";
    }
    if (executor.status === "needs_revision") {
      return "Executor 证据被要求修改，请重跑问题步骤或补充 steer。";
    }
    if (decider?.status === "stale") {
      return "检测到旧版 Decider 判断已失效，请基于当前证据重新调用 @Decider。";
    }
    if (!decider?.turn) {
      return "调用 @Decider，只基于 Evidence Ledger 做诊断判断。";
    }
    if (decider.status === "needs_review") {
      return "审批 Decider 判断，确认诊断、鉴别诊断和缺失信息是否合理。";
    }
    if (decider.status === "needs_revision") {
      return "Decider 判断需要修改，请基于证据意见重新融合。";
    }
    if (report?.status === "stale") {
      return "检测到旧版报告已失效，请基于当前判断重新调用 @Report。";
    }
    if (!report?.turn) {
      return "调用 @Report，将 Decider 判断转换为带证据引用的报告 artifact。";
    }
    if (report.status === "needs_review") {
      return "审批最终报告，并确认所有关键陈述都能回到证据。";
    }
    if (!currentCaseFeedback(session)) {
      return "完成病例评分，为证据、诊断和报告留下质量数据。";
    }
    return "病例闭环已完成，可继续随访、导出或开始新病例。";
  }

  function latestCaseTask(session) {
    const turns = buildTurnList(session);
    const latest = turns[turns.length - 1];
    return String(latest?.user_input || session?.submission?.chief_complaint || session?.submission?.case_summary || "").trim();
  }

  function caseContextAlerts(submission) {
    const alerts = [];
    const assets = imageAssetsFromSubmission(submission);
    const textPresent = Boolean(String(submission?.case_summary || submission?.chief_complaint || "").trim());
    if (!textPresent) {
      alerts.push("未提供文本目标，系统将以图像内容作为主要规划依据。");
    }
    if (!assets.length) {
      alerts.push("当前病例没有可视图像证据。");
    }
    if (!String(submission?.patient_age || "").trim()) {
      alerts.push("年龄未填写。");
    }
    if (!String(submission?.patient_sex || "").trim()) {
      alerts.push("性别未填写。");
    }
    return alerts;
  }

  function evidenceFeedbackRows(session) {
    const executorTurn = latestExecutorTurn(session, { currentOnly: true });
    const records = executorTurn?.result?.execution_records || [];
    return records
      .map((record, index) => {
        const stepId = numericStepId(record?.step_id, index + 1);
        if (!stepId) {
          return null;
        }
        const display = resolveExecutionDisplay(record, executorTurn?.result?.plan_display_steps || [], index);
        return {
          evidence_id: `E${stepId}`,
          label: display?.title_zh || `证据 ${stepId}`,
        };
      })
      .filter(Boolean);
  }

  function createEditorTokenElement(token) {
    const element = document.createElement("span");
    element.className = "editor-token";
    element.contentEditable = "false";
    element.dataset.tokenLabel = token.label;
    element.dataset.tokenText = token.text || `【${token.label}】`;
    element.dataset.tokenCategory = token.category || "";
    element.dataset.tokenValue = token.value || "";
    element.textContent = token.label;
    return element;
  }

  function readEditorBlocks(editor) {
    const blocks = [];

    function pushText(text) {
      if (!text) {
        return;
      }
      blocks.push({ type: "text", text });
    }

    Array.from(editor.childNodes).forEach((node, index) => {
      if (node.nodeType === Node.TEXT_NODE) {
        pushText(node.nodeValue || "");
        return;
      }
      if (node.nodeType !== Node.ELEMENT_NODE) {
        return;
      }

      const element = node;
      if (element.classList.contains("editor-token")) {
        const tokenLabel = element.dataset.tokenLabel || element.textContent || "";
        const tokenValue = element.dataset.tokenValue || "";
        if (tokenValue === "auto" || tokenLabel === "@Auto") {
          blocks.push({
            type: "token",
            label: tokenLabel || "@Auto",
            text: "@Auto",
            category: "agent",
            value: "auto",
          });
          return;
        }
        if (tokenValue === "planner" || tokenLabel === "@Planner") {
          blocks.push({
            type: "token",
            label: tokenLabel || "@Planner",
            text: "@Planner",
            category: "agent",
            value: "planner",
          });
          return;
        }
        if (tokenValue === "executor" || tokenLabel === "@Executor") {
          blocks.push({
            type: "token",
            label: tokenLabel || "@Executor",
            text: "@Executor",
            category: "agent",
            value: "executor",
          });
          return;
        }
        if (tokenValue === "decider" || tokenLabel === "@Decider") {
          blocks.push({
            type: "token",
            label: tokenLabel || "@Decider",
            text: "@Decider",
            category: "agent",
            value: "decider",
          });
          return;
        }
        if (tokenValue === "report" || tokenLabel === "@Report" || tokenLabel === "@Report Generator") {
          blocks.push({
            type: "token",
            label: tokenLabel || "@Report",
            text: "@Report",
            category: "agent",
            value: "report",
          });
          return;
        }
        blocks.push({
          type: "token",
          label: element.dataset.tokenLabel || element.textContent || "",
          text: element.dataset.tokenText || `【${element.dataset.tokenLabel || element.textContent || ""}】`,
          category: element.dataset.tokenCategory || "",
          value: element.dataset.tokenValue || "",
        });
        return;
      }

      if (element.tagName === "BR") {
        pushText("\n");
        return;
      }

      pushText(element.textContent || "");
      if (index < editor.childNodes.length - 1) {
        pushText("\n");
      }
    });

    return normalizeCaseBlocks(blocks);
  }

  function renderEditorBlocks(editor, blocks) {
    editor.innerHTML = "";
    normalizeCaseBlocks(blocks).forEach((block) => {
      if (block.type === "token") {
        editor.appendChild(createEditorTokenElement(block));
      } else {
        editor.appendChild(document.createTextNode(block.text));
      }
    });
  }

  function getSlashItems(path, trigger = "/") {
    let current = commandTreeForTrigger(trigger);
    for (const step of path || []) {
      const matched = current.find((item) => item.id === step);
      if (!matched || !matched.children) {
        return [];
      }
      current = matched.children;
    }
    return current;
  }

  function filterSlashItems(items, query) {
    if (!query) {
      return items;
    }
    const needle = normalizeSearchText(query);
    return items.filter((item) =>
      normalizeSearchText([item.label, item.hint, item.searchText, item.tokenLabel].filter(Boolean).join(" ")).includes(needle)
    );
  }

  function buildSlashToken(item, path, trigger = "/") {
    const parents = path.map((step) => getSlashItems([], trigger).find((root) => root.id === step)).filter(Boolean);
    const category = parents.length ? parents[parents.length - 1].label : "";
    const label = item.tokenLabel || (category ? `${category}·${item.label}` : item.label);
    return {
      type: "token",
      label,
      text: `【${label}】`,
      category: category || "",
      value: item.value || item.id || item.label,
    };
  }

  function placeCaretAfterNode(node) {
    const selection = window.getSelection();
    if (!selection) {
      return;
    }
    const range = document.createRange();
    if (node.nodeType === Node.TEXT_NODE) {
      range.setStart(node, node.nodeValue.length);
    } else {
      range.setStartAfter(node);
    }
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  function ensureEditorSelection(editor) {
    const selection = window.getSelection();
    if (!selection) {
      return null;
    }
    if (!selection.rangeCount || !editor.contains(selection.anchorNode)) {
      const range = document.createRange();
      range.selectNodeContents(editor);
      range.collapse(false);
      selection.removeAllRanges();
      selection.addRange(range);
    }
    return selection;
  }

  function insertPlainTextAtSelection(editor, text) {
    const selection = ensureEditorSelection(editor);
    if (!selection || !selection.rangeCount) {
      return null;
    }
    const range = selection.getRangeAt(0);
    range.deleteContents();
    const node = document.createTextNode(text);
    range.insertNode(node);
    placeCaretAfterNode(node);
    return node;
  }

  function getSlashTriggerContext(editor, wrap) {
    const selection = window.getSelection();
    if (!selection || !selection.rangeCount || !selection.isCollapsed) {
      return null;
    }

    let node = selection.anchorNode;
    let offset = selection.anchorOffset;
    if (!node || !editor.contains(node)) {
      return null;
    }

    if (node.nodeType !== Node.TEXT_NODE) {
      if (node === editor && offset > 0) {
        const previous = node.childNodes[offset - 1];
        if (previous && previous.nodeType === Node.TEXT_NODE) {
          node = previous;
          offset = previous.nodeValue.length;
        } else {
          return null;
        }
      } else {
        return null;
      }
    }

    const textBefore = (node.nodeValue || "").slice(0, offset);
    const triggerCandidates = [
      { trigger: "/", index: textBefore.lastIndexOf("/") },
      { trigger: "@", index: textBefore.lastIndexOf("@") },
    ].filter((item) => item.index >= 0);
    if (!triggerCandidates.length) {
      return null;
    }
    const activeTrigger = triggerCandidates.sort((left, right) => right.index - left.index)[0];
    const slashIndex = activeTrigger.index;
    const trigger = activeTrigger.trigger;

    const query = textBefore.slice(slashIndex + 1);
    const previousChar = slashIndex > 0 ? textBefore[slashIndex - 1] : "";
    if ((previousChar && !/[\s\n([{（【，。,、；;:：-]/.test(previousChar)) || /\s/.test(query)) {
      return null;
    }

    const triggerRange = document.createRange();
    triggerRange.setStart(node, slashIndex);
    triggerRange.setEnd(node, offset);
    const caretRange = triggerRange.cloneRange();
    caretRange.collapse(false);
    const rect = caretRange.getBoundingClientRect();
    void wrap;
    const viewportMargin = 14;
    const estimatedMenuWidth = 560;
    const estimatedMenuHeight = 430;
    const left = Math.max(viewportMargin, Math.min(rect.left, window.innerWidth - estimatedMenuWidth - viewportMargin));
    const spaceBelow = window.innerHeight - rect.bottom - viewportMargin;
    const spaceAbove = rect.top - viewportMargin;
    const openDownward = spaceBelow >= 220 || spaceBelow >= spaceAbove;
    const top = openDownward
      ? Math.max(viewportMargin, Math.min(rect.bottom + 8, window.innerHeight - viewportMargin - 180))
      : Math.max(viewportMargin, rect.top - Math.min(estimatedMenuHeight, Math.max(180, spaceAbove)) - 8);
    const maxHeight = Math.max(
      180,
      openDownward
        ? window.innerHeight - top - viewportMargin
        : rect.top - viewportMargin - 8
    );

    return {
      node,
      slashIndex,
      endOffset: offset,
      query,
      trigger,
      position: {
        left,
        top,
        maxHeight: Math.min(estimatedMenuHeight, maxHeight),
        placement: openDownward ? "down" : "up",
      },
    };
  }

  function removeAdjacentToken(editor, direction) {
    const selection = window.getSelection();
    if (!selection || !selection.rangeCount || !selection.isCollapsed || !editor.contains(selection.anchorNode)) {
      return false;
    }

    let node = selection.anchorNode;
    let offset = selection.anchorOffset;
    if (node.nodeType === Node.TEXT_NODE) {
      if (direction === "backward" && offset === 0) {
        const previous = node.previousSibling;
        if (previous && previous.nodeType === Node.ELEMENT_NODE && previous.classList.contains("editor-token")) {
          previous.remove();
          return true;
        }
      }
      if (direction === "forward" && offset === node.nodeValue.length) {
        const next = node.nextSibling;
        if (next && next.nodeType === Node.ELEMENT_NODE && next.classList.contains("editor-token")) {
          next.remove();
          return true;
        }
      }
      return false;
    }

    if (node === editor) {
      const target = direction === "backward" ? node.childNodes[offset - 1] : node.childNodes[offset];
      if (target && target.nodeType === Node.ELEMENT_NODE && target.classList.contains("editor-token")) {
        target.remove();
        return true;
      }
    }

    return false;
  }

  function resolveSingleModelProvider(settings) {
    const firstRole = settings?.agent_roles?.[0] || null;
    if (!firstRole) {
      return { role: null, provider: null, providerIndex: -1 };
    }
    const providers = settings?.api_providers || [];
    const providerIndex = providers.findIndex((item) =>
      firstRole.provider_id ? item.provider_id === firstRole.provider_id : item.provider_name === firstRole.provider_name
    );
    return {
      role: firstRole,
      provider: providerIndex >= 0 ? providers[providerIndex] : null,
      providerIndex,
    };
  }

  function resolveRoleProvider(settings, roleName) {
    const role = (settings?.agent_roles || []).find((item) => item.role_name === roleName) || null;
    if (!role) {
      return { role: null, provider: null, providerIndex: -1 };
    }
    const providers = settings?.api_providers || [];
    const providerIndex = providers.findIndex((item) =>
      role.provider_id ? item.provider_id === role.provider_id : item.provider_name === role.provider_name
    );
    return {
      role,
      provider: providerIndex >= 0 ? providers[providerIndex] : null,
      providerIndex,
    };
  }

  function resolveRoleExecution(settings, roleName) {
    const { role, provider } = resolveRoleProvider(settings, roleName);
    if (!role) {
      return { roleName, providerName: "未配置", modelName: "未配置模型" };
    }
    return {
      roleName: role.role_name || roleName,
      providerName: providerOptionLabel(provider) || role.provider_name || "未配置",
      modelName: provider?.model_name || "未配置模型",
    };
  }

  function resolveSingleModelExecution(settings) {
    const { role: firstRole, provider } = resolveSingleModelProvider(settings);
    if (!firstRole) {
      return { roleName: "", providerName: "未配置", modelName: "未配置" };
    }
    return {
      roleName: firstRole.role_name || "",
      providerName: providerOptionLabel(provider) || firstRole.provider_name || "未配置",
      modelName: provider?.model_name || "未配置模型",
    };
  }

  function readAuthToken() {
    try {
      return window.localStorage.getItem(AUTH_TOKEN_KEY) || "";
    } catch (error) {
      return "";
    }
  }

  function writeAuthToken(token) {
    try {
      if (token) {
        window.localStorage.setItem(AUTH_TOKEN_KEY, token);
      } else {
        window.localStorage.removeItem(AUTH_TOKEN_KEY);
      }
    } catch (error) {}
  }

  async function fetchJson(url, options) {
    const token = readAuthToken();
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options && options.headers ? options.headers : {}),
      },
      ...options,
    });
    let payload = {};
    let rawText = "";
    try {
      rawText = await response.text();
      payload = rawText ? JSON.parse(rawText) : {};
    } catch (error) {
      payload = {};
    }
    if (!response.ok) {
      if (response.status === 401) {
        writeAuthToken("");
      }
      const detail = payload.detail || rawText || `Request failed with status ${response.status}.`;
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function cloneData(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function makeProviderId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return `provider-${window.crypto.randomUUID().slice(0, 12)}`;
    }
    return `provider-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  }

  function providerValue(provider) {
    return provider?.provider_id || provider?.provider_name || "";
  }

  function providerOptionLabel(provider) {
    if (!provider) {
      return "未配置接口";
    }
    let host = "";
    try {
      const rawEndpoint = String(provider.endpoint || "").trim();
      if (rawEndpoint) {
        host = new URL(rawEndpoint.startsWith("http") ? rawEndpoint : `https://${rawEndpoint}`).host.replace(/^www\./, "");
      }
    } catch (error) {}
    const parts = [provider.provider_name || "未命名接口"];
    if (provider.model_name) {
      parts.push(provider.model_name);
    }
    if (host) {
      parts.push(host);
    }
    return parts.join(" · ");
  }

  function cx(...parts) {
    return parts.filter(Boolean).join(" ");
  }

  function label(meta, group, value) {
    return meta?.labels?.[group]?.[value] || value || "";
  }

  function makeDefaultComposer(meta, settings) {
    return {
      case_summary: "",
      case_blocks: [],
      chief_complaint: "",
      patient_age: "",
      patient_sex: meta?.sex_options?.[0] || "Unknown",
      insurance_type: meta?.insurance_options?.[0] || "Resident insurance",
      department: settings?.default_department || meta?.departments?.[0] || "",
      output_style: meta?.output_styles?.[0] || "Diagnostic",
      urgency: meta?.urgency_options?.[0] || "Routine",
      show_process: settings?.show_diagnostics ?? true,
      input_expanded: false,
      single_model_test: false,
      attachment_panel_open: false,
      image_files: [],
      doc_files: [],
      attachment_epoch: Date.now(),
    };
  }

  function formatTimestamp(value) {
    return value || "";
  }

  function markdownToHtml(value) {
    if (!value) {
      return "";
    }
    const rendered = marked.parse(value, { breaks: true });
    return DOMPurify.sanitize(rendered);
  }

  function Icon({ name, size = 18, className = "" }) {
    if (name === "singleModel") {
      return html`
        <svg
          className=${className}
          width=${size}
          height=${size}
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9.2" stroke="currentColor" strokeWidth="1.9"></circle>
          <text
            x="12"
            y="13.35"
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="13.9"
            fontWeight="700"
            fill="currentColor"
            stroke="none"
            style=${{ fontFamily: '"Noto Serif SC", "Songti SC", "STSong", serif' }}
          >
            单
          </text>
        </svg>
      `;
    }

    return html`
      <svg
        className=${className}
        width=${size}
        height=${size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d=${ICON_PATHS[name]}></path>
      </svg>
    `;
  }

  function BrandGlyph({ className = "" }) {
    return html`
      <svg className=${className} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <g transform="rotate(-30 22.8 15.2)">
          <path
            d="M22.8 15.2V7.6"
            stroke="rgba(255,255,255,0.97)"
            strokeWidth="2.6"
            strokeLinecap="round"
          ></path>
          <path
            d="M16.2 7.6h13.2"
            stroke="rgba(255,255,255,0.97)"
            strokeWidth="2.8"
            strokeLinecap="round"
          ></path>
          <circle
            cx="22.8"
            cy="7.6"
            r="2.1"
            fill="rgba(255,255,255,0.97)"
            stroke="rgba(255,255,255,0.97)"
            strokeWidth="1.8"
          ></circle>
        </g>
        <path
          d="M18.2 26.6c0-8.4 6.4-14.6 15.2-14.6h7.8c7.1 0 13.8 2.5 18.8 6.8l-9.4 2.6H37.4c-2 0-3.2.8-3.2 1.9s1.2 1.8 2.7 1.8H60c1.1 0 2 .9 2 2s-.9 2-2 2H36.9c-1.5 0-2.7.8-2.7 1.8s1.2 1.9 3.2 1.9h13.2l9.4 2.6c-5 4.3-11.7 6.8-18.8 6.8h-7.8c-8.8 0-15.2-6.2-15.2-14.6Z"
          fill="rgba(255,255,255,0.97)"
          stroke="#2b3645"
          strokeWidth="2.2"
          strokeLinejoin="round"
        ></path>
        <ellipse cx="29.1" cy="20.6" rx="4.6" ry="4.1" fill="#2b3645"></ellipse>
        <circle cx="27.8" cy="19.2" r="1.08" fill="rgba(255,255,255,0.94)"></circle>
        <path
          d="M40.6 28.5c4.9-.4 9.9-.4 14.8 0M45 28.7l1.4 1.8M48.5 28.6l1.4 1.8M52 28.6l1.4 1.7"
          stroke="#2b3645"
          strokeWidth="1.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        ></path>
        <circle cx="53.6" cy="24.5" r="1.6" fill="#2b3645"></circle>
        <path
          d="M19.4 58V48.8c0-6 4.8-10.8 10.8-10.8h4.4c6 0 10.8 4.8 10.8 10.8V58"
          fill="rgba(255,255,255,0.97)"
          stroke="#2b3645"
          strokeWidth="2"
          strokeLinejoin="round"
        ></path>
        <path
          d="M32.2 39V58"
          stroke="#2b3645"
          strokeWidth="2"
          strokeLinecap="round"
        ></path>
        <circle cx="41.4" cy="47.9" r="5.3" fill="#2b3645"></circle>
        <path
          d="M41.4 45.3v5.2M38.8 47.9h5.2"
          stroke="rgba(255,255,255,0.98)"
          strokeWidth="2.1"
          strokeLinecap="round"
        ></path>
      </svg>
    `;
  }

  function NoticeStack({ notices }) {
    return html`
      <div className="notice-stack">
        ${notices.map(
          (notice) => html`
            <div key=${notice.id} className=${cx("notice", notice.kind === "error" && "is-error", notice.kind === "success" && "is-success")}>
              ${notice.message}
            </div>
          `
        )}
      </div>
    `;
  }

  function Sidebar({
    meta,
    profile,
    currentUser,
    sessions,
    currentSessionId,
    onOpenSession,
    onOpenSettings,
    onLogout,
    sidebarCollapsed,
    onToggleSidebar,
    showDiagnosticsToggle,
    diagnosticsOpen,
    onToggleDiagnostics,
    onNewChat,
    settingsMenuOpen,
    onToggleSettingsMenu,
  }) {
    const sidebarSessions = sessions.filter((session) => session.show_in_sidebar !== false);

    return html`
      <aside className="shell-sidebar">
        <div className="sidebar-inner">
          <div className="sidebar-toolbar">
            <button
              className=${cx("tooltip-button", "sidebar-toggle-button")}
              onClick=${onToggleSidebar}
              aria-label=${sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
              data-tooltip=${sidebarCollapsed ? "展开" : "收合"}
            >
              <${Icon} name="panelToggle" size=${27} className=${cx("sidebar-toggle-icon", sidebarCollapsed && "is-collapsed")} />
            </button>

            ${showDiagnosticsToggle &&
            html`
              <button
                className=${cx("tooltip-button", "sidebar-diagnostics-button", diagnosticsOpen && "is-active")}
                onClick=${onToggleDiagnostics}
                aria-label="诊断面板"
                data-tooltip="诊断面板"
              >
                <${Icon} name="diagnostics" size=${27} />
              </button>

              <button
                className=${cx("tooltip-button", "sidebar-newchat-button")}
                onClick=${onNewChat}
                aria-label="新建对话"
                data-tooltip="新建对话"
              >
                <${Icon} name="newChat" size=${27} />
              </button>
            `}
          </div>

          <div className="sidebar-brand">
            <div className="brand-mark"><${BrandGlyph} className="brand-mark-glyph" /></div>
            <div className="brand-text">
              <div className="brand-name">RareMDT</div>
              <div className="brand-copy">罕见病多智能体诊疗系统</div>
            </div>
          </div>

          <div className="sidebar-head">
            <div className="sidebar-title">Sessions</div>
          </div>

          <div className="sidebar-session-list">
            ${sidebarSessions.length
              ? sidebarSessions.map(
                  (session) => html`
                    <button
                      key=${session.session_id}
                      className=${cx("sidebar-item", currentSessionId === session.session_id && "is-selected")}
                      onClick=${() => onOpenSession(session.session_id)}
                    >
                      <div className="sidebar-item-row">
                        <div className="sidebar-item-title">${session.title}</div>
                        <span className="badge">${Math.round((session.consensus_score || 0) * 100)}%</span>
                      </div>
                      <div className="sidebar-item-meta">${label(meta, "department", session.department)} · ${label(meta, "output", session.output_style)}</div>
                      <div className="sidebar-item-meta">${formatTimestamp(session.timestamp)}</div>
                    </button>
                  `
                )
              : html`<div className="sidebar-item-meta">暂无既往记录</div>`}
          </div>

          <div className="sidebar-footer">
            <div className="sidebar-head">
              <div>
                <div className="sidebar-footer-name">${profile?.user_name || ""}</div>
                <div className="sidebar-footer-copy">
                  ${currentUser?.username || ""}${profile?.title ? ` · ${profile.title}` : ""}${profile?.department ? ` · ${label(meta, "department", profile.department)}` : ""}
                </div>
              </div>
              <button
                className=${cx("tooltip-button", "sidebar-settings-button", settingsMenuOpen && "is-active")}
                onClick=${onToggleSettingsMenu}
                aria-label="Settings menu"
                data-tooltip="系统设置"
              >
                <${Icon} name="settings" size=${26} />
              </button>
            </div>
            <div className="sidebar-footer-copy" style=${{ marginTop: "8px" }}>
              ${profile?.hospital_name || ""}
            </div>

            ${settingsMenuOpen &&
            html`
              <div className="sidebar-menu">
                ${meta.settings_menu.map(
                  (item) => html`
                    <button key=${item.section} className="menu-item" onClick=${() => onOpenSettings(item.section)}>
                      <${Icon} name=${item.icon} size=${18} />
                      <div>
                        <div className="sidebar-footer-name">${item.label}</div>
                        <div className="menu-item-copy">${SETTINGS_SECTION_COPY[item.section].copy}</div>
                      </div>
                    </button>
                  `
                )}
                <div className="menu-divider"></div>
                <button className="menu-item danger-menu-item" onClick=${onLogout}>
                  <${Icon} name="logout" size=${18} />
                  <div>
                    <div className="sidebar-footer-name">退出登录</div>
                    <div className="menu-item-copy">返回登录页面</div>
                  </div>
                </button>
              </div>
            `}
          </div>
        </div>
      </aside>
    `;
  }

  function SessionSummaryOnly({ session, meta }) {
    return html`
      <div className="summary-card result-card">
        <div className="result-head">
          <div>
            <div className="result-title">${session.title}</div>
            <div className="result-summary">${session.summary}</div>
          </div>
          <div className="badge-row">
            <span className="badge">${label(meta, "department", session.department)}</span>
            <span className="badge">${label(meta, "output", session.output_style)}</span>
          </div>
        </div>
        <div className="markdown-panel">
          <div className="panel-title">历史摘要</div>
          <p style=${{ margin: 0 }}>该记录来自旧版历史摘要，暂未保存完整诊断面板与多智能体过程数据。</p>
        </div>
      </div>
    `;
  }

  function ExecutionStatusCard({ executionMode, providerName, modelName, isPending = false }) {
    if (executionMode === "auto") {
      return html`
        <div className=${cx("status-card", isPending && "is-pending")}>
          <div className="status-card-title">@Auto</div>
          <div className="status-card-copy">${isPending ? "正在自动执行完整诊断流程" : "已完成 planner 到 report 的自动执行"}</div>
        </div>
      `;
    }

    if (executionMode === "planner") {
      return html`
        <div className=${cx("status-card", isPending && "is-pending")}>
          <div className="status-card-title">@Planner</div>
          <div className="status-card-copy">已完成检索并生成执行计划</div>
        </div>
      `;
    }

    if (executionMode === "executor") {
      return html`
        <div className=${cx("status-card", isPending && "is-pending")}>
          <div className="status-card-title">@Executor</div>
          <div className="status-card-copy">${isPending ? "正在按计划执行并记录证据" : "已按计划完成执行并记录证据"}</div>
        </div>
      `;
    }

    if (executionMode === "decider") {
      return html`
        <div className=${cx("status-card", isPending && "is-pending")}>
          <div className="status-card-title">@Decider</div>
          <div className="status-card-copy">${isPending ? "正在融合执行证据并形成诊断判断" : "已完成证据融合并形成诊断判断"}</div>
        </div>
      `;
    }

    if (executionMode === "report") {
      return html`
        <div className=${cx("status-card", isPending && "is-pending")}>
          <div className="status-card-title">@Report</div>
          <div className="status-card-copy">${isPending ? "正在整理证据并生成医疗报告" : "已生成带证据引用的医疗报告"}</div>
        </div>
      `;
    }

    if (executionMode !== "single_model") {
      return null;
    }

    return html`
      <div className=${cx("status-card", isPending && "is-pending")}>
        <div className="status-card-title">单模型测试已启用</div>
        <div className="status-card-copy">${providerName} / ${modelName}</div>
      </div>
    `;
  }

  function StarRatingInput({ value, onChange, disabled = false }) {
    return html`
      <div className="star-rating" role="radiogroup" aria-label="rating">
        ${[1, 2, 3, 4, 5].map((star) => html`
          <button
            key=${star}
            type="button"
            className=${cx("review-link-button", "star-rating-button", value >= star && "is-active")}
            onClick=${() => !disabled && onChange(star)}
            disabled=${disabled}
            aria-label=${`${star} star`}
          >
            ★
          </button>
        `)}
      </div>
    `;
  }

  function DoctorApprovalPanel({ session, turn, onSubmit }) {
    const latestApproval = latestApprovalForTurn(session, turn.turn_id);
    const [note, setNote] = useState(latestApproval?.note || "");
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function submit(action) {
      setIsSubmitting(true);
      try {
        await onSubmit(session.session_id, turn.turn_id, action, note);
      } finally {
        setIsSubmitting(false);
      }
    }

    return html`
      <div className="doctor-review-panel">
        <div className="doctor-review-head">
          <div>
            <div className="panel-title" style=${{ marginBottom: "6px" }}>医生审批</div>
            <div className="doctor-review-copy">
              ${latestApproval
                ? `最近操作：${latestApproval.action === "approved" ? "已通过" : "要求修改"} · ${formatTimestamp(latestApproval.created_at)}`
                : "当前阶段尚未审批。"}
            </div>
          </div>
          ${latestApproval
            ? html`<span className=${cx("review-badge", latestApproval.action === "approved" ? "is-approved" : "is-revision")}>
                ${latestApproval.action === "approved" ? "已通过" : "待修改"}
              </span>`
            : null}
        </div>
        <textarea
          className="review-note-input"
          rows="3"
          value=${note}
          placeholder="填写审批意见或修改要求"
          onInput=${(event) => setNote(event.target.value)}
        ></textarea>
        <div className="review-action-row">
          <button type="button" className="review-action-button is-primary" disabled=${isSubmitting} onClick=${() => submit("approved")}>
            通过
          </button>
          <button type="button" className="review-action-button" disabled=${isSubmitting} onClick=${() => submit("revision_requested")}>
            要求修改
          </button>
        </div>
      </div>
    `;
  }

  function CaseFeedbackPanel({ session, onSubmit, autoFinal = false }) {
    const rows = evidenceFeedbackRows(session);
    const existing = currentCaseFeedback(session);
    const [open, setOpen] = useState(Boolean(autoFinal));
    const [diagnosisRating, setDiagnosisRating] = useState(existing?.diagnosis_rating || 0);
    const [reportRating, setReportRating] = useState(existing?.report_rating || 0);
    const [comment, setComment] = useState(existing?.comment || "");
    const [evidenceRatings, setEvidenceRatings] = useState(() => {
      const base = {};
      rows.forEach((row) => {
        const matched = (existing?.evidence_ratings || []).find((item) => item?.evidence_id === row.evidence_id);
        base[row.evidence_id] = matched?.rating || 0;
      });
      return base;
    });
    const [isSubmitting, setIsSubmitting] = useState(false);

    function setEvidenceRating(evidenceId, rating) {
      setEvidenceRatings((current) => ({ ...current, [evidenceId]: rating }));
    }

    async function submitFeedback() {
      setIsSubmitting(true);
      try {
        await onSubmit(session.session_id, {
          diagnosis_rating: diagnosisRating,
          report_rating: reportRating,
          evidence_ratings: rows.map((row) => ({
            evidence_id: row.evidence_id,
            rating: Number(evidenceRatings[row.evidence_id] || 0),
          })),
          comment,
        });
      } finally {
        setIsSubmitting(false);
      }
    }

    if (!rows.length || !hasReportTurn(session, { currentOnly: true })) {
      return null;
    }

    return html`
      <div className=${cx("result-card", autoFinal && "auto-final-rating-card")}>
        <div className="result-head">
          <div>
            <div className="result-title">${autoFinal ? "打分" : "病例评分"}</div>
            ${autoFinal
              ? null
              : html`<div className="result-summary">${existing ? "评分已保存，可展开后修改。" : "医生可对证据、最终诊断和最终报告进行评分，数据会持久化保存用于后续分析。"}</div>`}
          </div>
          ${autoFinal
            ? null
            : html`
                <button type="button" className="review-link-button" onClick=${() => setOpen((current) => !current)}>
                  ${open ? "收起评分区" : "进入评分区"}
                </button>
              `}
        </div>
        ${open
          ? html`
              <div className="feedback-grid">
                <div className="feedback-row">
                  <span className="feedback-label">最终诊断</span>
                  <${StarRatingInput} value=${diagnosisRating} onChange=${setDiagnosisRating} disabled=${isSubmitting} />
                </div>
                <div className="feedback-row">
                  <span className="feedback-label">最终报告</span>
                  <${StarRatingInput} value=${reportRating} onChange=${setReportRating} disabled=${isSubmitting} />
                </div>
                ${rows.map((row) => html`
                  <div key=${row.evidence_id} className="feedback-row">
                    <span className="feedback-label">${row.evidence_id} · ${row.label}</span>
                    <${StarRatingInput}
                      value=${Number(evidenceRatings[row.evidence_id] || 0)}
                      onChange=${(rating) => setEvidenceRating(row.evidence_id, rating)}
                      disabled=${isSubmitting}
                    />
                  </div>
                `)}
                <textarea
                  className="review-note-input"
                  rows="4"
                  value=${comment}
                  placeholder="补充评价意见"
                  onInput=${(event) => setComment(event.target.value)}
                ></textarea>
                <div className="review-action-row">
                  <button type="button" className="review-action-button is-primary" disabled=${isSubmitting} onClick=${submitFeedback}>
                    保存评分
                  </button>
                </div>
              </div>
            `
          : null}
      </div>
    `;
  }

  function autoStageStatus(mode, submission) {
    const completedModes = Array.isArray(submission?.completed_modes) ? submission.completed_modes : [];
    if (String(submission?.failed_stage || "") === mode) {
      return "failed";
    }
    if (completedModes.includes(mode)) {
      return "completed";
    }
    if (String(submission?.active_mode || "") === mode) {
      return "running";
    }
    return "pending";
  }

  function AutoPipelineProgress({ submission }) {
    const stages = [
      { mode: "planner", title: "@Planner" },
      { mode: "executor", title: "@Executor" },
      { mode: "decider", title: "@Decider" },
      { mode: "report", title: "@Report" },
    ];
    return html`
      <div className="executor-metro">
        <div className="executor-metro-head">
          <div className="executor-metro-head-main">
            <div className="panel-title" style=${{ marginBottom: 0 }}>自动流程</div>
            <div className="executor-metro-summary">
              <span>${(submission?.completed_modes || []).length}/${stages.length} 阶段</span>
              ${submission?.active_mode ? html`<span>· 当前：${submission.active_mode}</span>` : null}
            </div>
          </div>
        </div>
        <div className="executor-metro-list">
          ${stages.map((stage, index) => {
            const status = autoStageStatus(stage.mode, submission);
            return html`
              <div key=${stage.mode} className="executor-metro-step">
                <div className="executor-metro-rail">
                  <span className=${cx("executor-metro-dot", `is-${status}`)}></span>
                  ${index < stages.length - 1 ? html`<span className=${cx("executor-metro-line", `is-${status}`)}></span>` : null}
                </div>
                <div className="executor-metro-copy">
                  <div className="executor-metro-step-title">${stage.title}</div>
                  <div className="executor-metro-step-meta">
                    ${status === "completed" ? "已完成" : status === "running" ? "执行中" : status === "failed" ? "失败" : "待执行"}
                  </div>
                </div>
              </div>
            `;
          })}
        </div>
      </div>
    `;
  }

  function autoLiveStatusLabel(stage, status, submission) {
    if (status === "completed") {
      return "已完成";
    }
    if (status === "failed") {
      return "失败";
    }
    if (status !== "running") {
      return "等待中";
    }
    if (stage.mode === "planner") {
      return "正在读取病例、检索参考知识并制定执行计划";
    }
    if (stage.mode === "executor") {
      const done = Array.isArray(submission?.completed_step_ids) ? submission.completed_step_ids.length : 0;
      const total = Number(submission?.step_count || 0);
      return total ? `正在执行证据步骤 ${done}/${total}` : "正在执行证据采集";
    }
    if (stage.mode === "decider") {
      return "正在融合证据并形成诊断判断";
    }
    if (stage.mode === "report") {
      return "正在生成最终医疗报告";
    }
    return "执行中";
  }

  function AutoLiveStatusWindow({ submission }) {
    const stages = [
      { mode: "planner", title: "@Planner" },
      { mode: "executor", title: "@Executor" },
      { mode: "decider", title: "@Decider" },
      { mode: "report", title: "@Report" },
    ];
    return html`
      <div className="auto-live-window">
        <div className="auto-live-head">
          <div>
            <div className="panel-title" style=${{ marginBottom: 0 }}>实时工作状态</div>
            <div className="auto-live-copy">后台正在完成完整诊断流程；页面只显示状态，完成后直接打开最终报告。</div>
          </div>
          <span className="badge">streaming</span>
        </div>
        <div className="auto-live-list">
          ${stages.map((stage) => {
            const status = autoStageStatus(stage.mode, submission);
            return html`
              <div key=${stage.mode} className="auto-live-item">
                <div className="auto-live-item-main">
                  <span className=${cx("auto-live-dot", `is-${status}`)}></span>
                  <span className="auto-live-stage">${stage.title}</span>
                </div>
                <span className="auto-live-item-copy">${autoLiveStatusLabel(stage, status, submission)}</span>
              </div>
            `;
          })}
        </div>
        ${submission?.stream_transport_warning
          ? html`<div className="auto-live-warning">实时连接曾中断，已切换为状态刷新；后台任务仍在继续。</div>`
          : null}
        ${submission?.stream_event_count
          ? html`
              <div className="auto-live-preview">
                <div className="auto-live-preview-title">${submission.stream_label || "模型输出"}</div>
                <pre>${submission.stream_label || "模型"} 正在生成结构化结果。已接收 ${submission.stream_event_count} 个流式片段。</pre>
              </div>
            `
          : null}
      </div>
    `;
  }

  function PendingWorkspace({ submission, execution, currentSession, meta }) {
    if (!submission) {
      return null;
    }
    const failed = Boolean(submission.error_message);
    const isAuto = execution?.mode === "auto";
    const isExecutor = execution?.mode === "executor";
    const isDecider = execution?.mode === "decider";
    const isReport = execution?.mode === "report";
    const planDisplaySteps =
      submission.plan_display_steps ||
      currentSession?.result?.plan_display_steps ||
      currentSession?.turns?.[currentSession.turns.length - 1]?.result?.plan_display_steps ||
      [];
    const records = submission.execution_records || [];
    const contextSubmission = currentSession?.context_submission || currentSession?.submission || null;
    const primaryAsset = imageAssetsFromSubmission(submission)[0] || imageAssetsFromSubmission(contextSubmission)[0] || null;
    let pendingTitle = failed
      ? isExecutor
        ? "执行已中断"
        : isDecider
          ? "诊断判断失败"
          : isReport
            ? "报告生成失败"
        : "没有生成计划"
      : isExecutor
        ? submission.stage === "rendering"
          ? "正在整理执行结果"
          : "正在按计划执行"
        : isDecider
          ? "正在生成诊断判断"
          : isReport
            ? "正在生成医疗报告"
        : "正在生成结果";
    let pendingSummary = failed
      ? "当前 agent 在严格模式下失败，不会 fallback 到半成品输出。错误详情如下。"
      : isExecutor
        ? pendingExecutorStatusCopy(submission, planDisplaySteps)
        : isDecider
          ? "系统正在收集当前上下文中的执行证据并形成 evidence-based 诊断判断。"
          : isReport
            ? "系统正在基于 Decider 判断与 Executor 证据生成带引用的医疗报告。"
        : "请求已提交，系统正在处理当前病例并准备回填临床结论。";
    if (isAuto) {
      pendingTitle = failed ? "自动流程执行失败" : "正在自动执行完整流程";
      pendingSummary = failed
        ? "当前 agent 在严格模式下失败，不会 fallback 到半成品输出。错误详情如下。"
        : `系统正在串行执行 @Planner -> @Executor -> @Decider -> @Report。已完成 ${(submission.completed_modes || []).length}/4 个阶段。`;
    }
    if (isAuto) {
      pendingTitle = failed ? "自动流程执行失败" : "正在生成最终报告";
      pendingSummary = failed
        ? "当前 agent 在严格模式下失败，不会 fallback 到半成品输出。错误详情如下。"
        : "系统正在通过流式模型调用执行完整诊断流程。页面只展示实时工作状态，完成后直接打开最终报告。";
    }
    const activeStep = (planDisplaySteps || []).find((step) => numericStepId(step?.id) === numericStepId(submission.active_step_id));

    return html`
      <div className="workspace-feed">
        <div className="message-card message-user">
          <div className="message-meta">
            <span>病例输入</span>
            <span>·</span>
            <span>${formatTimestamp(submission.timestamp)}</span>
          </div>
          <div className="message-body">${submission.case_summary}</div>
        </div>

        ${failed
          ? html`
              <div className="status-card">
                <div className="status-card-title">执行失败</div>
                <div className="status-card-copy">请求已到达后端，但当前流程没有生成可展示结果。</div>
              </div>
            `
          : html`
              <${ExecutionStatusCard}
                executionMode=${execution?.mode}
                providerName=${execution?.providerName || "未配置"}
                modelName=${execution?.modelName || "未配置模型"}
                isPending=${true}
              />
            `}

        <div className="result-card pending-result-card">
          <div className="result-head">
            <div>
              <div className="result-title">${pendingTitle}</div>
              <div className="result-summary">${pendingSummary}</div>
            </div>
            ${isExecutor
              ? html`
                  <div className="badge-row">
                    <span className="badge">${records.length}/${submission.step_count || planDisplaySteps.length || records.length} 步</span>
                    ${activeStep ? html`<span className="badge">当前：${activeStep.title_zh || `步骤 ${submission.active_step_id}`}</span>` : null}
                    ${submission.stage === "rendering" ? html`<span className="badge">整理中</span>` : null}
                  </div>
                `
              : null}
          </div>
          ${isAuto
            ? html`
                <div className="info-panel" style=${{ marginTop: "18px" }}>
                  <${AutoLiveStatusWindow} submission=${submission} />
                </div>
              `
            : null}
          ${isExecutor && planDisplaySteps.length
            ? html`
                <div className="info-panel" style=${{ marginTop: "18px" }}>
                  <${ExecutorMetroProgress}
                    planDisplaySteps=${planDisplaySteps}
                    records=${records}
                    activeStepId=${submission.active_step_id}
                    failedStepId=${submission.failed_step_id}
                  />
                </div>
              `
            : null}
          ${isExecutor && records.length
            ? html`
                <div style=${{ display: "grid", gap: "18px", marginTop: "18px" }}>
                  ${records.map(
                    (record, index) => html`
                      <${ExecutorRecordCard}
                        key=${record.step_id || index}
                        record=${record}
                        index=${index}
                        asset=${primaryAsset}
                        display=${resolveExecutionDisplay(record, planDisplaySteps, index)}
                      />
                    `
                  )}
                </div>
              `
            : null}
          ${failed
            ? html`
                <div className="info-panel" style=${{ marginTop: "18px" }}>
                  <div className="panel-title">错误详情</div>
                  <div className="info-list-item" style=${{ alignItems: "flex-start", color: "var(--text-subtle)", whiteSpace: "pre-wrap" }}>
                    <span>${submission.error_message}</span>
                  </div>
                </div>
              `
            : null}
        </div>
      </div>
    `;
  }

  function EmptyWorkspaceWordmark() {
    return html`
      <div className="empty-workspace-mark" aria-hidden="true">
        <svg className="empty-wordmark" viewBox="0 0 1200 240" role="img" aria-label="港大智多星">
          <defs>
            <filter id="wordmark-soft-shadow" x="-12%" y="-40%" width="124%" height="180%">
              <feGaussianBlur in="SourceAlpha" stdDeviation="3.2" result="blur"></feGaussianBlur>
              <feOffset dy="4" result="offsetBlur"></feOffset>
              <feColorMatrix
                in="offsetBlur"
                type="matrix"
                values="0 0 0 0 0.11 0 0 0 0 0.14 0 0 0 0 0.19 0 0 0 0.08 0"
              ></feColorMatrix>
              <feMerge>
                <feMergeNode></feMergeNode>
                <feMergeNode in="SourceGraphic"></feMergeNode>
              </feMerge>
            </filter>
          </defs>
          <text x="600" y="95" textAnchor="middle" dominantBaseline="middle" className="empty-wordmark-highlight">
            港大智多星
          </text>
          <text x="600" y="90" textAnchor="middle" dominantBaseline="middle" className="empty-wordmark-text" filter="url(#wordmark-soft-shadow)">
            港大智多星
          </text>
          <text x="600" y="164" textAnchor="middle" dominantBaseline="middle" className="empty-wordmark-subtitle">
            Multi-agent Platform for Rare Diseases
          </text>
        </svg>
      </div>
    `;
  }

  function PlanDisplayCopy({ step }) {
    if (step.goal_zh || step.evidence_zh || step.human_check_zh) {
      return html`
        <span style=${{ display: "grid", gap: "6px", marginTop: "6px", color: "var(--text-subtle)", lineHeight: 1.65 }}>
          ${step.goal_zh ? html`<span><strong style=${{ color: "var(--text-main)" }}>目标：</strong>${step.goal_zh}</span>` : null}
          ${step.evidence_zh ? html`<span><strong style=${{ color: "var(--text-main)" }}>证据：</strong>${step.evidence_zh}</span>` : null}
          ${step.human_check_zh ? html`<span><strong style=${{ color: "var(--text-main)" }}>核查：</strong>${step.human_check_zh}</span>` : null}
        </span>
      `;
    }
    return html`<span style=${{ display: "block", marginTop: "5px", color: "var(--text-subtle)", lineHeight: 1.65 }}>${step.desc_zh}</span>`;
  }

  function ExecutionDisplayCopy({ display }) {
    if (display?.evidence_summary_zh || display?.human_check_zh) {
      return html`
        ${display?.conclusion_zh
          ? html`
              <span style=${{ display: "block", marginTop: "6px", color: "var(--text-main)", fontWeight: 700, lineHeight: 1.6 }}>
                ${display.conclusion_zh}
              </span>
            `
          : null}
        <span style=${{ display: "grid", gap: "6px", marginTop: "6px", color: "var(--text-subtle)", lineHeight: 1.65 }}>
          ${display.evidence_summary_zh ? html`<span><strong style=${{ color: "var(--text-main)" }}>证据：</strong>${display.evidence_summary_zh}</span>` : null}
          ${display.human_check_zh ? html`<span><strong style=${{ color: "var(--text-main)" }}>核查：</strong>${display.human_check_zh}</span>` : null}
        </span>
      `;
    }
    return html`
      ${display?.conclusion_zh
        ? html`<span style=${{ display: "block", marginTop: "6px", color: "var(--text-main)", fontWeight: 700, lineHeight: 1.6 }}>${display.conclusion_zh}</span>`
        : null}
      <span style=${{ display: "block", marginTop: "5px", color: "var(--text-subtle)", lineHeight: 1.65 }}>
        ${display?.desc_zh || "已完成当前步骤。"}
      </span>
    `;
  }

  function numericStepId(value, fallback = 0) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return fallback;
    }
    return Math.trunc(parsed);
  }

  function planStepForRecord(planDisplaySteps, record, fallbackIndex = 0) {
    const targetId = numericStepId(record?.step_id, fallbackIndex + 1);
    return (planDisplaySteps || []).find((step) => numericStepId(step?.id) === targetId) || null;
  }

  function normalizeEvidenceConclusion(value) {
    const normalized = String(value || "").trim().toLowerCase();
    if (!normalized) {
      return "";
    }
    if (normalized === "yes") {
      return "当前证据支持该征象。";
    }
    if (normalized === "no") {
      return "当前证据不支持该征象。";
    }
    if (normalized === "uncertain") {
      return "当前证据仍不足以做出确定判断。";
    }
    if (normalized === "localized") {
      return "已完成目标区域定位。";
    }
    return String(value || "").trim();
  }

  function buildPendingExecutionDisplay(record, planDisplaySteps, index = 0) {
    const planStep = planStepForRecord(planDisplaySteps, record, index);
    const evidence = record?.evidence || {};
    const artifactType = String(evidence.artifact_type || "").trim().toLowerCase();
    const title = planStep?.title_zh || `步骤 ${numericStepId(record?.step_id, index + 1)}`;
    const desc = planStep?.desc_zh || "已完成当前步骤。";
    const humanCheck = planStep?.human_check_zh || "";
    const conclusion = normalizeEvidenceConclusion(evidence.conclusion);
    const confidence = typeof evidence.confidence === "number" ? ` 置信度 ${Math.round(evidence.confidence * 100)}%。` : "";

    if (artifactType === "grounding") {
      const grounding = evidence.grounding || {};
      const evidenceBits = [];
      if (Array.isArray(grounding.boundary_points) && grounding.boundary_points.length) {
        evidenceBits.push("边界");
      }
      else if ((Array.isArray(grounding.bbox) && grounding.bbox.length === 4) || (Array.isArray(grounding.coarse_bbox) && grounding.coarse_bbox.length === 4)) {
        evidenceBits.push("包围框");
      }
      return {
        title_zh: title,
        desc_zh: desc,
        conclusion_zh: conclusion || "已完成区域定位。",
        evidence_summary_zh: `${evidenceBits.length ? `已输出${evidenceBits.join("、")}证据。` : "已输出结构化定位证据。"}${confidence}`.trim(),
        human_check_zh: humanCheck,
        tag_zh: planStep?.tag_zh || "定位",
      };
    }

    if (artifactType === "measurements") {
      const measurementCount = Object.keys(evidence.measurements || {}).length;
      return {
        title_zh: title,
        desc_zh: desc,
        conclusion_zh: "已完成量化计算。",
        evidence_summary_zh: `已生成 ${measurementCount || 1} 项结构化量化指标。`,
        human_check_zh: humanCheck,
        tag_zh: planStep?.tag_zh || "量化",
      };
    }

    return {
      title_zh: title,
      desc_zh: desc,
      conclusion_zh: conclusion || "已完成当前证据判断。",
      evidence_summary_zh: `已基于上游证据生成结构化判断。${confidence}`.trim(),
      human_check_zh: humanCheck,
      tag_zh: planStep?.tag_zh || "证据",
    };
  }

  function resolveExecutionDisplay(record, planDisplaySteps, index = 0) {
    if (record?.display) {
      return record.display;
    }
    return buildPendingExecutionDisplay(record, planDisplaySteps, index);
  }

  function executorStepStatus(stepId, records, activeStepId, failedStepId) {
    const normalizedId = numericStepId(stepId);
    if (normalizedId && numericStepId(failedStepId) === normalizedId) {
      return "failed";
    }
    if ((records || []).some((record) => numericStepId(record?.step_id) === normalizedId)) {
      return "completed";
    }
    if (normalizedId && numericStepId(activeStepId) === normalizedId) {
      return "running";
    }
    return "pending";
  }

  function pendingExecutorStatusCopy(pending, steps) {
    if (pending?.error_message) {
      const failedId = numericStepId(pending?.failed_step_id);
      return failedId ? `执行在步骤 ${failedId} 中断，已保留此前完成的证据。` : "执行已中断，已保留此前完成的证据。";
    }
    if (pending?.stage === "rendering") {
      return "所有计划步骤已执行完成，正在整理最终展示结果。";
    }
    const completedCount = (pending?.execution_records || []).length;
    const totalCount = Number(pending?.step_count || steps?.length || 0);
    const activeId = numericStepId(pending?.active_step_id);
    const activeStep = (steps || []).find((step) => numericStepId(step?.id) === activeId);
    if (activeId && activeStep) {
      return `正在执行步骤 ${activeId}：${activeStep.title_zh || "当前步骤"}。已完成 ${completedCount}/${totalCount || steps.length || completedCount} 步。`;
    }
    if (completedCount) {
      return `已完成 ${completedCount}/${totalCount || steps.length || completedCount} 步，正在继续执行剩余计划。`;
    }
    return "已接收执行任务，正在准备第一步证据处理。";
  }

  function ExecutorMetroProgress({ planDisplaySteps, records, activeStepId, failedStepId }) {
    const steps = planDisplaySteps || [];
    const [collapsed, setCollapsed] = useState(false);
    if (!steps.length) {
      return null;
    }
    const completedCount = steps.filter((step, index) => executorStepStatus(numericStepId(step?.id, index + 1), records, activeStepId, failedStepId) === "completed").length;
    const runningStep = steps.find((step, index) => executorStepStatus(numericStepId(step?.id, index + 1), records, activeStepId, failedStepId) === "running");
    return html`
      <div className="executor-metro">
        <div className="executor-metro-head">
          <div className="executor-metro-head-main">
            <div className="panel-title" style=${{ marginBottom: 0 }}>执行进度</div>
            <div className="executor-metro-summary">
              <span>${completedCount}/${steps.length} 步</span>
              ${runningStep ? html`<span>· 当前：${runningStep.title_zh || "执行中"}</span>` : null}
            </div>
          </div>
          <div className="executor-metro-head-actions">
            <div className="executor-metro-legend">
              <span className="executor-metro-legend-item"><span className="executor-metro-dot is-completed"></span>已完成</span>
              <span className="executor-metro-legend-item"><span className="executor-metro-dot is-running"></span>执行中</span>
              <span className="executor-metro-legend-item"><span className="executor-metro-dot is-pending"></span>待执行</span>
            </div>
            <button type="button" className="executor-metro-toggle" onClick=${() => setCollapsed((current) => !current)}>
              ${collapsed ? "展开线路图" : "收起线路图"}
            </button>
          </div>
        </div>
        <div className=${cx("executor-metro-list", collapsed && "is-collapsed")}>
          ${steps.map((step, index) => {
            const stepId = numericStepId(step?.id, index + 1);
            const status = executorStepStatus(stepId, records, activeStepId, failedStepId);
            return html`
              <div key=${stepId || index} className="executor-metro-step">
                <div className="executor-metro-rail">
                  <span className=${cx("executor-metro-dot", `is-${status}`)}></span>
                  ${index < steps.length - 1 ? html`<span className=${cx("executor-metro-line", `is-${status}`)}></span>` : null}
                </div>
                <div className="executor-metro-copy">
                  <div className="executor-metro-step-title">${step.title_zh || `步骤 ${index + 1}`}</div>
                  <div className="executor-metro-step-meta">
                    ${status === "completed" ? "已完成" : status === "running" ? "执行中" : status === "failed" ? "失败" : "待执行"}
                    ${step.tag_zh ? ` · ${step.tag_zh}` : ""}
                  </div>
                </div>
              </div>
            `;
          })}
        </div>
      </div>
    `;
  }

  function PlannerResultWorkspace({ session, meta }) {
    const result = session.result;
    const submission = session.submission;
    const rows = result.plan_display_steps || [];
    return html`
      <div className="workspace-feed">
        <div className="message-card message-user">
          <div className="message-meta">
            <span>Planner 输入</span>
            <span>·</span>
            <span>${formatTimestamp(session.timestamp)}</span>
          </div>
          <div className="message-body">${submission.case_summary}</div>
        </div>

        <div className="status-card">
          <div className="status-card-title">@Planner</div>
          <div className="status-card-copy">中文展示层已生成，英文执行计划保留在后端。</div>
        </div>

        <div className="result-card">
          <div className="result-head">
            <div>
              <div className="result-title">${result.title}</div>
              <div className="result-summary">${result.executive_summary}</div>
            </div>
            <div className="badge-row">
              <span className="badge">@Planner</span>
              <span className="badge">${label(meta, "department", result.department)}</span>
              <span className="badge">计划</span>
            </div>
          </div>

          <div className="info-panel">
            <div className="panel-title">执行计划</div>
            <div className="info-list">
              ${rows.map(
                (step, index) => html`
                  <div key=${step.id || index} className="info-list-item">
                    <span className="badge">${index + 1}</span>
                    <span>
                      <strong>${step.title_zh || `步骤 ${index + 1}`}</strong>
                      <${PlanDisplayCopy} step=${step} />
                      <span style=${{ display: "inline-flex", marginTop: "8px" }} className="badge">${step.tag_zh || "步骤"}</span>
                    </span>
                  </div>
                `
              )}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function ExecutorResultWorkspace({ session, meta }) {
    const result = session.result;
    const submission = session.submission;
    const records = result.execution_records || [];
    const planDisplaySteps = result.plan_display_steps || [];
    const primaryAsset = imageAssetsFromSubmission(submission)[0] || imageAssetsFromSubmission(session.context_submission)[0] || null;
    return html`
      <div className="workspace-feed">
        <div className="message-card message-user">
          <div className="message-meta">
            <span>Executor 输入</span>
            <span>·</span>
            <span>${formatTimestamp(session.timestamp)}</span>
          </div>
          <div className="message-body">${submission.case_summary}</div>
        </div>

        <div className="status-card">
          <div className="status-card-title">@Executor</div>
          <div className="status-card-copy">已按计划完成执行，并为每一步生成证据记录。</div>
        </div>

        <div className="result-card">
          <div className="result-head">
            <div>
              <div className="result-title">${result.title}</div>
              <div className="result-summary">${result.executive_summary}</div>
            </div>
            <div className="badge-row">
              <span className="badge">@Executor</span>
              <span className="badge">${label(meta, "department", result.department)}</span>
              <span className="badge">证据执行</span>
            </div>
          </div>

          <div className="info-panel" style=${{ marginBottom: "18px" }}>
            <${ExecutorMetroProgress}
              planDisplaySteps=${planDisplaySteps}
              records=${records}
              activeStepId=${null}
              failedStepId=${null}
            />
          </div>

          <div style=${{ display: "grid", gap: "18px" }}>
            ${records.map(
              (record, index) => html`
                <${ExecutorRecordCard}
                  key=${record.step_id || index}
                  record=${record}
                  index=${index}
                  asset=${primaryAsset}
                  display=${resolveExecutionDisplay(record, planDisplaySteps, index)}
                />
              `
            )}
          </div>
        </div>
      </div>
    `;
  }

  function WorkflowOverview({ session, compact = false }) {
    const stages = clinicalWorkflowStages(session);
    return html`
      <div className=${cx("result-card", "workflow-overview-card", compact && "is-compact")}>
        <div className="workflow-overview-head">
          <div>
            <div className="panel-title">工作流</div>
            ${compact ? null : html`<div className="workflow-overview-copy">每个阶段都有明确产物、审批状态和下一步动作。</div>`}
          </div>
          <span className="badge">${buildTurnList(session).length} 次操作</span>
        </div>
        <div className="workflow-stage-row">
          ${stages.map((stage, index) => {
            const status = stage.status;
            return html`
              <div key=${stage.mode} className=${cx("workflow-stage", `is-${String(status).replace(/_/g, "-")}`)}>
                <span className="workflow-stage-dot"></span>
                <span>
                  <strong>${stage.label}</strong>
                  <em>${workflowStageText(status)} · ${status === "stale" ? "旧版结果已被当前计划替换" : stage.copy}</em>
                </span>
                ${index < stages.length - 1 ? html`<span className="workflow-stage-line"></span>` : null}
              </div>
            `;
          })}
        </div>
      </div>
    `;
  }

  function RuntimeReviewQueue({ session }) {
    const stages = clinicalWorkflowStages(session);
    const reviewRows = stages.map((stage) => ({
      label: stage.label,
      status: workflowStageText(stage.status),
      note:
        stage.status === "pending"
          ? "尚未产出"
          : stage.status === "stale"
            ? "旧版结果已失效"
          : stage.status === "needs_review"
            ? "等待医生复核"
            : stage.status === "needs_revision"
              ? "已有修改要求"
            : stage.status === "accepted"
              ? "已评分闭环"
              : "已通过",
    }));
    return html`
      <div className="runtime-section-card">
        <div className="runtime-section-head">
          <div className="panel-title">复核队列</div>
        </div>
        <div className="clinical-review-queue runtime-review-queue">
          ${reviewRows.map((row) => html`
            <div key=${row.label} className="clinical-review-item">
              <span>${row.label}</span>
              <strong>${row.status}</strong>
              <em>${row.note}</em>
            </div>
          `)}
        </div>
      </div>
    `;
  }

  function CaseRuntimePanel({ session, meta, contextSubmission }) {
    if (!session || !contextSubmission) {
      return null;
    }
    const stats = clinicalEvidenceStats(session);
    const feedback = currentCaseFeedback(session);
    return html`
      <div className="case-runtime-panel" aria-label="病例工作台">
        <div className="result-card case-runtime-card">
          <div className="case-runtime-head">
            <div>
              <div className="result-title">病例工作台</div>
            </div>
            <span className="badge">Live Case</span>
          </div>
          <div className="clinical-next-action">
            <span>下一步</span>
            <strong>${nextClinicalAction(session)}</strong>
          </div>
          <div className="clinical-command-grid runtime-metric-grid">
            <div className="clinical-command-metric">
              <span>证据</span>
              <strong>${stats.total}</strong>
              <em>${stats.grounded} 条含图像定位</em>
            </div>
            <div className="clinical-command-metric">
              <span>引用</span>
              <strong>${stats.cited}/${stats.total || 0}</strong>
              <em>${stats.total ? `${stats.uncited} 条未引用` : "等待证据"}</em>
            </div>
            <div className="clinical-command-metric">
              <span>反馈</span>
              <strong>${feedback ? "已保存" : "未完成"}</strong>
              <em>${feedback ? `诊断 ${feedback.diagnosis_rating} 星` : "报告后评分"}</em>
            </div>
          </div>
        </div>

        <${ContextPanel} submission=${contextSubmission} meta=${meta} compact=${true} session=${session} />
        <${WorkflowOverview} session=${session} compact=${true} />
        <${EvidenceLedger} session=${session} contextSubmission=${contextSubmission} compact=${true} />
        <${RuntimeReviewQueue} session=${session} />
      </div>
    `;
  }

  function ClinicalCommandCenter({ session }) {
    const stages = clinicalWorkflowStages(session);
    const stats = clinicalEvidenceStats(session);
    const feedback = currentCaseFeedback(session);
    const reviewRows = stages.map((stage) => ({
      label: stage.label,
      status: workflowStageText(stage.status),
      note:
        stage.status === "pending"
          ? "尚未产出"
          : stage.status === "stale"
            ? "旧版结果已失效"
          : stage.status === "needs_review"
            ? "等待医生复核"
            : stage.status === "needs_revision"
              ? "已有修改要求"
              : stage.status === "accepted"
                ? "已评分闭环"
                : "已通过",
    }));
    return html`
      <div className="result-card clinical-command-card">
        <div className="clinical-command-head">
          <div>
            <div className="result-title">临床控制台</div>
            <div className="result-summary">把病例当作一个持续工作区：计划、证据、判断、报告和医生反馈都在这里形成闭环。</div>
          </div>
          <span className="badge">Case Workspace</span>
        </div>

        <div className="clinical-next-action">
          <span>下一步</span>
          <strong>${nextClinicalAction(session)}</strong>
        </div>

        <div className="clinical-command-grid">
          <div className="clinical-command-metric">
            <span>证据</span>
            <strong>${stats.total}</strong>
            <em>${stats.grounded} 条含图像定位</em>
          </div>
          <div className="clinical-command-metric">
            <span>引用</span>
            <strong>${stats.cited}/${stats.total || 0}</strong>
            <em>${stats.total ? `${stats.uncited} 条暂未被判断或报告引用` : "等待 Executor 产出证据"}</em>
          </div>
          <div className="clinical-command-metric">
            <span>医生反馈</span>
            <strong>${feedback ? "已保存" : "未完成"}</strong>
            <em>${feedback ? `诊断 ${feedback.diagnosis_rating} 星 · 报告 ${feedback.report_rating} 星` : "报告完成后进入评分闭环"}</em>
          </div>
        </div>

        <div className="clinical-review-queue">
          ${reviewRows.map((row) => html`
            <div key=${row.label} className="clinical-review-item">
              <span>${row.label}</span>
              <strong>${row.status}</strong>
              <em>${row.note}</em>
            </div>
          `)}
        </div>
      </div>
    `;
  }

  function ContextPanel({ submission, meta, compact = false, session = null }) {
    if (!submission) {
      return null;
    }
    const assets = imageAssetsFromSubmission(submission);
    const alerts = caseContextAlerts(submission);
    const task = latestCaseTask(session) || submission.chief_complaint || submission.case_summary || "未填写";
    const turnCount = buildTurnList(session).length;
    return html`
      <details className=${cx("result-card", "context-details", compact && "is-compact")} open=${!compact}>
        <summary className="context-summary">
          <div>
            <div className="result-title">Case Context</div>
            <div className="result-summary">
              ${compact
                ? `${submission.chief_complaint || submission.case_summary || "当前病例"} · ${assets.length ? assets.map((asset) => asset.name).filter(Boolean).join("，") : "无影像附件"}`
                : "当前病例的文本、图像与历史 agent 结果都会影响后续步骤。输入 /clear 开始新病例。"}
            </div>
          </div>
          <div className="badge-row">
            <span className="badge">${label(meta, "department", submission.department)}</span>
            <span className="badge">${label(meta, "output", submission.output_style)}</span>
            <span className="badge">${label(meta, "urgency", submission.urgency)}</span>
          </div>
        </summary>

        <div className="context-inspector">
          <div className="context-metric">
            <span>当前任务</span>
            <strong>${task}</strong>
          </div>
          <div className="context-metric">
            <span>图像</span>
            <strong>${assets.length}</strong>
          </div>
          <div className="context-metric">
            <span>文本</span>
            <strong>${String(submission.case_summary || submission.chief_complaint || "").trim() ? "已提供" : "未提供"}</strong>
          </div>
          <div className="context-metric">
            <span>上下文</span>
            <strong>${turnCount ? `${turnCount} 步历史` : "新病例"}</strong>
          </div>
        </div>

        ${alerts.length
          ? html`
              <div className="context-alert-list">
                ${alerts.map((item, index) => html`
                  <div key=${index} className="context-alert">${item}</div>
                `)}
              </div>
            `
          : null}

        <div className="context-detail-grid">
          <div className="context-detail-block">
            <div className="panel-title">病例资料</div>
            <div className="info-list">
              ${submission.chief_complaint
                ? html`
                    <div className="info-list-item">
                      <span className="badge">主诉</span>
                      <span>${submission.chief_complaint}</span>
                    </div>
                  `
                : null}
              <div className="info-list-item">
                <span className="badge">摘要</span>
                <span>${submission.case_summary || "未填写"}</span>
              </div>
              <div className="info-list-item">
                <span className="badge">患者</span>
                <span>${submission.patient_age || "年龄未填"} · ${label(meta, "sex", submission.patient_sex)}</span>
              </div>
              <div className="info-list-item">
                <span className="badge">附件</span>
                <span>${submission.uploaded_images?.length ? submission.uploaded_images.join("，") : "无影像附件"}${submission.uploaded_docs?.length ? `；${submission.uploaded_docs.join("，")}` : ""}</span>
              </div>
            </div>
          </div>
        </div>

        ${assets.length
          ? html`
              <div className="context-detail-block" style=${{ marginTop: "18px" }}>
                <div className="panel-title">原始图像</div>
                <div style=${{ display: "grid", gap: "14px", gridTemplateColumns: assets.length > 1 ? "repeat(2, minmax(0, 1fr))" : "1fr" }}>
                  ${assets.map(
                    (asset, index) => html`
                      <div key=${asset.name || index} style=${{ overflow: "hidden", borderRadius: "8px", border: "1px solid var(--line)", background: "#fff" }}>
                        <img src=${imageSrcFromAsset(asset)} alt=${asset.name || `原始图像 ${index + 1}`} style=${{ display: "block", width: "100%", height: "auto" }} />
                        <div style=${{ padding: "10px 12px", fontSize: "13px", color: "var(--text-subtle)" }}>${asset.name || `图像 ${index + 1}`}</div>
                      </div>
                    `
                  )}
                </div>
              </div>
            `
          : null}
      </div>
    `;
  }

  function StepEvidenceFigure({ asset, record, index }) {
    if (!asset || !hasGroundingEvidence(record)) {
      return null;
    }
    const grounding = groundingPayload(record) || {};
    const color = overlayColor(index);
    const boundary = Array.isArray(grounding.boundary_points) ? grounding.boundary_points : [];
    const bbox = Array.isArray(grounding.bbox) ? grounding.bbox : Array.isArray(grounding.coarse_bbox) ? grounding.coarse_bbox : null;
    const polygon = boundary.map((item) => `${Math.max(0, Math.min(1, Number(item?.[0] || 0))) * 100},${Math.max(0, Math.min(1, Number(item?.[1] || 0))) * 100}`).join(" ");
    const showBoundary = boundary.length >= 3 && Boolean(polygon);
    const showBbox = !showBoundary && Array.isArray(bbox) && bbox.length === 4;
    return html`
      <div style=${{ marginTop: "14px", overflow: "hidden", borderRadius: "8px", border: "1px solid var(--line)", background: "#fff" }}>
        <div style=${{ position: "relative" }}>
          <img src=${imageSrcFromAsset(asset)} alt=${asset.name || `步骤 ${record.step_id || index + 1} 证据图`} style=${{ display: "block", width: "100%", height: "auto" }} />
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" style=${{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}>
            ${showBoundary
              ? html`
                  <polygon
                    points=${polygon}
                    fill="none"
                    stroke=${color}
                    strokeWidth="1.4"
                    vectorEffect="non-scaling-stroke"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  ></polygon>
                `
              : null}
            ${showBbox
              ? html`
                  <rect
                    x=${Math.max(0, Math.min(1, Number(bbox[0] || 0))) * 100}
                    y=${Math.max(0, Math.min(1, Number(bbox[1] || 0))) * 100}
                    width=${Math.max(0, Math.min(1, Number((bbox[2] || 0) - (bbox[0] || 0)))) * 100}
                    height=${Math.max(0, Math.min(1, Number((bbox[3] || 0) - (bbox[1] || 0)))) * 100}
                    fill="none"
                    stroke=${color}
                    strokeDasharray="4 3"
                    strokeWidth="1.2"
                    vectorEffect="non-scaling-stroke"
                  ></rect>
                `
              : null}
          </svg>
        </div>
        <div style=${{ padding: "10px 12px", fontSize: "13px", color: "var(--text-subtle)" }}>
          本图仅显示步骤 ${record.step_id || index + 1} 的证据标注，不叠加其他步骤。
        </div>
      </div>
    `;
  }

  function ExecutorRecordCard({ record, index, asset, display }) {
    return html`
      <div className="info-panel executor-record-card">
        <div className="panel-title">步骤 ${record.step_id || index + 1}</div>
        <div className="info-list-item" style=${{ alignItems: "flex-start" }}>
          <span className="badge">${record.step_id || index + 1}</span>
          <span>
            <strong>${display?.title_zh || `步骤 ${index + 1}`}</strong>
            <${ExecutionDisplayCopy} display=${display} />
            <span style=${{ display: "inline-flex", marginTop: "8px" }} className="badge">${display?.tag_zh || "完成"}</span>
          </span>
        </div>
        ${hasGroundingEvidence(record) && asset
          ? html`<${StepEvidenceFigure} asset=${asset} record=${record} index=${index} />`
          : hasGroundingEvidence(record)
            ? html`
                <div className="info-list-item" style=${{ marginTop: "14px", color: "var(--text-subtle)" }}>
                  <span>此步骤已生成 grounding 坐标，但当前上下文缺少原始图像，暂时无法绘制证据图。</span>
                </div>
              `
            : html`
                <div className="info-list-item" style=${{ marginTop: "14px", color: "var(--text-subtle)" }}>
                  <span>此步骤输出结构化证据，不单独绘制图像标注。</span>
                </div>
              `}
      </div>
    `;
  }

  function DisplayQualityNotice({ warnings }) {
    const items = Array.isArray(warnings) ? warnings.filter(Boolean) : [];
    if (!items.length) {
      return null;
    }
    return html`
      <div className="display-quality-notice">
        <div className="display-quality-title">中文展示需复核</div>
        <div className="display-quality-copy">结构化结果已完成；以下问题只影响界面文案，不影响后端证据链。</div>
        <ul>
          ${items.slice(0, 4).map((item, index) => html`<li key=${index}>${item}</li>`)}
        </ul>
      </div>
    `;
  }

  function plannerReviewFromApproval(approval) {
    const parsed = parseObjectJson(approval?.note);
    if (!parsed || parsed.type !== "planner_step_review" || !Array.isArray(parsed.steps)) {
      return null;
    }
    return parsed;
  }

  function PlannerReviewPanel({ session, turn, steps, onSubmitApproval, stale = false }) {
    if (!session || !turn?.turn_id || !onSubmitApproval) {
      return null;
    }
    const latestApproval = latestApprovalForTurn(session, turn.turn_id);
    const savedReview = plannerReviewFromApproval(latestApproval);
    const [reviewRows, setReviewRows] = useState(() =>
      steps.map((step, index) => {
        const id = numericStepId(step?.id, index + 1);
        const saved = savedReview?.steps?.find((item) => numericStepId(item?.id) === id);
        return {
          id,
          title: step?.title_zh || `步骤 ${index + 1}`,
          status: saved?.status === "steer" ? "steer" : "approve",
          note: saved?.note || "",
        };
      })
    );
    const [comment, setComment] = useState(savedReview?.comment || "");
    const [isSubmitting, setIsSubmitting] = useState(false);

    function updateRow(id, patch) {
      setReviewRows((current) => current.map((row) => (row.id === id ? { ...row, ...patch } : row)));
    }

    async function submitReview() {
      const payload = {
        type: "planner_step_review",
        version: 1,
        steps: reviewRows.map((row) => ({
          id: row.id,
          title: row.title,
          status: row.status,
          note: row.note,
        })),
        comment,
      };
      const action = reviewRows.every((row) => row.status === "approve") ? "approved" : "revision_requested";
      setIsSubmitting(true);
      try {
        await onSubmitApproval(session.session_id, turn.turn_id, action, JSON.stringify(payload));
      } finally {
        setIsSubmitting(false);
      }
    }

    return html`
      <div className="planner-review-panel">
        <div className="planner-review-head">
          <div>
            <div className="panel-title">Planner Review</div>
            <div className="planner-review-copy">
              ${stale ? "该计划属于旧版 workflow revision，现仅保留为历史记录，不再接受复核。" : "逐步确认计划是否可执行；需要修改的步骤会作为 steer 意见保存。"}
            </div>
          </div>
          ${latestApproval
            ? html`<span className=${cx("review-badge", latestApproval.action === "approved" ? "is-approved" : "is-revision")}>
                ${latestApproval.action === "approved" ? "计划已通过" : "计划需修改"}
              </span>`
            : null}
        </div>
        ${stale ? html`<div className="context-alert">当前病例已生成新的 Planner 计划。旧计划不会再驱动 Executor / Decider / Report。</div>` : null}
        <div className="planner-review-list">
          ${reviewRows.map((row) => html`
            <div key=${row.id} className="planner-review-row">
              <div className="planner-review-row-main">
                <span className="badge">${row.id}</span>
                <strong>${row.title}</strong>
              </div>
              ${stale
                ? html`<span className="badge">历史计划</span>`
                : html`
                    <div className="planner-review-actions">
                      <button
                        type="button"
                        className=${cx("review-action-button", row.status === "approve" && "is-primary")}
                        disabled=${isSubmitting}
                        onClick=${() => updateRow(row.id, { status: "approve" })}
                      >
                        通过
                      </button>
                      <button
                        type="button"
                        className=${cx("review-action-button", row.status === "steer" && "is-warning")}
                        disabled=${isSubmitting}
                        onClick=${() => updateRow(row.id, { status: "steer" })}
                      >
                        修改
                      </button>
                    </div>
                  `}
              ${row.status === "steer"
                ? html`
                    <textarea
                      className="review-note-input planner-step-note"
                      rows="2"
                      value=${row.note}
                      placeholder="写清楚这一步需要改什么，例如目标、顺序、证据类型或核查要求。"
                      disabled=${stale}
                      onInput=${(event) => updateRow(row.id, { note: event.target.value })}
                    ></textarea>
                  `
                : null}
            </div>
          `)}
        </div>
        ${stale
          ? null
          : html`
              <textarea
                className="review-note-input"
                rows="3"
                value=${comment}
                placeholder="整体意见，可留空"
                onInput=${(event) => setComment(event.target.value)}
              ></textarea>
              <div className="review-action-row">
                <button type="button" className="review-action-button is-primary" disabled=${isSubmitting} onClick=${submitReview}>
                  保存计划复核
                </button>
              </div>
            `}
      </div>
    `;
  }

  function PlannerTurnCard({ turn, meta, session, onSubmitApproval, stale = false }) {
    const result = turn.result;
    const rows = result.plan_display_steps || [];
    return html`
      <div className=${cx("result-card", stale && "is-stale-turn")}>
        <div className="result-head">
          <div>
            <div className="result-title">${result.title}</div>
            <div className="result-summary">${result.executive_summary}</div>
          </div>
          <div className="badge-row">
            <span className="badge">@Planner</span>
            <span className="badge">${label(meta, "department", result.department)}</span>
            <span className="badge">计划</span>
            ${stale ? html`<span className="badge stale-badge">已失效</span>` : null}
          </div>
        </div>
        <div className="info-panel">
          <div className="panel-title">执行计划</div>
          <${DisplayQualityNotice} warnings=${result.display_quality_warnings} />
          <div className="info-list">
            ${rows.map(
              (step, index) => html`
                <div key=${step.id || index} className="info-list-item">
                  <span className="badge">${index + 1}</span>
                  <span>
                    <strong>${step.title_zh || `步骤 ${index + 1}`}</strong>
                    <${PlanDisplayCopy} step=${step} />
                    <span style=${{ display: "inline-flex", marginTop: "8px" }} className="badge">${step.tag_zh || "步骤"}</span>
                  </span>
                </div>
              `
            )}
          </div>
        </div>
        <${PlannerReviewPanel} session=${session} turn=${turn} steps=${rows} onSubmitApproval=${onSubmitApproval} stale=${stale} />
      </div>
    `;
  }

  function ExecutorTurnCard({ turn, meta, contextSubmission }) {
    const result = turn.result;
    const records = result.execution_records || [];
    const planDisplaySteps = result.plan_display_steps || [];
    const primaryAsset = imageAssetsFromSubmission(turn.submission)[0] || imageAssetsFromSubmission(contextSubmission)[0] || null;
    return html`
      <div className="result-card">
        <div className="result-head">
          <div>
            <div className="result-title">${result.title}</div>
            <div className="result-summary">${result.executive_summary}</div>
          </div>
          <div className="badge-row">
            <span className="badge">@Executor</span>
            <span className="badge">${label(meta, "department", result.department)}</span>
            <span className="badge">证据执行</span>
          </div>
        </div>
        <div className="info-panel" style=${{ marginBottom: "18px" }}>
          <${DisplayQualityNotice} warnings=${result.display_quality_warnings} />
          <${ExecutorMetroProgress}
            planDisplaySteps=${planDisplaySteps}
            records=${records}
            activeStepId=${null}
            failedStepId=${null}
          />
        </div>
        <div style=${{ display: "grid", gap: "18px", marginTop: "18px" }}>
          ${records.map(
            (record, index) => html`
              <${ExecutorRecordCard}
                key=${record.step_id || index}
                record=${record}
                index=${index}
                asset=${primaryAsset}
                display=${resolveExecutionDisplay(record, planDisplaySteps, index)}
              />
            `
          )}
        </div>
      </div>
    `;
  }

  function EvidenceLedger({ session, contextSubmission, compact = false }) {
    const executorTurn = latestExecutorTurn(session, { currentOnly: true });
    if (!executorTurn) {
      return null;
    }
    const result = executorTurn.result || {};
    const records = Array.isArray(result.execution_records) ? result.execution_records : [];
    if (!records.length) {
      return null;
    }
    const planDisplaySteps = Array.isArray(result.plan_display_steps) ? result.plan_display_steps : [];
    const primaryAsset = imageAssetsFromSubmission(executorTurn.submission)[0] || imageAssetsFromSubmission(contextSubmission)[0] || null;
    return html`
      <div className=${cx("result-card", "evidence-ledger-card", compact && "is-compact")}>
        <div className="result-head">
          <div>
            <div className="result-title">证据台账</div>
            ${compact ? null : html`<div className="result-summary">所有诊断判断和报告引用都必须回到这里的 Executor 证据。</div>`}
          </div>
          <div className="badge-row">
            <span className="badge">${records.length} 条证据</span>
            <span className="badge">可复核</span>
          </div>
        </div>
        <div className="evidence-ledger-list">
          ${records.map((record, index) => {
            const stepId = numericStepId(record?.step_id, index + 1);
            const display = resolveExecutionDisplay(record, planDisplaySteps, index);
            const evidence = record.evidence || {};
            const confidence = typeof evidence.confidence === "number" ? `${Math.round(evidence.confidence * 100)}%` : "";
            return html`
              <details key=${stepId} className="evidence-ledger-item">
                <summary>
                  <span className="badge">E${stepId}</span>
                  <span>
                    <strong>${display?.title_zh || `证据 ${stepId}`}</strong>
                    <em>${display?.conclusion_zh || display?.evidence_summary_zh || "已完成证据采集。"}</em>
                  </span>
                  ${confidence ? html`<span className="badge">${confidence}</span>` : html`<span className="badge">证据</span>`}
                </summary>
                <${AutoEvidenceRecordDetail}
                  evidenceId=${`E${stepId}`}
                  record=${record}
                  planDisplaySteps=${planDisplaySteps}
                  asset=${primaryAsset}
                  index=${index}
                />
              </details>
            `;
          })}
        </div>
      </div>
    `;
  }

  function parseObjectJson(value) {
    if (!value) {
      return null;
    }
    try {
      const parsed = JSON.parse(String(value));
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
    } catch (error) {
      return null;
    }
  }

  function decisionPayloadFromResult(result) {
    return parseObjectJson(result?.raw_provider_payload) || {};
  }

  function deciderDisplayPayloadFromResult(result) {
    return parseObjectJson(result?.display_payload) || {};
  }

  function reportPayloadFromResult(result) {
    return parseObjectJson(result?.raw_provider_payload) || {};
  }

  function evidenceIdLabel(ids) {
    const values = Array.isArray(ids) ? ids.filter(Boolean) : [];
    return values.length ? values.join(", ") : "未引用";
  }

  function evidenceIdsFromItem(item) {
    return Array.isArray(item?.evidence_ids) ? item.evidence_ids.map((value) => String(value || "").trim()).filter(Boolean) : [];
  }

  function recordForEvidenceId(records, evidenceId) {
    const match = String(evidenceId || "").match(/^E(\d+)$/i);
    if (!match) {
      return null;
    }
    const stepId = Number(match[1]);
    return (records || []).find((record) => numericStepId(record?.step_id) === stepId) || null;
  }

  function AutoEvidenceRecordDetail({ evidenceId, record, planDisplaySteps, asset, index }) {
    if (!record) {
      return html`
        <div className="auto-final-evidence-missing">
          ${evidenceId} 未在当前 Executor 记录中找到对应证据。
        </div>
      `;
    }
    const display = resolveExecutionDisplay(record, planDisplaySteps || [], index);
    const evidence = record.evidence || {};
    const confidence = typeof evidence.confidence === "number" ? `${Math.round(evidence.confidence * 100)}%` : "";
    return html`
      <div className="auto-final-evidence-detail">
        <div className="auto-final-evidence-detail-head">
          <span className="badge">${evidenceId}</span>
          <strong>${display?.title_zh || `证据 ${evidenceId}`}</strong>
          ${confidence ? html`<span className="badge">${confidence}</span>` : null}
        </div>
        <${ExecutionDisplayCopy} display=${display} />
        <div className="auto-final-evidence-facts">
          ${evidence.target_label ? html`<div><strong>目标：</strong>${evidence.target_label}</div>` : null}
          ${evidence.conclusion ? html`<div><strong>结论：</strong>${normalizeEvidenceConclusion(evidence.conclusion)}</div>` : null}
          ${evidence.rationale ? html`<div><strong>理由：</strong>${evidence.rationale}</div>` : null}
        </div>
        ${hasGroundingEvidence(record) && asset
          ? html`<${StepEvidenceFigure} asset=${asset} record=${record} index=${index} />`
          : hasGroundingEvidence(record)
            ? html`<div className="auto-final-evidence-missing">该证据含定位坐标，但当前记录缺少原始图像，无法绘制证据图。</div>`
            : null}
      </div>
    `;
  }

  function AutoEvidenceDisclosure({ item, records, planDisplaySteps, asset, index }) {
    const evidenceIds = evidenceIdsFromItem(item);
    const matchedRecords = evidenceIds.map((evidenceId) => ({
      evidenceId,
      record: recordForEvidenceId(records, evidenceId),
    }));
    return html`
      <details className="auto-final-evidence-details">
        <summary>
          <span className="badge">${evidenceIdLabel(evidenceIds)}</span>
          <span>${item.statement}</span>
          <span className="auto-final-evidence-action">查看证据</span>
        </summary>
        <div className="auto-final-evidence-detail-list">
          ${matchedRecords.length
            ? matchedRecords.map(({ evidenceId, record }, recordIndex) => html`
                <${AutoEvidenceRecordDetail}
                  key=${evidenceId}
                  evidenceId=${evidenceId}
                  record=${record}
                  planDisplaySteps=${planDisplaySteps}
                  asset=${asset}
                  index=${record ? Math.max(0, numericStepId(record.step_id, recordIndex + 1) - 1) : recordIndex}
                />
              `)
            : html`<div className="auto-final-evidence-missing">该条报告未引用可展开的证据编号。</div>`}
        </div>
      </details>
    `;
  }

  function DeciderTurnCard({ turn, meta, contextSubmission }) {
    const result = turn.result;
    const decision = decisionPayloadFromResult(result);
    const decisionDisplay = deciderDisplayPayloadFromResult(result);
    const keyEvidence = Array.isArray(decision.key_evidence) ? decision.key_evidence : [];
    const keyEvidenceDisplay = Array.isArray(decisionDisplay.key_evidence) ? decisionDisplay.key_evidence : [];
    const displayByEvidenceId = Object.fromEntries(
      keyEvidenceDisplay
        .filter((item) => item && typeof item === "object" && String(item.evidence_id || "").trim())
        .map((item) => [String(item.evidence_id || "").trim(), item])
    );
    const differentials = Array.isArray(decision.differential_diagnoses) ? decision.differential_diagnoses : [];
    const differentialDisplay = Array.isArray(decisionDisplay.differential_diagnoses) ? decisionDisplay.differential_diagnoses : [];
    const evidenceGaps = Array.isArray(decisionDisplay.evidence_gaps_zh)
      ? decisionDisplay.evidence_gaps_zh.filter(Boolean)
      : Array.isArray(decision.evidence_gaps) ? decision.evidence_gaps.filter(Boolean) : [];
    const nextSteps = Array.isArray(decisionDisplay.recommended_next_steps_zh)
      ? decisionDisplay.recommended_next_steps_zh.filter(Boolean)
      : Array.isArray(decision.recommended_next_steps) ? decision.recommended_next_steps.filter(Boolean) : [];
    const safetyFlags = Array.isArray(decisionDisplay.safety_flags_zh)
      ? decisionDisplay.safety_flags_zh.filter(Boolean)
      : Array.isArray(decision.safety_flags) ? decision.safety_flags.filter(Boolean) : [];
    const reviewPoints = Array.isArray(decisionDisplay.human_review_points_zh)
      ? decisionDisplay.human_review_points_zh.filter(Boolean)
      : Array.isArray(decision.human_review_points) ? decision.human_review_points.filter(Boolean) : [];
    const records = Array.isArray(result.execution_records) ? result.execution_records : [];
    const planDisplaySteps = Array.isArray(result.plan_display_steps) ? result.plan_display_steps : [];
    const primaryAsset = imageAssetsFromSubmission(turn.submission)[0] || imageAssetsFromSubmission(contextSubmission)[0] || null;
    const confidence = Math.round(Number(decision.diagnosis_confidence ?? result.consensus_score ?? 0) * 100);
    return html`
      <div className="result-card decider-artifact-card">
        <div className="result-head">
          <div>
            <div className="result-title">诊断判断</div>
            <div className="result-summary">Decider 只负责基于 Executor 证据形成判断，不生成最终报告。</div>
          </div>
          <div className="badge-row">
            <span className="badge">@Decider</span>
            <span className="badge">${label(meta, "department", result.department)}</span>
            <span className="badge">${decisionDisplay.decision_status_zh || decision.decision_status || "unknown"}</span>
            <span className="badge">${confidence}% 置信度</span>
          </div>
        </div>

        <section className="decider-primary">
          <span>最可能判断</span>
          <strong>${decisionDisplay.diagnostic_impression_zh || decision.diagnostic_impression || result.executive_summary}</strong>
        </section>

        <div className="decider-grid">
          <section className="report-brief-section">
            <div className="panel-title">关键证据</div>
            <div className="report-evidence-list">
              ${keyEvidence.map((item, index) => html`
                <${AutoEvidenceDisclosure}
                  key=${index}
                  item=${{
                    statement: displayByEvidenceId[String(item.evidence_id || "").trim()]?.supports_zh
                      || displayByEvidenceId[String(item.evidence_id || "").trim()]?.quote_zh
                      || item.supports
                      || item.quote
                      || "该证据被 Decider 纳入判断。",
                    evidence_ids: item.evidence_id ? [item.evidence_id] : [],
                  }}
                  records=${records}
                  planDisplaySteps=${planDisplaySteps}
                  asset=${primaryAsset}
                  index=${index}
                />
              `)}
              ${!keyEvidence.length ? html`<div className="report-muted">暂无关键证据条目。</div>` : null}
            </div>
          </section>

          <section className="report-brief-section">
            <div className="panel-title">鉴别诊断</div>
            <div className="report-evidence-list">
              ${differentials.slice(0, 4).map((item, index) => {
                const ids = [...(item.supporting_evidence_ids || []), ...(item.refuting_evidence_ids || [])];
                const displayItem = differentialDisplay[index] || {};
                return html`
                  <div key=${index} className="report-evidence-item">
                    <span className="badge">${evidenceIdLabel(ids)}</span>
                    <span>
                      <strong>${displayItem.name_zh || item.name || "未命名鉴别诊断"} · ${displayItem.likelihood_zh || item.likelihood || "unknown"}</strong>
                      ${(displayItem.comment_zh || item.comment) ? html`<em>${displayItem.comment_zh || item.comment}</em>` : null}
                    </span>
                  </div>
                `;
              })}
              ${!differentials.length ? html`<div className="report-muted">暂无鉴别诊断条目。</div>` : null}
            </div>
          </section>
        </div>

        <div className="decider-grid">
          <section className="report-brief-section">
            <div className="panel-title">缺失信息</div>
            <div className="info-list">
              ${evidenceGaps.slice(0, 5).map((item, index) => html`
                <div key=${index} className="info-list-item"><span className="badge">${index + 1}</span><span>${item}</span></div>
              `)}
              ${!evidenceGaps.length ? html`<div className="report-muted">Decider 未列出关键缺失信息。</div>` : null}
            </div>
          </section>
          <section className="report-brief-section">
            <div className="panel-title">医生复核点</div>
            <div className="info-list">
              ${reviewPoints.slice(0, 5).map((item, index) => html`
                <div key=${index} className="info-list-item"><span className="badge">${index + 1}</span><span>${item}</span></div>
              `)}
              ${!reviewPoints.length ? html`<div className="report-muted">请复核关键证据、诊断判断和鉴别诊断。</div>` : null}
            </div>
          </section>
        </div>

        ${nextSteps.length || safetyFlags.length
          ? html`
              <details className="result-raw-details report-detail-details">
                <summary>展开下一步建议与安全提醒</summary>
                <div className="result-raw-body">
                  ${nextSteps.length
                    ? html`
                        <div className="report-detail-panel">
                          <div className="panel-title">下一步检查</div>
                          <div className="info-list">
                            ${nextSteps.map((item, index) => html`
                              <div key=${index} className="info-list-item"><span className="badge">${index + 1}</span><span>${item}</span></div>
                            `)}
                          </div>
                        </div>
                      `
                    : null}
                  ${safetyFlags.length
                    ? html`
                        <div className="report-detail-panel">
                          <div className="panel-title">安全提醒</div>
                          <div className="info-list">
                            ${safetyFlags.map((item, index) => html`
                              <div key=${index} className="info-list-item"><span className="badge">${index + 1}</span><span>${item}</span></div>
                            `)}
                          </div>
                        </div>
                      `
                    : null}
                </div>
              </details>
            `
          : null}
      </div>
    `;
  }

  function ReportTurnCard({ turn, meta, contextSubmission }) {
    const result = turn.result;
    const report = reportPayloadFromResult(result);
    const findings = Array.isArray(report.evidence_based_findings) ? report.evidence_based_findings : [];
    const recommendations = Array.isArray(report.recommendations) ? report.recommendations : [];
    const differentials = Array.isArray(report.differential_diagnosis) ? report.differential_diagnosis : [];
    const limitations = Array.isArray(report.limitations) ? report.limitations.filter(Boolean) : [];
    const reviewChecklist = Array.isArray(report.doctor_review_checklist) ? report.doctor_review_checklist.filter(Boolean) : result.next_steps || [];
    const records = Array.isArray(result.execution_records) ? result.execution_records : [];
    const planDisplaySteps = Array.isArray(result.plan_display_steps) ? result.plan_display_steps : [];
    const primaryAsset = imageAssetsFromSubmission(turn.submission)[0] || imageAssetsFromSubmission(contextSubmission)[0] || null;
    const rawModelText = result.raw_model_text || "";
    const rawProviderRequest = result.raw_provider_request || "";
    const rawProviderPayload = result.raw_provider_payload || "";
    const confidence = Math.round(Number(result.consensus_score || 0) * 100);
    return html`
      <div className="result-card report-brief-card report-artifact-card">
        <div className="result-head">
          <div>
            <div className="result-title">${report.report_title || result.title}</div>
            <div className="result-summary">${report.clinical_summary || result.executive_summary}</div>
          </div>
          <div className="badge-row">
            <span className="badge">Report Artifact</span>
            <span className="badge">${label(meta, "department", result.department)}</span>
            <span className="badge">${confidence}% 置信度</span>
          </div>
        </div>

        <div className="report-brief-grid">
          <section className="report-brief-section report-brief-primary">
            <div className="panel-title">诊断结论</div>
            <p>${report.diagnostic_assessment || result.executive_summary}</p>
          </section>

          <section className="report-brief-section">
            <div className="panel-title">关键证据</div>
            <div className="report-evidence-list">
              ${findings.slice(0, 5).map((item, index) => html`
                <${AutoEvidenceDisclosure}
                  key=${index}
                  item=${item}
                  records=${records}
                  planDisplaySteps=${planDisplaySteps}
                  asset=${primaryAsset}
                  index=${index}
                />
              `)}
              ${!findings.length ? html`<div className="report-muted">暂无结构化证据条目。</div>` : null}
            </div>
          </section>

          <section className="report-brief-section">
            <div className="panel-title">下一步建议</div>
            <div className="report-evidence-list">
              ${recommendations.slice(0, 5).map((item, index) => html`
                <div key=${index} className="report-evidence-item">
                  <span className="badge">${evidenceIdLabel(item.evidence_ids)}</span>
                  <span>
                    <strong>${item.recommendation}</strong>
                    ${item.rationale ? html`<em>${item.rationale}</em>` : null}
                  </span>
                </div>
              `)}
              ${!recommendations.length && reviewChecklist.length
                ? reviewChecklist.slice(0, 5).map((item, index) => html`
                    <div key=${index} className="report-evidence-item">
                      <span className="badge">${index + 1}</span>
                      <span>${item}</span>
                    </div>
                  `)
                : null}
              ${!recommendations.length && !reviewChecklist.length ? html`<div className="report-muted">暂无下一步建议。</div>` : null}
            </div>
          </section>

          <section className="report-brief-section report-review-section">
            <div className="panel-title">医生复核</div>
            <div className="report-evidence-list">
              ${reviewChecklist.slice(0, 4).map((item, index) => html`
                <div key=${index} className="report-evidence-item">
                  <span className="badge">${index + 1}</span>
                  <span>${item}</span>
                </div>
              `)}
              ${!reviewChecklist.length ? html`<div className="report-muted">${result.safety_note}</div>` : null}
            </div>
          </section>
        </div>

        <details className="result-raw-details report-detail-details">
          <summary>展开完整报告与核查材料</summary>
          <div className="result-raw-body">
            <div className="markdown-panel" dangerouslySetInnerHTML=${{ __html: markdownToHtml(result.professional_answer) }}></div>

            ${differentials.length
              ? html`
                  <div className="report-detail-panel">
                    <div className="panel-title">鉴别诊断</div>
                    <div className="report-evidence-list">
                      ${differentials.map((item, index) => html`
                        <div key=${index} className="report-evidence-item">
                          <span className="badge">${evidenceIdLabel(item.evidence_ids)}</span>
                          <span><strong>${item.name}</strong>${item.assessment ? html`<em>${item.assessment}</em>` : null}</span>
                        </div>
                      `)}
                    </div>
                  </div>
                `
              : null}

            ${limitations.length
              ? html`
                  <div className="report-detail-panel">
                    <div className="panel-title">局限性</div>
                    <div className="info-list">
                      ${limitations.map((item, index) => html`
                        <div key=${index} className="info-list-item">
                          <${Icon} name="history" size=${16} />
                          <span>${item}</span>
                        </div>
                      `)}
                    </div>
                  </div>
                `
              : null}

            ${report.patient_facing_note
              ? html`
                  <div className="report-detail-panel">
                    <div className="panel-title">患者说明</div>
                    <p className="report-muted">${report.patient_facing_note}</p>
                  </div>
                `
              : null}

            ${rawModelText || rawProviderRequest || rawProviderPayload
              ? html`
                  <details className="result-raw-details">
                    <summary>查看原始模型响应</summary>
                    <div className="result-raw-body">
                      <div className="result-raw-label">请求 JSON</div>
                      <pre className="result-raw-block">${rawProviderRequest || "当前记录未保存请求 JSON。"}</pre>
                      <div className="result-raw-label">结构化报告 JSON</div>
                      <pre className="result-raw-block">${rawProviderPayload || "当前记录未保存结构化报告 JSON。"}</pre>
                      <div className="result-raw-label">模型文本</div>
                      <pre className="result-raw-block">${rawModelText || "当前记录未保存模型原始文本。"}</pre>
                    </div>
                  </details>
                `
              : null}
          </div>
        </details>
      </div>
    `;
  }

  function AutoFinalConclusion({ turn }) {
    const result = turn.result;
    const report = reportPayloadFromResult(result);
    const assessment = String(report.diagnostic_assessment || "").trim();
    const findings = Array.isArray(report.evidence_based_findings) ? report.evidence_based_findings : [];
    const records = Array.isArray(result.execution_records) ? result.execution_records : [];
    const planDisplaySteps = Array.isArray(result.plan_display_steps) ? result.plan_display_steps : [];
    const primaryAsset = imageAssetsFromSubmission(turn.submission)[0] || null;
    const confidence = Math.round(Number(result.consensus_score || 0) * 100);
    return html`
      <div className="result-card auto-final-report-card">
        <div className="auto-final-report-head">
          <div>
            <div className="panel-title">证据化报告</div>
            <div className="auto-final-assessment">
              ${assessment || "报告缺少 diagnostic_assessment，无法展示最终结论。"}
            </div>
          </div>
          <div className="auto-final-meta">
            <span className="badge">${confidence}% 置信度</span>
          </div>
        </div>

        <div className="auto-final-evidence-list">
          ${findings.slice(0, 5).map((item, index) => html`
            <${AutoEvidenceDisclosure}
              key=${index}
              item=${item}
              records=${records}
              planDisplaySteps=${planDisplaySteps}
              asset=${primaryAsset}
              index=${index}
            />
          `)}
          ${!findings.length ? html`<div className="report-muted">暂无结构化证据条目。</div>` : null}
        </div>
      </div>
    `;
  }

  function GeneralTurnCard({ turn, meta }) {
    const result = turn.result;
    const rawModelText = result.raw_model_text || "";
    const rawProviderRequest = result.raw_provider_request || "";
    const rawProviderPayload = result.raw_provider_payload || "";
    const showRawInspector =
      result.execution_mode === "single_model" || Boolean(rawProviderRequest || rawProviderPayload || rawModelText);
    return html`
      <div className="result-card">
        <div className="result-head">
          <div>
            <div className="result-title">${result.title}</div>
            <div className="result-summary">${result.executive_summary}</div>
          </div>
          <div className="badge-row">
            <span className="badge">${label(meta, "department", result.department)}</span>
            <span className="badge">${label(meta, "output", result.output_style)}</span>
            <span className="badge">${Math.round(result.consensus_score * 100)}% 一致性</span>
          </div>
        </div>

        <div className="result-section-grid">
          <div className="markdown-panel" dangerouslySetInnerHTML=${{ __html: markdownToHtml(result.professional_answer) }}></div>
          <div className="info-panel">
            <div className="panel-title">下一步建议</div>
            <div className="info-list">
              ${result.next_steps.map(
                (step, index) => html`
                  <div key=${index} className="info-list-item">
                    <${Icon} name="spark" size=${16} />
                    <span>${step}</span>
                  </div>
                `
              )}
            </div>

            <div className="panel-title" style=${{ marginTop: "18px" }}>安全提醒</div>
            <div className="info-list-item">
              <${Icon} name="history" size=${16} />
              <span>${result.safety_note}</span>
            </div>
          </div>
        </div>

        ${showRawInspector &&
        html`
          <details className="result-raw-details">
            <summary>查看原始模型响应（用于核查）</summary>
            <div className="result-raw-body">
              <div className="result-raw-label">请求 JSON</div>
              <pre className="result-raw-block">${rawProviderRequest || "当前记录未保存请求 JSON。请提交新请求后再核查。"}</pre>

              <div className="result-raw-label">API 原始 JSON</div>
              <pre className="result-raw-block">${rawProviderPayload || "当前记录未保存 API 原始 JSON。请提交新请求后再核查。"}</pre>

              <div className="result-raw-label">模型文本</div>
              <pre className="result-raw-block">${rawModelText || "当前记录未保存模型原始文本。请提交新请求后再核查。"}</pre>
            </div>
          </details>
        `}

        <${DataTableCard}
          title="编码建议"
          rows=${result.coding_table}
          columns=${[
            { key: "编码体系", label: "编码体系" },
            { key: "建议编码", label: "建议编码" },
            { key: "临床用途", label: "临床用途" },
          ]}
        />

        <${DataTableCard}
          title="费用评估"
          rows=${result.cost_table}
          columns=${[
            { key: "项目", label: "项目" },
            { key: "估算", label: "估算" },
          ]}
        />

        <${DataTableCard}
          title="参考依据"
          rows=${result.references}
          columns=${[
            { key: "type", label: "来源" },
            { key: "title", label: "标题" },
            { key: "region", label: "区域" },
          ]}
        />
      </div>
    `;
  }

  function TurnWorkspace({ turn, meta, contextSubmission, session, onSubmitApproval }) {
    const result = turn.result;
    const submission = turn.submission;
    const autoTurn = isAutoTurn(turn);
    const stale = isTurnStale(session, turn);
    return html`
      <div>
        ${autoTurn
          ? null
          : html`
              <div className="message-card message-user">
                <div className="message-meta">
                  <span>当前输入</span>
                  <span>·</span>
                  <span>${formatTimestamp(turn.timestamp)}</span>
                  ${stale ? html`<span className="message-meta-stale">旧版 workflow</span>` : null}
                </div>
                <div className="message-body">${turn.user_input || submission.case_summary}</div>
              </div>
            `}

        <${ExecutionStatusCard}
          executionMode=${result.execution_mode}
          providerName=${result.serving_provider}
          modelName=${result.serving_model}
        />
        ${stale
          ? html`<div className="context-alert stale-turn-alert">该结果基于旧版 Planner 计划，已降级为历史记录，不会再作为当前 Executor / Decider / Report 的输入。</div>`
          : null}

        ${result.execution_mode === "planner"
          ? html`<${PlannerTurnCard} turn=${turn} meta=${meta} session=${session} onSubmitApproval=${onSubmitApproval} stale=${stale} />`
          : result.execution_mode === "executor"
            ? html`<${ExecutorTurnCard} turn=${turn} meta=${meta} contextSubmission=${contextSubmission} />`
            : result.execution_mode === "decider"
              ? html`<${DeciderTurnCard} turn=${turn} meta=${meta} contextSubmission=${contextSubmission} />`
              : result.execution_mode === "report"
                ? html`<${ReportTurnCard} turn=${turn} meta=${meta} contextSubmission=${contextSubmission} />`
                : html`<${GeneralTurnCard} turn=${turn} meta=${meta} />`}
        ${session && turn?.turn_id && onSubmitApproval && result.execution_mode !== "planner" && !stale
          ? html`<${DoctorApprovalPanel} session=${session} turn=${turn} onSubmit=${onSubmitApproval} />`
          : null}
      </div>
    `;
  }

  function ResultWorkspace({ session, meta, onSubmitApproval, onSubmitFeedback }) {
    if (!session) {
      return null;
    }

    if (!session.result || !session.submission) {
      return html`<${SessionSummaryOnly} session=${session} meta=${meta} />`;
    }

    const contextSubmission = session.context_submission || session.submission;
    const turns = visibleTurnsForSession(session);
    const autoFinalTurn = autoFinalTurnForSession(session);
    if (autoFinalTurn) {
      return html`
        <div className="workspace-feed auto-final-feed">
          <${AutoFinalConclusion} turn=${autoFinalTurn} />
          ${onSubmitFeedback ? html`<${CaseFeedbackPanel} key=${`${session.session_id}-feedback`} session=${session} onSubmit=${onSubmitFeedback} autoFinal=${true} />` : null}
        </div>
      `;
    }
    return html`
      <div className="workspace-feed">
        ${turns.map((turn, index) => html`
          <${TurnWorkspace}
            key=${turn.turn_id || `${turn.timestamp}-${index}`}
            turn=${turn}
            meta=${meta}
            contextSubmission=${contextSubmission}
            session=${session}
            onSubmitApproval=${onSubmitApproval}
          />
        `)}
        ${onSubmitFeedback ? html`<${CaseFeedbackPanel} key=${`${session.session_id}-feedback`} session=${session} onSubmit=${onSubmitFeedback} />` : null}
      </div>
    `;
  }

  function formatTableValue(value) {
    if (Array.isArray(value)) {
      return value.join(", ");
    }
    if (value === null || value === undefined || value === "") {
      return "—";
    }
    if (typeof value === "object") {
      return JSON.stringify(value);
    }
    return value;
  }

  function DataTableCard({ title, columns, rows }) {
    const safeRows = Array.isArray(rows) ? rows : [];
    if (!safeRows.length) {
      return null;
    }
    return html`
      <div className="table-card">
        <div className="table-head">
          <div className="panel-title">${title}</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              ${columns.map((column) => html`<th key=${column.key}>${column.label}</th>`)}
            </tr>
          </thead>
          <tbody>
            ${safeRows.map(
              (row, index) => html`
                <tr key=${index}>
                  ${columns.map((column) => html`<td key=${column.key}>${formatTableValue(row[column.key])}</td>`)}
                </tr>
              `
            )}
          </tbody>
        </table>
      </div>
    `;
  }

  function DiagnosticsDrawer({ open, session, meta, onClose }) {
    const result = session?.result;
    const contextSubmission = session?.context_submission || session?.submission || null;
    return html`
      <aside className=${cx("drawer", open && "is-open")}>
        <div className="drawer-head">
          <div>
            <div className="drawer-title">诊断面板</div>
            <div className="topbar-copy">病例状态、证据台账和复核队列。</div>
          </div>
          <button className="icon-button" onClick=${onClose} aria-label="Close diagnostics">
            <${Icon} name="close" size=${18} />
          </button>
        </div>
        <div className="drawer-body">
          ${!result
            ? html`
                <div className="drawer-card" style=${{ padding: "18px" }}>
                  <div className="panel-title">暂无结果</div>
                  <p style=${{ margin: 0, color: "var(--text-subtle)", lineHeight: 1.7 }}>
                    提交病例后，这里会显示病例上下文、执行阶段、证据台账和医生复核状态。
                  </p>
                </div>
              `
            : html`
                <${CaseRuntimePanel} session=${session} meta=${meta} contextSubmission=${contextSubmission} />

                <details className="result-raw-details report-detail-details">
                  <summary>模型轨迹</summary>
                  <div className="drawer-card" style=${{ padding: "18px" }}>
                    <div className="badge-row">
                      <span className="badge">${label(meta, "department", result.department)}</span>
                      <span className="badge">${label(meta, "output", result.output_style)}</span>
                      <span className="badge">${Math.round(result.consensus_score * 100)}% 一致性</span>
                    </div>
                  </div>
                  ${result.rounds.map(
                    (round) => html`
                      <div key=${round.round} className="drawer-card" style=${{ padding: "18px" }}>
                        <div className="panel-title">Round ${round.round}</div>
                        <div className="result-title" style=${{ fontSize: "1rem" }}>${Math.round(round.alignment * 100)}% Alignment</div>
                        <p style=${{ color: "var(--text-subtle)", lineHeight: 1.7, marginBottom: 0 }}>${round.summary}</p>
                      </div>
                    `
                  )}
                  ${result.agent_trace.map(
                    (trace, index) => html`
                      <div key=${index} className="drawer-card" style=${{ padding: "18px" }}>
                        <div className="panel-title">${label(meta, "role", trace.role)}</div>
                        <div className="sidebar-footer-name">${trace.provider}</div>
                        <p style=${{ color: "var(--text-subtle)", lineHeight: 1.7, marginBottom: 0 }}>${trace.note}</p>
                      </div>
                    `
                  )}
                </details>
              `}
        </div>
      </aside>
    `;
  }

  function Composer({
    meta,
    settings,
    composer,
    setComposer,
    currentSession,
    onToggleSingleModelTest,
    onSubmit,
    onReset,
    isSubmitting,
    pushNotice,
  }) {
    const hasInput = composer.case_summary.trim().length > 0;
    const attachmentMenuRef = useRef(null);
    const editorWrapRef = useRef(null);
    const editorRef = useRef(null);
    const slashContextRef = useRef(null);
    const slashRootItemRefs = useRef([]);
    const slashChildItemRefs = useRef([]);
    const [slashMenu, setSlashMenu] = useState({
      open: false,
      trigger: "/",
      path: [],
      activeIndex: 0,
      query: "",
      position: { left: 20, top: 156, maxHeight: 360, placement: "down" },
    });
    const slashRootItems = useMemo(() => {
      const rootItems = commandTreeForTrigger(slashMenu.trigger);
      const filtered = filterSlashItems(rootItems, slashMenu.path.length ? "" : slashMenu.query);
      return filtered.length || slashMenu.path.length ? filtered : rootItems;
    }, [slashMenu.path.length, slashMenu.query, slashMenu.trigger]);
    const activeRootId = slashMenu.path[0] || null;
    const activeRootItem = useMemo(() => commandTreeForTrigger(slashMenu.trigger).find((item) => item.id === activeRootId) || null, [activeRootId, slashMenu.trigger]);
    const slashChildItems = useMemo(() => activeRootItem?.children || [], [activeRootItem]);

    useEffect(() => {
      if (!composer.attachment_panel_open) {
        return undefined;
      }

      function handlePointerDown(event) {
        if (attachmentMenuRef.current && !attachmentMenuRef.current.contains(event.target)) {
          setComposer((current) => ({ ...current, attachment_panel_open: false }));
        }
      }

      window.addEventListener("pointerdown", handlePointerDown);
      return () => window.removeEventListener("pointerdown", handlePointerDown);
    }, [composer.attachment_panel_open, setComposer]);

    useEffect(() => {
      const editor = editorRef.current;
      if (!editor) {
        return;
      }
      const currentBlocks = serializeCaseBlocks(readEditorBlocks(editor));
      const targetBlocks = serializeCaseBlocks(composer.case_blocks || []);
      if (currentBlocks !== targetBlocks) {
        renderEditorBlocks(editor, composer.case_blocks || []);
      }
    }, [composer.case_blocks]);

    useEffect(() => {
      if (!slashMenu.open) {
        return undefined;
      }

      function handlePointerDown(event) {
        if (editorWrapRef.current && !editorWrapRef.current.contains(event.target)) {
          slashContextRef.current = null;
          setSlashMenu((current) => ({ ...current, open: false, path: [], activeIndex: 0, query: "" }));
        }
      }

      window.addEventListener("pointerdown", handlePointerDown);
      return () => window.removeEventListener("pointerdown", handlePointerDown);
    }, [slashMenu.open]);

    useEffect(() => {
      if (!slashMenu.open) {
        return;
      }
      if (!slashRootItems.length) {
        slashContextRef.current = null;
        setSlashMenu((current) => ({ ...current, open: false, path: [], activeIndex: 0, query: "" }));
        return;
      }
      if (!slashMenu.path.length && slashMenu.activeIndex >= slashRootItems.length) {
        setSlashMenu((current) => ({ ...current, activeIndex: 0 }));
      }
      if (slashMenu.path.length && slashMenu.activeIndex >= slashChildItems.length) {
        setSlashMenu((current) => ({ ...current, activeIndex: 0 }));
      }
    }, [slashRootItems.length, slashChildItems.length, slashMenu.activeIndex, slashMenu.open, slashMenu.path.length]);

    useEffect(() => {
      if (!slashMenu.open) {
        return;
      }
      const activeNode = slashMenu.path.length ? slashChildItemRefs.current[slashMenu.activeIndex] : slashRootItemRefs.current[slashMenu.activeIndex];
      if (!activeNode) {
        return;
      }
      activeNode.scrollIntoView({
        block: "nearest",
        inline: "nearest",
      });
    }, [slashMenu.open, slashMenu.activeIndex, slashMenu.path.length, slashRootItems.length, slashChildItems.length, slashMenu.query]);

    function syncComposerFromEditor() {
      const editor = editorRef.current;
      if (!editor) {
        return;
      }
      const nextBlocks = readEditorBlocks(editor);
      const nextSummary = blocksToPlainText(nextBlocks);
      const nextKey = serializeCaseBlocks(nextBlocks);
      setComposer((current) => {
        if (current.case_summary === nextSummary && serializeCaseBlocks(current.case_blocks || []) === nextKey) {
          return current;
        }
        return {
          ...current,
          case_summary: nextSummary,
          case_blocks: nextBlocks,
        };
      });
    }

    function closeSlashMenu() {
      slashContextRef.current = null;
      setSlashMenu((current) => ({ ...current, open: false, path: [], activeIndex: 0, query: "" }));
    }

    function refreshSlashMenu(pathOverride) {
      const editor = editorRef.current;
      const wrap = editorWrapRef.current;
      if (!editor || !wrap) {
        return;
      }

      const context = getSlashTriggerContext(editor, wrap);
      if (!context) {
        closeSlashMenu();
        return;
      }

      const nextPath = context.trigger === slashMenu.trigger ? pathOverride || slashMenu.path : [];
      const rootItems = commandTreeForTrigger(context.trigger);
      const visibleItems = nextPath.length ? getSlashItems(nextPath, context.trigger) : filterSlashItems(rootItems, context.query);
      if (!visibleItems.length) {
        closeSlashMenu();
        return;
      }

      slashContextRef.current = context;
      setSlashMenu((current) => ({
        ...current,
        open: true,
        trigger: context.trigger,
        path: nextPath,
        activeIndex: Math.min(current.activeIndex, visibleItems.length - 1),
        query: context.query,
        position: context.position,
      }));
    }

    function insertEditorText(text) {
      const editor = editorRef.current;
      if (!editor) {
        return;
      }
      editor.focus();
      insertPlainTextAtSelection(editor, text);
      syncComposerFromEditor();
      window.requestAnimationFrame(() => refreshSlashMenu());
    }

    async function pasteFromClipboard() {
      try {
        const text = await navigator.clipboard.readText();
        if (!text.trim()) {
          pushNotice("未读取到剪贴板内容。", "error");
          return;
        }
        insertEditorText(text);
      } catch (error) {
        pushNotice("浏览器未允许剪贴板读取。", "error");
      }
    }

    function updateField(key, value) {
      setComposer((current) => ({ ...current, [key]: value }));
    }

    function handleFiles(key, fileList) {
      setComposer((current) => ({
        ...current,
        [key]: Array.from(fileList || []),
        attachment_panel_open: false,
        attachment_epoch: Date.now(),
      }));
    }

    function removeFile(key, index) {
      setComposer((current) => ({
        ...current,
        [key]: current[key].filter((_, itemIndex) => itemIndex !== index),
      }));
    }

    function insertSlashToken(item) {
      const editor = editorRef.current;
      if (!editor) {
        return;
      }

      const context = getSlashTriggerContext(editor, editorWrapRef.current) || slashContextRef.current;
      if (!context) {
        closeSlashMenu();
        return;
      }

      const selection = ensureEditorSelection(editor);
      if (!selection || !selection.rangeCount) {
        closeSlashMenu();
        return;
      }

      const range = document.createRange();
      range.setStart(context.node, context.slashIndex);
      range.setEnd(context.node, context.endOffset);
      range.deleteContents();

      const token = buildSlashToken(item, slashMenu.path, slashMenu.trigger);
      const fragment = document.createDocumentFragment();
      const tokenNode = createEditorTokenElement(token);
      const spacer = document.createTextNode(" ");
      fragment.appendChild(tokenNode);
      fragment.appendChild(spacer);
      range.insertNode(fragment);
      placeCaretAfterNode(spacer);
      syncComposerFromEditor();
      closeSlashMenu();
      editor.focus();
    }

    function handleEditorInput() {
      syncComposerFromEditor();
      window.requestAnimationFrame(() => refreshSlashMenu());
    }

    function handleEditorPaste(event) {
      event.preventDefault();
      const text = event.clipboardData?.getData("text/plain") || "";
      if (text) {
        insertEditorText(text);
      }
    }

    function handleEditorKeyDown(event) {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && hasInput && !isSubmitting) {
        event.preventDefault();
        onSubmit();
        return;
      }

      if (slashMenu.open) {
        if (event.key === "ArrowDown") {
          event.preventDefault();
          setSlashMenu((current) => ({
            ...current,
            activeIndex: current.path.length
              ? slashChildItems.length
                ? (current.activeIndex + 1) % slashChildItems.length
                : 0
              : slashRootItems.length
                ? (current.activeIndex + 1) % slashRootItems.length
                : 0,
          }));
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          setSlashMenu((current) => ({
            ...current,
            activeIndex: current.path.length
              ? slashChildItems.length
                ? (current.activeIndex - 1 + slashChildItems.length) % slashChildItems.length
                : 0
              : slashRootItems.length
                ? (current.activeIndex - 1 + slashRootItems.length) % slashRootItems.length
                : 0,
          }));
          return;
        }
        if (event.key === "ArrowRight" || event.key === "Enter") {
          const activeItem = slashMenu.path.length ? slashChildItems[slashMenu.activeIndex] : slashRootItems[slashMenu.activeIndex];
          if (activeItem) {
            event.preventDefault();
            if (activeItem.children) {
              setSlashMenu((current) => ({
                ...current,
                open: true,
                path: [...current.path, activeItem.id],
                activeIndex: 0,
                query: "",
              }));
            } else {
              insertSlashToken(activeItem);
            }
          }
          return;
        }
        if (event.key === "ArrowLeft") {
          if (slashMenu.path.length) {
            event.preventDefault();
            setSlashMenu((current) => ({
              ...current,
              path: current.path.slice(0, -1),
              activeIndex: 0,
              query: "",
            }));
          }
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          closeSlashMenu();
          return;
        }
      }

      if (event.key === "Enter") {
        event.preventDefault();
        insertEditorText("\n");
        return;
      }

      if (event.key === "Backspace" && removeAdjacentToken(editorRef.current, "backward")) {
        event.preventDefault();
        syncComposerFromEditor();
        window.requestAnimationFrame(() => refreshSlashMenu());
        return;
      }

      if (event.key === "Delete" && removeAdjacentToken(editorRef.current, "forward")) {
        event.preventDefault();
        syncComposerFromEditor();
        window.requestAnimationFrame(() => refreshSlashMenu());
      }
    }

    return html`
      <div className="composer-shell">
        <div className="composer-body">
          ${currentSession &&
          html`
            <div className="status-card" style=${{ marginBottom: "12px" }}>
              <div className="status-card-title">当前上下文已启用</div>
              <div className="status-card-copy">${currentSession.title || "当前病例"} · 输入 /clear 可开始新的会话</div>
            </div>
          `}
          <div className="composer-textarea-wrap" ref=${editorWrapRef}>
            <div
              ref=${editorRef}
              className="composer-textarea composer-editor"
              contentEditable=${true}
              role="textbox"
              aria-multiline="true"
              spellCheck=${false}
              data-placeholder="粘贴或输入完整病例摘要（病史、查体、检验/影像摘要等）…"
              onInput=${handleEditorInput}
              onPaste=${handleEditorPaste}
              onKeyDown=${handleEditorKeyDown}
              onClick=${() => window.requestAnimationFrame(() => refreshSlashMenu())}
              onKeyUp=${(event) => {
                if (!slashMenu.open && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
                  window.requestAnimationFrame(() => refreshSlashMenu());
                }
              }}
            ></div>

            ${slashMenu.open &&
            slashRootItems.length > 0 &&
            html`
              <div className="slash-menu-stack" style=${{ left: `${slashMenu.position.left}px`, top: `${slashMenu.position.top}px` }}>
                <div className="slash-menu-popup" style=${{ maxHeight: `${slashMenu.position.maxHeight}px` }}>
                  <div className="slash-menu-list">
                    ${slashRootItems.map(
                      (item, index) => html`
                        <button
                          key=${item.id}
                          ref=${(node) => {
                            slashRootItemRefs.current[index] = node;
                          }}
                          type="button"
                          className=${cx(
                            "slash-menu-item",
                            item.dividerBefore && "has-divider",
                            !slashMenu.path.length && index === slashMenu.activeIndex && "is-active",
                            slashMenu.path[0] === item.id && "is-selected"
                          )}
                          title=${item.hint || ""}
                          onMouseDown=${(event) => event.preventDefault()}
                          onMouseEnter=${() => {
                            if (slashMenu.path.length) {
                              setSlashMenu((current) => ({ ...current, path: [item.id], activeIndex: 0, query: "" }));
                            } else {
                              setSlashMenu((current) => ({ ...current, activeIndex: index }));
                            }
                          }}
                          onClick=${() =>
                            item.children
                              ? setSlashMenu((current) => ({ ...current, path: [item.id], activeIndex: 0, query: "" }))
                              : insertSlashToken(item)}
                        >
                          <div className="slash-menu-copy">
                            <span className="slash-menu-label">${item.label}</span>
                          </div>
                          ${item.children && html`<span className="slash-menu-arrow">›</span>`}
                        </button>
                      `
                    )}
                  </div>
                </div>

                ${Boolean(slashMenu.path.length) &&
                slashChildItems.length > 0 &&
                html`
                  <div className="slash-menu-popup slash-submenu-popup" style=${{ maxHeight: `${slashMenu.position.maxHeight}px` }}>
                    <div className="slash-menu-list">
                      ${slashChildItems.map(
                        (item, index) => html`
                          <button
                            key=${item.id}
                            ref=${(node) => {
                              slashChildItemRefs.current[index] = node;
                            }}
                            type="button"
                            className=${cx("slash-menu-item", index === slashMenu.activeIndex && "is-active")}
                            title=${item.hint || ""}
                            onMouseDown=${(event) => event.preventDefault()}
                            onMouseEnter=${() => setSlashMenu((current) => ({ ...current, activeIndex: index }))}
                            onClick=${() => insertSlashToken(item)}
                          >
                            <div className="slash-menu-copy">
                              <span className="slash-menu-label">${item.label}</span>
                            </div>
                          </button>
                        `
                      )}
                    </div>
                  </div>
                `}
              </div>
            `}
          </div>

          ${composer.input_expanded &&
          html`
            <div className="advanced-panel">
              <div className="panel-title">高级录入</div>
              <div className="form-grid wide">
                <label className="field">
                  <span className="field-label">主诉</span>
                  <input value=${composer.chief_complaint} onChange=${(event) => updateField("chief_complaint", event.target.value)} />
                </label>
                <label className="field">
                  <span className="field-label">年龄</span>
                  <input value=${composer.patient_age} onChange=${(event) => updateField("patient_age", event.target.value)} />
                </label>
                <label className="field">
                  <span className="field-label">性别</span>
                  <select value=${composer.patient_sex} onChange=${(event) => updateField("patient_sex", event.target.value)}>
                    ${meta.sex_options.map((option) => html`<option key=${option} value=${option}>${label(meta, "sex", option)}</option>`)}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">医保</span>
                  <select value=${composer.insurance_type} onChange=${(event) => updateField("insurance_type", event.target.value)}>
                    ${meta.insurance_options.map((option) => html`<option key=${option} value=${option}>${label(meta, "insurance", option)}</option>`)}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">科室</span>
                  <select value=${composer.department} onChange=${(event) => updateField("department", event.target.value)}>
                    ${meta.departments.map((option) => html`<option key=${option} value=${option}>${label(meta, "department", option)}</option>`)}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">输出类型</span>
                  <select value=${composer.output_style} onChange=${(event) => updateField("output_style", event.target.value)}>
                    ${meta.output_styles.map((option) => html`<option key=${option} value=${option}>${label(meta, "output", option)}</option>`)}
                  </select>
                </label>
                <label className="field">
                  <span className="field-label">紧急程度</span>
                  <select value=${composer.urgency} onChange=${(event) => updateField("urgency", event.target.value)}>
                    ${meta.urgency_options.map((option) => html`<option key=${option} value=${option}>${label(meta, "urgency", option)}</option>`)}
                  </select>
                </label>
                <button
                  className=${cx("toggle-pill", composer.show_process && "is-on")}
                  onClick=${() => updateField("show_process", !composer.show_process)}
                  style=${{ alignSelf: "end", marginBottom: "2px" }}
                >
                  <span className="toggle-switch"></span>
                  过程诊断
                </button>
              </div>
            </div>
          `}

          <div className="composer-controls">
            <div className="attachment-menu-anchor" ref=${attachmentMenuRef}>
              <button
                className=${cx("icon-button", composer.attachment_panel_open && "is-active")}
                onClick=${() => updateField("attachment_panel_open", !composer.attachment_panel_open)}
                aria-label="Toggle attachments"
              >
                <${Icon} name="plus" size=${24} />
              </button>

              ${composer.attachment_panel_open &&
              html`
                <div className="attachment-menu" role="menu" aria-label="附件菜单">
                  <label className="attachment-menu-item" key=${`images-${composer.attachment_epoch}`}>
                    <span className="attachment-menu-label">上传影像</span>
                    <span className="attachment-menu-copy">PNG / JPG / WEBP</span>
                    <input
                      className="attachment-menu-input"
                      type="file"
                      accept=".png,.jpg,.jpeg,.webp"
                      multiple
                      onChange=${(event) => handleFiles("image_files", event.target.files)}
                    />
                  </label>

                  <label className="attachment-menu-item" key=${`docs-${composer.attachment_epoch}`}>
                    <span className="attachment-menu-label">上传文档</span>
                    <span className="attachment-menu-copy">PDF / TXT / DOCX</span>
                    <input
                      className="attachment-menu-input"
                      type="file"
                      accept=".pdf,.txt,.docx"
                      multiple
                      onChange=${(event) => handleFiles("doc_files", event.target.files)}
                    />
                  </label>
                </div>
              `}
            </div>

            <div className="composer-status">${composer.attachment_panel_open ? "附件菜单已展开" : "Command + Enter 提交病例"}</div>

            <button
              className=${cx("icon-button", "tooltip-button", composer.single_model_test && "is-active")}
              onClick=${() =>
                onToggleSingleModelTest
                  ? onToggleSingleModelTest(!composer.single_model_test)
                  : updateField("single_model_test", !composer.single_model_test)}
              aria-label="Single model test"
              data-tooltip="单模型测试"
            >
              <${Icon} name="singleModel" size=${26} />
            </button>

            <button
              className=${cx("toggle-pill", "tooltip-button", composer.input_expanded && "is-on")}
              onClick=${() => updateField("input_expanded", !composer.input_expanded)}
              data-tooltip="逐项输入"
            >
              <span className="toggle-switch"></span>
              高级模式
            </button>

            <button className="icon-button tooltip-button" onClick=${pasteFromClipboard} aria-label="Paste from clipboard" data-tooltip="从剪贴板粘贴">
              <${Icon} name="paste" size=${24} />
            </button>

            <button className="icon-button tooltip-button" onClick=${onReset} aria-label="Reset composer" data-tooltip="清空重置">
              <${Icon} name="reset" size=${22} />
            </button>

            <div className="tooltip-button" data-tooltip=${hasInput ? "提交" : "请填写病例内容"}>
              <button
                className=${cx("send-button", hasInput && "is-ready")}
                disabled=${!hasInput || isSubmitting}
                onClick=${onSubmit}
                aria-label="Submit case"
              >
                <${Icon} name="arrowUp" size=${24} />
              </button>
            </div>
          </div>

          ${Boolean(composer.image_files.length || composer.doc_files.length) &&
          html`
            <div className="file-chips">
              ${composer.image_files.map(
                (file, index) => html`
                  <span key=${`img-${file.name}-${index}`} className="file-chip">
                    <span className="file-chip-name">${file.name}</span>
                    <button
                      className="file-chip-remove"
                      onClick=${() => removeFile("image_files", index)}
                      aria-label=${`移除附件 ${file.name}`}
                      type="button"
                    >
                      <${Icon} name="close" size=${12} />
                    </button>
                  </span>
                `
              )}
              ${composer.doc_files.map(
                (file, index) => html`
                  <span key=${`doc-${file.name}-${index}`} className="file-chip">
                    <span className="file-chip-name">${file.name}</span>
                    <button
                      className="file-chip-remove"
                      onClick=${() => removeFile("doc_files", index)}
                      aria-label=${`移除附件 ${file.name}`}
                      type="button"
                    >
                      <${Icon} name="close" size=${12} />
                    </button>
                  </span>
                `
              )}
            </div>
          `}
        </div>
      </div>
    `;
  }

  function HistoryPage({
    meta,
    sessions,
    onOpenSession,
    onToggleSidebarSession,
    onSetAllSidebarSessions,
    visibilityBusyKey,
    selectedSession,
    isLoadingDetail,
    onBack,
    onSubmitApproval,
    onSubmitFeedback,
  }) {
    const [sortMode, setSortMode] = useState("date_desc");
    const visibleCount = useMemo(() => sessions.filter((session) => session.show_in_sidebar !== false).length, [sessions]);
    const sortedSessions = useMemo(() => {
      const next = [...sessions];
      if (sortMode === "name_asc") {
        return next.sort((left, right) => left.title.localeCompare(right.title, "zh-Hans-CN"));
      }
      if (sortMode === "name_desc") {
        return next.sort((left, right) => right.title.localeCompare(left.title, "zh-Hans-CN"));
      }
      if (sortMode === "date_asc") {
        return next.sort((left, right) => (left.timestamp || "").localeCompare(right.timestamp || ""));
      }
      return next.sort((left, right) => (right.timestamp || "").localeCompare(left.timestamp || ""));
    }, [sessions, sortMode]);

    if (selectedSession || isLoadingDetail) {
      return html`
        <div className="settings-content history-detail-view">
          <div className="history-detail-actions">
            <button className="secondary-button" onClick=${onBack}>
              <${Icon} name="chevronLeft" size=${16} />
              返回历史列表
            </button>
          </div>

          ${isLoadingDetail
            ? html`<div className="empty-feed">正在加载会诊记录…</div>`
                    : html`<${ResultWorkspace} session=${selectedSession} meta=${meta} onSubmitApproval=${onSubmitApproval} onSubmitFeedback=${onSubmitFeedback} />`}
        </div>
      `;
    }

    return html`
      <div className="settings-content">
        <div className="history-toolbar">
          <div className="history-toolbar-group">
            <button className="secondary-button" onClick=${() => onSetAllSidebarSessions(true)} disabled=${Boolean(visibilityBusyKey)}>
              全部显示
            </button>
            <button className="secondary-button" onClick=${() => onSetAllSidebarSessions(false)} disabled=${Boolean(visibilityBusyKey)}>
              全部隐藏
            </button>
          </div>
          <div className="history-toolbar-group history-toolbar-meta">
            <span>${visibleCount} / ${sessions.length} 显示在侧栏</span>
            <select value=${sortMode} onChange=${(event) => setSortMode(event.target.value)}>
              <option value="date_desc">按时间排序: 新到旧</option>
              <option value="date_asc">按时间排序: 旧到新</option>
              <option value="name_asc">按名称排序: A-Z</option>
              <option value="name_desc">按名称排序: Z-A</option>
            </select>
          </div>
        </div>
        <div className="history-list">
          ${sortedSessions.length
            ? sortedSessions.map(
                (session) => html`
                  <div key=${session.session_id} className="history-card">
                    <button className="history-card-main" onClick=${() => onOpenSession(session.session_id)}>
                      <div className="sidebar-item-row">
                        <div className="sidebar-item-title">${session.title}</div>
                        <span className="badge">${Math.round((session.consensus_score || 0) * 100)}%</span>
                      </div>
                      <div className="sidebar-item-meta">${label(meta, "department", session.department)} · ${label(meta, "output", session.output_style)}</div>
                      <div className="history-item-time">${formatTimestamp(session.timestamp)}</div>
                      <div className="history-item-summary">${session.summary}</div>
                    </button>
                    <button
                      className=${cx("history-toggle", session.show_in_sidebar !== false && "is-on")}
                      onClick=${() => onToggleSidebarSession(session.session_id, session.show_in_sidebar === false)}
                      disabled=${Boolean(visibilityBusyKey)}
                      aria-label=${session.show_in_sidebar === false ? "Show in sidebar" : "Hide from sidebar"}
                      title=${session.show_in_sidebar === false ? "在侧栏显示" : "从侧栏隐藏"}
                    >
                      <span className="history-toggle-thumb"></span>
                    </button>
                  </div>
                `
              )
            : html`<div className="sidebar-item-meta">暂无历史记录。</div>`}
        </div>
      </div>
    `;
  }

  function LoginScreen({ draft, setDraft, onSubmit, isSubmitting }) {
    function update(key, value) {
      setDraft((current) => ({ ...current, [key]: value }));
    }

    return html`
      <div className="login-shell">
        <div className="login-card">
          <div className="login-brand">
            <div className="brand-mark"><${BrandGlyph} className="brand-mark-glyph" /></div>
            <div>
              <div className="brand-name">RareMDT</div>
              <div className="brand-copy">罕见病多智能体诊疗系统</div>
            </div>
          </div>

          <div>
            <div className="settings-title">登录工作台</div>
            <div className="settings-copy">使用账号进入会诊工作区，管理员可在登录后管理用户与查询概览。</div>
          </div>

          <div className="settings-content">
            <label className="field">
              <span className="field-label">用户名</span>
              <input value=${draft.username} onChange=${(event) => update("username", event.target.value)} onKeyDown=${(event) => event.key === "Enter" && onSubmit()} />
            </label>
            <label className="field">
              <span className="field-label">密码</span>
              <input type="password" value=${draft.password} onChange=${(event) => update("password", event.target.value)} onKeyDown=${(event) => event.key === "Enter" && onSubmit()} />
            </label>
          </div>

          <button className="primary-button login-button" onClick=${onSubmit} disabled=${isSubmitting}>
            ${isSubmitting ? "登录中..." : "登录"}
          </button>
        </div>

        <div className="login-footer">
          <div>© HKU-SZH 2026</div>
          <div>Authors Peikai Chen and Marco Xu @AIBD Lab</div>
        </div>
      </div>
    `;
  }

  function AdminAccountsPage({
    accounts,
    draft,
    setDraft,
    onCreate,
    onToggleDisabled,
    onDelete,
    currentUsername,
    isMutating,
  }) {
    function update(key, value) {
      setDraft((current) => ({ ...current, [key]: value }));
    }

    return html`
      <div className="settings-content">
        <div className="account-create-card">
          <div className="config-card-head">
            <div className="config-card-title">新增账户</div>
          </div>
          <div className="form-grid wide">
            <label className="field">
              <span className="field-label">用户名</span>
              <input value=${draft.username} onChange=${(event) => update("username", event.target.value)} />
            </label>
            <label className="field">
              <span className="field-label">密码</span>
              <input type="password" value=${draft.password} onChange=${(event) => update("password", event.target.value)} />
            </label>
            <button className=${cx("toggle-pill", draft.is_admin && "is-on")} onClick=${() => update("is_admin", !draft.is_admin)} style=${{ alignSelf: "end", marginBottom: "2px" }}>
              <span className="toggle-switch"></span>
              管理员
            </button>
          </div>
          <div style=${{ display: "flex", justifyContent: "flex-end", marginTop: "16px" }}>
            <button className="primary-button" onClick=${onCreate} disabled=${isMutating}>创建账户</button>
          </div>
        </div>

        <div className="card-list">
          ${accounts.length
            ? accounts.map(
                (account) => html`
                  <div key=${account.username} className="account-card">
                    <div className="config-card-head">
                      <div>
                        <div className="config-card-title">${account.display_name || account.username}</div>
                        <div className="sidebar-item-meta">@${account.username}${account.hospital_name ? ` · ${account.hospital_name}` : ""}</div>
                      </div>
                      <div className="badge-row">
                        ${account.is_admin && html`<span className="badge">管理员</span>`}
                        <span className="badge">${account.disabled ? "已停用" : "启用中"}</span>
                        <span className="badge">${account.query_count} 条查询</span>
                      </div>
                    </div>

                    <div className="account-meta-row">
                      <div className="sidebar-item-meta">创建时间: ${formatTimestamp(account.created_at)}</div>
                      <div className="sidebar-item-meta">最近查询: ${account.last_query_at ? formatTimestamp(account.last_query_at) : "暂无"}</div>
                    </div>

                    <div className="recent-query-list">
                      ${account.recent_queries?.length
                        ? account.recent_queries.map(
                            (query) => html`
                              <div key=${`${account.username}-${query.session_id}`} className="recent-query-item">
                                <div className="sidebar-footer-name">${query.title}</div>
                                <div className="sidebar-item-meta">${formatTimestamp(query.timestamp)}</div>
                              </div>
                            `
                          )
                        : html`<div className="sidebar-item-meta">暂无查询记录。</div>`}
                    </div>

                    <div className="config-card-actions" style=${{ justifyContent: "flex-end" }}>
                      <button
                        className="secondary-button"
                        onClick=${() => onToggleDisabled(account.username, !account.disabled)}
                        disabled=${isMutating || account.username === currentUsername}
                      >
                        ${account.disabled ? "启用" : "停用"}
                      </button>
                      ${account.username !== currentUsername &&
                      html`
                        <button className="subtle-button danger-button" onClick=${() => onDelete(account.username)} disabled=${isMutating}>
                          删除
                        </button>
                      `}
                    </div>
                  </div>
                `
              )
            : html`<div className="sidebar-item-meta">暂无账户。</div>`}
        </div>
      </div>
    `;
  }

  function ProfileSettings({ meta, draft, setDraft }) {
    function update(key, value) {
      setDraft((current) => ({ ...current, [key]: value }));
    }

    return html`
      <div className="settings-content">
        <div className="form-grid">
          <label className="field">
            <span className="field-label">医生姓名</span>
            <input value=${draft.user_name || ""} onChange=${(event) => update("user_name", event.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">职称</span>
            <input value=${draft.title || ""} onChange=${(event) => update("title", event.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">医院</span>
            <input value=${draft.hospital_name || ""} onChange=${(event) => update("hospital_name", event.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">科室</span>
            <select value=${draft.department || ""} onChange=${(event) => update("department", event.target.value)}>
              ${meta.departments.map((option) => html`<option key=${option} value=${option}>${label(meta, "department", option)}</option>`)}
            </select>
          </label>
          <label className="field">
            <span className="field-label">专业方向</span>
            <input value=${draft.specialty_focus || ""} onChange=${(event) => update("specialty_focus", event.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">地区</span>
            <input value=${draft.locale || ""} onChange=${(event) => update("locale", event.target.value)} />
          </label>
        </div>
        <label className="stack-field">
          <span className="field-label">患者群体</span>
          <textarea value=${draft.patient_population || ""} onChange=${(event) => update("patient_population", event.target.value)}></textarea>
        </label>
      </div>
    `;
  }

  function SettingsEditor({ meta, draft, setDraft, onTestProvider, testingProviderIndex, onTestRoleProvider, testingRoleName }) {
    const [configSection, setConfigSection] = useState("system");

    function updateRoot(key, value) {
      setDraft((current) => ({ ...current, [key]: value }));
    }

    function updateProvider(index, key, value) {
      setDraft((current) => {
        const next = cloneData(current);
        const provider = next.api_providers[index];
        if (key === "provider_name") {
          const oldEndpoint = provider.endpoint;
          provider.provider_name = value;
          next.agent_roles = (next.agent_roles || []).map((role) =>
            role.provider_id && role.provider_id === provider.provider_id
              ? { ...role, provider_name: value }
              : role
          );
          if (!oldEndpoint || Object.values(meta.provider_presets).includes(oldEndpoint)) {
            provider.endpoint = meta.provider_presets[value] || oldEndpoint;
          }
          return next;
        }
        provider[key] = key === "agents_for_api" ? Number(value) : key === "enabled" ? Boolean(value) : value;
        return next;
      });
    }

    function updateRole(index, key, value) {
      setDraft((current) => {
        const next = cloneData(current);
        const role = next.agent_roles[index];
        if (key === "provider_id") {
          const provider = (next.api_providers || []).find((item) => providerValue(item) === value) || null;
          role.provider_id = provider?.provider_id || "";
          role.provider_name = provider?.provider_name || role.provider_name || "DeepSeek";
          return next;
        }
        role[key] = key === "agent_count" ? Number(value) : value;
        return next;
      });
    }

    function addProvider() {
      setDraft((current) => ({
        ...current,
        api_providers: [
          ...current.api_providers,
          {
            provider_id: makeProviderId(),
            provider_name: "OpenAI Compatible",
            model_name: "",
            endpoint: meta.provider_presets["OpenAI Compatible"] || "",
            api_key: "",
            agents_for_api: 1,
            enabled: true,
          },
        ],
      }));
    }

    function addRole() {
      setDraft((current) => ({
        ...current,
        agent_roles: [
          ...current.agent_roles,
          {
            role_name: "Planner",
            role_spec: "",
            provider_id: current.api_providers[0]?.provider_id || "",
            provider_name: current.api_providers[0]?.provider_name || "DeepSeek",
            agent_count: 1,
          },
        ],
      }));
    }

    function addSpecificRole(roleName) {
      setDraft((current) => ({
        ...current,
        agent_roles: [
          ...current.agent_roles,
          {
            role_name: roleName,
            role_spec: "",
            provider_id: current.api_providers[0]?.provider_id || "",
            provider_name: current.api_providers[0]?.provider_name || "DeepSeek",
            agent_count: 1,
          },
        ],
      }));
    }

    function removeProvider(index) {
      setDraft((current) => {
        const next = cloneData(current);
        const [removed] = next.api_providers.splice(index, 1);
        const fallbackProvider = next.api_providers[0] || null;
        next.agent_roles = (next.agent_roles || []).map((role) => {
          if (!removed || role.provider_id !== removed.provider_id) {
            return role;
          }
          return {
            ...role,
            provider_id: fallbackProvider?.provider_id || "",
            provider_name: fallbackProvider?.provider_name || role.provider_name,
          };
        });
        return next;
      });
    }

    function removeRole(index) {
      setDraft((current) => {
        const next = cloneData(current);
        next.agent_roles.splice(index, 1);
        return next;
      });
    }

    const plannerExecutorRoles = ["Planner", "Executor"].map((roleName) => {
      const roleIndex = (draft.agent_roles || []).findIndex((item) => item.role_name === roleName);
      const role = roleIndex >= 0 ? draft.agent_roles[roleIndex] : null;
      const provider = role
        ? (draft.api_providers || []).find((item) =>
            role.provider_id ? item.provider_id === role.provider_id : item.provider_name === role.provider_name
          ) || null
        : null;
      return { roleName, roleIndex, role, provider };
    });

    return html`
      <div className="settings-content">
        <div className="settings-nav">
          <button className=${cx("chip", configSection === "system" && "is-active")} onClick=${() => setConfigSection("system")}>
            总体策略
          </button>
          <button className=${cx("chip", configSection === "plannerExecutor" && "is-active")} onClick=${() => setConfigSection("plannerExecutor")}>
            Planner / Executor
          </button>
          <button className=${cx("chip", configSection === "roles" && "is-active")} onClick=${() => setConfigSection("roles")}>
            Agent Roles
          </button>
          <button className=${cx("chip", configSection === "providers" && "is-active")} onClick=${() => setConfigSection("providers")}>
            API Providers
          </button>
        </div>

        ${configSection === "system" &&
        html`
          <div className="form-grid wide">
            <label className="field">
              <span className="field-label">编排拓扑</span>
              <select value=${draft.orchestration_mode} onChange=${(event) => updateRoot("orchestration_mode", event.target.value)}>
                ${meta.topologies.map((option) => html`<option key=${option} value=${option}>${label(meta, "topology", option)}</option>`)}
              </select>
            </label>
            <label className="field">
              <span className="field-label">默认科室</span>
              <select value=${draft.default_department} onChange=${(event) => updateRoot("default_department", event.target.value)}>
                ${meta.departments.map((option) => html`<option key=${option} value=${option}>${label(meta, "department", option)}</option>`)}
              </select>
            </label>
            <label className="field">
              <span className="field-label">共识阈值</span>
              <input type="number" step="0.01" min="0.4" max="0.99" value=${draft.consensus_threshold} onChange=${(event) => updateRoot("consensus_threshold", Number(event.target.value))} />
            </label>
            <label className="field">
              <span className="field-label">最大轮次</span>
              <input type="number" min="1" max="8" value=${draft.max_rounds} onChange=${(event) => updateRoot("max_rounds", Number(event.target.value))} />
            </label>
            <button className=${cx("toggle-pill", draft.show_diagnostics && "is-on")} onClick=${() => updateRoot("show_diagnostics", !draft.show_diagnostics)} style=${{ alignSelf: "end", marginBottom: "2px" }}>
              <span className="toggle-switch"></span>
              默认显示诊断面板
            </button>
          </div>
        `}

        ${configSection === "plannerExecutor" &&
        html`
          <div className="card-list">
            <div className="config-card">
              <div className="config-card-title">视觉接口要求</div>
              <div className="sidebar-item-meta" style=${{ marginTop: "8px", lineHeight: 1.7 }}>
                Planner 与 Executor 不走任何代理或回退逻辑，都会直接调用这里绑定的真实图像接口。
                请为它们选择支持 <code>image_url</code> 输入的多模态模型，并逐个点击“测试视觉接口”验证。
              </div>
            </div>

            ${plannerExecutorRoles.map(({ roleName, roleIndex, role, provider }) =>
              role
                ? html`
                    <div key=${roleName} className="config-card">
                      <div className="config-card-head">
                        <div className="config-card-title">${roleName}</div>
                        <button
                          className="secondary-button"
                          onClick=${() => onTestRoleProvider(roleName)}
                          disabled=${testingRoleName === roleName}
                        >
                          <${Icon} name=${testingRoleName === roleName ? "reset" : "pulse"} size=${16} className=${testingRoleName === roleName ? "spin-icon" : ""} />
                          测试视觉接口
                        </button>
                      </div>
                      <div className="form-grid wide">
                        <label className="field">
                          <span className="field-label">Provider</span>
                          <select value=${role.provider_id || role.provider_name} onChange=${(event) => updateRole(roleIndex, "provider_id", event.target.value)}>
                            ${draft.api_providers.map((item, providerIndex) => html`
                              <option key=${item.provider_id || `${item.provider_name}-${providerIndex}`} value=${providerValue(item)}>
                                ${providerOptionLabel(item)}
                              </option>
                            `)}
                          </select>
                        </label>
                        <label className="field">
                          <span className="field-label">Model</span>
                          <input value=${provider?.model_name || ""} readOnly=${true} />
                        </label>
                        <label className="field">
                          <span className="field-label">Endpoint</span>
                          <input value=${provider?.endpoint || ""} readOnly=${true} />
                        </label>
                      </div>
                      <label className="stack-field" style=${{ marginTop: "14px" }}>
                        <span className="field-label">角色说明</span>
                        <textarea value=${role.role_spec || ""} onChange=${(event) => updateRole(roleIndex, "role_spec", event.target.value)}></textarea>
                      </label>
                    </div>
                  `
                : html`
                    <div key=${roleName} className="config-card">
                      <div className="config-card-head">
                        <div className="config-card-title">${roleName}</div>
                        <button className="secondary-button" onClick=${() => addSpecificRole(roleName)}>
                          <${Icon} name="plus" size=${16} />
                          添加 ${roleName}
                        </button>
                      </div>
                      <div className="sidebar-item-meta" style=${{ marginTop: "8px" }}>
                        当前尚未配置 ${roleName} 角色。添加后即可在这里绑定真实视觉接口。
                      </div>
                    </div>
                  `
            )}
          </div>
        `}

        ${configSection === "roles" &&
        html`
          <div style=${{ display: "flex", justifyContent: "flex-end" }}>
            <button className="secondary-button" onClick=${addRole}>
              <${Icon} name="plus" size=${16} />
              新增角色
            </button>
          </div>
          <div className="card-list">
            ${draft.agent_roles.map(
              (role, index) => html`
                <div key=${index} className="config-card">
                  <div className="config-card-head">
                    <div className="config-card-title">${label(meta, "role", role.role_name) || role.role_name}</div>
                    <button className="subtle-button danger-button" onClick=${() => removeRole(index)}>移除</button>
                  </div>
                  <div className="form-grid wide">
                    <label className="field">
                      <span className="field-label">Role</span>
                      <select value=${role.role_name} onChange=${(event) => updateRole(index, "role_name", event.target.value)}>
                        ${meta.role_templates.map((option) => html`<option key=${option} value=${option}>${label(meta, "role", option)}</option>`)}
                      </select>
                    </label>
                    <label className="field">
                      <span className="field-label">Provider</span>
                      <select value=${role.provider_id || role.provider_name} onChange=${(event) => updateRole(index, "provider_id", event.target.value)}>
                        ${draft.api_providers.map((provider, providerIndex) => html`
                          <option key=${provider.provider_id || `${provider.provider_name}-${providerIndex}`} value=${providerValue(provider)}>
                            ${providerOptionLabel(provider)}
                          </option>
                        `)}
                      </select>
                    </label>
                    <label className="field">
                      <span className="field-label">Agents</span>
                      <input type="number" min="1" value=${role.agent_count} onChange=${(event) => updateRole(index, "agent_count", event.target.value)} />
                    </label>
                  </div>
                  <label className="stack-field" style=${{ marginTop: "14px" }}>
                    <span className="field-label">角色说明</span>
                    <textarea value=${role.role_spec || ""} onChange=${(event) => updateRole(index, "role_spec", event.target.value)}></textarea>
                  </label>
                </div>
              `
            )}
          </div>
        `}

        ${configSection === "providers" &&
        html`
          <div style=${{ display: "flex", justifyContent: "flex-end" }}>
            <button className="secondary-button" onClick=${addProvider}>
              <${Icon} name="plus" size=${16} />
              新增接口
            </button>
          </div>
          <div className="card-list">
            ${draft.api_providers.map(
              (provider, index) => html`
                <div key=${provider.provider_id || index} className="config-card">
                  <div className="config-card-head">
                    <div className="config-card-title">${providerOptionLabel(provider) || `Provider ${index + 1}`}</div>
                    <div className="config-card-actions">
                      <button
                        className="subtle-icon-button"
                        onClick=${() => onTestProvider(index)}
                        disabled=${testingProviderIndex === index}
                        aria-label="Test provider"
                        title="测试接口"
                      >
                        <${Icon} name=${testingProviderIndex === index ? "reset" : "pulse"} size=${16} className=${testingProviderIndex === index ? "spin-icon" : ""} />
                      </button>
                      <button className="subtle-button danger-button" onClick=${() => removeProvider(index)}>移除</button>
                    </div>
                  </div>
                  <div className="form-grid wide">
                    <label className="field">
                      <span className="field-label">Provider</span>
                      <select value=${provider.provider_name} onChange=${(event) => updateProvider(index, "provider_name", event.target.value)}>
                        ${Object.keys(meta.provider_presets).map((option) => html`<option key=${option} value=${option}>${label(meta, "provider", option)}</option>`)}
                      </select>
                    </label>
                    <label className="field">
                      <span className="field-label">Model</span>
                      <input value=${provider.model_name || ""} onChange=${(event) => updateProvider(index, "model_name", event.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">Agents</span>
                      <input type="number" min="1" value=${provider.agents_for_api} onChange=${(event) => updateProvider(index, "agents_for_api", event.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">Endpoint</span>
                      <input value=${provider.endpoint || ""} onChange=${(event) => updateProvider(index, "endpoint", event.target.value)} />
                    </label>
                    <label className="field">
                      <span className="field-label">API Key</span>
                      <input type="password" value=${provider.api_key || ""} onChange=${(event) => updateProvider(index, "api_key", event.target.value)} />
                    </label>
                    <button className=${cx("toggle-pill", provider.enabled && "is-on")} onClick=${() => updateProvider(index, "enabled", !provider.enabled)} style=${{ alignSelf: "end", marginBottom: "2px" }}>
                      <span className="toggle-switch"></span>
                      已启用
                    </button>
                  </div>
                </div>
              `
            )}
          </div>
        `}
      </div>
    `;
  }

  function SettingsWorkspace({
    meta,
    section,
    profileDraft,
    setProfileDraft,
    settingsDraft,
    setSettingsDraft,
    sessions,
    onOpenSession,
    onClose,
    onSaveProfile,
    onSaveSettings,
    onSwitchSection,
    isSaving,
    onTestProvider,
    testingProviderIndex,
    onTestRoleProvider,
    testingRoleName,
    onToggleSidebarSession,
    onSetAllSidebarSessions,
    visibilityBusyKey,
    historyPreviewSession,
    isHistoryPreviewLoading,
    onCloseHistoryPreview,
    onSubmitApproval,
    onSubmitFeedback,
    adminAccounts,
    accountDraft,
    setAccountDraft,
    onCreateAccount,
    onToggleAccountDisabled,
    onDeleteAccount,
    currentUser,
    isAccountMutating,
  }) {
    const sectionMeta = SETTINGS_SECTION_COPY[section];

    return html`
      <div className="settings-shell">
        <div className="settings-header">
          <div>
            <div className="settings-title">${sectionMeta.title}</div>
            <div className="settings-copy">${sectionMeta.copy}</div>
          </div>
          <button className="secondary-button" onClick=${onClose}>
            <${Icon} name="close" size=${16} />
            关闭设置
          </button>
        </div>

        ${section === "医生档案" &&
        html`
          <${ProfileSettings} meta=${meta} draft=${profileDraft} setDraft=${setProfileDraft} />
          <div style=${{ display: "flex", justifyContent: "flex-end", marginTop: "18px" }}>
            <button className="primary-button" onClick=${onSaveProfile} disabled=${isSaving}>保存账户</button>
          </div>
        `}

        ${section === "系统设置" &&
        html`
          <${SettingsEditor}
            meta=${meta}
            draft=${settingsDraft}
            setDraft=${setSettingsDraft}
            onTestProvider=${onTestProvider}
            testingProviderIndex=${testingProviderIndex}
            onTestRoleProvider=${onTestRoleProvider}
            testingRoleName=${testingRoleName}
          />
          <div style=${{ display: "flex", justifyContent: "flex-end", marginTop: "18px" }}>
            <button className="primary-button" onClick=${onSaveSettings} disabled=${isSaving}>保存设置</button>
          </div>
        `}

        ${section === "历史记录" &&
        html`
          <${HistoryPage}
            meta=${meta}
            sessions=${sessions}
            onOpenSession=${onOpenSession}
            onToggleSidebarSession=${onToggleSidebarSession}
            onSetAllSidebarSessions=${onSetAllSidebarSessions}
            visibilityBusyKey=${visibilityBusyKey}
            selectedSession=${historyPreviewSession}
            isLoadingDetail=${isHistoryPreviewLoading}
            onBack=${onCloseHistoryPreview}
            onSubmitApproval=${onSubmitApproval}
            onSubmitFeedback=${onSubmitFeedback}
          />
        `}

        ${section === "账户管理" &&
        html`
          <${AdminAccountsPage}
            accounts=${adminAccounts}
            draft=${accountDraft}
            setDraft=${setAccountDraft}
            onCreate=${onCreateAccount}
            onToggleDisabled=${onToggleAccountDisabled}
            onDelete=${onDeleteAccount}
            currentUsername=${currentUser?.username}
            isMutating=${isAccountMutating}
          />
        `}
      </div>
    `;
  }

  function App() {
    const [bootstrapping, setBootstrapping] = useState(true);
    const [currentUser, setCurrentUser] = useState(null);
    const [profile, setProfile] = useState(null);
    const [settings, setSettings] = useState(null);
    const [meta, setMeta] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [currentSession, setCurrentSession] = useState(null);
    const [activeView, setActiveView] = useState("workspace");
    const [settingsSection, setSettingsSection] = useState("医生档案");
    const [settingsMenuOpen, setSettingsMenuOpen] = useState(false);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
    const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);
    const [profileDraft, setProfileDraft] = useState(null);
    const [settingsDraft, setSettingsDraft] = useState(null);
    const [composer, setComposer] = useState(makeDefaultComposer());
    const [pendingSubmission, setPendingSubmission] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isLoggingIn, setIsLoggingIn] = useState(false);
    const [isAccountMutating, setIsAccountMutating] = useState(false);
    const [testingProviderIndex, setTestingProviderIndex] = useState(null);
    const [testingRoleName, setTestingRoleName] = useState("");
    const [visibilityBusyKey, setVisibilityBusyKey] = useState(null);
    const [historyPreviewSession, setHistoryPreviewSession] = useState(null);
    const [isHistoryPreviewLoading, setIsHistoryPreviewLoading] = useState(false);
    const [loginDraft, setLoginDraft] = useState({ username: "", password: "" });
    const [adminAccounts, setAdminAccounts] = useState([]);
    const [accountDraft, setAccountDraft] = useState({ username: "", password: "", is_admin: false });
    const [notices, setNotices] = useState([]);

    function pushNotice(message, kind = "success") {
      const id = `${Date.now()}-${Math.random()}`;
      setNotices((current) => [...current, { id, message, kind }]);
      window.setTimeout(() => {
        setNotices((current) => current.filter((item) => item.id !== id));
      }, 2800);
    }

    function resetAppState() {
      setCurrentUser(null);
      setProfile(null);
      setSettings(null);
      setMeta(null);
      setSessions([]);
      setCurrentSession(null);
      setPendingSubmission(null);
      setProfileDraft(null);
      setSettingsDraft(null);
      setAdminAccounts([]);
      setTestingProviderIndex(null);
      setTestingRoleName("");
      setActiveView("workspace");
      setSettingsSection("医生档案");
      setSettingsMenuOpen(false);
      setDiagnosticsOpen(false);
      setHistoryPreviewSession(null);
      setIsHistoryPreviewLoading(false);
      setComposer(makeDefaultComposer());
    }

    function handleAuthError(error) {
      if (error?.status !== 401) {
        return false;
      }
      writeAuthToken("");
      resetAppState();
      setBootstrapping(false);
      return true;
    }

    function applySessionList(nextSessions) {
      setSessions(nextSessions || []);
      setCurrentSession((current) => {
        if (!current) {
          return current;
        }
        const matched = (nextSessions || []).find((session) => session.session_id === current.session_id);
        if (!matched) {
          return current;
        }
        return {
          ...current,
          show_in_sidebar: matched.show_in_sidebar,
        };
      });
    }

    async function bootstrap() {
      const token = readAuthToken();
      if (!token) {
        resetAppState();
        setBootstrapping(false);
        return;
      }
      setBootstrapping(true);
      try {
        const data = await fetchJson("/api/bootstrap");
        setCurrentUser(data.current_user || null);
        setProfile(data.profile);
        setSettings(data.settings);
        setMeta(data.meta);
        applySessionList(data.sessions || []);
        setCurrentSession(data.active_session || null);
        setProfileDraft(cloneData(data.profile));
        setSettingsDraft(cloneData(data.settings));
        setComposer(makeDefaultComposer(data.meta, data.settings));
        setAdminAccounts(data.admin_accounts || []);
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setBootstrapping(false);
      }
    }

    useEffect(() => {
      bootstrap();
    }, []);

    useEffect(() => {
      function handleKeydown(event) {
        if (event.key === "Escape") {
          setDiagnosticsOpen(false);
          setSettingsMenuOpen(false);
        }
      }
      window.addEventListener("keydown", handleKeydown);
      return () => window.removeEventListener("keydown", handleKeydown);
    }, []);

    useEffect(() => {
      if (!pendingSubmission?.job_id || pendingSubmission?.execution?.mode !== "executor") {
        return undefined;
      }
      let disposed = false;
      let timerId = null;
      const jobPath = pendingSubmission?.execution?.mode === "auto" ? "/api/auto-jobs" : "/api/executor-jobs";
      const completionNotice = pendingSubmission?.execution?.mode === "auto" ? "Auto 流程已完成。" : "Executor 已完成执行。";

      async function pollJob() {
        try {
          const data = await fetchJson(`${jobPath}/${pendingSubmission.job_id}`);
          if (disposed) {
            return;
          }
          const job = data.job || {};
          if (job.session) {
            setCurrentSession(job.session);
            applySessionList(job.sessions || []);
            setActiveView("workspace");
          }
          if (job.status === "completed" && job.session) {
            setCurrentSession(job.session);
            applySessionList(job.sessions || []);
            setPendingSubmission(null);
            setActiveView("workspace");
            pushNotice(completionNotice);
            return;
          }
          setPendingSubmission((current) =>
            current && current.job_id === job.job_id
              ? {
                  ...current,
                  ...job,
                }
              : current
          );
          if (job.status === "failed") {
            return;
          }
        } catch (error) {
          if (disposed) {
            return;
          }
          if (!handleAuthError(error)) {
            setPendingSubmission((current) =>
              current && current.job_id === pendingSubmission.job_id
                ? {
                    ...current,
                    status: "failed",
                    stage: "failed",
                    error_message: error.message,
                  }
                : current
            );
          }
          return;
        }
        timerId = window.setTimeout(pollJob, 1200);
      }

      pollJob();
      return () => {
        disposed = true;
        if (timerId) {
          window.clearTimeout(timerId);
        }
      };
    }, [pendingSubmission?.job_id]);

    useEffect(() => {
      if (!pendingSubmission?.job_id || pendingSubmission?.execution?.mode !== "auto") {
        return undefined;
      }
      const jobId = pendingSubmission.job_id;
      const controller = new AbortController();
      let disposed = false;
      let terminalReceived = false;

      function applyAutoJob(job) {
        if (!job || disposed) {
          return;
        }
        if (job.status === "completed" && !job.session) {
          terminalReceived = true;
          fetchJson(`/api/auto-jobs/${jobId}`)
            .then((data) => applyAutoJob(data.job || {}))
            .catch((error) => {
              setPendingSubmission((current) =>
                current && current.job_id === jobId
                  ? {
                      ...current,
                      status: "failed",
                      stage: "failed",
                      error_message: error.message,
                    }
                  : current
              );
            });
          return;
        }
        if (job.status === "completed" && job.session) {
          terminalReceived = true;
          setCurrentSession(job.session);
          applySessionList(job.sessions || []);
          setPendingSubmission(null);
          setActiveView("workspace");
          pushNotice("Auto 流程已完成。");
          return;
        }
        setPendingSubmission((current) =>
          current && current.job_id === job.job_id
            ? {
                ...current,
                ...job,
              }
            : current
        );
        if (job.status === "failed") {
          terminalReceived = true;
        }
      }

      function applyStreamChunk(chunk) {
        const dataLines = chunk
          .split(/\r?\n/)
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trim())
          .filter(Boolean);
        if (!dataLines.length) {
          return;
        }
        const payload = JSON.parse(dataLines.join("\n"));
        applyAutoJob(payload.job || {});
      }

      async function recoverAutoJobAfterStreamError(error) {
        const data = await fetchJson(`/api/auto-jobs/${jobId}`);
        const job = data.job || {};
        applyAutoJob(job);
        if (job.status === "completed" || job.status === "failed") {
          return;
        }
        setPendingSubmission((current) =>
          current && current.job_id === jobId
            ? {
                ...current,
                ...job,
                stream_transport_warning: error.message || "Auto stream interrupted.",
              }
            : current
        );
        window.setTimeout(() => {
          if (!disposed) {
            recoverAutoJobAfterStreamError(error).catch(() => {});
          }
        }, 2000);
      }

      async function streamAutoJob() {
        try {
          const token = readAuthToken();
          const response = await fetch(`/api/auto-jobs/${jobId}/stream`, {
            headers: {
              Accept: "text/event-stream",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            signal: controller.signal,
          });
          if (!response.ok) {
            if (response.status === 401) {
              writeAuthToken("");
            }
            const detail = await response.text();
            throw new Error(detail || `Auto stream failed with status ${response.status}.`);
          }
          if (!response.body) {
            throw new Error("Auto stream response has no readable body.");
          }
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (true) {
            const { value, done } = await reader.read();
            if (done) {
              break;
            }
            buffer += decoder.decode(value, { stream: true });
            const chunks = buffer.split(/\n\n/);
            buffer = chunks.pop() || "";
            chunks.forEach(applyStreamChunk);
          }
          buffer += decoder.decode();
          if (buffer.trim()) {
            applyStreamChunk(buffer);
          }
          if (!terminalReceived && !disposed) {
            await recoverAutoJobAfterStreamError(new Error("Auto stream closed before completion."));
          }
        } catch (error) {
          if (disposed || controller.signal.aborted) {
            return;
          }
          if (!handleAuthError(error)) {
            try {
              await recoverAutoJobAfterStreamError(error);
            } catch (recoverError) {
              setPendingSubmission((current) =>
                current && current.job_id === jobId
                  ? {
                      ...current,
                      status: "failed",
                      stage: "failed",
                      error_message: recoverError.message || error.message,
                    }
                  : current
              );
            }
          }
        }
      }

      streamAutoJob();
      return () => {
        disposed = true;
        controller.abort();
      };
    }, [pendingSubmission?.job_id]);

    async function login() {
      if (!loginDraft.username.trim() || !loginDraft.password) {
        pushNotice("请输入用户名和密码。", "error");
        return;
      }
      setIsLoggingIn(true);
      try {
        const data = await fetchJson("/api/auth/login", {
          method: "POST",
          body: JSON.stringify(loginDraft),
        });
        writeAuthToken(data.token);
        setLoginDraft({ username: loginDraft.username.trim(), password: "" });
        await bootstrap();
        pushNotice("已登录。");
      } catch (error) {
        pushNotice(error.message, "error");
      } finally {
        setIsLoggingIn(false);
      }
    }

    async function logout() {
      try {
        await fetchJson("/api/auth/logout", { method: "POST" });
      } catch (error) {}
      writeAuthToken("");
      resetAppState();
      setBootstrapping(false);
      pushNotice("已退出登录。");
    }

    async function openSession(sessionId) {
      try {
        const data = await fetchJson(`/api/sessions/${sessionId}`);
        await fetchJson("/api/workspace/active", {
          method: "POST",
          body: JSON.stringify({ session_id: sessionId }),
        });
        setCurrentSession(data.session);
        setPendingSubmission(null);
        setActiveView("workspace");
        setDiagnosticsOpen(false);
        setSettingsMenuOpen(false);
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      }
    }

    async function clearActiveWorkspace() {
      await fetchJson("/api/workspace/active", {
        method: "POST",
        body: JSON.stringify({ session_id: "" }),
      });
      setCurrentSession(null);
      setPendingSubmission(null);
      setHistoryPreviewSession(null);
      setIsHistoryPreviewLoading(false);
      setSettingsMenuOpen(false);
      setDiagnosticsOpen(false);
      setActiveView("workspace");
    }

    async function submitApproval(sessionId, turnId, action, note) {
      try {
        const data = await fetchJson(`/api/sessions/${sessionId}/approvals`, {
          method: "POST",
          body: JSON.stringify({
            turn_id: turnId,
            action,
            note,
          }),
        });
        setCurrentSession(data.session);
        setHistoryPreviewSession((current) => (current?.session_id === data.session.session_id ? data.session : current));
        applySessionList(
          sessions.map((item) =>
            item.session_id === data.session.session_id
              ? { ...item, timestamp: data.session.timestamp, title: data.session.title, summary: data.session.summary }
              : item
          )
        );
        pushNotice(action === "approved" ? "已记录通过意见。" : "已记录修改要求。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
        throw error;
      }
    }

    async function submitFeedback(sessionId, payload) {
      try {
        const data = await fetchJson(`/api/sessions/${sessionId}/feedback`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setCurrentSession(data.session);
        setHistoryPreviewSession((current) => (current?.session_id === data.session.session_id ? data.session : current));
        applySessionList(
          sessions.map((item) =>
            item.session_id === data.session.session_id
              ? { ...item, timestamp: data.session.timestamp, title: data.session.title, summary: data.session.summary }
              : item
          )
        );
        pushNotice("病例评分已保存。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
        throw error;
      }
    }

    async function openHistorySession(sessionId) {
      setIsHistoryPreviewLoading(true);
      try {
        const data = await fetchJson(`/api/sessions/${sessionId}`);
        setHistoryPreviewSession(data.session);
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setIsHistoryPreviewLoading(false);
      }
    }

    function closeHistoryPreview() {
      setHistoryPreviewSession(null);
      setIsHistoryPreviewLoading(false);
    }

    function openSettings(section) {
      closeHistoryPreview();
      setSettingsSection(section);
      setActiveView("settings");
      setSettingsMenuOpen(false);
      setDiagnosticsOpen(false);
    }

    function closeSettings() {
      closeHistoryPreview();
      setActiveView("workspace");
    }

    function switchSettingsSection(section) {
      closeHistoryPreview();
      setSettingsSection(section);
    }

    function resetComposer() {
      setComposer((current) => ({
        ...makeDefaultComposer(meta, settings),
        input_expanded: current.input_expanded,
        single_model_test: current.single_model_test,
      }));
      setPendingSubmission(null);
    }

    function hasComposerDraft() {
      const defaultComposer = makeDefaultComposer(meta, settings);
      return Boolean(
        composer.case_summary.trim() ||
          composer.case_blocks.length ||
          composer.chief_complaint.trim() ||
          composer.patient_age.trim() ||
          composer.patient_sex !== defaultComposer.patient_sex ||
          composer.insurance_type !== defaultComposer.insurance_type ||
          composer.department !== defaultComposer.department ||
          composer.output_style !== defaultComposer.output_style ||
          composer.urgency !== defaultComposer.urgency ||
          composer.show_process !== defaultComposer.show_process ||
          composer.image_files.length ||
          composer.doc_files.length
      );
    }

    async function startNewChat() {
      const hasDraft = hasComposerDraft();
      const hasContext = Boolean(currentSession || pendingSubmission);
      const shouldReturnToWorkspace = activeView !== "workspace";
      if (!hasDraft && !hasContext && !shouldReturnToWorkspace) {
        return;
      }
      try {
        await clearActiveWorkspace();
        if (hasDraft || hasContext) {
          resetComposer();
        }
        pushNotice("已开始新的病例工作区。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      }
    }

    async function submitCase() {
      const trimmedInput = composer.case_summary.trim();
      if (trimmedInput === "/clear") {
        setIsSubmitting(true);
        try {
          await clearActiveWorkspace();
          resetComposer();
          pushNotice("已清空当前上下文。");
        } catch (error) {
          if (!handleAuthError(error)) {
            pushNotice(error.message, "error");
          }
        } finally {
          setIsSubmitting(false);
        }
        return;
      }

      if (!trimmedInput) {
        pushNotice("请先输入病例摘要。", "error");
        return;
      }
      setIsSubmitting(true);
      try {
        const autoRequested = isAutoInvocation(composer.case_summary);
        const plannerRequested = isPlannerInvocation(composer.case_summary);
        const executorRequested = isExecutorInvocation(composer.case_summary);
        const deciderRequested = isDeciderInvocation(composer.case_summary);
        const reportRequested = isReportInvocation(composer.case_summary);
        const hasNewAttachments = Boolean(composer.image_files.length || composer.doc_files.length);
        const startsNewCaseContext = (plannerRequested || autoRequested) && hasNewAttachments;
        const imageAssets = plannerRequested || executorRequested || autoRequested ? await serializeImageAssets(composer.image_files) : [];
        const anyAgentRequested = autoRequested || plannerRequested || executorRequested || deciderRequested || reportRequested;
        const execution = autoRequested
          ? { mode: "auto", providerName: "Auto Pipeline", modelName: "Planner -> Executor -> Decider -> Report", roleName: "Auto" }
          : reportRequested
          ? { mode: "report", ...resolveRoleExecution(settings, "Report Generator") }
          : deciderRequested
            ? { mode: "decider", ...resolveRoleExecution(settings, "Decider") }
            : executorRequested
              ? { mode: "executor", ...resolveRoleExecution(settings, "Executor") }
              : plannerRequested
                ? { mode: "planner", ...resolveRoleExecution(settings, "Planner") }
                : composer.single_model_test
                  ? { mode: "single_model", ...resolveSingleModelExecution(settings) }
                  : { mode: "multi_agent", providerName: "", modelName: "", roleName: "" };
        const payload = {
          case_summary: composer.case_summary,
          chief_complaint: composer.chief_complaint,
          patient_age: composer.patient_age,
          patient_sex: composer.patient_sex,
          insurance_type: composer.insurance_type,
          department: composer.department,
          output_style: composer.output_style,
          urgency: composer.urgency,
          show_process: composer.show_process,
          single_model_test: anyAgentRequested ? false : composer.single_model_test,
          uploaded_images: composer.image_files.map((file) => file.name),
          uploaded_docs: composer.doc_files.map((file) => file.name),
          uploaded_image_assets: imageAssets,
          context_session_id: startsNewCaseContext ? "" : currentSession?.session_id || "",
        };
        const pendingTimestamp = new Date().toLocaleString("zh-CN", { hour12: false });
        setActiveView("workspace");
        if (startsNewCaseContext) {
          setCurrentSession(null);
        }
        if (autoRequested) {
          setPendingSubmission({
            timestamp: pendingTimestamp,
            case_summary: composer.case_summary,
            execution,
            status: "queued",
            stage: "queued",
            active_mode: "",
            active_step_id: null,
            failed_stage: "",
            failed_step_id: null,
            step_count: 0,
            completed_modes: [],
            plan_display_steps: [],
            execution_records: [],
            error_message: "",
          });
          const data = await fetchJson("/api/auto-jobs", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          setPendingSubmission((current) =>
            current
              ? {
                  ...current,
                  ...(data.job || {}),
                }
              : null
          );
          setComposer((current) => ({
            ...makeDefaultComposer(meta, settings),
            input_expanded: current.input_expanded,
            single_model_test: current.single_model_test,
          }));
          pushNotice("Auto 流程已启动。");
        } else if (executorRequested) {
          setPendingSubmission({
            timestamp: pendingTimestamp,
            case_summary: composer.case_summary,
            execution,
            status: "queued",
            stage: "queued",
            active_step_id: null,
            failed_step_id: null,
            step_count: currentSession?.result?.plan_display_steps?.length || 0,
            plan_display_steps: currentSession?.result?.plan_display_steps || [],
            execution_records: [],
            error_message: "",
          });
          const data = await fetchJson("/api/executor-jobs", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          setPendingSubmission((current) =>
            current
              ? {
                  ...current,
                  ...(data.job || {}),
                }
              : null
          );
          setComposer((current) => ({
            ...makeDefaultComposer(meta, settings),
            input_expanded: current.input_expanded,
            single_model_test: current.single_model_test,
          }));
          pushNotice("Executor 已开始按计划执行。");
        } else {
          setPendingSubmission({
            timestamp: pendingTimestamp,
            case_summary: composer.case_summary,
            execution,
          });
          const data = await fetchJson("/api/diagnose", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          setCurrentSession(data.session);
          setPendingSubmission(null);
          applySessionList(data.sessions || []);
          setComposer((current) => ({
            ...makeDefaultComposer(meta, settings),
            input_expanded: current.input_expanded,
            single_model_test: current.single_model_test,
          }));
          setActiveView("workspace");
          pushNotice(
            reportRequested
              ? "Report 已生成。"
              : deciderRequested
                ? "Decider 已完成证据融合。"
                : plannerRequested
                  ? "Planner 已生成执行计划。"
                  : "会诊已生成。"
          );
        }
      } catch (error) {
        setPendingSubmission((current) =>
          current
            ? {
                ...current,
                error_message: error.message,
              }
            : {
                timestamp: new Date().toLocaleString("zh-CN", { hour12: false }),
                case_summary: composer.case_summary,
                execution: { mode: "error", providerName: "", modelName: "", roleName: "" },
                error_message: error.message,
              }
        );
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setIsSubmitting(false);
      }
    }

    async function saveProfileDraft() {
      setIsSaving(true);
      try {
        const payload = { ...profileDraft, first_run_complete: true };
        const data = await fetchJson("/api/profile", {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        setProfile(data.profile);
        setProfileDraft(cloneData(data.profile));
        pushNotice("账户已保存。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setIsSaving(false);
      }
    }

    async function saveSettingsDraft() {
      setIsSaving(true);
      try {
        const data = await fetchJson("/api/settings", {
          method: "PUT",
          body: JSON.stringify(settingsDraft),
        });
        setSettings(data.settings);
        setSettingsDraft(cloneData(data.settings));
        setComposer((current) => ({
          ...current,
          department: current.case_summary ? current.department : data.settings.default_department,
          show_process: data.settings.show_diagnostics,
        }));
        pushNotice("设置已保存。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setIsSaving(false);
      }
    }

    async function toggleSingleModelTest(nextValue) {
      setComposer((current) => ({ ...current, single_model_test: nextValue }));
      if (!nextValue) {
        return;
      }

      const { role, provider } = resolveSingleModelProvider(settings);
      if (!role) {
        pushNotice("单模型测试已开启，但尚未配置 Agent Role。", "error");
        return;
      }
      if (!provider) {
        pushNotice(`单模型测试已开启，但未找到“${role.provider_name || role.role_name || "默认"}”接口配置。`, "error");
        return;
      }

      try {
        const data = await fetchJson("/api/providers/test", {
          method: "POST",
          body: JSON.stringify({ provider }),
        });
        pushNotice(data.message || `单模型默认接口 ${providerOptionLabel(provider)} 测试通过。`);
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(`单模型默认接口 ${providerOptionLabel(provider)} 测试失败：${error.message}`, "error");
        }
      }
    }

    async function testProvider(index) {
      const provider = settingsDraft?.api_providers?.[index];
      if (!provider) {
        pushNotice("未找到要测试的接口。", "error");
        return;
      }
      setTestingProviderIndex(index);
      try {
        const data = await fetchJson("/api/providers/test", {
          method: "POST",
          body: JSON.stringify({ provider }),
        });
        pushNotice(data.message || `${providerOptionLabel(provider)} 接口可用。`);
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setTestingProviderIndex(null);
      }
    }

    async function testRoleProvider(roleName) {
      const { role, provider } = resolveRoleProvider(settingsDraft, roleName);
      if (!role) {
        pushNotice(`${roleName} 尚未配置，请先在设置页添加该角色。`, "error");
        return;
      }
      if (!provider) {
        pushNotice(`${roleName} 当前绑定的 Provider 不存在或未启用。`, "error");
        return;
      }
      setTestingRoleName(roleName);
      try {
        const data = await fetchJson("/api/providers/test", {
          method: "POST",
          body: JSON.stringify({ provider, mode: "vision" }),
        });
        pushNotice(data.message || `${roleName} 视觉接口测试通过。`);
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(`${roleName} 视觉接口测试失败：${error.message}`, "error");
        }
      } finally {
        setTestingRoleName("");
      }
    }

    async function setSessionSidebarVisibility(sessionId, showInSidebar) {
      setVisibilityBusyKey(sessionId);
      try {
        const data = await fetchJson("/api/sessions/sidebar-visibility", {
          method: "PUT",
          body: JSON.stringify({
            session_id: sessionId,
            show_in_sidebar: showInSidebar,
          }),
        });
        applySessionList(data.sessions || []);
        pushNotice(showInSidebar ? "已显示在侧栏。" : "已从侧栏隐藏。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setVisibilityBusyKey(null);
      }
    }

    async function setAllSidebarSessions(showInSidebar) {
      setVisibilityBusyKey(showInSidebar ? "all-show" : "all-hide");
      try {
        const data = await fetchJson("/api/sessions/sidebar-visibility", {
          method: "PUT",
          body: JSON.stringify({
            apply_to_all: true,
            show_in_sidebar: showInSidebar,
          }),
        });
        applySessionList(data.sessions || []);
        pushNotice(showInSidebar ? "已将全部记录显示到侧栏。" : "已将全部记录从侧栏隐藏。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setVisibilityBusyKey(null);
      }
    }

    async function createAccount() {
      if (!accountDraft.username.trim() || !accountDraft.password) {
        pushNotice("请填写新账户的用户名和密码。", "error");
        return;
      }
      setIsAccountMutating(true);
      try {
        const data = await fetchJson("/api/admin/accounts", {
          method: "POST",
          body: JSON.stringify(accountDraft),
        });
        setAdminAccounts(data.accounts || []);
        setAccountDraft({ username: "", password: "", is_admin: false });
        pushNotice("账户已创建。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setIsAccountMutating(false);
      }
    }

    async function toggleAccountDisabled(username, disabled) {
      setIsAccountMutating(true);
      try {
        const data = await fetchJson(`/api/admin/accounts/${username}`, {
          method: "PUT",
          body: JSON.stringify({ disabled }),
        });
        setAdminAccounts(data.accounts || []);
        pushNotice(disabled ? "账户已停用。" : "账户已启用。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setIsAccountMutating(false);
      }
    }

    async function deleteAccount(username) {
      if (!window.confirm(`确定删除账户 @${username} 吗？`)) {
        return;
      }
      setIsAccountMutating(true);
      try {
        const data = await fetchJson(`/api/admin/accounts/${username}`, {
          method: "DELETE",
        });
        setAdminAccounts(data.accounts || []);
        pushNotice("账户已删除。");
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setIsAccountMutating(false);
      }
    }

    if (bootstrapping) {
      return html`
        <div className="loading-screen">
          <div className="loading-card">
            <div className="loading-pulse"></div>
            <div className="result-title">RareMDT</div>
            <div className="result-summary">正在加载新的工作区界面与会诊数据。</div>
          </div>
        </div>
      `;
    }

    if (!currentUser) {
      return html`
        <div>
          <${NoticeStack} notices=${notices} />
          <${LoginScreen} draft=${loginDraft} setDraft=${setLoginDraft} onSubmit=${login} isSubmitting=${isLoggingIn} />
        </div>
      `;
    }

    if (!meta || !profile || !settings || !profileDraft || !settingsDraft) {
      return html`
        <div className="loading-screen">
          <div className="loading-card">
            <div className="loading-pulse"></div>
            <div className="result-title">RareMDT</div>
            <div className="result-summary">正在加载新的工作区界面与会诊数据。</div>
          </div>
        </div>
      `;
    }

    return html`
      <div className=${cx("app-shell", sidebarCollapsed && "sidebar-collapsed")}>
        <${NoticeStack} notices=${notices} />

        <${Sidebar}
          meta=${meta}
          profile=${profile}
          currentUser=${currentUser}
          sessions=${sessions}
          currentSessionId=${currentSession?.session_id}
          onOpenSession=${openSession}
          onOpenSettings=${openSettings}
          onLogout=${logout}
          sidebarCollapsed=${sidebarCollapsed}
          onToggleSidebar=${() => {
            setSettingsMenuOpen(false);
            setSidebarCollapsed((current) => !current);
          }}
          showDiagnosticsToggle=${activeView === "workspace"}
          diagnosticsOpen=${diagnosticsOpen}
          onToggleDiagnostics=${() => setDiagnosticsOpen((current) => !current)}
          onNewChat=${startNewChat}
          settingsMenuOpen=${settingsMenuOpen}
          onToggleSettingsMenu=${() => setSettingsMenuOpen((current) => !current)}
        />

        <div className=${cx("workspace-region", activeView === "workspace" && diagnosticsOpen && "diagnostics-open")}>
          <div className="main-stage">
            <main className="shell-main">
              ${activeView === "workspace" && !currentSession && !pendingSubmission && html`<${EmptyWorkspaceWordmark} />`}
              <div className="main-scroll">
                ${activeView === "settings"
                  ? html`
          <${SettingsWorkspace}
            meta=${meta}
            section=${settingsSection}
            profileDraft=${profileDraft}
            setProfileDraft=${setProfileDraft}
                        settingsDraft=${settingsDraft}
                        setSettingsDraft=${setSettingsDraft}
                        sessions=${sessions}
                        onOpenSession=${openHistorySession}
                        onClose=${closeSettings}
                        onSaveProfile=${saveProfileDraft}
                        onSaveSettings=${saveSettingsDraft}
                        onSwitchSection=${switchSettingsSection}
            isSaving=${isSaving}
            onTestProvider=${testProvider}
            testingProviderIndex=${testingProviderIndex}
            onTestRoleProvider=${testRoleProvider}
            testingRoleName=${testingRoleName}
            onToggleSidebarSession=${setSessionSidebarVisibility}
            onSetAllSidebarSessions=${setAllSidebarSessions}
             visibilityBusyKey=${visibilityBusyKey}
             historyPreviewSession=${historyPreviewSession}
                         isHistoryPreviewLoading=${isHistoryPreviewLoading}
                         onCloseHistoryPreview=${closeHistoryPreview}
                         onSubmitApproval=${submitApproval}
                         onSubmitFeedback=${submitFeedback}
                         adminAccounts=${adminAccounts}
                        accountDraft=${accountDraft}
                        setAccountDraft=${setAccountDraft}
                        onCreateAccount=${createAccount}
                        onToggleAccountDisabled=${toggleAccountDisabled}
                        onDeleteAccount=${deleteAccount}
                        currentUser=${currentUser}
                        isAccountMutating=${isAccountMutating}
                      />
                    `
                  : pendingSubmission
                    ? pendingSubmission.execution?.mode === "auto"
                      ? html`
                          <${PendingWorkspace}
                            submission=${pendingSubmission}
                            execution=${pendingSubmission.execution}
                            currentSession=${currentSession}
                            meta=${meta}
                          />
                        `
                      : currentSession
                      ? html`
                          <div className="workspace-feed">
                            <${ResultWorkspace} session=${currentSession} meta=${meta} onSubmitApproval=${submitApproval} onSubmitFeedback=${submitFeedback} />
                            <${PendingWorkspace}
                              submission=${pendingSubmission}
                              execution=${pendingSubmission.execution}
                              currentSession=${currentSession}
                              meta=${meta}
                            />
                          </div>
                        `
                      : html`
                          <${PendingWorkspace}
                            submission=${pendingSubmission}
                            execution=${pendingSubmission.execution}
                            currentSession=${currentSession}
                            meta=${meta}
                          />
                        `
                    : html`<${ResultWorkspace} session=${currentSession} meta=${meta} onSubmitApproval=${submitApproval} onSubmitFeedback=${submitFeedback} />`}
              </div>

              ${activeView === "workspace" &&
              html`
                <${Composer}
                  meta=${meta}
                  settings=${settings}
                  composer=${composer}
                  setComposer=${setComposer}
                  currentSession=${currentSession}
                  onToggleSingleModelTest=${toggleSingleModelTest}
                  onSubmit=${submitCase}
                  onReset=${resetComposer}
                  isSubmitting=${isSubmitting}
                  pushNotice=${pushNotice}
                />
              `}
            </main>

          </div>

          ${activeView === "workspace" &&
          html`<${DiagnosticsDrawer} open=${diagnosticsOpen} session=${currentSession} meta=${meta} onClose=${() => setDiagnosticsOpen(false)} />`}
        </div>
      </div>
    `;
  }

  ReactDOM.createRoot(document.getElementById("app")).render(html`<${App} />`);
})();
