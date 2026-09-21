"""
app.py
Executive C-Suite Commercial Decision Suite: Automated Metric Tree & Root Cause Analysis.
Minimalist, high-aesthetic dark executive SaaS platform inspired by DocMind and modern web apps.
Features:
- Combined sidebar card modules (Commercial Scope & AI Engine)
- Docked, clean bottom chat bar matching the main layout perfectly
- Underline-style tabs with vibrant accent (no boxy containers)
- Multi-format visual switchers in diagnostic tabs (Waterfall, Bars, Treemap, Tables)
- Grounded Metrics Conversational Copilot powered by Groq
- RCA Methodology & Architecture Blueprint interactive dialog
"""

import os
import re
import time
import html
from typing import Optional
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd

import importlib
import src.engine
import src.ai_advisor
importlib.reload(src.engine)
importlib.reload(src.ai_advisor)

from src.engine import MetricEngine
from src.schema import RootCauseReport
from src.ai_advisor import (
    generate_executive_briefing,
    ask_metric_copilot,
    DEFAULT_GROQ_MODEL,
)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Pre-configured Backend AI Engine Settings
def _resolve_backend_secret(key: str, default: str = "") -> str:
    val = os.getenv(key) or os.getenv(key.lower()) or os.getenv(key.upper())
    if val and str(val).strip():
        return str(val).strip()
    try:
        if key in st.secrets and str(st.secrets[key]).strip():
            return str(st.secrets[key]).strip()
        if key.upper() in st.secrets and str(st.secrets[key.upper()]).strip():
            return str(st.secrets[key.upper()]).strip()
        if key.lower() in st.secrets and str(st.secrets[key.lower()]).strip():
            return str(st.secrets[key.lower()]).strip()
        for sec in ["groq", "general", "default"]:
            if sec in st.secrets and isinstance(st.secrets[sec], dict):
                sub = st.secrets[sec]
                found = sub.get(key) or sub.get(key.lower()) or sub.get(key.upper()) or sub.get("api_key")
                if found and str(found).strip():
                    return str(found).strip()
    except Exception:
        pass
    return default

BACKEND_AI_MODEL = _resolve_backend_secret("GROQ_MODEL", "qwen/qwen3.8-27b")
BACKEND_GROQ_KEY = _resolve_backend_secret("GROQ_API_KEY", "")

