import React, { useEffect, useMemo, useRef, useState } from "https://esm.sh/react@18.3.1";
import { createRoot } from "https://esm.sh/react-dom@18.3.1/client";
import htm from "https://esm.sh/htm@3.1.1";
import { marked } from "https://esm.sh/marked@12.0.2";
import DOMPurify from "https://esm.sh/dompurify@3.1.6";
import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  useExternalStoreRuntime,
} from "https://esm.sh/@assistant-ui/react@0.12.24?bundle&deps=react@18.3.1,react-dom@18.3.1";

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
      id: "gender",
      label: "性别",
      hint: "患者性别",
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
    {
      id: "taskType",
      label: "任务类型",
      hint: "快速指定输出目标",
      searchText: "诊断意见 治疗规划 康复计划 任务类型",
      children: [
        { id: "diagnosticOpinion", label: "请做出诊断意见", tokenLabel: "任务类型·请做出诊断意见" },
        { id: "treatmentPlan", label: "请做出治疗规划", tokenLabel: "任务类型·请做出治疗规划" },
        { id: "rehabPlan", label: "请做出康复计划", tokenLabel: "任务类型·请做出康复计划" },
      ],
    },
  ];

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

  function getSlashItems(path) {
    let current = SLASH_MENU_TREE;
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

  function buildSlashToken(item, path) {
    const parents = path.map((step) => getSlashItems([]).find((root) => root.id === step)).filter(Boolean);
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
    const slashIndex = textBefore.lastIndexOf("/");
    if (slashIndex < 0) {
      return null;
    }

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
    const wrapRect = wrap ? wrap.getBoundingClientRect() : { left: 0, top: 0 };

    return {
      node,
      slashIndex,
      endOffset: offset,
      query,
      position: {
        left: Math.max(14, rect.left - wrapRect.left),
        bottom: Math.max(24, wrapRect.bottom - rect.top + 8),
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
    const providerIndex = providers.findIndex((item) => item.provider_name === firstRole.provider_name);
    return {
      role: firstRole,
      provider: providerIndex >= 0 ? providers[providerIndex] : null,
      providerIndex,
    };
  }

  function resolveSingleModelExecution(settings) {
    const { role: firstRole, provider } = resolveSingleModelProvider(settings);
    if (!firstRole) {
      return { roleName: "", providerName: "未配置", modelName: "未配置" };
    }
    return {
      roleName: firstRole.role_name || "",
      providerName: provider?.provider_name || firstRole.provider_name || "未配置",
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
    try {
      payload = await response.json();
    } catch (error) {
      payload = {};
    }
    if (!response.ok) {
      if (response.status === 401) {
        writeAuthToken("");
      }
      const error = new Error(payload.detail || "Request failed.");
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function cloneData(value) {
    return JSON.parse(JSON.stringify(value));
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

  function getThreadMessageText(message) {
    return (message?.content || [])
      .filter((part) => part?.type === "text" || part?.type === "reasoning")
      .map((part) => String(part.text || ""))
      .join("\n\n")
      .trim();
  }

  function makeThreadMessage({ id, role, text = "", createdAt = "", metadata = {} }) {
    return {
      id,
      role,
      createdAt: createdAt || undefined,
      content: text ? [{ type: "text", text }] : [],
      metadata: { custom: metadata },
    };
  }

  function buildConversationState(session, pendingSubmission) {
    if (pendingSubmission) {
      const messages = [
        makeThreadMessage({
          id: "pending-user",
          role: "user",
          text: pendingSubmission.case_summary,
          createdAt: pendingSubmission.timestamp,
          metadata: {
            kind: "submission",
            timestamp: pendingSubmission.timestamp,
          },
        }),
      ];

      if (pendingSubmission.execution?.mode === "single_model") {
        messages.push(
          makeThreadMessage({
            id: "pending-execution-status",
            role: "assistant",
            createdAt: pendingSubmission.timestamp,
            metadata: {
              kind: "execution-status",
              pending: true,
              executionMode: "single_model",
              providerName: pendingSubmission.execution.providerName || "未配置",
              modelName: pendingSubmission.execution.modelName || "未配置模型",
            },
          })
        );
      }

      return { messages, isRunning: true };
    }

    if (!session) {
      return { messages: [], isRunning: false };
    }

    if (!session.result || !session.submission) {
      return {
        messages: [
          makeThreadMessage({
            id: `legacy-${session.session_id}`,
            role: "assistant",
            text: session.summary || "该记录来自旧版历史摘要，暂未保存完整诊断面板与多智能体过程数据。",
            createdAt: session.timestamp,
            metadata: {
              kind: "legacy-summary",
              session,
            },
          }),
        ],
        isRunning: false,
      };
    }

    const messages = [
      makeThreadMessage({
        id: `submission-${session.session_id}`,
        role: "user",
        text: session.submission.case_summary,
        createdAt: session.timestamp,
        metadata: {
          kind: "submission",
          timestamp: session.timestamp,
        },
      }),
    ];

    if (session.result.execution_mode === "single_model") {
      messages.push(
        makeThreadMessage({
          id: `status-${session.session_id}`,
          role: "assistant",
          createdAt: session.timestamp,
          metadata: {
            kind: "execution-status",
            pending: false,
            executionMode: "single_model",
            providerName: session.result.serving_provider || "未配置",
            modelName: session.result.serving_model || "未配置模型",
          },
        })
      );
    }

    messages.push(
      makeThreadMessage({
        id: `result-${session.session_id}`,
        role: "assistant",
        text: session.result.professional_answer || "",
        createdAt: session.timestamp,
        metadata: {
          kind: "result",
          timestamp: session.timestamp,
          result: session.result,
        },
      })
    );

    return { messages, isRunning: false };
  }

  function ConversationThreadHeader() {
    return html`
      <div className="assistant-thread-head">
        <div className="assistant-thread-head-title">RareMDT Conversation</div>
        <div className="assistant-thread-head-chip">Assistant-UI Thread</div>
      </div>
    `;
  }

  function ConversationUserMessage({ message }) {
    const custom = message?.metadata?.custom || {};
    const text = getThreadMessageText(message);

    return html`
      <div className="thread-message thread-message-user">
        <div className="thread-row thread-row-user">
          <div className="thread-bubble thread-bubble-user">
            <div className="thread-message-meta">
              <span>病例输入</span>
              <span>·</span>
              <span>${formatTimestamp(custom.timestamp || message.createdAt || "")}</span>
            </div>
            <div className="thread-message-text">${text}</div>
          </div>
          <div className="thread-avatar thread-avatar-user">你</div>
        </div>
      </div>
    `;
  }

  function ConversationExecutionStatus({ custom }) {
    return html`
      <div className="thread-message thread-message-status">
        <div className="thread-row">
          <div className="thread-avatar thread-avatar-assistant">AI</div>
          <div className=${cx("thread-status-pill", custom.pending && "is-pending")}>
            <div className="thread-status-label">单模型测试已启用</div>
            <div className="thread-status-value">${custom.providerName} / ${custom.modelName}</div>
          </div>
        </div>
      </div>
    `;
  }

  function ConversationThinkingMessage() {
    return html`
      <div className="thread-message thread-message-assistant">
        <div className="thread-row">
          <div className="thread-avatar thread-avatar-assistant">AI</div>
          <div className="thread-bubble thread-bubble-assistant thread-bubble-thinking">
            <div className="thread-message-meta">
              <span>RareMDT Assistant</span>
              <span>·</span>
              <span>正在分析</span>
            </div>
            <div className="thread-thinking-row">
              <span className="thread-thinking-dot"></span>
              <span className="thread-thinking-dot"></span>
              <span className="thread-thinking-dot"></span>
              <span className="thread-thinking-copy">系统正在整理临床判断与诊疗建议…</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function ConversationLegacySummary({ session, meta }) {
    return html`
      <div className="thread-message thread-message-assistant">
        <div className="thread-row">
          <div className="thread-avatar thread-avatar-assistant">AI</div>
          <div className="thread-bubble thread-bubble-assistant">
            <div className="thread-message-meta">
              <span>RareMDT Assistant</span>
              <span>·</span>
              <span>${formatTimestamp(session.timestamp)}</span>
            </div>
            <div className="thread-response-shell">
              <div className="thread-response-head">
                <div>
                  <div className="thread-response-title">${session.title}</div>
                  <div className="thread-response-summary">${session.summary}</div>
                </div>
                <div className="badge-row">
                  <span className="badge">${label(meta, "department", session.department)}</span>
                  <span className="badge">${label(meta, "output", session.output_style)}</span>
                </div>
              </div>
              <div className="thread-muted-panel">该记录来自旧版历史摘要，暂未保存完整诊断面板与多智能体过程数据。</div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function ConversationAssistantResult({ result, timestamp, meta }) {
    const bodyHtml = markdownToHtml(result.professional_answer || "");
    const rawModelText = result.raw_model_text || result.professional_answer || "";
    const rawProviderRequest = result.raw_provider_request || "";
    const rawProviderPayload = result.raw_provider_payload || "";
    const showRawSection = Boolean(rawModelText || rawProviderRequest || rawProviderPayload);

    return html`
      <div className="thread-message thread-message-assistant">
        <div className="thread-row">
          <div className="thread-avatar thread-avatar-assistant">AI</div>
          <div className="thread-bubble thread-bubble-assistant">
            <div className="thread-message-meta">
              <span>RareMDT Assistant</span>
              <span>·</span>
              <span>${formatTimestamp(timestamp)}</span>
            </div>

            <div className="thread-response-shell">
              <div className="thread-response-head">
                <div>
                  <div className="thread-response-title">${result.title}</div>
                  <div className="thread-response-summary">${result.executive_summary}</div>
                </div>
                <div className="badge-row">
                  <span className="badge">${label(meta, "department", result.department)}</span>
                  <span className="badge">${label(meta, "output", result.output_style)}</span>
                  <span className="badge">${Math.round(result.consensus_score * 100)}% 一致性</span>
                </div>
              </div>

              <div className="thread-markdown-panel" dangerouslySetInnerHTML=${{ __html: bodyHtml }}></div>

              ${showRawSection &&
              html`
                <details className="thread-details thread-raw-details">
                  <summary>查看原始模型响应（用于核查）</summary>
                  <div className="thread-details-body">
                    ${rawProviderRequest &&
                    html`
                      <div className="thread-raw-label">请求 JSON</div>
                      <pre className="thread-raw-response thread-raw-json">${rawProviderRequest}</pre>
                    `}
                    ${rawProviderPayload &&
                    html`
                      <div className="thread-raw-label">API 原始 JSON</div>
                      <pre className="thread-raw-response thread-raw-json">${rawProviderPayload}</pre>
                    `}
                    <div className="thread-raw-label">模型文本</div>
                    <pre className="thread-raw-response">${rawModelText || "模型未返回可用文本。"}</pre>
                  </div>
                </details>
              `}

              <div className="thread-support-grid">
                <div className="thread-support-card">
                  <div className="thread-support-title">下一步建议</div>
                  <div className="thread-support-list">
                    ${result.next_steps.map(
                      (step, index) => html`
                        <div key=${index} className="thread-support-item">
                          <${Icon} name="spark" size=${15} />
                          <span>${step}</span>
                        </div>
                      `
                    )}
                  </div>
                </div>
                <div className="thread-support-card">
                  <div className="thread-support-title">安全提醒</div>
                  <div className="thread-support-note">${result.safety_note}</div>
                </div>
              </div>

              <details className="thread-details">
                <summary>展开编码、费用与参考依据</summary>
                <div className="thread-details-body">
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
              </details>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function ConversationAssistantMessage({ message, meta }) {
    const custom = message?.metadata?.custom || {};
    const text = getThreadMessageText(message);

    if (custom.kind === "execution-status") {
      return html`<${ConversationExecutionStatus} custom=${custom} />`;
    }

    if (custom.kind === "legacy-summary") {
      return html`<${ConversationLegacySummary} session=${custom.session} meta=${meta} />`;
    }

    if (custom.kind === "result" && custom.result) {
      return html`<${ConversationAssistantResult} result=${custom.result} timestamp=${custom.timestamp} meta=${meta} />`;
    }

    if (!text) {
      return html`<${ConversationThinkingMessage} />`;
    }

    return html`
      <div className="thread-message thread-message-assistant">
        <div className="thread-row">
          <div className="thread-avatar thread-avatar-assistant">AI</div>
          <div className="thread-bubble thread-bubble-assistant">
            <div className="thread-message-meta">
              <span>RareMDT Assistant</span>
            </div>
            <div className="thread-markdown-panel" dangerouslySetInnerHTML=${{ __html: markdownToHtml(text) }}></div>
          </div>
        </div>
      </div>
    `;
  }

  function ConversationThread({ session = null, pendingSubmission = null, meta }) {
    const threadState = useMemo(
      () => buildConversationState(session, pendingSubmission),
      [session, pendingSubmission]
    );

    const runtime = useExternalStoreRuntime({
      messages: threadState.messages,
      isRunning: threadState.isRunning,
      setMessages: () => {},
      convertMessage: (message) => message,
      onNew: async () => {},
    });

    return html`
      <${AssistantRuntimeProvider} runtime=${runtime}>
        <${ThreadPrimitive.Root} className="assistant-thread">
          <div className="assistant-thread-frame">
            <${ConversationThreadHeader} />
            <${ThreadPrimitive.Viewport} className="assistant-thread-viewport">
              <div className="assistant-thread-inner">
                ${threadState.messages.length === 0 && html`<div className="thread-empty-spacer"></div>`}
                <${ThreadPrimitive.Messages}
                  children=${({ message }) =>
                    message?.role === "user"
                      ? html`<${ConversationUserMessage} message=${message} />`
                      : html`<${ConversationAssistantMessage} message=${message} meta=${meta} />`}
                />
              </div>
            </${ThreadPrimitive.Viewport}>
          </div>
        </${ThreadPrimitive.Root}>
      </${AssistantRuntimeProvider}>
    `;
  }

  function PendingWorkspace({ submission, execution, meta }) {
    if (!submission) {
      return null;
    }

    return html`<${ConversationThread} pendingSubmission=${{ ...submission, execution }} meta=${meta} />`;
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

  function ResultWorkspace({ session, meta }) {
    if (!session) {
      return null;
    }

    return html`<${ConversationThread} session=${session} meta=${meta} />`;
  }

  function DataTableCard({ title, columns, rows }) {
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
            ${rows.map(
              (row, index) => html`
                <tr key=${index}>
                  ${columns.map((column) => html`<td key=${column.key}>${row[column.key]}</td>`)}
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
    return html`
      <aside className=${cx("drawer", open && "is-open")}>
        <div className="drawer-head">
          <div>
            <div className="drawer-title">多智能体诊断</div>
            <div className="topbar-copy">查看收敛轮次、角色轨迹与一致性结果。</div>
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
                    提交病例后，这里会显示多智能体轮次、角色分工和一致性分数。
                  </p>
                </div>
              `
            : html`
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
      path: [],
      activeIndex: 0,
      query: "",
      position: { left: 20, bottom: 156 },
    });
    const slashRootItems = useMemo(() => {
      const filtered = filterSlashItems(SLASH_MENU_TREE, slashMenu.path.length ? "" : slashMenu.query);
      return filtered.length || slashMenu.path.length ? filtered : SLASH_MENU_TREE;
    }, [slashMenu.path.length, slashMenu.query]);
    const activeRootId = slashMenu.path[0] || null;
    const activeRootItem = useMemo(() => SLASH_MENU_TREE.find((item) => item.id === activeRootId) || null, [activeRootId]);
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

      const nextPath = pathOverride || slashMenu.path;
      const visibleItems = nextPath.length ? getSlashItems(nextPath) : filterSlashItems(SLASH_MENU_TREE, context.query);
      if (!visibleItems.length) {
        closeSlashMenu();
        return;
      }

      slashContextRef.current = context;
      setSlashMenu((current) => ({
        ...current,
        open: true,
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

      const token = buildSlashToken(item, slashMenu.path);
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
              <div className="slash-menu-stack" style=${{ left: `${slashMenu.position.left}px`, bottom: `${slashMenu.position.bottom}px` }}>
                <div className="slash-menu-popup">
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
                            item.id === "taskType" && "has-divider",
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
                          onClick=${() => setSlashMenu((current) => ({ ...current, path: [item.id], activeIndex: 0, query: "" }))}
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

                ${slashMenu.path.length &&
                slashChildItems.length > 0 &&
                html`
                  <div className="slash-menu-popup slash-submenu-popup">
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
            : html`<${ResultWorkspace} session=${selectedSession} meta=${meta} />`}
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

  function SettingsEditor({ meta, draft, setDraft, onTestProvider, testingProviderIndex }) {
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
        next.agent_roles[index][key] = key === "agent_count" ? Number(value) : value;
        return next;
      });
    }

    function addProvider() {
      setDraft((current) => ({
        ...current,
        api_providers: [
          ...current.api_providers,
          {
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
            provider_name: current.api_providers[0]?.provider_name || "DeepSeek",
            agent_count: 1,
          },
        ],
      }));
    }

    function removeProvider(index) {
      setDraft((current) => {
        const next = cloneData(current);
        next.api_providers.splice(index, 1);
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

    return html`
      <div className="settings-content">
        <div className="settings-nav">
          <button className=${cx("chip", configSection === "system" && "is-active")} onClick=${() => setConfigSection("system")}>
            总体策略
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
                      <select value=${role.provider_name} onChange=${(event) => updateRole(index, "provider_name", event.target.value)}>
                        ${draft.api_providers.map((provider) => html`<option key=${provider.provider_name} value=${provider.provider_name}>${provider.provider_name}</option>`)}
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
                <div key=${index} className="config-card">
                  <div className="config-card-head">
                    <div className="config-card-title">${provider.provider_name || `Provider ${index + 1}`}</div>
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
    onToggleSidebarSession,
    onSetAllSidebarSessions,
    visibilityBusyKey,
    historyPreviewSession,
    isHistoryPreviewLoading,
    onCloseHistoryPreview,
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

    async function submitCase() {
      if (!composer.case_summary.trim()) {
        pushNotice("请先输入病例摘要。", "error");
        return;
      }
      const submittedComposer = {
        ...composer,
        case_blocks: [...(composer.case_blocks || [])],
        image_files: [...(composer.image_files || [])],
        doc_files: [...(composer.doc_files || [])],
      };
      setIsSubmitting(true);
      try {
        const execution = composer.single_model_test
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
          single_model_test: composer.single_model_test,
          uploaded_images: composer.image_files.map((file) => file.name),
          uploaded_docs: composer.doc_files.map((file) => file.name),
        };
        setCurrentSession(null);
        setPendingSubmission({
          timestamp: new Date().toLocaleString("zh-CN", { hour12: false }),
          case_summary: composer.case_summary,
          execution,
        });
        setComposer((current) => ({
          ...makeDefaultComposer(meta, settings),
          input_expanded: current.input_expanded,
          single_model_test: current.single_model_test,
        }));
        setActiveView("workspace");
        const data = await fetchJson("/api/diagnose", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setCurrentSession(data.session);
        setPendingSubmission(null);
        applySessionList(data.sessions || []);
        setActiveView("workspace");
        pushNotice("会诊已生成。");
      } catch (error) {
        setPendingSubmission(null);
        setComposer((current) => ({
          ...submittedComposer,
          input_expanded: current.input_expanded,
          single_model_test: current.single_model_test,
        }));
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
        pushNotice(data.message || `单模型默认接口 ${provider.provider_name || "未命名接口"} 测试通过。`);
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(`单模型默认接口 ${provider.provider_name || "未命名接口"} 测试失败：${error.message}`, "error");
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
        pushNotice(data.message || `${provider.provider_name} 接口可用。`);
      } catch (error) {
        if (!handleAuthError(error)) {
          pushNotice(error.message, "error");
        }
      } finally {
        setTestingProviderIndex(null);
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
                        onToggleSidebarSession=${setSessionSidebarVisibility}
                        onSetAllSidebarSessions=${setAllSidebarSessions}
                        visibilityBusyKey=${visibilityBusyKey}
                        historyPreviewSession=${historyPreviewSession}
                        isHistoryPreviewLoading=${isHistoryPreviewLoading}
                        onCloseHistoryPreview=${closeHistoryPreview}
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
                    ? html`<${PendingWorkspace} submission=${pendingSubmission} execution=${pendingSubmission.execution} meta=${meta} />`
                    : html`<${ResultWorkspace} session=${currentSession} meta=${meta} />`}
              </div>

              ${activeView === "workspace" &&
              html`
                <${Composer}
                  meta=${meta}
                  settings=${settings}
                  composer=${composer}
                  setComposer=${setComposer}
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

createRoot(document.getElementById("app")).render(html`<${App} />`);
