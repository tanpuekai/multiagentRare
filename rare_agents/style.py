from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

            :root {
                --bg-base: #f4f7fb;
                --bg-surface: #ffffff;
                --bg-elevated: #f8fbff;
                --bg-sidebar: #ecf2f8;
                --bg-hover: #eef3fb;
                --bg-muted: #f1f5f9;
                --border-subtle: #dde5ef;
                --border-mid: #cdd8e5;
                --border-strong: #afbdcf;
                --text-primary: #0f172a;
                --text-secondary: #475569;
                --text-tertiary: #64748b;
                --text-inverse: #ffffff;
                --accent: #2f6df6;
                --accent-soft: rgba(47, 109, 246, 0.10);
                --accent-hover: #2459cf;
                --green: #14976b;
                --green-soft: rgba(20, 151, 107, 0.10);
                --red: #cf4b4b;
                --red-soft: rgba(207, 75, 75, 0.10);
                --blue: #2563eb;
                --blue-soft: rgba(37, 99, 235, 0.10);
                --shadow-sm: 0 8px 24px rgba(15, 23, 42, 0.05);
                --shadow-md: 0 18px 40px rgba(15, 23, 42, 0.09);
                --shadow-lg: 0 24px 60px rgba(15, 23, 42, 0.14);
                --radius-sm: 12px;
                --radius-md: 18px;
                --radius-lg: 24px;
                --radius-xl: 28px;
                --sidebar-w: 304px;
                --sidebar-motion: 320ms cubic-bezier(0.22, 1, 0.36, 1);
            }

            html, body, [class*="css"] {
                font-family: "IBM Plex Sans", "Noto Sans SC", -apple-system, BlinkMacSystemFont, sans-serif;
            }

            body,
            .stApp {
                background: radial-gradient(circle at top right, rgba(47,109,246,0.08), transparent 26%), var(--bg-base) !important;
                color: var(--text-primary) !important;
            }

            .stApp [data-testid="stHeader"],
            .stApp [data-testid="stToolbar"],
            .stApp #MainMenu,
            .stApp footer,
            .stApp [data-testid="stStatusWidget"] {
                display: none !important;
            }

            .stApp [data-testid="stAppViewContainer"] {
                padding-top: 0 !important;
                background: transparent !important;
                transition: width var(--sidebar-motion) !important;
                margin-left: 0 !important;
            }

            .stApp .block-container {
                max-width: 1160px !important;
                min-height: 100vh;
                padding: 1.05rem 1.5rem 1.4rem 1.5rem !important;
                margin: 0 auto !important;
                background: transparent !important;
                transition: max-width var(--sidebar-motion), padding var(--sidebar-motion) !important;
            }

            .stApp [data-testid="stSidebar"] {
                width: var(--sidebar-w) !important;
                min-width: var(--sidebar-w) !important;
                max-width: var(--sidebar-w) !important;
                background: linear-gradient(180deg, rgba(255,255,255,0.36), rgba(255,255,255,0.16)), var(--bg-sidebar) !important;
                border-right: 1px solid var(--border-subtle) !important;
                box-shadow: 8px 0 30px rgba(15, 23, 42, 0.04);
                z-index: 120 !important;
                will-change: transform, opacity;
                overflow: hidden !important;
                transition: transform var(--sidebar-motion), opacity 240ms ease, width var(--sidebar-motion), min-width var(--sidebar-motion), max-width var(--sidebar-motion), border-color var(--sidebar-motion), box-shadow var(--sidebar-motion) !important;
            }

            body:not(.sidebar-collapsed) .stApp [data-testid="stSidebar"][aria-expanded="false"] {
                margin-left: 0 !important;
                transform: translateX(0) !important;
                opacity: 1 !important;
                pointer-events: auto !important;
            }

            body:not(.sidebar-collapsed) .stApp [data-testid="stSidebar"][aria-expanded="false"] > div,
            body:not(.sidebar-collapsed) .stApp [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarContent"] {
                width: var(--sidebar-w) !important;
                min-width: var(--sidebar-w) !important;
                max-width: var(--sidebar-w) !important;
            }

            .stApp [data-testid="stSidebarContent"] {
                padding: max(0.35rem, calc(5vh - 2.4rem)) 1rem 1rem !important;
                background: transparent !important;
            }

            .stApp [data-testid="stSidebarCollapseButton"],
            .stApp [data-testid="collapsedControl"] {
                display: none !important;
            }

            .sidebar-brand {
                position: relative;
                overflow: hidden;
                padding: 0.35rem 0.35rem 0.8rem;
                margin: 0 0 0.4rem;
                border-radius: 22px;
                background:
                    radial-gradient(circle at top right, rgba(96, 165, 250, 0.24), transparent 40%),
                    linear-gradient(180deg, rgba(255,255,255,0.78), rgba(255,255,255,0.54));
                border: 1px solid rgba(255,255,255,0.86);
                box-shadow: 0 16px 36px rgba(15, 23, 42, 0.07), inset 0 1px 0 rgba(255,255,255,0.9);
            }

            .sidebar-brand-logo {
                display: flex;
                align-items: flex-start;
                gap: 0.9rem;
            }

            .sidebar-brand-copy {
                display: flex;
                flex-direction: column;
                gap: 0.18rem;
                min-width: 0;
            }

            .sidebar-logo-mark {
                width: 46px;
                height: 46px;
                border-radius: 15px;
                background: linear-gradient(145deg, #1d4ed8, #60a5fa 72%, #93c5fd);
                color: var(--text-inverse);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1rem;
                font-weight: 700;
                letter-spacing: 0.03em;
                box-shadow: 0 16px 30px rgba(37, 99, 235, 0.26);
                flex-shrink: 0;
            }

            .sidebar-logo-text {
                font-size: 1.34rem;
                font-weight: 750;
                line-height: 1.05;
                letter-spacing: -0.03em;
                color: var(--text-primary);
            }

            .sidebar-brand-sub {
                font-size: 0.9rem;
                color: var(--text-secondary);
                line-height: 1.45;
                max-width: 210px;
                font-weight: 500;
            }

            .sidebar-divider {
                height: 1px;
                background: rgba(100, 116, 139, 0.16);
                margin: 1rem 0;
            }

            .sidebar-section-label {
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--text-tertiary);
                margin-bottom: 0.55rem;
                padding-left: 0.15rem;
            }

            .sidebar-status-strip {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.65rem;
                margin-top: 0.85rem;
            }

            .sidebar-status-card {
                background: rgba(255, 255, 255, 0.68);
                border: 1px solid rgba(255, 255, 255, 0.85);
                border-radius: var(--radius-md);
                padding: 0.8rem 0.9rem;
                box-shadow: var(--shadow-sm);
            }

            .sidebar-status-label {
                font-size: 0.72rem;
                color: var(--text-tertiary);
                margin-bottom: 0.2rem;
            }

            .sidebar-status-value {
                font-size: 1.15rem;
                font-weight: 700;
                color: var(--text-primary);
            }

            .sidebar-empty {
                background: rgba(255, 255, 255, 0.66);
                border: 1px dashed var(--border-mid);
                border-radius: var(--radius-md);
                padding: 0.9rem 1rem;
                color: var(--text-secondary);
                font-size: 0.84rem;
                line-height: 1.55;
            }

            .sidebar-profile-card {
                background: rgba(255, 255, 255, 0.74);
                border: 1px solid rgba(255, 255, 255, 0.88);
                border-radius: var(--radius-md);
                padding: 0.95rem 1rem;
                box-shadow: var(--shadow-sm);
            }

            .sidebar-profile-name {
                font-size: 0.9rem;
                font-weight: 700;
                color: var(--text-primary);
                margin-bottom: 0.2rem;
            }

            .sidebar-profile-meta {
                font-size: 0.8rem;
                color: var(--text-secondary);
                line-height: 1.55;
            }

            .sidebar-footer {
                margin-top: 1.1rem;
                padding-top: 1rem;
                border-top: 1px solid rgba(100, 116, 139, 0.16);
                font-size: 0.72rem;
                color: var(--text-tertiary);
                line-height: 1.65;
            }

            body.sidebar-collapsed .stApp [data-testid="stSidebar"] {
                width: 0 !important;
                min-width: 0 !important;
                max-width: 0 !important;
                transform: translateX(calc(-1 * var(--sidebar-w) - 1rem)) !important;
                opacity: 0 !important;
                pointer-events: none !important;
                border-right-color: transparent !important;
                box-shadow: none !important;
            }

            body.sidebar-collapsed .stApp .block-container {
                max-width: 1240px !important;
            }

            .sidebar-toggle-rail {
                position: fixed;
                top: 50%;
                width: 10px;
                height: 62px;
                transform: translateY(-50%);
                border: none;
                border-radius: 999px;
                background: linear-gradient(180deg, rgba(255,255,255,0.72), rgba(241,245,249,0.64));
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
                z-index: 132;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                text-decoration: none !important;
                padding: 0;
                opacity: 0.52;
                transition: left var(--sidebar-motion), background 180ms ease, box-shadow 180ms ease, transform 180ms ease, opacity 180ms ease;
            }

            .sidebar-toggle-rail:hover {
                background: linear-gradient(180deg, rgba(255,255,255,0.88), rgba(236,242,248,0.84));
                box-shadow: 0 10px 22px rgba(15, 23, 42, 0.10);
                opacity: 0.92;
                transform: translateY(-50%) scaleX(1.18);
            }

            .sidebar-toggle-rail:focus-visible {
                outline: none;
                opacity: 1;
                box-shadow: 0 0 0 3px rgba(47, 109, 246, 0.16), 0 10px 22px rgba(15, 23, 42, 0.10);
            }

            .sidebar-toggle-rail {
                left: calc(var(--sidebar-w) - 5px);
            }

            body.sidebar-collapsed .sidebar-toggle-rail {
                left: 4px;
                opacity: 0.42;
            }

            body.sidebar-collapsed .sidebar-toggle-rail:hover {
                opacity: 0.82;
            }

            .sidebar-toggle-rail-core {
                width: 2px;
                height: 18px;
                border-radius: 999px;
                background: linear-gradient(180deg, rgba(100, 116, 139, 0.70), rgba(148, 163, 184, 0.58));
            }

            .topbar-card,
            .page-intro-card,
            .workspace-summary-card,
            .history-highlight-card {
                background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(255,255,255,0.88));
                border: 1px solid rgba(255,255,255,0.92);
                box-shadow: var(--shadow-sm);
            }

            .topbar-card {
                border-radius: var(--radius-lg);
                padding: 1rem 1.15rem;
                margin-bottom: 0.35rem;
            }

            .topbar-kicker,
            .page-intro-kicker,
            .history-highlight-kicker {
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--accent);
                margin-bottom: 0.22rem;
            }

            .topbar-heading,
            .page-intro-title,
            .history-highlight-title {
                font-size: 1.3rem;
                font-weight: 700;
                color: var(--text-primary);
                line-height: 1.2;
            }

            .topbar-subtitle,
            .page-intro-copy,
            .history-highlight-copy {
                font-size: 0.9rem;
                color: var(--text-secondary);
                line-height: 1.6;
                margin-top: 0.4rem;
            }

            .topbar-chip-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin-top: 0.7rem;
            }

            .topbar-chip {
                font-size: 0.76rem;
                color: var(--text-secondary);
                background: var(--bg-muted);
                border: 1px solid var(--border-subtle);
                border-radius: 999px;
                padding: 0.28rem 0.75rem;
            }

            .page-intro-card {
                border-radius: var(--radius-lg);
                padding: 1rem 1.15rem;
                margin-bottom: 1rem;
            }

            .history-highlight-card {
                border-radius: var(--radius-lg);
                padding: 1rem 1.15rem;
                margin-bottom: 1rem;
            }

            .history-highlight-meta {
                font-size: 0.8rem;
                color: var(--text-tertiary);
                margin-top: 0.25rem;
            }

            .workspace-summary-card {
                border-radius: var(--radius-lg);
                padding: 1rem 1.05rem;
                min-height: 132px;
                margin: 0.35rem 0 0.95rem;
            }

            .workspace-summary-label {
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: var(--text-tertiary);
                margin-bottom: 0.38rem;
            }

            .workspace-summary-value {
                font-size: 1.08rem;
                font-weight: 700;
                color: var(--text-primary);
                line-height: 1.35;
            }

            .workspace-summary-copy {
                font-size: 0.82rem;
                color: var(--text-secondary);
                line-height: 1.6;
                margin-top: 0.45rem;
            }

            .msg-card {
                display: flex;
                gap: 0.95rem;
                padding: 1rem 1.1rem;
                margin-bottom: 1rem;
                background: var(--bg-surface);
                border: 1px solid var(--border-subtle);
                border-radius: var(--radius-xl);
                box-shadow: var(--shadow-sm);
            }

            .msg-avatar {
                width: 38px;
                height: 38px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.78rem;
                font-weight: 700;
                flex-shrink: 0;
            }

            .msg-avatar-user {
                background: #e2e8f0;
                color: #334155;
            }

            .msg-avatar-claude {
                background: linear-gradient(135deg, #1d4ed8, #60a5fa);
                color: var(--text-inverse);
            }

            .msg-avatar-system {
                background: var(--bg-muted);
                border: 1px solid var(--border-subtle);
                color: var(--text-secondary);
            }

            .msg-body {
                flex: 1;
                min-width: 0;
            }

            .msg-meta {
                display: flex;
                align-items: center;
                gap: 0.55rem;
                flex-wrap: wrap;
                margin-bottom: 0.45rem;
            }

            .msg-role {
                font-size: 0.84rem;
                font-weight: 700;
                color: var(--text-primary);
            }

            .msg-time {
                font-size: 0.75rem;
                color: var(--text-tertiary);
            }

            .msg-dept-chip {
                font-size: 0.72rem;
                color: var(--blue);
                background: var(--blue-soft);
                border-radius: 999px;
                padding: 0.16rem 0.55rem;
                font-weight: 600;
            }

            .msg-content {
                font-size: 0.92rem;
                color: var(--text-primary);
                line-height: 1.7;
            }

            .msg-content p {
                margin: 0 0 0.7em;
            }

            .msg-content p:last-child {
                margin-bottom: 0;
            }

            .msg-content h1,
            .msg-content h2,
            .msg-content h3 {
                color: var(--text-primary);
                font-weight: 700;
                margin: 1em 0 0.45em;
                line-height: 1.35;
            }

            .msg-content h2 {
                font-size: 1.05rem;
            }

            .msg-content h3 {
                font-size: 0.95rem;
            }

            .msg-content ul,
            .msg-content ol {
                padding-left: 1.3rem;
                margin: 0.4rem 0 0.8rem;
            }

            .msg-content li {
                margin: 0.25rem 0;
            }

            .msg-content code {
                background: var(--bg-muted);
                border: 1px solid var(--border-subtle);
                border-radius: 8px;
                padding: 0.08rem 0.35rem;
                font-size: 0.84em;
            }

            .empty-state {
                background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,255,255,0.90));
                border: 1px solid rgba(255,255,255,0.92);
                border-radius: 30px;
                box-shadow: var(--shadow-md);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 1.9rem 1.8rem 1.7rem;
                margin: 0 0 0.95rem;
                text-align: center;
                min-height: 240px;
            }

            .empty-state-icon {
                width: 60px;
                height: 60px;
                border-radius: 18px;
                background: linear-gradient(135deg, #dbeafe, #eff6ff);
                color: var(--accent);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1rem;
                font-weight: 700;
                margin-bottom: 1rem;
            }

            .empty-state h2 {
                font-size: 1.32rem;
                font-weight: 700;
                color: var(--text-primary);
                margin: 0 0 0.45rem;
            }

            .empty-state p {
                max-width: 560px;
                font-size: 0.92rem;
                color: var(--text-secondary);
                line-height: 1.7;
                margin: 0;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) {
                position: relative;
                overflow: hidden;
                background:
                    radial-gradient(circle at top left, rgba(47, 109, 246, 0.12), transparent 34%),
                    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 255, 0.96)) !important;
                border: 1px solid rgba(223, 232, 243, 0.96) !important;
                border-radius: 30px !important;
                box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.88) !important;
                padding: 0.15rem 0.22rem 0.48rem !important;
                margin: 0 0 1rem !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip)::before {
                content: "";
                position: absolute;
                inset: 0 0 auto 0;
                height: 132px;
                background:
                    radial-gradient(circle at 10% 0%, rgba(147, 197, 253, 0.30), transparent 42%),
                    linear-gradient(180deg, rgba(255,255,255,0.38), rgba(255,255,255,0));
                pointer-events: none;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) > div {
                padding: 0 !important;
                position: relative;
                z-index: 1;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip):focus-within {
                border-color: rgba(47, 109, 246, 0.30);
                box-shadow: var(--shadow-lg), 0 0 0 4px rgba(47, 109, 246, 0.08);
            }

            .composer-head {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 1rem;
                padding: 1.1rem 1.15rem 0.15rem;
            }

            .composer-head-copy {
                min-width: 0;
            }

            .composer-eyebrow {
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--accent);
                margin-bottom: 0.3rem;
            }

            .composer-title {
                font-size: 1.16rem;
                font-weight: 700;
                color: var(--text-primary);
                line-height: 1.2;
            }

            .composer-copy {
                margin-top: 0.35rem;
                font-size: 0.84rem;
                color: var(--text-secondary);
                line-height: 1.6;
                max-width: 620px;
            }

            .composer-head-badge {
                flex-shrink: 0;
                font-size: 0.74rem;
                font-weight: 600;
                color: var(--accent);
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(196, 213, 235, 0.96);
                border-radius: 999px;
                padding: 0.45rem 0.75rem;
                box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
            }

            .stats-strip {
                display: flex;
                align-items: center;
                gap: 0.55rem;
                flex-wrap: wrap;
                padding: 0.55rem 1.15rem 0.7rem;
                border-bottom: 1px solid rgba(214, 224, 238, 0.78);
            }

            .stat-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                font-size: 0.74rem;
                color: var(--text-secondary);
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(214, 224, 238, 0.92);
                border-radius: 999px;
                padding: 0.34rem 0.72rem;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);
            }

            .stat-pill-dot {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: var(--green);
            }

            .stat-pill-dot-warning {
                background: var(--accent);
            }

            .quick-actions {
                display: flex;
                gap: 0.45rem;
                flex-wrap: wrap;
                padding: 0.2rem 0 0.35rem;
            }

            .quick-chip {
                font-size: 0.74rem;
                color: var(--text-secondary);
                background: rgba(242, 246, 251, 0.92);
                border: 1px solid rgba(213, 223, 238, 0.96);
                border-radius: 999px;
                padding: 0.34rem 0.8rem;
                transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease, transform 0.12s ease;
            }

            .quick-chip:hover {
                background: var(--bg-hover);
                border-color: var(--border-strong);
                color: var(--text-primary);
                transform: translateY(-1px);
            }

            .quick-chip-active {
                background: rgba(47, 109, 246, 0.12);
                border-color: rgba(47, 109, 246, 0.20);
                color: var(--accent);
            }

            .composer-section-label {
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--text-tertiary);
                margin: 0.35rem 0 0.45rem;
            }

            .diagnostic-round-card,
            .agent-trace-card {
                background: var(--bg-elevated);
                border: 1px solid var(--border-subtle);
                border-radius: var(--radius-md);
                padding: 0.85rem 0.95rem;
                margin-bottom: 0.7rem;
            }

            .diagnostic-round-head {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.75rem;
                margin-bottom: 0.35rem;
                font-size: 0.86rem;
                font-weight: 700;
                color: var(--text-primary);
            }

            .diagnostic-round-copy,
            .agent-trace-copy {
                font-size: 0.83rem;
                color: var(--text-secondary);
                line-height: 1.65;
            }

            .agent-trace-title {
                font-size: 0.9rem;
                font-weight: 700;
                color: var(--text-primary);
            }

            .agent-trace-meta {
                font-size: 0.76rem;
                color: var(--accent);
                margin: 0.18rem 0 0.4rem;
            }

            .stApp .stTabs [data-baseweb="tab-list"] {
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid var(--border-subtle);
                border-radius: 16px;
                padding: 4px;
                gap: 3px;
            }

            .stApp .stTabs [data-baseweb="tab"] {
                border-radius: 12px !important;
                background: transparent !important;
                color: var(--text-secondary) !important;
                font-size: 0.82rem !important;
                font-weight: 600 !important;
                padding: 0.48rem 0.92rem !important;
            }

            .stApp .stTabs [aria-selected="true"] {
                background: var(--bg-surface) !important;
                color: var(--text-primary) !important;
                box-shadow: var(--shadow-sm);
            }

            .stApp .stTextInput input,
            .stApp .stTextArea textarea,
            .stApp .stNumberInput input,
            .stApp div[data-baseweb="textarea"] textarea {
                background: transparent !important;
                color: var(--text-primary) !important;
                border: none !important;
                box-shadow: none !important;
                font-size: 0.9rem !important;
                line-height: 1.55 !important;
                caret-color: var(--accent);
            }

            .stApp .stTextInput input::placeholder,
            .stApp .stTextArea textarea::placeholder {
                color: var(--text-tertiary) !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) [data-testid="stHorizontalBlock"] > div {
                gap: 0.75rem;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stTextArea [data-baseweb="textarea"] {
                background: rgba(249, 251, 255, 0.96) !important;
                border: 1px solid rgba(213, 223, 238, 0.96) !important;
                border-radius: 24px !important;
                padding: 0.58rem 0.78rem !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.9) !important;
                transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stTextArea [data-baseweb="textarea"]:focus-within {
                background: rgba(255, 255, 255, 0.98) !important;
                border-color: rgba(47, 109, 246, 0.34) !important;
                box-shadow: 0 0 0 4px rgba(47, 109, 246, 0.08), inset 0 1px 0 rgba(255,255,255,0.92) !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stTextArea textarea {
                min-height: 112px !important;
                max-height: 340px !important;
                resize: none !important;
                font-size: 0.95rem !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stTextInput > div > div,
            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stNumberInput > div,
            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) div[data-baseweb="select"] > div {
                background: rgba(249, 251, 255, 0.96) !important;
                border: 1px solid rgba(213, 223, 238, 0.96) !important;
                border-radius: 16px !important;
                min-height: 46px !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.9) !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stTextInput > div > div:focus-within,
            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stNumberInput > div:focus-within {
                border-color: rgba(47, 109, 246, 0.34) !important;
                box-shadow: 0 0 0 3px rgba(47, 109, 246, 0.08), inset 0 1px 0 rgba(255,255,255,0.9) !important;
            }

            .stApp div[data-baseweb="select"] > div {
                background: var(--bg-elevated) !important;
                border: 1px solid var(--border-subtle) !important;
                border-radius: 12px !important;
                min-height: 42px !important;
                padding: 0 0.55rem !important;
                box-shadow: none !important;
            }

            .stApp div[data-baseweb="select"] span,
            .stApp div[data-baseweb="select"] * {
                color: var(--text-primary) !important;
                font-size: 0.84rem !important;
            }

            .stApp div[data-baseweb="select"] svg {
                fill: var(--text-tertiary) !important;
            }

            .stApp .stRadio [role="radiogroup"] {
                gap: 0.35rem;
                flex-wrap: wrap;
            }

            .stApp .stRadio [data-baseweb="radio"] {
                background: var(--bg-elevated) !important;
                border: 1px solid var(--border-subtle) !important;
                border-radius: 999px !important;
                padding: 0.18rem 0.58rem !important;
            }

            .stApp .stRadio [data-baseweb="radio"]:has(input:checked) {
                background: var(--accent-soft) !important;
                border-color: rgba(47, 109, 246, 0.24) !important;
            }

            .stApp .stRadio [data-baseweb="radio"] label,
            .stApp .stRadio [data-baseweb="radio"] span,
            .stApp .stRadio [data-baseweb="radio"] p {
                color: var(--text-secondary) !important;
                font-size: 0.78rem !important;
            }

            .stApp .stRadio [data-baseweb="radio"]:has(input:checked) label,
            .stApp .stRadio [data-baseweb="radio"]:has(input:checked) span {
                color: var(--accent) !important;
            }

            .stApp [data-testid="stCheckbox"] label,
            .stApp [data-testid="stToggle"] label {
                color: var(--text-secondary) !important;
                font-size: 0.82rem !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) [data-testid="stToggle"] {
                background: rgba(255,255,255,0.78);
                border: 1px solid rgba(213, 223, 238, 0.96);
                border-radius: 18px;
                padding: 0.48rem 0.72rem 0.28rem;
                min-height: 54px;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.86);
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) [data-testid="stToggle"] label {
                color: var(--text-primary) !important;
                font-weight: 600 !important;
            }

            .stApp .stButton > button,
            .stApp .stDownloadButton > button,
            .stApp div[data-testid="stPopoverButton"] > button {
                background: rgba(255, 255, 255, 0.88) !important;
                color: var(--text-primary) !important;
                border: 1px solid var(--border-mid) !important;
                border-radius: 14px !important;
                font-size: 0.84rem !important;
                font-weight: 600 !important;
                min-height: 42px !important;
                box-shadow: none !important;
                transition: background 0.12s ease, border-color 0.12s ease, transform 0.12s ease;
            }

            .stApp .stButton > button:hover,
            .stApp .stDownloadButton > button:hover,
            .stApp div[data-testid="stPopoverButton"] > button:hover {
                background: var(--bg-hover) !important;
                border-color: var(--border-strong) !important;
                transform: translateY(-1px);
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stButton > button {
                min-height: 48px !important;
                border-radius: 16px !important;
                background: rgba(255, 255, 255, 0.82) !important;
                border: 1px solid rgba(213, 223, 238, 0.96) !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.86) !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #1d4ed8, #3b82f6) !important;
                border-color: transparent !important;
                color: var(--text-inverse) !important;
                box-shadow: 0 14px 28px rgba(37, 99, 235, 0.22) !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stButton > button[kind="primary"]:hover {
                background: linear-gradient(135deg, #1b47c5, #2f6df6) !important;
                border-color: transparent !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stButton > button[kind="tertiary"] {
                width: 56px !important;
                min-width: 56px !important;
                max-width: 56px !important;
                min-height: 56px !important;
                aspect-ratio: 1 / 1;
                padding: 0 !important;
                border-radius: 18px !important;
                background: rgba(248, 251, 255, 0.98) !important;
                border: 1px solid rgba(196, 213, 235, 0.96) !important;
                box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06), inset 0 1px 0 rgba(255,255,255,0.9) !important;
                color: var(--accent) !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) .stButton > button[kind="tertiary"]:hover {
                background: rgba(255, 255, 255, 1) !important;
                border-color: rgba(47, 109, 246, 0.32) !important;
                box-shadow: 0 14px 24px rgba(15, 23, 42, 0.08), 0 0 0 3px rgba(47, 109, 246, 0.06) !important;
            }

            .stApp [data-testid="stSidebar"] .stButton > button {
                justify-content: flex-start !important;
                text-align: left !important;
                min-height: 40px !important;
                font-size: 0.82rem !important;
                background: rgba(255, 255, 255, 0.68) !important;
            }

            .stApp .stFormSubmitButton > button {
                background: var(--accent) !important;
                color: var(--text-inverse) !important;
                border-color: var(--accent) !important;
            }

            .stApp .stFormSubmitButton > button:hover {
                background: var(--accent-hover) !important;
                border-color: var(--accent-hover) !important;
            }

            .stApp [data-testid="stHorizontalBlock"] > div {
                gap: 0.6rem;
            }

            [data-testid="stMetric"] {
                background: rgba(255, 255, 255, 0.84);
                border: 1px solid var(--border-subtle);
                border-radius: 16px;
                padding: 0.75rem 0.9rem;
            }

            [data-testid="stMetricLabel"] {
                color: var(--text-tertiary) !important;
                font-size: 0.72rem !important;
                font-weight: 700 !important;
                letter-spacing: 0.05em !important;
                text-transform: uppercase !important;
            }

            [data-testid="stMetricValue"] {
                color: var(--text-primary) !important;
                font-size: 1.05rem !important;
                font-weight: 700 !important;
            }

            [data-testid="stMetricDelta"] {
                display: none !important;
            }

            .stApp table,
            .stApp [data-testid="stTable"] table {
                width: 100%;
                border-collapse: collapse;
                border: 1px solid var(--border-subtle) !important;
                border-radius: 16px;
                overflow: hidden;
            }

            .stApp th {
                background: var(--bg-elevated) !important;
                color: var(--text-secondary) !important;
                font-size: 0.74rem !important;
                font-weight: 700 !important;
                padding: 0.58rem 0.72rem !important;
                border-bottom: 1px solid var(--border-subtle) !important;
            }

            .stApp td {
                padding: 0.58rem 0.72rem !important;
                border-bottom: 1px solid var(--border-subtle) !important;
                color: var(--text-primary) !important;
            }

            .stApp tr:last-child td {
                border-bottom: none !important;
            }

            .stApp .stAlert,
            .stApp [data-testid="stAlert"] {
                border-radius: 16px !important;
                border: 1px solid var(--border-mid) !important;
                font-size: 0.84rem !important;
            }

            .stApp .stWarning {
                background: rgba(245, 158, 11, 0.10) !important;
                border-color: rgba(245, 158, 11, 0.18) !important;
            }

            .stApp .stSuccess {
                background: var(--green-soft) !important;
                border-color: rgba(20, 151, 107, 0.18) !important;
            }

            .stApp .stInfo {
                background: var(--blue-soft) !important;
                border-color: rgba(37, 99, 235, 0.16) !important;
            }

            .stApp .stError {
                background: var(--red-soft) !important;
                border-color: rgba(207, 75, 75, 0.18) !important;
            }

            .stApp [data-testid="stFileUploaderDropzone"] {
                background: var(--bg-elevated) !important;
                border: 1px dashed var(--border-mid) !important;
                border-radius: 16px !important;
                color: var(--text-tertiary) !important;
            }

            .stApp [data-testid="stFileUploaderDropzone"]:hover {
                background: var(--bg-hover) !important;
                border-color: var(--accent) !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) [data-testid="stFileUploaderDropzone"] {
                min-height: 92px;
                background: linear-gradient(180deg, rgba(248, 250, 255, 0.98), rgba(241, 245, 251, 0.92)) !important;
                border: 1px dashed rgba(175, 189, 207, 0.96) !important;
                border-radius: 18px !important;
                padding: 0.8rem 0.9rem !important;
                transition: border-color 140ms ease, background 140ms ease, transform 140ms ease, box-shadow 140ms ease !important;
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.stats-strip) [data-testid="stFileUploaderDropzone"]:hover {
                background: linear-gradient(180deg, rgba(255,255,255,0.99), rgba(244,248,255,0.96)) !important;
                border-color: rgba(47, 109, 246, 0.46) !important;
                box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06) !important;
                transform: translateY(-1px);
            }

            .stApp details {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid var(--border-subtle);
                border-radius: 16px;
            }

            .stApp details summary {
                color: var(--text-secondary);
                font-weight: 600;
                font-size: 0.84rem;
                padding: 0.55rem 0.8rem;
            }

            .stApp [data-testid="stProgressBar"] .st-bo {
                background: #d8e2f1 !important;
            }

            .stApp [data-testid="stProgressBar"] .st-bp {
                background: var(--accent) !important;
            }

            .stApp .stCaption,
            .stApp [data-testid="stCaption"] {
                color: var(--text-tertiary) !important;
                font-size: 0.72rem !important;
            }

            hr,
            .stApp hr {
                border: none;
                border-top: 1px solid rgba(100, 116, 139, 0.14);
                margin: 0.85rem 0;
            }

            body div[data-baseweb="popover"],
            body div[data-baseweb="menu"],
            body div[data-baseweb="menu"] > div,
            body div[role="listbox"] {
                background: var(--bg-surface) !important;
                border: 1px solid var(--border-mid) !important;
                border-radius: 16px !important;
                box-shadow: var(--shadow-lg) !important;
            }

            body div[data-baseweb="popover"] li,
            body div[data-baseweb="menu"] li,
            body div[role="listbox"] li {
                color: var(--text-primary) !important;
                font-size: 0.84rem !important;
                border-radius: 10px !important;
                margin: 2px !important;
            }

            body div[data-baseweb="popover"] li:hover,
            body div[data-baseweb="menu"] li:hover,
            body div[role="listbox"] li:hover,
            body [role="option"][data-highlighted="true"] {
                background: var(--bg-hover) !important;
            }

            body [role="option"][aria-selected="true"] {
                background: var(--accent-soft) !important;
                color: var(--accent) !important;
            }

            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }

            ::-webkit-scrollbar-track {
                background: transparent;
            }

            ::-webkit-scrollbar-thumb {
                background: rgba(100, 116, 139, 0.28);
                border-radius: 999px;
            }

            ::-webkit-scrollbar-thumb:hover {
                background: rgba(100, 116, 139, 0.42);
            }

            @media (max-width: 1180px) {
                :root {
                    --sidebar-w: 272px;
                }
            }

            @media (max-width: 720px) {
                :root {
                    --sidebar-w: 0px;
                }

                .stApp [data-testid="stSidebar"] {
                    display: none !important;
                }

                .sidebar-toggle-rail {
                    display: none !important;
                }

                .stApp .block-container {
                    padding: 1rem 1rem 1rem 1rem !important;
                }

                .stApp [data-testid="stAppViewContainer"] {
                    margin-left: 0 !important;
                }

                .workspace-summary-card {
                    min-height: auto;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
