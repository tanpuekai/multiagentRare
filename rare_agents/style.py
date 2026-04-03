from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');

            :root {
                --app-bg: #f4f7fb;
                --app-bg-soft: #eef3f8;
                --surface: #ffffff;
                --surface-soft: #f8fbff;
                --surface-muted: #f1f5f9;
                --border: #d7e0ea;
                --border-strong: #c4d2e0;
                --text: #152338;
                --muted: #5d6d82;
                --accent: #2457d6;
                --accent-soft: rgba(36, 87, 214, 0.08);
                --accent-line: rgba(36, 87, 214, 0.18);
                --success: #0f8c6a;
                --warning: #8a5b00;
                --danger: #b23a3a;
                --shadow-soft: 0 8px 24px rgba(21, 35, 56, 0.06);
                --shadow-panel: 0 14px 40px rgba(21, 35, 56, 0.08);
                --left-open-space: 18.6rem;
                --right-open-space: min(360px, 33vw);
            }

            html, body, [class*="css"] {
                font-family: "IBM Plex Sans", "Noto Sans SC", "PingFang SC", sans-serif;
            }

            body {
                background: var(--app-bg);
                color: var(--text);
            }

            .stApp {
                background:
                    linear-gradient(180deg, var(--app-bg) 0%, #f8fbff 42%, var(--app-bg-soft) 100%);
                color: var(--text);
                font-family: "IBM Plex Sans", "Noto Sans SC", "PingFang SC", sans-serif;
            }

            .stApp [data-testid="stHeader"] {
                background: transparent !important;
                height: 0 !important;
                border: 0 !important;
            }

            .stApp [data-testid="stToolbar"],
            .stApp #MainMenu,
            .stApp footer {
                display: none !important;
            }

            .stApp [data-testid="stAppViewContainer"] > .main {
                padding-top: 0 !important;
            }

            .stApp .block-container {
                max-width: 1320px;
                padding-top: 0.65rem !important;
                padding-bottom: 0.85rem !important;
                margin-left: auto;
                margin-right: auto;
                transition:
                    margin-left 0.2s ease,
                    margin-right 0.2s ease,
                    max-width 0.2s ease;
            }

            body:has(.stApp [data-testid="stSidebar"]:hover) .stApp .block-container {
                margin-left: var(--left-open-space) !important;
            }

            body:has(.diagnostic-hover-rail:hover) .stApp .block-container,
            body:has(.diagnostic-drawer:hover) .stApp .block-container,
            body:has(.diagnostic-drawer.pinned) .stApp .block-container {
                margin-right: var(--right-open-space) !important;
            }

            .stApp [data-testid="stSidebar"] {
                position: fixed !important;
                left: 0;
                top: 0;
                width: 20rem !important;
                height: 100vh !important;
                transform: translateX(calc(-100% + 14px));
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                z-index: 1200;
                overflow: visible !important;
                background: var(--surface) !important;
                border-right: 1px solid var(--border) !important;
                box-shadow: none;
            }

            .stApp [data-testid="stSidebar"]:hover {
                transform: translateX(0);
                box-shadow: 18px 0 40px rgba(21, 35, 56, 0.10);
            }

            .stApp [data-testid="stSidebar"]::after {
                content: "";
                position: absolute;
                top: 0;
                right: 0;
                width: 14px;
                height: 100%;
                background: linear-gradient(180deg, rgba(36, 87, 214, 0.20), rgba(36, 87, 214, 0.06));
                border-left: 1px solid var(--accent-line);
            }

            .stApp [data-testid="stSidebarContent"] {
                position: relative;
                min-height: 100vh;
                background: var(--surface) !important;
                padding-bottom: 5rem;
            }

            h1, h2, h3 {
                color: var(--text);
                letter-spacing: -0.01em;
                font-weight: 700;
            }

            .sidebar-brand {
                margin: 0.8rem 0 1rem 0;
                padding: 1rem 1rem 0.95rem 1rem;
                background: var(--surface-soft);
                border: 1px solid var(--border);
                border-radius: 16px;
                box-shadow: var(--shadow-soft);
            }

            .brand-kicker {
                color: var(--accent);
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                margin-bottom: 0.3rem;
            }

            .brand-title {
                font-size: 1.15rem;
                font-weight: 700;
                color: var(--text);
                line-height: 1.35;
                margin-bottom: 0.2rem;
            }

            .brand-subtitle {
                color: var(--muted);
                font-size: 0.88rem;
            }

            .sidebar-footer {
                position: absolute;
                left: 1rem;
                right: 1.2rem;
                bottom: 1rem;
                padding-top: 0.9rem;
                border-top: 1px solid var(--border);
                color: var(--muted);
                font-size: 0.76rem;
                line-height: 1.5;
            }

            .page-banner {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
                margin: 0 0 0.75rem 0;
                padding: 0.95rem 1.1rem;
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 16px;
                box-shadow: var(--shadow-soft);
            }

            .page-banner-main h1 {
                margin: 0.15rem 0 0.1rem 0;
                font-size: 1.35rem;
                line-height: 1.3;
            }

            .page-banner-main p {
                margin: 0;
                color: var(--muted);
                font-size: 0.92rem;
            }

            .page-banner-kicker {
                color: var(--accent);
                font-size: 0.75rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .page-banner-side {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                flex-wrap: wrap;
                justify-content: flex-end;
            }

            .page-banner-view,
            .page-banner-chip {
                padding: 0.42rem 0.72rem;
                border-radius: 999px;
                font-size: 0.82rem;
                border: 1px solid var(--border);
                background: var(--surface-muted);
                color: var(--muted);
            }

            .page-banner-view {
                color: var(--accent);
                border-color: var(--accent-line);
                background: rgba(36, 87, 214, 0.06);
                font-weight: 700;
            }

            .compact-corner-heading {
                position: fixed;
                top: 0.75rem;
                right: 0.9rem;
                z-index: 1150;
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 0.28rem;
                pointer-events: none;
                transition: right 0.2s ease;
            }

            body:has(.diagnostic-hover-rail:hover) .compact-corner-heading,
            body:has(.diagnostic-drawer:hover) .compact-corner-heading,
            body:has(.diagnostic-drawer.pinned) .compact-corner-heading {
                right: calc(var(--right-open-space) + 0.9rem);
            }

            .compact-corner-title,
            .compact-corner-view {
                background: rgba(255, 255, 255, 0.96);
                border: 1px solid var(--border);
                box-shadow: var(--shadow-soft);
                color: var(--text);
                border-radius: 999px;
                padding: 0.34rem 0.68rem;
            }

            .compact-corner-title {
                font-size: 0.8rem;
                font-weight: 700;
            }

            .compact-corner-view {
                font-size: 0.72rem;
                color: var(--muted);
            }

            .hero-shell {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
                margin-bottom: 0.75rem;
                padding: 1rem 1.05rem;
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 16px;
                box-shadow: var(--shadow-soft);
            }

            .hero-left h1 {
                margin: 0.15rem 0 0.12rem 0;
                font-size: 1.3rem;
                line-height: 1.25;
            }

            .hero-left p,
            .hero-right,
            .footer-note,
            .diag-card,
            .trace-card {
                color: var(--muted);
            }

            .hero-kicker {
                color: var(--accent);
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .hero-right {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                flex-wrap: wrap;
                justify-content: flex-end;
            }

            .hero-badge,
            .hero-chip {
                padding: 0.42rem 0.72rem;
                border-radius: 999px;
                font-size: 0.82rem;
                background: var(--surface-muted);
                border: 1px solid var(--border);
            }

            .hero-badge {
                color: var(--accent);
                border-color: var(--accent-line);
                background: rgba(36, 87, 214, 0.06);
                font-weight: 700;
            }

            .glass-card,
            .diag-card,
            .trace-card,
            .result-hero,
            .stApp [data-testid="stVerticalBlockBorderWrapper"] {
                background: var(--surface);
                border: 1px solid var(--border) !important;
                border-radius: 14px !important;
                box-shadow: var(--shadow-soft);
            }

            .glass-card,
            .diag-card,
            .trace-card,
            .result-hero {
                padding: 1rem;
            }

            .result-placeholder {
                min-height: 150px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            .result-hero {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 0.85rem;
            }

            .result-eyebrow {
                color: var(--accent);
                font-size: 0.76rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
            }

            .result-score {
                min-width: 110px;
                text-align: right;
                color: var(--muted);
            }

            .result-score strong {
                display: block;
                margin-top: 0.12rem;
                color: var(--accent);
                font-size: 1.65rem;
                line-height: 1.1;
            }

            .diag-card,
            .trace-card {
                margin-bottom: 0.7rem;
            }

            .diag-header {
                display: flex;
                justify-content: space-between;
                gap: 0.75rem;
                color: var(--text);
                margin-bottom: 0.35rem;
            }

            .footer-note {
                margin-top: 1rem;
                text-align: center;
                font-size: 0.84rem;
                color: var(--muted);
                padding-bottom: 0.4rem;
            }

            .control-label,
            .action-row-label {
                color: var(--muted);
                font-size: 0.78rem;
                font-weight: 600;
                letter-spacing: 0.01em;
            }

            .control-label {
                min-height: 1.45rem;
                display: flex;
                align-items: flex-end;
                margin-bottom: 0.22rem;
            }

            .action-row-label {
                margin: 0.35rem 0 0.45rem 0;
            }

            [data-testid="stMetric"] {
                background: var(--surface);
                border: 1px solid var(--border);
                padding: 0.75rem;
                border-radius: 12px;
                box-shadow: var(--shadow-soft);
            }

            [data-testid="stMetricLabel"] {
                color: var(--muted);
            }

            [data-testid="stMetricValue"] {
                color: var(--text);
            }

            [data-baseweb="tab-panel"] {
                padding-top: 0.55rem;
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.45rem;
            }

            .stTabs [data-baseweb="tab"] {
                background: var(--surface-muted);
                border: 1px solid var(--border);
                border-radius: 999px;
                color: var(--muted);
                padding: 0.35rem 0.8rem;
            }

            .stTabs [aria-selected="true"] {
                background: rgba(36, 87, 214, 0.08) !important;
                color: var(--accent) !important;
                border-color: var(--accent-line) !important;
            }

            .stApp [data-testid="stWidgetLabel"],
            .stApp [data-testid="stWidgetLabel"] p,
            .stApp .stRadio label,
            .stApp .stToggle label,
            .stApp .stCheckbox label,
            .stApp .stFileUploader label,
            .stCaption {
                color: var(--text) !important;
                font-weight: 600 !important;
            }

            .stApp .stTextInput input,
            .stApp .stTextArea textarea,
            .stApp .stNumberInput input,
            .stApp div[data-baseweb="base-input"] > div,
            .stApp div[data-baseweb="select"] > div,
            .stApp [data-testid="stFileUploaderDropzone"] {
                background: var(--surface) !important;
                color: var(--text) !important;
                border: 1px solid var(--border-strong) !important;
                border-radius: 12px !important;
                box-shadow: none !important;
            }

            .stApp .stTextInput input,
            .stApp .stNumberInput input,
            .stApp div[data-baseweb="select"] > div,
            .stApp .stButton > button,
            .stApp .stFormSubmitButton > button {
                min-height: 44px !important;
            }

            .stApp .stTextInput input,
            .stApp .stNumberInput input {
                height: 44px !important;
            }

            .stApp .stTextInput input::placeholder,
            .stApp .stTextArea textarea::placeholder,
            .stApp .stNumberInput input::placeholder {
                color: #8b98ab !important;
            }

            .stApp div[data-baseweb="select"] *,
            .stApp div[data-baseweb="base-input"] input,
            .stApp [data-testid="stFileUploaderDropzone"] * {
                color: var(--text) !important;
            }

            .stApp div[data-baseweb="select"] svg,
            .stApp .stFileUploader svg {
                fill: #6c7c92 !important;
            }

            .stButton > button,
            .stDownloadButton > button {
                background: var(--surface) !important;
                color: var(--text) !important;
                border: 1px solid var(--border-strong) !important;
                border-radius: 12px !important;
                box-shadow: none !important;
                transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
            }

            .stFormSubmitButton > button {
                background: var(--accent) !important;
                color: #ffffff !important;
                border: 1px solid var(--accent) !important;
                border-radius: 12px !important;
                box-shadow: none !important;
                transition: background 0.15s ease, border-color 0.15s ease;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover {
                background: var(--surface-soft) !important;
                border-color: var(--accent-line) !important;
                color: var(--accent) !important;
            }

            .stFormSubmitButton > button:hover {
                background: #1e4bb8 !important;
                border-color: #1e4bb8 !important;
            }

            .stButton > button:focus,
            .stDownloadButton > button:focus,
            .stFormSubmitButton > button:focus,
            .stApp .stTextInput input:focus,
            .stApp .stTextArea textarea:focus,
            .stApp .stNumberInput input:focus,
            .stApp div[data-baseweb="select"] > div:focus-within {
                border-color: rgba(36, 87, 214, 0.36) !important;
                box-shadow: 0 0 0 3px rgba(36, 87, 214, 0.10) !important;
            }

            .stApp .stRadio [role="radiogroup"] {
                gap: 0.4rem;
            }

            .stApp .stRadio [data-baseweb="radio"] {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 999px;
                padding: 0.24rem 0.58rem;
            }

            .stApp .stRadio [data-baseweb="radio"] label,
            .stApp .stRadio [data-baseweb="radio"] span,
            .stApp .stRadio [data-baseweb="radio"] p {
                color: var(--text) !important;
            }

            .stApp [data-testid="stFileUploaderDropzoneInstructions"],
            .stApp [data-testid="stFileUploaderDropzone"] small,
            .stApp [data-testid="stFileUploaderDropzone"] span {
                color: var(--muted) !important;
            }

            .stApp div[data-baseweb="popover"],
            .stApp div[data-baseweb="menu"],
            .stApp div[data-baseweb="menu"] > div,
            .stApp div[data-baseweb="menu"] ul,
            .stApp div[role="listbox"],
            body div[data-baseweb="popover"],
            body div[data-baseweb="menu"],
            body div[data-baseweb="menu"] > div,
            body div[data-baseweb="menu"] ul,
            body div[role="listbox"] {
                background: var(--surface) !important;
                color: var(--text) !important;
                border: 1px solid var(--border) !important;
                box-shadow: var(--shadow-panel) !important;
            }

            body div[data-baseweb="popover"] *,
            body div[data-baseweb="menu"] *,
            body div[role="listbox"] * {
                color: var(--text) !important;
            }

            body div[data-baseweb="popover"] ul,
            body div[data-baseweb="popover"] li,
            body div[data-baseweb="popover"] li > div,
            body div[data-baseweb="popover"] [role="option"],
            body div[data-baseweb="popover"] [role="option"] > div,
            body div[data-baseweb="menu"] ul,
            body div[data-baseweb="menu"] li,
            body div[data-baseweb="menu"] li > div,
            body div[role="listbox"] li,
            body div[role="listbox"] li > div {
                background: transparent !important;
                color: var(--text) !important;
            }

            [role="option"] {
                color: var(--text) !important;
                background: transparent !important;
                font-weight: 600 !important;
            }

            [role="option"][aria-selected="true"],
            [role="option"]:hover,
            [role="option"][data-highlighted="true"],
            body div[data-baseweb="popover"] li:hover,
            body div[data-baseweb="popover"] li[aria-selected="true"],
            body div[data-baseweb="menu"] li:hover,
            body div[data-baseweb="menu"] li[aria-selected="true"],
            body div[role="listbox"] li:hover,
            body div[role="listbox"] li[aria-selected="true"] {
                background: var(--accent-soft) !important;
            }

            .diagnostic-hover-rail {
                position: fixed;
                top: 0;
                right: 0;
                width: 14px;
                height: 100vh;
                z-index: 1190;
            }

            .diagnostic-drawer {
                position: fixed;
                top: 0;
                right: 0;
                width: var(--right-open-space);
                height: 100vh;
                transform: translateX(calc(100% - 14px));
                transition: transform 0.2s ease;
                z-index: 1195;
                background: var(--surface);
                border-left: 1px solid var(--border);
                box-shadow: -12px 0 36px rgba(21, 35, 56, 0.10);
                overflow: hidden;
            }

            .diagnostic-hover-rail:hover + .diagnostic-drawer,
            .diagnostic-drawer:hover,
            .diagnostic-drawer.pinned {
                transform: translateX(0);
            }

            .diagnostic-drawer-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
                padding: 1rem;
                border-bottom: 1px solid var(--border);
            }

            .diagnostic-drawer-kicker {
                color: var(--accent);
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.05em;
                text-transform: uppercase;
            }

            .diagnostic-drawer-title {
                color: var(--text);
                font-size: 1rem;
                font-weight: 700;
            }

            .diagnostic-drawer-score {
                color: var(--accent);
                font-size: 1.25rem;
                font-weight: 700;
            }

            .diagnostic-drawer-body {
                height: calc(100% - 84px);
                overflow-y: auto;
                padding: 0.9rem 1rem 1rem 1rem;
                background: var(--surface-soft);
            }

            .drawer-block-title {
                color: var(--text);
                font-size: 0.9rem;
                font-weight: 700;
                margin: 0.35rem 0 0.7rem 0;
            }

            .drawer-section-card {
                margin-bottom: 0.7rem;
                padding: 0.8rem 0.85rem;
                border-radius: 12px;
                border: 1px solid var(--border);
                background: var(--surface);
                color: var(--muted);
            }

            .drawer-section-head {
                display: flex;
                justify-content: space-between;
                gap: 0.6rem;
                margin-bottom: 0.35rem;
                color: var(--text);
                font-weight: 600;
            }

            @media (max-width: 1180px) {
                .page-banner {
                    flex-direction: column;
                    align-items: flex-start;
                }

                .page-banner-side {
                    justify-content: flex-start;
                }

                .diagnostic-drawer {
                    width: min(84vw, 340px);
                }
            }

            @media (max-width: 960px) {
                .hero-shell,
                .result-hero {
                    flex-direction: column;
                }

                .stApp .block-container {
                    margin-left: auto !important;
                    margin-right: auto !important;
                }

                .compact-corner-heading {
                    right: 0.6rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
