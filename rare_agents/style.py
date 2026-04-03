from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

            :root {
                --bg: #07111f;
                --panel: rgba(8, 20, 37, 0.78);
                --panel-soft: rgba(20, 38, 64, 0.68);
                --stroke: rgba(130, 179, 255, 0.22);
                --text: #f4f7fb;
                --muted: #abc0db;
                --aqua: #53f5d8;
                --gold: #ffc857;
                --blue: #7ab6ff;
                --danger: #ff8e72;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(83, 245, 216, 0.18), transparent 26%),
                    radial-gradient(circle at top right, rgba(122, 182, 255, 0.20), transparent 30%),
                    linear-gradient(180deg, #07111f 0%, #0b1527 50%, #09131f 100%);
                color: var(--text);
                font-family: "Manrope", sans-serif;
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
                padding-top: 1rem !important;
                padding-bottom: 2rem !important;
                max-width: 1480px;
            }

            .stApp [data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(4, 12, 24, 0.94), rgba(8, 18, 30, 0.92));
                border-right: 1px solid rgba(130, 179, 255, 0.16);
            }

            h1, h2, h3, .brand-title {
                font-family: "Space Grotesk", sans-serif;
                letter-spacing: -0.02em;
            }

            .sidebar-brand {
                padding: 1rem;
                margin-bottom: 1rem;
                border-radius: 22px;
                background: linear-gradient(160deg, rgba(16, 33, 59, 0.96), rgba(8, 18, 30, 0.88));
                border: 1px solid rgba(130, 179, 255, 0.2);
                box-shadow: 0 22px 50px rgba(0, 0, 0, 0.25);
            }

            .brand-kicker {
                color: var(--aqua);
                font-size: 0.82rem;
                text-transform: uppercase;
                letter-spacing: 0.16em;
                margin-bottom: 0.35rem;
            }

            .brand-title {
                font-size: 1.5rem;
                font-weight: 800;
                color: var(--text);
                margin-bottom: 0.2rem;
            }

            .brand-subtitle {
                color: var(--muted);
                font-size: 0.92rem;
            }

            .page-banner {
                display: flex;
                gap: 1rem;
                justify-content: space-between;
                align-items: stretch;
                margin: 0.2rem 0 1rem 0;
                padding: 1.2rem 1.35rem;
                border-radius: 24px;
                background:
                    linear-gradient(135deg, rgba(18, 34, 60, 0.96), rgba(7, 16, 29, 0.92)),
                    radial-gradient(circle at top right, rgba(255, 200, 87, 0.16), transparent 26%);
                border: 1px solid rgba(130, 179, 255, 0.2);
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.24);
            }

            .page-banner-main h1 {
                margin: 0.28rem 0 0.35rem 0;
                font-size: 2.25rem;
                color: white;
            }

            .page-banner-main p {
                margin: 0;
                color: var(--muted);
                font-size: 1rem;
            }

            .page-banner-kicker {
                color: var(--gold);
                text-transform: uppercase;
                letter-spacing: 0.16em;
                font-size: 0.78rem;
            }

            .page-banner-side {
                min-width: 240px;
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                justify-content: center;
                gap: 0.55rem;
            }

            .page-banner-view,
            .page-banner-chip {
                border-radius: 999px;
                padding: 0.55rem 0.9rem;
                font-size: 0.9rem;
            }

            .page-banner-view {
                background: rgba(83, 245, 216, 0.14);
                border: 1px solid rgba(83, 245, 216, 0.22);
                color: var(--aqua);
                font-weight: 700;
            }

            .page-banner-chip {
                background: rgba(122, 182, 255, 0.09);
                border: 1px solid rgba(122, 182, 255, 0.18);
                color: var(--muted);
            }

            .hero-shell {
                display: flex;
                gap: 1.2rem;
                justify-content: space-between;
                align-items: stretch;
                padding: 1.4rem;
                margin-bottom: 1rem;
                border-radius: 28px;
                background:
                    linear-gradient(135deg, rgba(17, 36, 64, 0.92), rgba(8, 17, 29, 0.88)),
                    radial-gradient(circle at bottom right, rgba(255, 200, 87, 0.18), transparent 24%);
                border: 1px solid rgba(130, 179, 255, 0.22);
                box-shadow: 0 25px 60px rgba(0, 0, 0, 0.24);
            }

            .hero-compact {
                padding: 1rem 1.2rem;
                border-radius: 22px;
                margin-bottom: 0.8rem;
            }

            .hero-left h1 {
                margin: 0.2rem 0 0.4rem 0;
                font-size: 3rem;
                color: white;
            }

            .hero-compact .hero-left h1 {
                font-size: 1.65rem;
            }

            .hero-compact .hero-right {
                min-width: 220px;
            }

            .hero-left p, .hero-right, .footer-note, .diag-card, .trace-card {
                color: var(--muted);
            }

            .hero-kicker {
                color: var(--gold);
                text-transform: uppercase;
                letter-spacing: 0.16em;
                font-size: 0.8rem;
            }

            .hero-right {
                min-width: 270px;
                display: flex;
                flex-direction: column;
                gap: 0.55rem;
                justify-content: center;
            }

            .hero-badge {
                background: rgba(83, 245, 216, 0.14);
                border: 1px solid rgba(83, 245, 216, 0.24);
                color: var(--aqua);
                border-radius: 999px;
                padding: 0.55rem 0.85rem;
                width: fit-content;
                font-weight: 700;
            }

            .hero-chip {
                background: rgba(122, 182, 255, 0.08);
                border: 1px solid rgba(122, 182, 255, 0.18);
                border-radius: 16px;
                padding: 0.7rem 0.85rem;
            }

            .glass-card, .diag-card, .trace-card, .result-hero {
                background: linear-gradient(180deg, rgba(10, 21, 38, 0.88), rgba(8, 16, 28, 0.8));
                border: 1px solid rgba(130, 179, 255, 0.18);
                border-radius: 20px;
                padding: 1rem;
                box-shadow: 0 18px 40px rgba(0, 0, 0, 0.18);
            }

            .stApp [data-testid="stVerticalBlockBorderWrapper"] {
                background: linear-gradient(180deg, rgba(10, 21, 38, 0.9), rgba(8, 16, 28, 0.82));
                border: 1px solid rgba(130, 179, 255, 0.18) !important;
                border-radius: 20px !important;
                box-shadow: 0 18px 40px rgba(0, 0, 0, 0.18);
            }

            .result-placeholder {
                min-height: 240px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            .result-hero {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 1rem;
            }

            .result-eyebrow {
                color: var(--gold);
                text-transform: uppercase;
                letter-spacing: 0.12em;
                font-size: 0.78rem;
            }

            .result-score {
                min-width: 130px;
                text-align: right;
                display: flex;
                flex-direction: column;
                justify-content: center;
                color: var(--muted);
            }

            .result-score strong {
                font-size: 2rem;
                color: var(--aqua);
            }

            .diag-card, .trace-card {
                margin-bottom: 0.75rem;
            }

            .diag-header {
                display: flex;
                justify-content: space-between;
                color: var(--text);
                margin-bottom: 0.35rem;
            }

            .footer-note {
                margin-top: 2rem;
                text-align: center;
                font-size: 0.9rem;
                padding-bottom: 1rem;
            }

            .control-label,
            .action-row-label {
                color: var(--muted);
                font-size: 0.8rem;
                font-weight: 600;
                letter-spacing: 0.03em;
            }

            .control-label {
                min-height: 1.55rem;
                display: flex;
                align-items: flex-end;
                margin-bottom: 0.25rem;
            }

            .action-row-label {
                margin: 0.45rem 0 0.5rem 0;
            }

            [data-testid="stMetric"] {
                background: rgba(10, 21, 38, 0.78);
                border: 1px solid rgba(130, 179, 255, 0.16);
                padding: 0.8rem;
                border-radius: 18px;
            }

            [data-testid="stMetricLabel"] {
                color: var(--muted);
            }

            [data-testid="stMetricValue"] {
                color: var(--text);
            }

            [data-baseweb="tab-panel"] {
                padding-top: 0.5rem;
            }

            .stApp [data-testid="stWidgetLabel"],
            .stApp [data-testid="stWidgetLabel"] p,
            .stApp .stRadio label,
            .stApp .stToggle label,
            .stApp .stCheckbox label,
            .stApp .stFileUploader label {
                color: var(--text) !important;
                font-weight: 600 !important;
            }

            .stApp .stTextInput input,
            .stApp .stTextArea textarea,
            .stApp .stNumberInput input,
            .stApp div[data-baseweb="base-input"] > div,
            .stApp div[data-baseweb="select"] > div,
            .stApp [data-testid="stFileUploaderDropzone"] {
                background: linear-gradient(180deg, rgba(13, 27, 47, 0.96), rgba(8, 18, 30, 0.92)) !important;
                color: var(--text) !important;
                border: 1px solid rgba(122, 182, 255, 0.28) !important;
                box-shadow: inset 0 0 0 1px rgba(122, 182, 255, 0.05);
            }

            .stApp .stTextInput input,
            .stApp .stTextArea textarea,
            .stApp .stNumberInput input,
            .stApp div[data-baseweb="select"] > div {
                border-radius: 14px !important;
            }

            .stApp .stTextInput input,
            .stApp .stNumberInput input,
            .stApp div[data-baseweb="select"] > div,
            .stApp .stButton > button,
            .stApp .stFormSubmitButton > button {
                min-height: 48px !important;
            }

            .stApp .stTextInput input,
            .stApp .stNumberInput input {
                height: 48px !important;
            }

            .stApp .stTextInput input::placeholder,
            .stApp .stTextArea textarea::placeholder,
            .stApp .stNumberInput input::placeholder {
                color: rgba(171, 192, 219, 0.7) !important;
            }

            .stApp div[data-baseweb="select"] *,
            .stApp div[data-baseweb="base-input"] input,
            .stApp [data-testid="stFileUploaderDropzone"] * {
                color: var(--text) !important;
            }

            .stApp div[data-baseweb="select"] svg,
            .stApp .stFileUploader svg {
                fill: var(--muted) !important;
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
                background: linear-gradient(180deg, rgba(10, 21, 38, 0.99), rgba(7, 16, 29, 0.98)) !important;
                color: var(--text) !important;
                border: 1px solid rgba(122, 182, 255, 0.24) !important;
                box-shadow: 0 18px 40px rgba(0, 0, 0, 0.28) !important;
            }

            body div[data-baseweb="popover"] *,
            body div[data-baseweb="menu"] *,
            body div[role="listbox"] * {
                color: var(--text) !important;
            }

            [role="listbox"] {
                background: rgba(9, 20, 34, 0.98) !important;
                border: 1px solid rgba(122, 182, 255, 0.24) !important;
            }

            [role="option"] {
                color: var(--text) !important;
                background: transparent !important;
                font-weight: 600 !important;
            }

            [role="option"][aria-selected="true"] {
                background: rgba(83, 245, 216, 0.12) !important;
            }

            [role="option"]:hover,
            [role="option"][data-highlighted="true"] {
                background: rgba(122, 182, 255, 0.14) !important;
            }

            .stApp [data-testid="stFileUploaderDropzoneInstructions"],
            .stApp [data-testid="stFileUploaderDropzone"] small,
            .stApp [data-testid="stFileUploaderDropzone"] span {
                color: var(--muted) !important;
            }

            .stButton > button,
            .stFormSubmitButton > button,
            .stDownloadButton > button,
            div[data-baseweb="select"] > div {
                border-radius: 14px !important;
            }

            .stButton > button,
            .stFormSubmitButton > button,
            .stDownloadButton > button {
                background: linear-gradient(180deg, rgba(14, 28, 48, 0.96), rgba(9, 18, 32, 0.92)) !important;
                color: var(--text) !important;
                border: 1px solid rgba(122, 182, 255, 0.24) !important;
                box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
                transition: all 0.18s ease;
            }

            .stButton > button:hover,
            .stFormSubmitButton > button:hover,
            .stDownloadButton > button:hover {
                border-color: rgba(83, 245, 216, 0.34) !important;
                background: linear-gradient(180deg, rgba(17, 36, 61, 0.98), rgba(10, 20, 34, 0.96)) !important;
                transform: translateY(-1px);
            }

            .stButton > button:focus,
            .stFormSubmitButton > button:focus,
            .stDownloadButton > button:focus,
            .stApp .stTextInput input:focus,
            .stApp .stTextArea textarea:focus,
            .stApp .stNumberInput input:focus,
            .stApp div[data-baseweb="select"] > div:focus-within {
                border-color: rgba(83, 245, 216, 0.36) !important;
                box-shadow: 0 0 0 1px rgba(83, 245, 216, 0.14), 0 12px 28px rgba(0, 0, 0, 0.18) !important;
            }

            .stTextInput input, .stTextArea textarea, .stNumberInput input {
                border-radius: 14px !important;
            }

            @media (max-width: 1100px) {
                .page-banner {
                    flex-direction: column;
                }

                .page-banner-side {
                    min-width: 0;
                    align-items: flex-start;
                }
            }

            @media (max-width: 960px) {
                .hero-shell, .result-hero {
                    flex-direction: column;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
