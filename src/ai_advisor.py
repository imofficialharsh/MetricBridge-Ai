"""
src/ai_advisor.py
Groq Executive Briefing Layer.
Transforms structured RootCauseReport payloads into concise,
grounded C-suite financial intelligence using Groq's low-latency API.
"""

import json
import os
from typing import Optional
from groq import Groq

from src.schema import RootCauseReport

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def generate_deterministic_fallback(report: RootCauseReport) -> str:
    """
    Generates a deterministic financial summary directly from the RootCauseReport
    when no Groq API Key is supplied.
    """
    b = report.variance_bridge
    k_a = report.baseline_kpi
    k_b = report.comparison_kpi

    margin_direction = "expanded" if b.net_margin_delta >= 0 else "contracted"
    rev_direction = "rose" if b.revenue_delta >= 0 else "fell"

    # Identify primary driver among Volume, Price, Freight
    effects = {
        "sales volume change": abs(b.volume_effect),
        "realized pricing shifts": abs(b.price_effect),
        "freight logistics costs": abs(b.freight_effect),
    }
    primary_driver = max(effects, key=effects.get)

    top_cat = report.top_category_drivers[0].name if report.top_category_drivers else "N/A"
    top_cat_delta = report.top_category_drivers[0].delta_val if report.top_category_drivers else 0.0
    det_cat = report.top_category_detractors[0].name if report.top_category_detractors else "N/A"
    det_cat_delta = report.top_category_detractors[0].delta_val if report.top_category_detractors else 0.0

    top_region = report.regional_performance[0].region if report.regional_performance else "N/A"
    top_region_growth = report.regional_performance[0].revenue_growth_pct if report.regional_performance else 0.0

    return f"""### 1. Executive TL;DR
Net margin proxy {margin_direction} by **R$ {abs(b.net_margin_delta):,.2f}** ({((k_b.net_margin_proxy - k_a.net_margin_proxy) / k_a.net_margin_proxy * 100):+.1f}%) from **{report.baseline_period}** to **{report.comparison_period}**, while gross revenue {rev_direction} by **R$ {abs(b.revenue_delta):,.2f}**. The overarching variance was primarily driven by **{primary_driver}** (Volume Effect: R$ {b.volume_effect:+,.2f}, Price Effect: R$ {b.price_effect:+,.2f}, Freight Effect: R$ {b.freight_effect:+,.2f}).

### 2. Key Drivers & Detractors (What)
- **Top Margin Contributor**: `{top_cat}` delivered an incremental **R$ {top_cat_delta:+,.2f}** in net margin.
- **Primary Detractor**: `{det_cat}` caused margin drag of **R$ {det_cat_delta:+,.2f}**.
- **Average Realized Price**: Moved from **R$ {k_a.avg_item_price:.2f}** to **R$ {k_b.avg_item_price:.2f}** per unit.

### 3. Regional Momentum & Geographic Focus (Where)
- **Primary Volume Engine**: The **{top_region}** region led sales performance with **{top_region_growth:+.1f}%** revenue growth.
- **Logistics Drag**: Shipping charges totaled **R$ {k_b.total_freight:,.2f}**, representing **{(k_b.total_freight / k_b.total_revenue * 100):.1f}%** of gross merchandise sales.

### 4. Recommended Tactical Actions
1. **Capitalize on Category Momentum**: Protect inventory allocation and promotional calendar for top expanding categories (`{top_cat}`).
2. **Logistics Optimization**: Conduct a freight cost audit for long-haul routes to mitigate margin dilution.

---
*Generated via deterministic financial rules. Provide a valid Groq API Key in the sidebar for AI-synthesized strategic commentary.*"""