# -----------------------------------------------------------------------------
# Streamlit Page Config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Metricsbridge AI | Commercial RCA Engine",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Modern Executive SaaS Dark Theme CSS (Matching DocMind & Modern Webapps)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

        /* Global Theme Foundation */
        html, body, [class*="css"], .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            background-color: #0E1117 !important;
            color: #F3F4F6 !important;
        }

        /* Clean Streamlit Layout: Align main content start with sidebar */
        .block-container,
        [data-testid="stMain"] .block-container,
        .main .block-container {
            padding-top: 4.25rem !important;
            padding-bottom: 4rem !important;
            max-width: 100% !important;
        }

        /* Streamlit Header: Sleek Navbar with Theme Matching Dark Background */
        header[data-testid="stHeader"] {
            background-color: #0E1117 !important;
            border-bottom: 1px solid #232736 !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35) !important;
            height: 3.5rem !important;
            min-height: 3.5rem !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-end !important;
            z-index: 99999 !important;
            visibility: visible !important;
            pointer-events: auto !important;
        }

        /* Allow interactions on the actual header toolbar elements (Deploy, Menu, Sidebar Toggle) */
        header[data-testid="stHeader"] button,
        header[data-testid="stHeader"] a,
        [data-testid="stToolbar"],
        [data-testid="stHeaderActionElements"],
        div[data-testid="stAppDeployButton"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stExpandSidebarButton"] {
            pointer-events: auto !important;
        }

        /* Refined Spacing Rhythm for Dashboards */
        [data-testid="stVerticalBlock"] {
            gap: 1rem !important;
        }

        /* Optimal, premium gap between horizontal blocks and dashboard cards */
        [data-testid="stHorizontalBlock"] {
            gap: 1.15rem !important;
        }

        /* Sidebar columns maintain a clean, compact gap */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            gap: 0.65rem !important;
        }

        /* Streamlit Header Toolbar & Actions: Centered on Navbar */
        [data-testid="stToolbar"] {
            top: 50% !important;
            transform: translateY(-50%) !important;
            right: 1.25rem !important;
        }

        [data-testid="stToolbar"],
        [data-testid="stHeaderActionElements"],
        div[data-testid="stAppDeployButton"] {
            background: transparent !important;
            visibility: visible !important;
            display: inline-flex !important;
            align-items: center !important;
            opacity: 1 !important;
            gap: 0.45rem !important;
            border: none !important;
        }

        /* Header action buttons and icons (Share, Star, Edit, 3-dots Menu) */
        header[data-testid="stHeader"] button,
        header[data-testid="stHeader"] a,
        [data-testid="stToolbar"] button,
        [data-testid="stToolbar"] a,
        [data-testid="stHeaderActionElements"] button,
        [data-testid="stHeaderActionElements"] a {
            color: #9CA3AF !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
            visibility: visible !important;
        }

        header[data-testid="stHeader"] button:hover,
        header[data-testid="stHeader"] a:hover,
        [data-testid="stToolbar"] button:hover,
        [data-testid="stToolbar"] a:hover,
        [data-testid="stHeaderActionElements"] button:hover,
        [data-testid="stHeaderActionElements"] a:hover {
            color: #FFFFFF !important;
            background-color: #1E293B !important;
        }

        header[data-testid="stHeader"] svg,
        [data-testid="stToolbar"] svg,
        [data-testid="stHeaderActionElements"] svg,
        [data-testid="stStatusWidget"] svg {
            fill: currentColor !important;
            stroke: none !important;
        }

        header[data-testid="stHeader"] svg path,
        [data-testid="stToolbar"] svg path,
        [data-testid="stHeaderActionElements"] svg path,
        [data-testid="stStatusWidget"] svg path {
            stroke: none !important;
        }

        /* The Reopen / Expand Sidebar Button (>>) when sidebar is collapsed */
        [data-testid="stExpandSidebarButton"],
        button[data-testid="stExpandSidebarButton"] {
            visibility: visible !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            background-color: #181B24 !important;
            border: 1px solid #282D3D !important;
            border-radius: 8px !important;
            color: #38BDF8 !important;
            padding: 6px 10px !important;
            margin: 6px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5) !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
            z-index: 999999 !important;
        }

        [data-testid="stExpandSidebarButton"]:hover,
        button[data-testid="stExpandSidebarButton"]:hover {
            background-color: #1E293B !important;
            border-color: #38BDF8 !important;
            color: #FFFFFF !important;
            transform: scale(1.05);
        }

        [data-testid="stExpandSidebarButton"] svg,
        button[data-testid="stExpandSidebarButton"] svg {
            fill: #38BDF8 !important;
            stroke: none !important;
            color: #38BDF8 !important;
        }

        [data-testid="stExpandSidebarButton"] svg path,
        button[data-testid="stExpandSidebarButton"] svg path {
            stroke: none !important;
        }

        /* The Collapse Sidebar Button (<<) inside expanded sidebar */
        [data-testid="stSidebarCollapseButton"] {
            visibility: visible !important;
            display: inline-flex !important;
        }

        [data-testid="stSidebarCollapseButton"] button {
            background-color: #1E2230 !important;
            border: 1px solid #2D3346 !important;
            color: #9CA3AF !important;
            border-radius: 6px !important;
            transition: all 0.15s ease !important;
        }

        [data-testid="stSidebarCollapseButton"] button:hover {
            color: #38BDF8 !important;
            border-color: #38BDF8 !important;
        }

        /* Hide Streamlit footer only; keep header toolbar and deploy/share fully visible */
        footer {
            display: none !important;
        }

        /* Hide Streamlit default Input Instructions */
        [data-testid="InputInstructions"],
        .stTextInput div[data-testid="InputInstructions"] {
            display: none !important;
        }

        /* Gradient Brand Headers */
        .main-title {
            font-size: 1.85rem;
            font-weight: 800;
            background: linear-gradient(135deg, #38BDF8 0%, #60A5FA 50%, #3B82F6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.15rem;
            letter-spacing: -0.5px;
            line-height: 1.2;
        }

        .subtitle {
            font-size: 0.86rem;
            color: #9CA3AF;
            margin-bottom: 0.35rem;
            line-height: 1.4;
        }

        /* Author & Status Pills */
        .author-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.35);
            color: #38BDF8;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 20px;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
        }

        .period-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: #181B24;
            border: 1px solid #282D3D;
            border-radius: 8px;
            padding: 0.35rem 0.75rem;
            font-size: 0.78rem;
            color: #9CA3AF;
        }

        .period-pill b {
            color: #F3F4F6;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .status-green {
            background: rgba(16, 185, 129, 0.14);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #34D399;
        }

        .status-red {
            background: rgba(244, 63, 94, 0.14);
            border: 1px solid rgba(244, 63, 94, 0.4);
            color: #FB7185;
        }

        /* =====================================================================
           1. SIDEBAR: COMBINED MODERN CARD MODULES (MATCHING DOCMIND)
           ===================================================================== */
        [data-testid="stSidebar"] {
            background-color: #0E1117 !important;
            border-right: 1px solid #232736 !important;
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 2rem !important;
        }

        /* Sidebar Branding Box */
        .brand-container {
            padding-bottom: 10px;
            margin-bottom: 12px;
            border-bottom: 1px solid #232736;
        }

        .brand-title {
            font-size: 1.35rem;
            font-weight: 800;
            background: linear-gradient(135deg, #38BDF8 0%, #60A5FA 50%, #3B82F6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            line-height: 1.15;
        }

        .brand-sub {
            font-size: 0.72rem;
            color: #9CA3AF;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            font-weight: 600;
            margin-top: 2px;
        }

        .creator-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.35);
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 0.75rem;
            color: #38BDF8;
            margin-top: 6px;
        }

        /* Section Headings in Sidebar */
        .sidebar-section-title {
            font-size: 0.82rem;
            font-weight: 700;
            color: #38BDF8;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-top: 14px;
            margin-bottom: 8px;
        }

        /* Combined Card Modules in Sidebar (Deep Dark Backdrop for Field Contrast) */
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(180deg, #0F1420 0%, #0A0D15 100%) !important;
            border: 1.5px solid #1C2638 !important;
            border-radius: 12px !important;
            padding: 16px 14px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5) !important;
        }

        /* High-Contrast Lighter Field Labels */
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] label,
        [data-testid="stSidebar"] label {
            color: #CBD5E1 !important;
            font-size: 0.76rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
            margin-bottom: 6px !important;
        }

        /* Distinct, Elevated Sidebar Fields & Dropdowns (Visibly Lighter Shade of Slate Navy) */
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-baseweb="input"],
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] .stTextInput div[data-baseweb="input"],
        [data-testid="stSidebar"] div[data-testid="stSelectbox"] > div > div,
        [data-testid="stSidebar"] div[data-testid="stTextInput"] > div > div {
            background: linear-gradient(180deg, #222F45 0%, #1A2436 100%) !important;
            border: 1.5px solid #384A68 !important;
            border-radius: 9px !important;
            min-height: 40px !important;
            height: 40px !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.09) !important;
            display: flex !important;
            align-items: center !important;
            transition: all 0.2s ease !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"]:hover > div,
        [data-testid="stSidebar"] div[data-baseweb="input"]:hover,
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"]:hover > div,
        [data-testid="stSidebar"] .stTextInput div[data-baseweb="input"]:hover,
        [data-testid="stSidebar"] div[data-testid="stSelectbox"] > div > div:hover,
        [data-testid="stSidebar"] div[data-testid="stTextInput"] > div > div:hover {
            background: linear-gradient(180deg, #2B3B56 0%, #202D42 100%) !important;
            border-color: #38BDF8 !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
        }

        /* Remove inner base-input borders and backgrounds */
        [data-testid="stSidebar"] div[data-baseweb="base-input"] {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            height: 100% !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
        }

        /* Unified Input Text Styling */
        [data-testid="stSidebar"] input {
            background-color: transparent !important;
            color: #FFFFFF !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.86rem !important;
            font-weight: 600 !important;
            border: none !important;
            padding: 0 12px !important;
            height: 100% !important;
            width: 100% !important;
        }

        [data-testid="stSidebar"] input::placeholder {
            color: #94A3B8 !important;
            font-size: 0.82rem !important;
            font-weight: 400 !important;
        }

        /* Unified Selectbox Text Styling */
        [data-testid="stSidebar"] div[data-baseweb="select"] span {
            color: #FFFFFF !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.86rem !important;
            font-weight: 600 !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="select"] svg {
            fill: #38BDF8 !important;
            color: #38BDF8 !important;
            transition: transform 0.2s ease;
        }

        /* Identical Focus States with Sky Blue Glow across all inputs & dropdowns */
        [data-testid="stSidebar"] div[data-baseweb="input"]:focus-within,
        [data-testid="stSidebar"] div[data-baseweb="select"]:focus-within > div {
            background-color: #263857 !important;
            border-color: #38BDF8 !important;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.35), 0 0 16px rgba(56, 189, 248, 0.3) !important;
        }

        /* Password eye toggle button inside API key input */
        [data-testid="stSidebar"] div[data-baseweb="input"] button {
            background-color: transparent !important;
            border: none !important;
            color: #94A3B8 !important;
        }

        [data-testid="stSidebar"] div[data-baseweb="input"] button:hover {
            color: #38BDF8 !important;
        }

        /* Dropdown Popover Menus */
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] > div,
        ul[role="listbox"] {
            background-color: #161B26 !important;
            border: 1px solid #2B354F !important;
            color: #F8FAFC !important;
            border-radius: 8px !important;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.6) !important;
        }

        li[role="option"] {
            background-color: #161B26 !important;
            color: #E2E8F0 !important;
            font-size: 0.84rem !important;
            transition: all 0.15s ease !important;
        }

        li[role="option"]:hover,
        li[role="option"][aria-selected="true"] {
            background-color: #0284C7 !important;
            color: #FFFFFF !important;
        }

        /* Slider Light Blue Styling with Crisp Visible Rail & Thumb */
        div[data-testid="stSlider"] div[role="slider"] {
            background-color: #38BDF8 !important;
            border: 2px solid #FFFFFF !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.7) !important;
            width: 16px !important;
            height: 16px !important;
        }

        [data-testid="stSidebar"] div[data-testid="stSlider"] [data-testid="stThumbValue"] {
            color: #38BDF8 !important;
            font-weight: 700 !important;
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Expanders styled for sleek dark mode */
        div[data-testid="stExpander"] {
            background-color: #181B24 !important;
            border: 1px solid #282D3D !important;
            border-radius: 10px !important;
            margin-bottom: 12px !important;
        }

        div[data-testid="stExpander"]:focus-within {
            border-color: rgba(56, 189, 248, 0.4) !important;
        }

        div[data-testid="stExpander"] summary {
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            color: #E5E7EB !important;
        }

        /* Distinct, Elevated Sidebar Buttons */
        [data-testid="stSidebar"] div.stButton > button {
            background: linear-gradient(180deg, #1E283C 0%, #161F2E 100%) !important;
            color: #F3F4F6 !important;
            border: 1.5px solid #334664 !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            font-size: 0.84rem !important;
            font-weight: 600 !important;
            padding: 0.52rem 1rem !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        }

        [data-testid="stSidebar"] div.stButton > button:hover {
            background: linear-gradient(180deg, #25334D 0%, #1A2438 100%) !important;
            border-color: #38BDF8 !important;
            color: #38BDF8 !important;
            box-shadow: 0 0 12px rgba(56, 189, 248, 0.25) !important;
            transform: translateY(-1px);
        }

        [data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0284C7 0%, #2563EB 100%) !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border: 1px solid #38BDF8 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 16px rgba(37, 99, 235, 0.45) !important;
            transition: all 0.2s ease !important;
            padding: 0.55rem 1rem !important;
            width: 100% !important;
            margin-top: 0.6rem !important;
        }

        [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.6) !important;
            filter: brightness(1.1);
        }

        /* General Button Styling across Main Page */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #0284C7 0%, #2563EB 100%) !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            border: none !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
            transition: all 0.2s ease !important;
            padding: 0.5rem 1rem !important;
            width: 100% !important;
            margin-top: 0.5rem !important;
        }

        div.stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5) !important;
            filter: brightness(1.1);
        }

        div.stButton > button {
            background-color: #1E2230 !important;
            color: #F3F4F6 !important;
            border: 1px solid #2D3346 !important;
            border-radius: 8px !important;
            transition: all 0.2s ease !important;
            font-size: 0.84rem !important;
            font-weight: 500 !important;
        }

        div.stButton > button:hover {
            border-color: #38BDF8 !important;
            color: #38BDF8 !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.2) !important;
        }

        /* =====================================================================
           2. DOCKED, SEAMLESS BOTTOM CHAT BAR (MATCHING DOCMIND)
           ==================================================================== */
        [data-testid="stBottom"] {
            background-color: #0E1117 !important;
            border-top: none !important;
            box-shadow: none !important;
            padding-top: 4px !important;
            padding-bottom: 12px !important;
        }

        div[data-testid="stChatInput"] > div {
            background-color: #181B24 !important;
            border: 1px solid #282D3D !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
            padding: 4px 8px !important;
        }

        div[data-testid="stChatInput"] textarea {
            background-color: transparent !important;
            color: #F9FAFB !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 0.88rem !important;
        }

        div[data-testid="stChatInput"] textarea::placeholder {
            color: #9CA3AF !important;
        }

        div[data-testid="stChatInput"] button {
            background-color: #232736 !important;
            color: #38BDF8 !important;
            border-radius: 8px !important;
            border: 1px solid #2D3346 !important;
            transition: all 0.15s ease !important;
        }

        div[data-testid="stChatInput"] button:hover {
            background-color: #0284C7 !important;
            color: #FFFFFF !important;
        }

        /* =====================================================================
           3. UNDERLINE-STYLE TABS (CLEAN BLUE ACCENT, NO BOXY OUTLINES)
           ===================================================================== */
        .stTabs [data-baseweb="tab-list"] {
            background-color: transparent !important;
            gap: 1.5rem !important;
            border-bottom: 1px solid #232736 !important;
            padding-bottom: 0px !important;
            margin-bottom: 1.2rem !important;
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            border: none !important;
            border-bottom: 2px solid transparent !important;
            border-radius: 0px !important;
            padding: 0.55rem 0.25rem !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            color: #9CA3AF !important;
            transition: color 0.15s ease, border-bottom-color 0.15s ease !important;
        }

        .stTabs [data-baseweb="tab"]:hover {
            color: #E2E8F0 !important;
        }

        .stTabs [aria-selected="true"],
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: transparent !important;
            border: none !important;
            border-bottom: 2px solid #38BDF8 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }

        .stTabs [data-baseweb="tab-highlight"],
        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }

        /* Format Radio Switchers */
        div[data-testid="stRadio"] > div {
            flex-direction: row !important;
            gap: 1.2rem !important;
            background-color: transparent !important;
            margin-bottom: 0.8rem !important;
        }

        div[data-testid="stRadio"] label {
            color: #9CA3AF !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
        }

        div[data-testid="stRadio"] label:hover {
            color: #F3F4F6 !important;
        }

        /* =====================================================================
           4. KPI METRIC CARDS & PANELS (ELEVATED EXECUTIVE CARD STYLING)
           ===================================================================== */
        .metric-card {
            background: linear-gradient(180deg, #171E2D 0%, #121724 100%);
            border: 1.5px solid #28364E;
            border-radius: 12px;
            padding: 1.05rem 1.25rem;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.06);
            transition: all 0.22s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            margin-bottom: 0.35rem !important;
        }

        .metric-card:hover {
            border-color: #38BDF8;
            box-shadow: 0 8px 24px rgba(56, 189, 248, 0.18);
            transform: translateY(-2px);
        }

        .metric-label {
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #94A3B8;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.6rem;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: -0.03em;
            line-height: 1.2;
            margin-bottom: 0.4rem;
        }

        .metric-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.76rem;
            color: #64748B;
        }

        .metric-delta-pill {
            display: inline-flex;
            align-items: center;
            font-size: 0.72rem;
            font-weight: 600;
            padding: 0.18rem 0.52rem;
            border-radius: 6px;
        }

        .delta-pos {
            color: #34D399;
            background: rgba(16, 185, 129, 0.14);
        }

        .delta-neg {
            color: #FB7185;
            background: rgba(244, 63, 94, 0.14);
        }

        /* Executive Briefing Box (Optimal Spacing Below Metric Cards) */
        .briefing-container {
            background: linear-gradient(180deg, #171E2D 0%, #121724 100%);
            border: 1.5px solid #28364E;
            border-radius: 12px;
            padding: 1.2rem 1.4rem;
            margin-top: 0.35rem !important;
            margin-bottom: 0.85rem !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 255, 255, 0.05);
        }

        .briefing-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 0.9rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid #232736;
            flex-wrap: wrap;
            gap: 0.75rem;
        }

        .briefing-title-wrap {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .briefing-title {
            font-size: 0.95rem;
            font-weight: 700;
            color: #38BDF8;
            letter-spacing: -0.01em;
        }

        .briefing-badge {
            font-size: 0.7rem;
            font-weight: 600;
            color: #9CA3AF;
            background: #1E2230;
            border: 1px solid #2D3346;
            padding: 0.2rem 0.55rem;
            border-radius: 9999px;
        }

        .pvm-pill-row {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            flex-wrap: wrap;
        }

        .pvm-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            font-size: 0.78rem;
            border: 1px solid transparent;
        }

        .pill-vol {
            background: rgba(16, 185, 129, 0.1);
            border-color: rgba(16, 185, 129, 0.25);
            color: #34D399;
        }

        .pill-pri {
            background: rgba(244, 63, 94, 0.1);
            border-color: rgba(244, 63, 94, 0.25);
            color: #FB7185;
        }

        .pill-frt {
            background: rgba(245, 158, 11, 0.1);
            border-color: rgba(245, 158, 11, 0.25);
            color: #FBBF24;
        }

        .pvm-pill-label {
            font-weight: 500;
            opacity: 0.85;
        }

        .pvm-pill-val {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
        }

        .briefing-body {
            font-size: 0.88rem;
            line-height: 1.65;
            color: #D1D5DB;
        }

        .briefing-body h3 {
            font-size: 0.85rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            color: #38BDF8 !important;
            margin-top: 1rem !important;
            margin-bottom: 0.45rem !important;
        }

        .briefing-body h3:first-child {
            margin-top: 0 !important;
        }

        .briefing-body p {
            margin-bottom: 0.65rem !important;
            color: #D1D5DB !important;
        }

        .briefing-body ul {
            margin-top: 0.2rem !important;
            margin-bottom: 0.75rem !important;
            padding-left: 1.2rem !important;
        }

        .briefing-body li {
            margin-bottom: 0.35rem !important;
            color: #D1D5DB !important;
        }

        .briefing-body strong {
            color: #F9FAFB !important;
            font-weight: 600 !important;
        }

        /* Tab Panels (Elevated Gradient Surface) */
        .tab-panel {
            background: linear-gradient(180deg, #161D2B 0%, #111622 100%);
            border: 1px solid #28364E;
            border-radius: 10px;
            padding: 1.25rem;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
        }

        .tab-panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.9rem;
            padding-bottom: 0.6rem;
            border-bottom: 1px solid #202A3B;
        }

        .tab-panel-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #FFFFFF;
        }

        .tab-panel-tag {
            font-size: 0.72rem;
            font-weight: 600;
            color: #94A3B8;
            background: #1C2436;
            border: 1px solid #2D3D58;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
        }

        /* Executive High-Contrast Tables (Not Submerged) */
        .exec-table-wrapper {
            background: #0F1522;
            border: 1.5px solid #28374E;
            border-radius: 10px;
            overflow-x: auto;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.4);
            margin-top: 0.5rem;
            margin-bottom: 0.4rem;
        }

        .exec-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Inter', sans-serif;
            font-size: 0.83rem;
            color: #E2E8F0;
            text-align: left;
        }

        .exec-table thead tr {
            background: #182235;
            border-bottom: 2px solid #2A3B54;
        }

        .exec-table th {
            padding: 10px 14px;
            font-weight: 700;
            font-size: 0.73rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94A3B8;
            white-space: nowrap;
        }

        .exec-table tbody tr {
            border-bottom: 1px solid #1C2638;
            transition: background 0.15s ease;
        }

        .exec-table tbody tr:nth-child(even) {
            background-color: #111724;
        }

        .exec-table tbody tr:nth-child(odd) {
            background-color: #151D2C;
        }

        .exec-table tbody tr:hover {
            background-color: #202C42 !important;
        }

        .exec-table td {
            padding: 9px 14px;
            vertical-align: middle;
            white-space: nowrap;
            color: #E2E8F0;
        }

        .exec-table td.num-cell {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            text-align: right;
            color: #F8FAFC;
        }

        .exec-table th.num-cell {
            text-align: right;
        }

        .table-pill-pos {
            display: inline-flex;
            align-items: center;
            background: rgba(16, 185, 129, 0.18);
            border: 1px solid rgba(16, 185, 129, 0.35);
            color: #34D399;
            font-weight: 700;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.76rem;
        }

        .table-pill-neg {
            display: inline-flex;
            align-items: center;
            background: rgba(244, 63, 94, 0.18);
            border: 1px solid rgba(244, 63, 94, 0.35);
            color: #FB7185;
            font-weight: 700;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.76rem;
        }

        .table-pill-amber {
            display: inline-flex;
            align-items: center;
            background: rgba(245, 158, 11, 0.18);
            border: 1px solid rgba(245, 158, 11, 0.35);
            color: #FBBF24;
            font-weight: 700;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.76rem;
        }

        .table-pill-neu {
            display: inline-flex;
            align-items: center;
            background: rgba(148, 163, 184, 0.14);
            border: 1px solid rgba(148, 163, 184, 0.3);
            color: #CBD5E1;
            font-weight: 600;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.74rem;
        }

        /* Also elevate Streamlit native dataframes if rendered */
        [data-testid="stDataFrame"] {
            background-color: #121825 !important;
            border: 1px solid #28364E !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
        }

        /* Copilot Section Container */
        .copilot-section {
            background: linear-gradient(180deg, #161D2B 0%, #111622 100%);
            border: 1px solid #28364E;
            border-radius: 10px;
            padding: 1.3rem;
            margin-top: 1.2rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
        }

        .copilot-header {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 0.35rem;
        }

        .copilot-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #38BDF8;
        }

        .copilot-subtitle {
            font-size: 0.78rem;
            color: #9CA3AF;
            margin-bottom: 0.75rem;
        }

        /* Copilot Suggested Questions Guide */
        .copilot-guide-box {
            background: rgba(18, 24, 37, 0.75);
            border: 1px solid #232E42;
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 0.85rem;
        }

        .copilot-guide-title {
            font-size: 0.75rem;
            font-weight: 700;
            color: #38BDF8;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .copilot-guide-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 8px;
        }

        .copilot-guide-chip {
            background: #141B28;
            border: 1px solid #243247;
            border-radius: 6px;
            padding: 7px 10px;
            font-size: 0.73rem;
            line-height: 1.35;
        }

        .copilot-guide-chip strong {
            color: #38BDF8;
            display: block;
            font-size: 0.71rem;
            margin-bottom: 3px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .copilot-guide-chip span {
            color: #94A3B8;
            font-size: 0.72rem;
        }

        /* Chat Message Avatars in Sleek Blue */
        [data-testid="stChatMessageAvatarAssistant"],
        div[data-testid="stChatMessageAvatarCustom"],
        div[data-testid="stChatMessage"] [data-testid="stIconMaterial"] {
            background-color: #0284C7 !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
        }

        [data-testid="stChatMessageAvatarAssistant"] svg {
            fill: #FFFFFF !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Initialize Metric Engine (Cached)
# -----------------------------------------------------------------------------
@st.cache_resource
def get_engine():
    parquet_file = "./data/olist_analytics_fact.parquet"
    return MetricEngine(parquet_file)


engine = get_engine()
available_periods = engine.get_available_periods()


def format_briefing_to_html(md_text: str) -> str:
    """
    Transforms markdown executive briefing into clean, beautifully structured HTML
    that renders completely inside an enclosed card container without escaping DOM blocks.
    """
    lines = md_text.strip().split("\n")
    html_out = []
    in_list = False

    for line in lines:
        s = line.strip()
        if not s:
            if in_list:
                html_out.append("</ul>")
                in_list = False
            continue

        if s.startswith("### "):
            if in_list:
                html_out.append("</ul>")
                in_list = False
            title = s[4:].strip()
            html_out.append(f"<h3>{html.escape(title)}</h3>")
        elif s.startswith("## "):
            if in_list:
                html_out.append("</ul>")
                in_list = False
            title = s[3:].strip()
            html_out.append(f"<h3>{html.escape(title)}</h3>")
        elif s.startswith("- ") or s.startswith("* "):
            if not in_list:
                html_out.append("<ul>")
                in_list = True
            content = s[2:].strip()
            content = html.escape(content)
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(
                r"`(.*?)`",
                r'<code style="background:#1E2638; padding:1px 5px; border-radius:4px; color:#38BDF8; font-size:0.85em;">\1</code>',
                content,
            )
            html_out.append(f"<li>{content}</li>")
        elif re.match(r"^\d+\.\s", s):
            if in_list:
                html_out.append("</ul>")
                in_list = False
            num_match = re.match(r"^(\d+)\.\s*(.*)", s)
            if num_match:
                num_str, rest = num_match.group(1), num_match.group(2)
                rest = html.escape(rest)
                rest = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", rest)
                rest = re.sub(
                    r"`(.*?)`",
                    r'<code style="background:#1E2638; padding:1px 5px; border-radius:4px; color:#38BDF8; font-size:0.85em;">\1</code>',
                    rest,
                )
                html_out.append(f"<p><span style='color:#38BDF8; font-weight:700;'>{num_str}.</span> {rest}</p>")
            else:
                html_out.append(f"<p>{html.escape(s)}</p>")
        elif s.startswith("---"):
            if in_list:
                html_out.append("</ul>")
                in_list = False
            html_out.append("<hr style='border:0; border-top:1px solid #28364E; margin:14px 0;'>")
        elif s.startswith("*") and s.endswith("*"):
            if in_list:
                html_out.append("</ul>")
                in_list = False
            inner = html.escape(s.strip("*"))
            html_out.append(f"<div style='font-size:0.75rem; color:#64748B; font-style:italic; margin-top:8px;'>{inner}</div>")
        else:
            if in_list:
                html_out.append("</ul>")
                in_list = False
            content = html.escape(s)
            content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(
                r"`(.*?)`",
                r'<code style="background:#1E2638; padding:1px 5px; border-radius:4px; color:#38BDF8; font-size:0.85em;">\1</code>',
                content,
            )
            html_out.append(f"<p>{content}</p>")

    if in_list:
        html_out.append("</ul>")

    return "\n".join(html_out)


def render_executive_table(
    headers: list[str],
    rows: list[dict],
    alignments: Optional[dict[str, str]] = None,
) -> str:
    """
    Renders a high-contrast executive HTML table with monospaced financial numbers,
    clean zebra striping, and vibrant performance badge pills.
    """
    if not rows:
        return "<div style='color: #64748B; padding: 12px; font-size: 0.85rem;'>No data available</div>"

    if alignments is None:
        alignments = {}

    out = ['<div class="exec-table-wrapper">']
    out.append('<table class="exec-table">')

    # Thead
    out.append('<thead><tr>')
    for h in headers:
        align = alignments.get(h, "left")
        align_cls = " num-cell" if align == "right" else ""
        out.append(f'<th class="{align_cls}">{html.escape(h)}</th>')
    out.append('</tr></thead>')

    # Tbody
    out.append('<tbody>')
    for row in rows:
        out.append('<tr>')
        for h in headers:
            val = str(row.get(h, ""))
            align = alignments.get(h, "left")
            align_cls = " num-cell" if align == "right" else ""

            cell_content = html.escape(val)
            if "Growth" in h or "Delta" in h:
                if val.startswith("+"):
                    cell_content = f'<span class="table-pill-pos">{cell_content}</span>'
                elif val.startswith("-"):
                    cell_content = f'<span class="table-pill-neg">{cell_content}</span>'
            elif h == "Strategic Focus":
                if "Expansion" in val:
                    cell_content = f'<span class="table-pill-pos">● {cell_content}</span>'
                elif "Focus" in val or "Contraction" in val or "Drag" in val:
                    cell_content = f'<span class="table-pill-neg">● {cell_content}</span>'
                else:
                    cell_content = f'<span class="table-pill-neu">● {cell_content}</span>'
            elif "Burden" in h:
                try:
                    num = float(val.replace("%", "").strip())
                    if num >= 20.0:
                        cell_content = f'<span class="table-pill-neg">{cell_content}</span>'
                    elif num >= 15.0:
                        cell_content = f'<span class="table-pill-amber">{cell_content}</span>'
                except ValueError:
                    pass

            out.append(f'<td class="{align_cls}">{cell_content}</td>')
        out.append('</tr>')
    out.append('</tbody>')
    out.append('</table>')
    out.append('</div>')
    return "".join(out)


# =============================================================================
# RCA METHODOLOGY BLUEPRINT MODAL
# =============================================================================
@st.dialog("Metricsbridge AI — RCA Methodology & Mathematical Framework", width="large")
def show_methodology_dialog():
    """Display comprehensive system architecture diagram and engineering breakdown."""
    st.markdown(
        """
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #282D3D; padding-bottom: 10px; margin-bottom: 14px;">
            <div>
                <span style="font-size: 1.15rem; font-weight: 700; color: #38BDF8;">End-to-End Commercial Root Cause Analysis Pipeline</span>
                <div style="font-size: 0.82rem; color: #9CA3AF;">Engineered by <b>Harsh Kumar</b> | Zero-API-Cost Hybrid Polars & PVM Mathematical Engine</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    components.html(
        """
        <div style="background-color: #12151E; padding: 16px; border-radius: 10px; border: 1px solid #282D3D; overflow-x: auto;">
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <script>mermaid.initialize({startOnLoad: true, theme: 'dark', themeVariables: {darkMode: true, background: '#12151E'}});</script>
            <div class="mermaid">
            flowchart TD
                subgraph Ingestion ["1. Data Ingestion & Lazy Polars Scan"]
                    CSV["Olist Brazilian E-Commerce Raw CSVs"] --> Scan["Lazy Polars Scan & Schema Validation"]
                    Scan --> Filter["Delivered Orders Filter & Macro-Region Mapping"]
                    Filter --> Parquet[("./data/olist_analytics_fact.parquet\nSnappy Compressed, 110k Rows")]
                end

                subgraph Math ["2. Mathematical Decomposition Engine"]
                    Parquet --> MetricEngine["MetricEngine (Zero-Copy Polars Slicing)"]
                    MetricEngine --> Baseline["Period A Baseline: Units, Price, Freight, Margin"]
                    MetricEngine --> Compare["Period B Compare: Units, Price, Freight, Margin"]
                    Baseline & Compare --> PVM["Exact PVM Variance Bridge\nΔ Margin = Δ Volume + Δ Price + Δ Freight"]
                end

                subgraph Diagnostics ["3. Dimensional Slicing"]
                    MetricEngine --> CategoryRCA["Category Movers (What Sold)"]
                    MetricEngine --> RegionalRCA["Macro-Regions & States (Where Sold)"]
                end

                subgraph AI ["4. Grounded Groq Cloud LPU Synthesis"]
                    PVM & CategoryRCA & RegionalRCA --> Payload["Strict Analytical Payload (Zero Hallucination)"]
                    Payload --> Groq["Groq Cloud LPU (qwen/qwen3.8-27b)"]
                    Groq --> Briefing["Executive Strategy Briefing"]
                    Groq --> Copilot["Interactive Grounded Metric Copilot"]
                end
            </div>
        </div>
        """,
        height=580,
        scrolling=True,
    )

    st.markdown(
        """
        <div style="margin-top: 14px; margin-bottom: 6px;">
            <div style="font-size: 0.88rem; font-weight: 700; color: #38BDF8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;">
                Key Architectural Decisions (Why Built This Way)
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
                <div style="background: #12151E; border: 1px solid #282D3D; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.05rem;">🎯</span>
                        <span style="font-weight: 700; color: #F3F4F6; font-size: 0.84rem;">1. Deterministic Math First</span>
                    </div>
                    <div style="font-size: 0.77rem; color: #94A3B8; line-height: 1.5;">
                        <strong style="color: #38BDF8;">Never let LLMs do math.</strong> Polars computes 100% exact variance deltas in under 5ms. The LLM only receives pre-calculated numbers to write the briefing, eliminating hallucinations.
                    </div>
                </div>
                <div style="background: #12151E; border: 1px solid #282D3D; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.05rem;">🔍</span>
                        <span style="font-weight: 700; color: #F3F4F6; font-size: 0.84rem;">2. True Root Cause (PVM)</span>
                    </div>
                    <div style="font-size: 0.77rem; color: #94A3B8; line-height: 1.5;">
                        <strong style="color: #34D399;">Beyond surface KPIs.</strong> Rather than just reporting revenue changes, Price-Volume-Mix decomposes margin shifts into volume expansion, pricing, and freight logistics drag.
                    </div>
                </div>
                <div style="background: #12151E; border: 1px solid #282D3D; border-radius: 10px; padding: 14px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                        <span style="font-size: 1.05rem;">⚡</span>
                        <span style="font-weight: 700; color: #F3F4F6; font-size: 0.84rem;">3. Fast & Low Cost</span>
                    </div>
                    <div style="font-size: 0.77rem; color: #94A3B8; line-height: 1.5;">
                        <strong style="color: #FBBF24;">High performance at near-zero cost.</strong> 110k rows are scanned in-memory via compressed Parquet, sending only a small JSON payload to Groq for lightning-fast inference.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# 1. Combined Modern Sidebar Modules (Matching DocMind)
# -----------------------------------------------------------------------------
with st.sidebar:
    # Clean Enterprise Brand Header with Harsh Kumar Attribution
    st.markdown(
        """
        <div class="brand-container">
            <div class="brand-title">Metricsbridge AI</div>
            <div class="brand-sub">COMMERCIAL INTELLIGENCE & RCA</div>
            <div class="creator-badge"><span style="color: #38BDF8; font-size: 0.82rem;">✦</span> Engineered by Harsh Kumar</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("⛶ View RCA Methodology Blueprint", key="sidebar_methodology_btn", use_container_width=True):
        show_methodology_dialog()

    # Combined Controls Section (All Dropdowns and Fields in the Same Section)
    st.markdown(
        '<div class="sidebar-section-title">ANALYSIS CONTROLS</div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        preset = st.selectbox(
            "Comparison Preset",
            [
                "Oct '17 vs Nov '17 (Black Friday Peak)",
                "Nov '17 vs Dec '17 (Holiday Season)",
                "Jul '17 vs Jul '18 (Year-over-Year)",
                "Custom Window",
            ],
            index=0,
        )

        if preset == "Oct '17 vs Nov '17 (Black Friday Peak)":
            idx_a = available_periods.index("2017-10") if "2017-10" in available_periods else 0
            idx_b = available_periods.index("2017-11") if "2017-11" in available_periods else len(available_periods) - 1
        elif preset == "Nov '17 vs Dec '17 (Holiday Season)":
            idx_a = available_periods.index("2017-11") if "2017-11" in available_periods else 0
            idx_b = available_periods.index("2017-12") if "2017-12" in available_periods else len(available_periods) - 1
        elif preset == "Jul '17 vs Jul '18 (Year-over-Year)":
            idx_a = available_periods.index("2017-07") if "2017-07" in available_periods else 0
            idx_b = available_periods.index("2018-07") if "2018-07" in available_periods else len(available_periods) - 1
        else:
            idx_a = available_periods.index("2017-10") if "2017-10" in available_periods else 0
            idx_b = available_periods.index("2017-11") if "2017-11" in available_periods else len(available_periods) - 1

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            period_a = st.selectbox("Baseline (A)", available_periods, index=idx_a)
        with col_s2:
            period_b = st.selectbox("Compare (B)", available_periods, index=idx_b)

        top_n = st.slider(
            "Diagnostic Depth (Top N Movers)",
            min_value=3,
            max_value=6,
            value=3,
            help="Number of top categories and states analyzed in deep dive diagnostics.",
        )

        # Pre-configured Backend AI Model & Credentials
        active_model = BACKEND_AI_MODEL
        groq_api_key = BACKEND_GROQ_KEY

        # Optional UI Input fallback if no key detected in secrets or environment
        if not groq_api_key:
            with st.expander("🔑 Groq AI Key Setup", expanded=False):
                st.caption("Enter a Groq key or configure `GROQ_API_KEY` in Streamlit Cloud Secrets.")
                user_key_input = st.text_input(
                    "Groq API Key",
                    type="password",
                    placeholder="gsk_...",
                    key="sidebar_user_groq_key",
                )
                if user_key_input and user_key_input.strip():
                    groq_api_key = user_key_input.strip()

        custom_inquiry = st.text_input(
            "Strategic Focus Question (Optional)",
            placeholder="e.g. Focus on freight in Northeast",
        )

        run_button = st.button("✦ Run Root Cause Analysis", type="primary", use_container_width=True)

    if st.button("Clear Copilot Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.last_chat_timestamp = 0.0
        st.rerun()

    st.markdown(
        """
        <div style="border-top: 1px solid #232736; padding-top: 14px; margin-top: 24px; text-align: center;">
            <div style="font-size: 0.76rem; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.8px;">Enterprise Commercial RCA</div>
            <div style="font-size: 0.85rem; color: #38BDF8; font-weight: 600; margin-top: 4px;">
                Made by <b>Harsh Kumar</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Execute Analytical Calculation
# -----------------------------------------------------------------------------
report: RootCauseReport = engine.generate_report(period_a, period_b, top_n=top_n)

k_a = report.baseline_kpi
k_b = report.comparison_kpi
b = report.variance_bridge

rev_delta = k_b.total_revenue - k_a.total_revenue
rev_pct = (rev_delta / k_a.total_revenue * 100) if k_a.total_revenue > 0 else 0.0

ord_delta = k_b.total_orders - k_a.total_orders
ord_pct = (ord_delta / k_a.total_orders * 100) if k_a.total_orders > 0 else 0.0

aov_delta = k_b.aov - k_a.aov
aov_pct = (aov_delta / k_a.aov * 100) if k_a.aov > 0 else 0.0

margin_delta = k_b.net_margin_proxy - k_a.net_margin_proxy
margin_pct = (margin_delta / k_a.net_margin_proxy * 100) if k_a.net_margin_proxy > 0 else 0.0

status_class = "status-green" if margin_delta >= 0 else "status-red"
status_sym = "▲" if margin_delta >= 0 else "▼"

# -----------------------------------------------------------------------------
# Header Bar (Matching DocMind Layout)
# -----------------------------------------------------------------------------
col_head_left, col_head_right = st.columns([3.0, 2.0], gap="medium")
with col_head_left:
    st.markdown('<div class="main-title">Metricsbridge AI: Commercial RCA Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Enterprise Commercial Root Cause Analysis with Price-Volume-Mix Decomposition, '
        'Regional Logistics Diagnostics, and Groq-Powered Executive Briefing.</div>',
        unsafe_allow_html=True,
    )
with col_head_right:
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: flex-end; justify-content: flex-start; gap: 6px; padding-top: 2px;">
            <div style="display: flex; gap: 8px; align-items: center; justify-content: flex-end;">
                <div class="status-pill {status_class}">
                    <span>{status_sym} Net Margin {margin_pct:+.1f}%</span>
                </div>
            </div>
            <div class="period-pill">
                <span>Baseline: <b>{period_a}</b> → Compare: <b>{period_b}</b></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Top Metric Cards (4 Equal-Width Cards)
# -----------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4, gap="medium")

with c1:
    tag = "delta-pos" if rev_delta >= 0 else "delta-neg"
    sym = "+" if rev_delta >= 0 else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Gross Revenue</div>
            <div class="metric-value">R$ {k_b.total_revenue:,.0f}</div>
            <div class="metric-footer">
                <span>vs R$ {k_a.total_revenue:,.0f}</span>
                <span class="metric-delta-pill {tag}">{sym}{rev_pct:.1f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    tag = "delta-pos" if ord_delta >= 0 else "delta-neg"
    sym = "+" if ord_delta >= 0 else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Delivered Orders</div>
            <div class="metric-value">{k_b.total_orders:,}</div>
            <div class="metric-footer">
                <span>vs {k_a.total_orders:,}</span>
                <span class="metric-delta-pill {tag}">{sym}{ord_pct:.1f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    tag = "delta-pos" if aov_delta >= 0 else "delta-neg"
    sym = "+" if aov_delta >= 0 else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Average Order Value</div>
            <div class="metric-value">R$ {k_b.aov:.2f}</div>
            <div class="metric-footer">
                <span>vs R$ {k_a.aov:.2f}</span>
                <span class="metric-delta-pill {tag}">{sym}{aov_pct:.1f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    tag = "delta-pos" if margin_delta >= 0 else "delta-neg"
    sym = "+" if margin_delta >= 0 else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Net Margin Proxy</div>
            <div class="metric-value">R$ {k_b.net_margin_proxy:,.0f}</div>
            <div class="metric-footer">
                <span>vs R$ {k_a.net_margin_proxy:,.0f}</span>
                <span class="metric-delta-pill {tag}">{sym}{margin_pct:.1f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------------------------
# Full-Width Executive Strategy Briefing
# -----------------------------------------------------------------------------
cache_key = f"{period_a}_{period_b}_{active_model}_{custom_inquiry}_{top_n}"
if "briefing_cache" not in st.session_state:
    st.session_state.briefing_cache = {}

if cache_key not in st.session_state.briefing_cache or run_button:
    with st.spinner("Synthesizing strategic briefing via Groq..."):
        raw_briefing = generate_executive_briefing(
            report=report,
            api_key=groq_api_key,
            model=active_model,
            custom_focus=custom_inquiry,
        )
        st.session_state.briefing_cache[cache_key] = raw_briefing
else:
    raw_briefing = st.session_state.briefing_cache[cache_key]

# 3 Horizontal Pill Metrics
vol_class = "pill-vol" if b.volume_effect >= 0 else "pill-pri"
pri_class = "pill-vol" if b.price_effect >= 0 else "pill-pri"
frt_class = "pill-vol" if b.freight_effect >= 0 else "pill-frt"

briefing_html_content = format_briefing_to_html(raw_briefing)

st.markdown(
    f"""
    <div class="briefing-container">
        <div class="briefing-header">
            <div class="briefing-title-wrap">
                <span class="briefing-title">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="#38BDF8" style="vertical-align: -2px; margin-right: 4px;"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
                    Executive Strategy Briefing
                </span>
            </div>
            <div class="pvm-pill-row">
                <div class="pvm-pill {vol_class}">
                    <span class="pvm-pill-label">Volume Effect</span>
                    <span class="pvm-pill-val">R$ {b.volume_effect:+,.0f}</span>
                </div>
                <div class="pvm-pill {pri_class}">
                    <span class="pvm-pill-label">Price Effect</span>
                    <span class="pvm-pill-val">R$ {b.price_effect:+,.0f}</span>
                </div>
                <div class="pvm-pill {frt_class}">
                    <span class="pvm-pill-label">Freight Drag</span>
                    <span class="pvm-pill-val">R$ {b.freight_effect:+,.0f}</span>
                </div>
            </div>
        </div>
        <div class="briefing-body">
            {briefing_html_content}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Deep-Dive Section: Underline Tabs with Multi-Format Visual Switchers
# -----------------------------------------------------------------------------
tab_waterfall, tab_categories, tab_geo = st.tabs([
    "📊 PVM Margin Bridge",
    "📦 Category Drivers (What)",
    "🗺️ Geographic Breakdown (Where)",
])

# -----------------------------------------------------------------------------
# TAB 1: PVM MARGIN BRIDGE
# -----------------------------------------------------------------------------
with tab_waterfall:
    tab1_view = st.radio(
        "Bridge View Format",
        ["Waterfall Bridge", "Component Contribution Bar"],
        horizontal=True,
        key="tab1_format_selector",
    )

    if tab1_view == "Waterfall Bridge":
        st.markdown(
            """
            <div class="tab-panel">
                <div class="tab-panel-header">
                    <div class="tab-panel-title">Price-Volume-Mix (PVM) Variance Reconciliation</div>
                    <div class="tab-panel-tag">100% Mathematically Reconciled</div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        fig = go.Figure(
            go.Waterfall(
                name="Net Margin Variance",
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=[
                    f"Baseline Margin ({period_a})",
                    "Volume Effect",
                    "Price Effect",
                    "Freight Effect",
                    f"Comparison Margin ({period_b})",
                ],
                textposition="outside",
                text=[
                    f"R$ {b.baseline_margin:,.0f}",
                    f"{b.volume_effect:+,.0f}",
                    f"{b.price_effect:+,.0f}",
                    f"{b.freight_effect:+,.0f}",
                    f"R$ {b.comparison_margin:,.0f}",
                ],
                y=[
                    b.baseline_margin,
                    b.volume_effect,
                    b.price_effect,
                    b.freight_effect,
                    b.comparison_margin,
                ],
                width=[0.45, 0.45, 0.45, 0.45, 0.45],
                connector={"line": {"color": "#374151", "width": 1.5, "dash": "dot"}},
                increasing={"marker": {"color": "#10B981"}},
                decreasing={"marker": {"color": "#F43F5E"}},
                totals={"marker": {"color": "#3B82F6"}},
                hovertemplate="<b>%{x}</b><br>Impact: R$ %{y:,.2f}<extra></extra>",
            )
        )

        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                tickfont=dict(color="#9CA3AF", size=12, family="Inter"),
                showgrid=False,
            ),
            yaxis=dict(
                title=dict(text="Net Margin Proxy (BRL R$)", font=dict(color="#6B7280", size=12)),
                tickfont=dict(color="#6B7280", size=11),
                showgrid=True,
                gridcolor="#1F2937",
            ),
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            f"""
            <div style="font-size: 0.8rem; color: #9CA3AF; border-top: 1px solid #1F2937; padding-top: 0.85rem; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                <span>Volume Effect: <b style="color:#10B981;">R$ {b.volume_effect:+,.2f}</b></span>
                <span>Price Effect: <b style="color:{'#10B981' if b.price_effect >= 0 else '#F43F5E'};">R$ {b.price_effect:+,.2f}</b></span>
                <span>Freight Drag: <b style="color:{'#10B981' if b.freight_effect >= 0 else '#F43F5E'};">R$ {b.freight_effect:+,.2f}</b></span>
                <span>Net Margin Delta: <b style="color:#3B82F6;">R$ {b.net_margin_delta:+,.2f}</b></span>
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        # Component Contribution Bar View
        st.markdown(
            """
            <div class="tab-panel">
                <div class="tab-panel-header">
                    <div class="tab-panel-title">PVM Variance Component Breakdown</div>
                    <div class="tab-panel-tag">Comparative Contribution</div>
                </div>
            """,
            unsafe_allow_html=True,
        )

        comp_names = ["Volume Effect", "Price Effect", "Freight Drag", "Total Net Delta"]
        comp_vals = [b.volume_effect, b.price_effect, b.freight_effect, b.net_margin_delta]
        comp_colors = [
            "#10B981" if b.volume_effect >= 0 else "#F43F5E",
            "#10B981" if b.price_effect >= 0 else "#F43F5E",
            "#10B981" if b.freight_effect >= 0 else "#F43F5E",
            "#3B82F6",
        ]

        bar_comp = go.Figure(
            go.Bar(
                x=comp_vals,
                y=comp_names,
                orientation="h",
                marker_color=comp_colors,
                text=[f"R$ {v:+,.0f}" for v in comp_vals],
                textposition="auto",
                hovertemplate="<b>%{y}</b><br>Value: R$ %{x:,.2f}<extra></extra>",
            )
        )
        bar_comp.update_layout(
            height=340,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#1F2937", title=dict(text="Impact (BRL R$)", font=dict(color="#6B7280", size=11))),
            yaxis=dict(autorange="reversed", tickfont=dict(color="#D1D5DB", size=11)),
        )
        st.plotly_chart(bar_comp, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 2: CATEGORY DRIVERS ("WHAT")
# -----------------------------------------------------------------------------
with tab_categories:
    tab2_view = st.radio(
        "Category View Format",
        ["Impact Bar Chart", "Treemap / Distribution", "Data Table"],
        horizontal=True,
        key="tab2_format_selector",
    )

    all_movers = report.top_category_drivers + report.top_category_detractors

    if tab2_view == "Impact Bar Chart":
        if all_movers:
            mover_names = [m.name.replace("_", " ").title() for m in all_movers]
            mover_deltas = [m.delta_val for m in all_movers]
            mover_colors = ["#10B981" if val >= 0 else "#F43F5E" for val in mover_deltas]

            cat_fig = go.Figure(
                go.Bar(
                    x=mover_deltas,
                    y=mover_names,
                    orientation="h",
                    marker_color=mover_colors,
                    text=[f"R$ {v:+,.0f}" for v in mover_deltas],
                    textposition="auto",
                    hovertemplate="<b>%{y}</b><br>Net Margin Delta: R$ %{x:,.2f}<extra></extra>",
                )
            )
            cat_fig.update_layout(
                title=dict(text="Net Margin Delta Across Key Categories", font=dict(color="#F9FAFB", size=13)),
                height=340,
                margin=dict(l=10, r=10, t=35, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#1F2937", title=dict(text="Margin Delta (BRL R$)", font=dict(color="#6B7280", size=11))),
                yaxis=dict(autorange="reversed", tickfont=dict(color="#D1D5DB", size=11)),
            )
            st.plotly_chart(cat_fig, use_container_width=True)

    elif tab2_view == "Treemap / Distribution":
        if all_movers:
            t_labels = ["Categories"] + [m.name.replace("_", " ").title() for m in all_movers]
            t_parents = [""] + ["Categories"] * len(all_movers)
            t_values = [sum(max(0.1, m.comparison_val) for m in all_movers)] + [max(0.1, m.comparison_val) for m in all_movers]
            t_colors = [0] + [m.delta_val for m in all_movers]

            treemap_fig = go.Figure(
                go.Treemap(
                    labels=t_labels,
                    parents=t_parents,
                    values=t_values,
                    marker=dict(
                        colors=t_colors,
                        colorscale=[[0, "#F43F5E"], [0.5, "#334155"], [1, "#10B981"]],
                        cmid=0,
                        showscale=True,
                        colorbar=dict(title=dict(text="Margin Delta (R$)", font=dict(color="#9CA3AF")), tickfont=dict(color="#9CA3AF")),
                    ),
                    hovertemplate="<b>%{label}</b><br>Margin: R$ %{value:,.0f}<extra></extra>",
                )
            )
            treemap_fig.update_layout(
                height=360,
                margin=dict(l=10, r=10, t=20, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(treemap_fig, use_container_width=True)

    else:
        # Data Table View
        c_w1, c_w2 = st.columns(2, gap="medium")

        with c_w1:
            st.markdown(
                """
                <div class="tab-panel">
                    <div class="tab-panel-header">
                        <div class="tab-panel-title"><span style="color:#10B981;">▲</span> Top Margin Drivers</div>
                        <div class="tab-panel-tag">Expansion Contributors</div>
                    </div>
                """,
                unsafe_allow_html=True,
            )
            if report.top_category_drivers:
                drivers_rows = [
                    {
                        "Category": d.name.replace("_", " ").title(),
                        "Baseline Margin": f"R$ {d.baseline_val:,.2f}",
                        "Comparison Margin": f"R$ {d.comparison_val:,.2f}",
                        "Margin Delta": f"R$ {d.delta_val:+,.2f}",
                        "Growth": f"{d.pct_change:+.1f}%",
                    }
                    for d in report.top_category_drivers
                ]
                headers = ["Category", "Baseline Margin", "Comparison Margin", "Margin Delta", "Growth"]
                aligns = {
                    "Category": "left",
                    "Baseline Margin": "right",
                    "Comparison Margin": "right",
                    "Margin Delta": "right",
                    "Growth": "right",
                }
                st.markdown(render_executive_table(headers, drivers_rows, aligns), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c_w2:
            st.markdown(
                """
                <div class="tab-panel">
                    <div class="tab-panel-header">
                        <div class="tab-panel-title"><span style="color:#F43F5E;">▼</span> Top Margin Detractors</div>
                        <div class="tab-panel-tag">Margin Contraction</div>
                    </div>
                """,
                unsafe_allow_html=True,
            )
            if report.top_category_detractors:
                detractors_rows = [
                    {
                        "Category": d.name.replace("_", " ").title(),
                        "Baseline Margin": f"R$ {d.baseline_val:,.2f}",
                        "Comparison Margin": f"R$ {d.comparison_val:,.2f}",
                        "Margin Delta": f"R$ {d.delta_val:+,.2f}",
                        "Growth": f"{d.pct_change:+.1f}%",
                    }
                    for d in report.top_category_detractors
                ]
                headers = ["Category", "Baseline Margin", "Comparison Margin", "Margin Delta", "Growth"]
                aligns = {
                    "Category": "left",
                    "Baseline Margin": "right",
                    "Comparison Margin": "right",
                    "Margin Delta": "right",
                    "Growth": "right",
                }
                st.markdown(render_executive_table(headers, detractors_rows, aligns), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# TAB 3: GEOGRAPHIC BREAKDOWN ("WHERE")
# -----------------------------------------------------------------------------
with tab_geo:
    tab3_view = st.radio(
        "Geographic View Format",
        ["Ranked Bar Chart", "Share Table"],
        horizontal=True,
        key="tab3_format_selector",
    )

    if tab3_view == "Ranked Bar Chart":
        # 5 Macro-Region Cards
        r_cols = st.columns(5, gap="medium")
        for idx, reg in enumerate(report.regional_performance):
            with r_cols[idx]:
                if reg.status_signal == "Expansion Driver":
                    status_html = '<span style="color:#34D399; font-weight:600; font-size:0.7rem;">● Expansion</span>'
                elif "Focus" in reg.status_signal:
                    status_html = '<span style="color:#FBBF24; font-weight:600; font-size:0.7rem;">● Margin Drag</span>'
                elif "Contraction" in reg.status_signal:
                    status_html = '<span style="color:#FB7185; font-weight:600; font-size:0.7rem;">● Contracting</span>'
                else:
                    status_html = '<span style="color:#9CA3AF; font-weight:600; font-size:0.7rem;">● Stable</span>'

                growth_color = "#34D399" if reg.revenue_growth_pct >= 0 else "#FB7185"
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(180deg, #161F2E 0%, #111724 100%); border: 1.5px solid #28374E; border-radius: 10px; padding: 0.95rem; text-align: left; margin-bottom: 0.75rem; box-shadow: 0 4px 14px rgba(0,0,0,0.35);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.45rem;">
                            <span style="font-weight:700; font-size:0.86rem; color:#F9FAFB;">{reg.region}</span>
                            {status_html}
                        </div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.15rem; font-weight:700; color:#FFFFFF; margin-bottom:0.2rem;">R$ {reg.comparison_revenue:,.0f}</div>
                        <div style="font-size: 0.74rem; color: {growth_color}; font-weight:600; margin-bottom:0.45rem;">{reg.revenue_growth_pct:+.1f}% vs baseline</div>
                        <div style="font-size: 0.72rem; color: #64748B; border-top:1px solid #202D42; padding-top:0.35rem;">
                            Sales Share: <b style="color:#D1D5DB;">{reg.comparison_share_pct:.1f}%</b><br>
                            Freight Burden: <b style="color:{'#FB7185' if reg.freight_burden_pct >= 20 else '#D1D5DB'};">{reg.freight_burden_pct:.1f}%</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # 2 Charts side by side
        rc1, rc2 = st.columns(2, gap="medium")

        with rc1:
            st.markdown(
                """
                <div class="tab-panel">
                    <div class="tab-panel-header">
                        <div class="tab-panel-title">Regional Gross Revenue Comparison</div>
                    </div>
                """,
                unsafe_allow_html=True,
            )
            reg_names = [r.region for r in report.regional_performance]
            rev_a_vals = [r.baseline_revenue for r in report.regional_performance]
            rev_b_vals = [r.comparison_revenue for r in report.regional_performance]

            b_fig = go.Figure()
            b_fig.add_trace(go.Bar(name=f"Baseline ({period_a})", x=reg_names, y=rev_a_vals, marker_color="#374151"))
            b_fig.add_trace(go.Bar(name=f"Comparison ({period_b})", x=reg_names, y=rev_b_vals, marker_color="#3B82F6"))
            b_fig.update_layout(
                barmode="group",
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#1F2937", tickfont=dict(color="#D1D5DB", size=10)),
                yaxis=dict(gridcolor="#1F2937", tickfont=dict(color="#6B7280", size=10)),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#9CA3AF", size=10)),
            )
            st.plotly_chart(b_fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with rc2:
            st.markdown(
                """
                <div class="tab-panel">
                    <div class="tab-panel-header">
                        <div class="tab-panel-title">Regional Freight Burden (% of Revenue)</div>
                    </div>
                """,
                unsafe_allow_html=True,
            )
            freight_burdens = [r.freight_burden_pct for r in report.regional_performance]
            b_colors = ["#F43F5E" if fb >= 20.0 else ("#FBBF24" if fb >= 15.0 else "#10B981") for fb in freight_burdens]

            f_fig = go.Figure(
                go.Bar(
                    x=reg_names,
                    y=freight_burdens,
                    marker_color=b_colors,
                    text=[f"{fb:.1f}%" for fb in freight_burdens],
                    textposition="outside",
                )
            )
            f_fig.add_hline(
                y=20.0,
                line_dash="dash",
                line_color="#F43F5E",
                annotation_text="20% Logistics Drag Warning Line",
                annotation_font=dict(color="#FB7185", size=9),
            )
            f_fig.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#1F2937", tickfont=dict(color="#D1D5DB", size=10)),
                yaxis=dict(gridcolor="#1F2937", tickfont=dict(color="#6B7280", size=10)),
            )
            st.plotly_chart(f_fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Share Table View
        st.markdown(
            """
            <div class="tab-panel">
                <div class="tab-panel-header">
                    <div class="tab-panel-title">Macro-Regional Commercial Share & Logistics Drag</div>
                    <div class="tab-panel-tag">IBGE Macro-Regions</div>
                </div>
            """,
            unsafe_allow_html=True,
        )
        reg_rows = [
            {
                "Region": r.region,
                f"Revenue ({period_a})": f"R$ {r.baseline_revenue:,.2f}",
                f"Revenue ({period_b})": f"R$ {r.comparison_revenue:,.2f}",
                "Delta (R$)": f"R$ {r.revenue_delta:+,.2f}",
                "Growth": f"{r.revenue_growth_pct:+.1f}%",
                "Sales Share": f"{r.comparison_share_pct:.1f}%",
                "Freight Burden": f"{r.freight_burden_pct:.1f}%",
                "Strategic Focus": r.status_signal,
            }
            for r in report.regional_performance
        ]
        reg_headers = [
            "Region",
            f"Revenue ({period_a})",
            f"Revenue ({period_b})",
            "Delta (R$)",
            "Growth",
            "Sales Share",
            "Freight Burden",
            "Strategic Focus",
        ]
        reg_aligns = {
            "Region": "left",
            f"Revenue ({period_a})": "right",
            f"Revenue ({period_b})": "right",
            "Delta (R$)": "right",
            "Growth": "right",
            "Sales Share": "right",
            "Freight Burden": "right",
            "Strategic Focus": "center",
        }
        st.markdown(render_executive_table(reg_headers, reg_rows, reg_aligns), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="tab-panel">
                <div class="tab-panel-header">
                    <div class="tab-panel-title">State-Level Performance Breakdown</div>
                    <div class="tab-panel-tag">Top Movers</div>
                </div>
            """,
            unsafe_allow_html=True,
        )
        all_states = report.top_state_growers + report.top_state_decliners
        state_rows = [
            {
                "State": s.name,
                f"Revenue ({period_a})": f"R$ {s.baseline_val:,.2f}",
                f"Revenue ({period_b})": f"R$ {s.comparison_val:,.2f}",
                "Revenue Delta": f"R$ {s.delta_val:+,.2f}",
                "Growth (%)": f"{s.pct_change:+.1f}%",
            }
            for s in all_states
        ]
        state_headers = ["State", f"Revenue ({period_a})", f"Revenue ({period_b})", "Revenue Delta", "Growth (%)"]
        state_aligns = {
            "State": "left",
            f"Revenue ({period_a})": "right",
            f"Revenue ({period_b})": "right",
            "Revenue Delta": "right",
            "Growth (%)": "right",
        }
        st.markdown(render_executive_table(state_headers, state_rows, state_aligns), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Grounded Metrics Conversational Copilot
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="copilot-section">
        <div class="copilot-header">
            <span style="font-size: 1.2rem;">💬</span>
            <span class="copilot-title">Metric Copilot</span>
        </div>
        <div class="copilot-subtitle">
            Grounded commercial finance AI assistant. Explores PVM drivers, regional logistics, and live product-level fact table queries.
        </div>
        <div class="copilot-guide-box">
            <div class="copilot-guide-title">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="#38BDF8"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
                <span>What kind of questions you can ask:</span>
            </div>
            <div class="copilot-guide-grid">
                <div class="copilot-guide-chip">
                    <strong>📊 PVM Math & Variance</strong>
                    <span>"Why did net margin contract?"<br>"Price vs volume effect?"</span>
                </div>
                <div class="copilot-guide-chip">
                    <strong>🗺️ Regional Products & Sales</strong>
                    <span>"What products sold in South & turnover?"<br>"Top categories in São Paulo"</span>
                </div>
                <div class="copilot-guide-chip">
                    <strong>📦 Category Movers</strong>
                    <span>"Top margin contributor categories"<br>"Primary category detractors"</span>
                </div>
                <div class="copilot-guide-chip">
                    <strong>🚚 Freight Logistics Drag</strong>
                    <span>"Which states had highest freight burden?"<br>"How did AOV shift?"</span>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Interactive 1-Click Suggestion Chips
col_chip1, col_chip2, col_chip3, col_chip4 = st.columns(4)
with col_chip1:
    if st.button("🗺️ South Products & Turnover", key="chip_south", use_container_width=True):
        st.session_state.pending_query = "What are the products sold in the South and their total turnover per product?"
with col_chip2:
    if st.button("📊 Price vs Volume Effect", key="chip_pvm", use_container_width=True):
        st.session_state.pending_query = "What was the price effect versus volume effect between baseline and comparison periods?"
with col_chip3:
    if st.button("📦 Top Category Drivers", key="chip_cat", use_container_width=True):
        st.session_state.pending_query = "Which product categories contributed the most to net margin expansion?"
with col_chip4:
    if st.button("🚚 High Freight Burden States", key="chip_frt", use_container_width=True):
        st.session_state.pending_query = "Which Brazilian states had the highest freight burden rate?"

st.markdown("<div style='margin-top: 0.5rem;'>", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": (
                f"Hello! I am your **Metricsbridge AI Copilot** for the **{period_a} ➔ {period_b}** comparison. "
                "Ask me any question about revenue, PVM effects, freight logistics drag, or category and regional performance."
            ),
        }
    ]

# Render chat history inline
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.markdown("</div>", unsafe_allow_html=True)

# Docked, width-constrained chat input at the bottom of the viewport
CHAT_COOLDOWN_SECONDS = 30
if "last_chat_timestamp" not in st.session_state:
    st.session_state.last_chat_timestamp = 0.0

user_query = st.chat_input("Ask any question or drill down (e.g., 'What are the products sold in South and their turnover?')")

# Determine if query came from text input or 1-click suggestion chip
active_query = None
if "pending_query" in st.session_state and st.session_state.pending_query:
    active_query = st.session_state.pop("pending_query")
elif user_query:
    active_query = user_query

if active_query:
    from src.ai_advisor import is_query_in_context
    in_scope, intent = is_query_in_context(active_query)

    # 1. Zero-API Guard: Handle greetings and out-of-context queries without hitting LLM or consuming cooldown
    if intent == "greeting" or not in_scope:
        reply = ask_metric_copilot(
            query=active_query,
            report=report,
            chat_history=st.session_state.chat_history[:-1],
            api_key=groq_api_key,
            model=active_model,
            engine=engine,
        )
        st.session_state.chat_history.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)
        with st.chat_message("assistant"):
            st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

        if not in_scope:
            st.toast("⚠️ Out-of-context query intercepted locally. Zero API tokens used.", icon="🛡️")

    # 2. In-Scope Commercial Query: Protected by 30-second rate limiter
    else:
        current_time = time.time()
        elapsed = current_time - st.session_state.last_chat_timestamp

        if elapsed < CHAT_COOLDOWN_SECONDS:
            remaining_secs = int(CHAT_COOLDOWN_SECONDS - elapsed) + 1
            st.toast(f"⏳ Rate limit: Please wait {remaining_secs}s before asking another question.", icon="⚠️")
            st.warning(
                f"⏱️ **Rate Limit Active**: Live AI queries are limited to once every 30 seconds to prevent spam and conserve API tokens. "
                f"Please wait **{remaining_secs}s** before submitting your next question."
            )
        else:
            st.session_state.last_chat_timestamp = current_time

            # Display user prompt
            st.session_state.chat_history.append({"role": "user", "content": active_query})
            with st.chat_message("user"):
                st.markdown(active_query)

            # Generate assistant grounded response
            with st.chat_message("assistant"):
                with st.spinner("Analyzing metrics payload & data dimensions..."):
                    reply = ask_metric_copilot(
                        query=active_query,
                        report=report,
                        chat_history=st.session_state.chat_history[:-1],
                        api_key=groq_api_key,
                        model=active_model,
                        engine=engine,
                    )
                    st.markdown(reply)

            # Save reply to history
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
