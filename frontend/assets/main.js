(function () {
  const { useEffect, useMemo, useState } = React;
  const html = htm.bind(React.createElement);

  const ICON_PATHS = {
    plus: "M12 5v14M5 12h14",
    paste: "M16 4h-2.2a2.8 2.8 0 0 0-5.6 0H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm-5-1a1.5 1.5 0 0 1 1.5 1.5h-3A1.5 1.5 0 0 1 11 3zm5 17H6V6h1.5v1.5h7V6H16v14z",
    reset: "M3 12a9 9 0 1 0 3-6.708M3 4v5h5",
    arrowUp: "M12 19V5M6 11l6-6 6 6",
    close: "M6 6l12 12M18 6 6 18",
    settings: "M12 8.6A3.4 3.4 0 1 0 12 15.4 3.4 3.4 0 0 0 12 8.6zm8 3.4-1.86-.62a6.77 6.77 0 0 0-.54-1.3l.88-1.74-1.7-1.7-1.75.88a6.78 6.78 0 0 0-1.29-.54L12 4l-2.74.96a6.78 6.78 0 0 0-1.29.54L6.22 4.6l-1.7 1.7.88 1.74c-.22.42-.4.86-.54 1.3L3 12l.96 2.74c.14.44.32.88.54 1.29l-.88 1.75 1.7 1.7 1.75-.88c.41.22.85.4 1.29.54L12 20l2.74-.96c.44-.14.88-.32 1.29-.54l1.75.88 1.7-1.7-.88-1.75c.22-.41.4-.85.54-1.29L20 12z",
    history: "M12 8v5l3 2M12 3a9 9 0 1 0 9 9",
    account: "M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-4 0-7 2-7 4.5V20h14v-1.5C19 16 16 14 12 14z",
    hub: "M12 3v4M5 8l3 2M19 8l-3 2M12 21v-4M5 16l3-2M19 16l-3-2M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    spark: "M12 3l1.8 4.8L18 9.6l-4.2 1.2L12 15.6l-1.8-4.8L6 9.6l4.2-1.8z",
    chevronLeft: "M15 6 9 12l6 6",
  };

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
  };

  async function fetchJson(url, options) {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
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
      throw new Error(payload.detail || "Request failed.");
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
      chief_complaint: "",
      patient_age: "",
      patient_sex: meta?.sex_options?.[0] || "Unknown",
      insurance_type: meta?.insurance_options?.[0] || "Resident insurance",
      department: settings?.default_department || meta?.departments?.[0] || "",
      output_style: meta?.output_styles?.[0] || "Diagnostic",
      urgency: meta?.urgency_options?.[0] || "Routine",
      show_process: settings?.show_diagnostics ?? true,
      input_expanded: false,
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
    sessions,
    currentSessionId,
    onOpenSession,
    onOpenSettings,
    settingsMenuOpen,
    onToggleSettingsMenu,
  }) {
    return html`
      <aside className="shell-sidebar">
        <div className="sidebar-inner">
          <div className="sidebar-brand">
            <div className="brand-mark">R</div>
            <div className="brand-name">RareMDT</div>
            <div className="brand-copy">罕见病多智能体诊疗系统</div>
          </div>

          <div className="sidebar-head">
            <div className="sidebar-title">Sessions</div>
          </div>

          <div className="sidebar-session-list">
            ${sessions.length
              ? sessions.map(
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
                <div className="sidebar-footer-copy">${profile?.title || ""} · ${label(meta, "department", profile?.department)}</div>
              </div>
              <button className=${cx("ghost-icon-button", settingsMenuOpen && "is-active")} onClick=${onToggleSettingsMenu} aria-label="Settings menu">
                <${Icon} name="settings" size=${18} />
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

  function ResultWorkspace({ session, meta }) {
    if (!session) {
      return html`<div className="empty-feed">将病例摘要粘贴到下方输入区，系统会在这里生成临床结论与过程诊断。</div>`;
    }

    if (!session.result || !session.submission) {
      return html`<${SessionSummaryOnly} session=${session} meta=${meta} />`;
    }

    const result = session.result;
    const submission = session.submission;

    return html`
      <div className="workspace-feed">
        <div className="message-card message-user">
          <div className="message-meta">
            <span>病例输入</span>
            <span>·</span>
            <span>${formatTimestamp(session.timestamp)}</span>
          </div>
          <div className="message-body">${submission.case_summary}</div>
        </div>

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
      </div>
    `;
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
      <div className=${cx("drawer-backdrop", open && "is-open")} onClick=${onClose}></div>
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
    onSubmit,
    onReset,
    isSubmitting,
    pushNotice,
  }) {
    const hasInput = composer.case_summary.trim().length > 0;

    async function pasteFromClipboard() {
      try {
        const text = await navigator.clipboard.readText();
        if (!text.trim()) {
          pushNotice("未读取到剪贴板内容。", "error");
          return;
        }
        setComposer((current) => ({
          ...current,
          case_summary: current.case_summary ? `${current.case_summary}\n\n${text}` : text,
        }));
      } catch (error) {
        pushNotice("浏览器未允许剪贴板读取。", "error");
      }
    }

    function updateField(key, value) {
      setComposer((current) => ({ ...current, [key]: value }));
    }

    function handleFiles(key, fileList) {
      updateField(key, Array.from(fileList || []));
    }

    return html`
      <div className="composer-shell">
        <div className="composer-body">
          <div className="composer-textarea-wrap">
            <textarea
              className="composer-textarea"
              placeholder="粘贴或输入完整病例摘要（病史、查体、检验/影像摘要等）…"
              value=${composer.case_summary}
              onChange=${(event) => updateField("case_summary", event.target.value)}
              onKeyDown=${(event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && hasInput && !isSubmitting) {
                  event.preventDefault();
                  onSubmit();
                }
              }}
            ></textarea>
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

          ${composer.attachment_panel_open &&
          html`
            <div className="attachment-panel">
              <div className="panel-title">附件</div>
              <div className="attachment-grid">
                <label className="uploader" key=${`images-${composer.attachment_epoch}`}>
                  <div className="sidebar-footer-name">上传影像</div>
                  <div className="sidebar-footer-copy">PNG / JPG / WEBP</div>
                  <input type="file" accept=".png,.jpg,.jpeg,.webp" multiple onChange=${(event) => handleFiles("image_files", event.target.files)} />
                </label>
                <label className="uploader" key=${`docs-${composer.attachment_epoch}`}>
                  <div className="sidebar-footer-name">上传文档</div>
                  <div className="sidebar-footer-copy">PDF / TXT / DOCX</div>
                  <input type="file" accept=".pdf,.txt,.docx" multiple onChange=${(event) => handleFiles("doc_files", event.target.files)} />
                </label>
              </div>
              ${(composer.image_files.length || composer.doc_files.length) &&
              html`
                <div className="file-chips">
                  ${composer.image_files.map((file) => html`<span key=${`img-${file.name}`} className="file-chip">${file.name}</span>`)}
                  ${composer.doc_files.map((file) => html`<span key=${`doc-${file.name}`} className="file-chip">${file.name}</span>`)}
                </div>
              `}
            </div>
          `}

          <div className="composer-controls">
            <button className="icon-button" onClick=${() => updateField("attachment_panel_open", !composer.attachment_panel_open)} aria-label="Toggle attachments">
              <${Icon} name="plus" size=${18} />
            </button>

            <div className="composer-status">${composer.attachment_panel_open ? "附件面板已展开" : "Command + Enter 提交病例"}</div>

            <button className=${cx("toggle-pill", composer.input_expanded && "is-on")} onClick=${() => updateField("input_expanded", !composer.input_expanded)}>
              <span className="toggle-switch"></span>
              高级模式
            </button>

            <button className="icon-button" onClick=${pasteFromClipboard} aria-label="Paste from clipboard">
              <${Icon} name="paste" size=${18} />
            </button>

            <button className="icon-button" onClick=${onReset} aria-label="Reset composer">
              <${Icon} name="reset" size=${18} />
            </button>

            <button
              className=${cx("send-button", hasInput && "is-ready")}
              disabled=${!hasInput || isSubmitting}
              onClick=${onSubmit}
              aria-label="Submit case"
            >
              <${Icon} name="arrowUp" size=${18} />
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function HistoryPage({ meta, sessions, onOpenSession }) {
    return html`
      <div className="settings-content">
        <div className="history-list">
          ${sessions.length
            ? sessions.map(
                (session) => html`
                  <button key=${session.session_id} className="sidebar-item" onClick=${() => onOpenSession(session.session_id)}>
                    <div className="sidebar-item-row">
                      <div className="sidebar-item-title">${session.title}</div>
                      <span className="badge">${Math.round((session.consensus_score || 0) * 100)}%</span>
                    </div>
                    <div className="sidebar-item-meta">${label(meta, "department", session.department)} · ${label(meta, "output", session.output_style)}</div>
                    <div className="sidebar-item-meta">${session.summary}</div>
                  </button>
                `
              )
            : html`<div className="sidebar-item-meta">暂无历史记录。</div>`}
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

  function SettingsEditor({ meta, draft, setDraft }) {
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

        <div className="config-card">
          <div className="config-card-head">
            <div className="config-card-title">API Providers</div>
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
                    <button className="subtle-button danger-button" onClick=${() => removeProvider(index)}>移除</button>
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
        </div>

        <div className="config-card">
          <div className="config-card-head">
            <div className="config-card-title">Agent Roles</div>
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
        </div>
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
  }) {
    const sectionMeta = SETTINGS_SECTION_COPY[section];

    return html`
      <div className="settings-shell">
        <div className="settings-panel">
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

          <div className="settings-nav">
            ${meta.settings_menu.map(
              (item) => html`
                <button key=${item.section} className=${cx("chip", section === item.section && "is-active")} onClick=${() => onSwitchSection(item.section)}>
                  <${Icon} name=${item.icon} size=${16} />
                  ${item.label}
                </button>
              `
            )}
          </div>
        </div>

        <div className="settings-panel">
          ${section === "医生档案" &&
          html`
            <${ProfileSettings} meta=${meta} draft=${profileDraft} setDraft=${setProfileDraft} />
            <div style=${{ display: "flex", justifyContent: "flex-end", marginTop: "18px" }}>
              <button className="primary-button" onClick=${onSaveProfile} disabled=${isSaving}>保存账户</button>
            </div>
          `}

          ${section === "系统设置" &&
          html`
            <${SettingsEditor} meta=${meta} draft=${settingsDraft} setDraft=${setSettingsDraft} />
            <div style=${{ display: "flex", justifyContent: "flex-end", marginTop: "18px" }}>
              <button className="primary-button" onClick=${onSaveSettings} disabled=${isSaving}>保存设置</button>
            </div>
          `}

          ${section === "历史记录" && html`<${HistoryPage} meta=${meta} sessions=${sessions} onOpenSession=${onOpenSession} />`}
        </div>
      </div>
    `;
  }

  function App() {
    const [bootstrapping, setBootstrapping] = useState(true);
    const [profile, setProfile] = useState(null);
    const [settings, setSettings] = useState(null);
    const [meta, setMeta] = useState(null);
    const [sessions, setSessions] = useState([]);
    const [currentSession, setCurrentSession] = useState(null);
    const [activeView, setActiveView] = useState("workspace");
    const [settingsSection, setSettingsSection] = useState("医生档案");
    const [settingsMenuOpen, setSettingsMenuOpen] = useState(false);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);
    const [profileDraft, setProfileDraft] = useState(null);
    const [settingsDraft, setSettingsDraft] = useState(null);
    const [composer, setComposer] = useState(makeDefaultComposer());
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [notices, setNotices] = useState([]);

    function pushNotice(message, kind = "success") {
      const id = `${Date.now()}-${Math.random()}`;
      setNotices((current) => [...current, { id, message, kind }]);
      window.setTimeout(() => {
        setNotices((current) => current.filter((item) => item.id !== id));
      }, 2800);
    }

    async function bootstrap() {
      setBootstrapping(true);
      try {
        const data = await fetchJson("/api/bootstrap");
        setProfile(data.profile);
        setSettings(data.settings);
        setMeta(data.meta);
        setSessions(data.sessions || []);
        setProfileDraft(cloneData(data.profile));
        setSettingsDraft(cloneData(data.settings));
        setComposer(makeDefaultComposer(data.meta, data.settings));
      } catch (error) {
        pushNotice(error.message, "error");
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

    async function openSession(sessionId) {
      try {
        const data = await fetchJson(`/api/sessions/${sessionId}`);
        setCurrentSession(data.session);
        setActiveView("workspace");
        setDiagnosticsOpen(false);
        setSettingsMenuOpen(false);
      } catch (error) {
        pushNotice(error.message, "error");
      }
    }

    function openSettings(section) {
      setSettingsSection(section);
      setActiveView("settings");
      setSettingsMenuOpen(false);
      setDiagnosticsOpen(false);
    }

    function closeSettings() {
      setActiveView("workspace");
    }

    function resetComposer() {
      setComposer((current) => ({
        ...makeDefaultComposer(meta, settings),
        input_expanded: current.input_expanded,
      }));
    }

    async function submitCase() {
      if (!composer.case_summary.trim()) {
        pushNotice("请先输入病例摘要。", "error");
        return;
      }
      setIsSubmitting(true);
      try {
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
          uploaded_images: composer.image_files.map((file) => file.name),
          uploaded_docs: composer.doc_files.map((file) => file.name),
        };
        const data = await fetchJson("/api/diagnose", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setCurrentSession(data.session);
        setSessions(data.sessions || []);
        setComposer(makeDefaultComposer(meta, settings));
        setActiveView("workspace");
        pushNotice("会诊已生成。");
      } catch (error) {
        pushNotice(error.message, "error");
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
        pushNotice(error.message, "error");
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
        pushNotice(error.message, "error");
      } finally {
        setIsSaving(false);
      }
    }

    const currentTitle = useMemo(() => {
      if (activeView === "settings") {
        return SETTINGS_SECTION_COPY[settingsSection].title;
      }
      return currentSession?.title || "会诊工作区";
    }, [activeView, currentSession, settingsSection]);

    const currentCopy = useMemo(() => {
      if (activeView === "settings") {
        return SETTINGS_SECTION_COPY[settingsSection].copy;
      }
      return currentSession?.summary || "在底部输入病例摘要，系统会生成结构化诊断建议。";
    }, [activeView, currentSession, settingsSection]);

    if (bootstrapping || !meta || !profile || !settings || !profileDraft || !settingsDraft) {
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
          sessions=${sessions}
          currentSessionId=${currentSession?.session_id}
          onOpenSession=${openSession}
          onOpenSettings=${openSettings}
          settingsMenuOpen=${settingsMenuOpen}
          onToggleSettingsMenu=${() => setSettingsMenuOpen((current) => !current)}
        />

        <button className="sidebar-toggle-rail" onClick=${() => setSidebarCollapsed((current) => !current)} aria-label="Toggle sidebar"></button>

        <main className="shell-main">
          <div className="main-topbar">
            <div>
              <div className="topbar-title">${currentTitle}</div>
              <div className="topbar-copy">${currentCopy}</div>
            </div>
            <div className="topbar-actions">
              ${activeView === "workspace" &&
              html`
                <button className=${cx("chip", diagnosticsOpen && "is-active")} onClick=${() => setDiagnosticsOpen(true)}>
                  <${Icon} name="hub" size=${16} />
                  诊断面板
                </button>
              `}
            </div>
          </div>

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
                    onOpenSession=${(sessionId) => {
                      openSession(sessionId);
                      closeSettings();
                    }}
                    onClose=${closeSettings}
                    onSaveProfile=${saveProfileDraft}
                    onSaveSettings=${saveSettingsDraft}
                    onSwitchSection=${setSettingsSection}
                    isSaving=${isSaving}
                  />
                `
              : html`<${ResultWorkspace} session=${currentSession} meta=${meta} />`}
          </div>

          ${activeView === "workspace" &&
          html`
            <${Composer}
              meta=${meta}
              settings=${settings}
              composer=${composer}
              setComposer=${setComposer}
              onSubmit=${submitCase}
              onReset=${resetComposer}
              isSubmitting=${isSubmitting}
              pushNotice=${pushNotice}
            />
          `}

          <${DiagnosticsDrawer} open=${diagnosticsOpen} session=${currentSession} meta=${meta} onClose=${() => setDiagnosticsOpen(false)} />
        </main>
      </div>
    `;
  }

  ReactDOM.createRoot(document.getElementById("app")).render(html`<${App} />`);
})();