def generate_executive_briefing(
    report: RootCauseReport,
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
    custom_focus: Optional[str] = None,
) -> str:
    """
    Calls the Groq API to generate an executive-ready root cause analysis briefing.
    Adheres to strict financial grounding rules to avoid hallucination.
    """
    resolved_api_key = api_key or os.getenv("GROQ_API_KEY")
    if not resolved_api_key or not resolved_api_key.strip():
        return generate_deterministic_fallback(report)

    # Convert Pydantic model to clean JSON payload
    payload = report.model_dump()
    payload_json = json.dumps(payload, indent=2)

    system_instruction = (
        "You are a Senior Commercial Finance & Strategy Director at a major e-commerce enterprise. "
        "You are presenting an executive C-suite briefing analyzing the variance between Baseline Period A "
        "and Comparison Period B.\n\n"
        "STRICT GROUNDING RULES:\n"
        "1. Rely EXCLUSIVELY on the exact numerical values, percentages, and metrics provided in the JSON payload below.\n"
        "2. Do NOT invent, assume, or hallucinate any numbers or external market events.\n"
        "3. Do NOT perform independent recalculations; cite the exact precomputed figures.\n"
        "4. Keep the tone executive, objective, and financially rigorous.\n\n"
        "REQUIRED OUTPUT STRUCTURE:\n"
        "### 1. Executive TL;DR\n"
        "Exactly two concise sentences summarizing whether net margin and gross revenue expanded or contracted, "
        "and identifying the primary mathematical driver (Volume Effect, Price Effect, or Freight Cost Effect).\n\n"
        "### 2. Key Drivers & Detractors (What)\n"
        "Bullet points identifying the top category margin contributors and detractors with exact dollar deltas and percentages.\n\n"
        "### 3. Regional Momentum & Geographic Focus (Where to Focus)\n"
        "Bullet points detailing which Brazilian macro-regions (Southeast, South, Northeast, Central-West, North) "
        "and states demonstrated high sales expansion versus contraction or severe freight burden rates.\n\n"
        "### 4. Recommended Tactical Actions\n"
        "Exactly two concrete, operational decisions for management to execute immediately."
    )

    user_prompt = f"Analyze the following verified Root Cause Report payload:\n\n```json\n{payload_json}\n```"

    if custom_focus and custom_focus.strip():
        user_prompt += (
            f"\n\nAdditionally, please answer this executive inquiry strictly using the provided payload:\n"
            f"Question / Focus: {custom_focus.strip()}\n"
            f"Add a 5th section: '### 5. Executive Deep-Dive: {custom_focus.strip()}'"
        )

    try:
        client = Groq(api_key=resolved_api_key.strip())
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for strict factual adherence
            max_tokens=1024,
        )
        return response.choices[0].message.content or "No response generated."
    except Exception as e:
        fallback = generate_deterministic_fallback(report)
        return f"{fallback}\n\n> *Note: Groq API call failed ({str(e)}). Displayed deterministic financial summary instead.*"


def ask_metric_copilot(
    query: str,
    report: RootCauseReport,
    chat_history: list,
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
) -> str:
    """
    Handles conversational Q&A grounded strictly in the pre-calculated RootCauseReport data.
    """
    resolved_api_key = api_key or os.getenv("GROQ_API_KEY")
    if not resolved_api_key or not resolved_api_key.strip():
        return (
            "**Groq API Key Required**: Please enter your Groq API Key in the sidebar under "
            "`LLM Configuration` to chat with the Metric Copilot."
        )

    payload = report.model_dump()
    payload_json = json.dumps(payload, indent=2)

    system_instruction = (
        "You are MetricBridge Copilot, an expert AI analytics assistant embedded in an executive commercial decision platform.\n\n"
        "GROUNDED METRICS PAYLOAD (PRE-CALCULATED FINANCIAL METRICS):\n"
        f"```json\n{payload_json}\n```\n\n"
        "STRICT OPERATIONAL RULES:\n"
        "1. You MUST ONLY answer questions using the exact numbers, metrics, and dimensions present in the provided JSON payload.\n"
        "2. If a user asks about anything not covered in the data, or asks you to guess, forecast, or assume facts outside this report, respond EXACTLY:\n"
        "   \"I can only answer questions based on the computed metrics for the selected time window.\"\n"
        "3. Never speculate or hallucinate external market conditions, macroeconomics, or missing categories/states.\n"
        "4. Keep replies concise, factual, executive-friendly, and commercially focused.\n"
        "5. Always format currency figures clearly in Brazilian Reais (e.g., R$ 123,456.78)."
    )

    messages = [{"role": "system", "content": system_instruction}]

    # Append recent chat history (up to last 10 messages)
    for msg in chat_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Append current question
    messages.append({"role": "user", "content": query})

    try:
        client = Groq(api_key=resolved_api_key.strip())
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=800,
        )
        return response.choices[0].message.content or "No response received."
    except Exception as e:
        return f"*Error contacting Groq API:* {str(e)}"

