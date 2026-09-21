"""
src/ai_advisor.py
Groq Executive Briefing Layer.
Transforms structured RootCauseReport payloads into concise,
grounded C-suite financial intelligence using Groq's low-latency API.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
from groq import Groq

from src.schema import RootCauseReport

DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

# =============================================================================
# Zero-API-Cost Domain Heuristics & Guardrails
# =============================================================================
COMMERCIAL_DOMAIN_KEYWORDS = {
    # Financial & Business Metrics
    "revenue", "turnover", "sales", "margin", "margins", "profit", "profits", "price", "prices",
    "pricing", "volume", "volumes", "unit", "units", "quantity", "order", "orders", "freight",
    "shipping", "logistics", "cost", "costs", "aov", "ticket", "kpi", "kpis", "bridge", "pvm",
    "variance", "delta", "growth", "contraction", "expansion", "drag", "burden", "gross", "net",
    "performance", "contributor", "contributors", "detractor", "detractors", "driver", "drivers",
    "basket", "spend", "spending", "discount", "discounts", "share",
    # Geography
    "region", "regions", "state", "states", "city", "cities", "south", "southeast", "northeast",
    "central-west", "north", "sul", "sudeste", "nordeste", "centro-oeste", "norte", "brazil",
    "sp", "rj", "mg", "rs", "pr", "sc", "ba", "es", "go", "df", "pe", "ce", "pa",
    # Products & Categories
    "product", "products", "category", "categories", "item", "items", "sku", "skus", "goods",
    "merchandise", "sports", "leisure", "beauty", "health", "watches", "gifts", "bed", "bath",
    "table", "furniture", "decor", "computers", "accessories", "telephony", "toys", "baby",
    "auto", "pet", "housewares", "tools", "appliances", "electronics", "fashion", "stationery",
    # Time & Analytical Dimensions
    "period", "periods", "baseline", "comparison", "compare", "month", "months", "year", "years",
    "trend", "trends", "quarter", "october", "november", "december", "2017", "2018", "2016",
    "top", "bottom", "highest", "lowest", "rank", "ranking", "breakdown", "decompose", "analysis",
    "analyze", "mover", "movers", "drop", "fell", "rose", "increase", "decrease", "pct", "percent",
}

OUT_OF_CONTEXT_TRIGGERS = [
    r"\bcapital of\b", r"\bpresident of\b", r"\bprime minister\b", r"\btell me a joke\b",
    r"\bwrite a poem\b", r"\bwrite a song\b", r"\brecipe for\b", r"\bhow to bake\b",
    r"\bhow to cook\b", r"\bweather in\b", r"\bweather today\b", r"\bwho won\b",
    r"\bworld cup\b", r"\bmovie\b", r"\bwho is\b", r"\bwho was\b",
    r"\btranslate to\b", r"\bpython code\b", r"\bwrite code\b", r"\bhomework\b",
]

GREETING_TOKENS = {"hello", "hi", "hey", "help", "guide", "start", "greetings", "good morning", "good afternoon"}


def is_query_in_context(query: str) -> tuple[bool, str]:
    """
    Validates query domain relevance with zero-API-cost heuristics before contacting the LLM.
    Returns (in_scope, intent_category).
    """
    q_lower = query.lower().strip()
    if not q_lower:
        return False, "empty"

    # Check for simple greetings
    if q_lower in GREETING_TOKENS or any(q_lower.startswith(g) for g in ["hello", "hi ", "hey "]):
        return True, "greeting"

    # Check for hard out-of-scope triggers
    for trigger in OUT_OF_CONTEXT_TRIGGERS:
        if re.search(trigger, q_lower):
            has_strong_metric = any(m in q_lower for m in ["revenue", "margin", "pvm", "freight", "turnover", "aov"])
            if not has_strong_metric:
                return False, "out_of_context"

    tokens = set(re.findall(r"\b[a-z0-9_-]+\b", q_lower))
    matches = tokens.intersection(COMMERCIAL_DOMAIN_KEYWORDS)
    if len(matches) > 0:
        return True, "commercial_analytics"

    return False, "out_of_context"


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
*Generated via deterministic financial rules. Pre-configure GROQ_API_KEY in the backend environment for AI-synthesized strategic commentary.*"""


def _resolve_groq_api_key(passed_key: Optional[str] = None) -> str:
    """Resolves Groq API key checking arguments, environment, and Streamlit secrets."""
    if passed_key and str(passed_key).strip():
        return str(passed_key).strip()
    env_key = os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key")
    if env_key and str(env_key).strip():
        return str(env_key).strip()
    try:
        import streamlit as st
        for k in ["GROQ_API_KEY", "groq_api_key"]:
            if k in st.secrets and str(st.secrets[k]).strip():
                return str(st.secrets[k]).strip()
        for sec in ["groq", "general", "default"]:
            if sec in st.secrets and isinstance(st.secrets[sec], dict):
                sub = st.secrets[sec]
                found = sub.get("GROQ_API_KEY") or sub.get("groq_api_key") or sub.get("api_key")
                if found and str(found).strip():
                    return str(found).strip()
    except Exception:
        pass
    return ""


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
    resolved_api_key = _resolve_groq_api_key(api_key)
    if not resolved_api_key:
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


QUERY_COMMERCIAL_DATA_TOOL = {
    "type": "function",
    "function": {
        "name": "query_commercial_data",
        "description": (
            "Dynamically query the 110,000-row Brazilian e-commerce analytical fact table to answer granular questions "
            "about product categories, sales turnover, unit volumes, freight costs, regions, and states. "
            "Use this whenever the user asks for specific products, turnover by region (e.g. South), "
            "city/state performance, or dimensional breakdowns not present in the top-level summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Columns to group by. Available dimensions: "
                        "'category' (product_category_name_english), "
                        "'region' (customer_region: South, Southeast, Northeast, Central-West, North), "
                        "'state' (customer_state: SP, RJ, MG, RS, PR, SC, BA, etc.), 'city' (customer_city), "
                        "'period' (year_month: e.g. '2017-10', '2017-11'), 'year'."
                    ),
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Metrics to calculate: 'gross_revenue' (total sales turnover), 'units' (volume), "
                        "'orders' (order count), 'freight_cost', 'avg_item_price', 'aov', 'net_margin_proxy'."
                    ),
                },
                "filters": {
                    "type": "object",
                    "description": (
                        "Optional key-value filters. Example: {'region': 'South'} or "
                        "{'region': 'South', 'period': '2017-11'} or {'category': 'sports_leisure'} or {'state': 'SP'}."
                    ),
                },
                "order_by": {
                    "type": "string",
                    "description": "Metric to sort descending by (e.g. 'gross_revenue' or 'units').",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return (default 10, max 15).",
                },
            },
            "required": ["group_by", "metrics"],
        },
    },
}


def ask_metric_copilot(
    query: str,
    report: RootCauseReport,
    chat_history: list,
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
    engine: Optional[Any] = None,
) -> str:
    """
    Handles conversational Q&A grounded in pre-calculated RootCauseReport data
    and equipped with dynamic Polars fact table querying for granular commercial inquiries.
    Guarantees direct business answers and tables without outputting SQL code.
    """
    clean_q = query.strip()
    in_scope, intent = is_query_in_context(clean_q)

    # Fast Zero-API Guard for Greetings
    if intent == "greeting":
        return (
            f"👋 **Hello!** I am your **Metricsbridge AI Copilot** for the **{report.baseline_period} ➔ {report.comparison_period}** analysis window.\n\n"
            "You can ask me questions about:\n"
            "- **Root Cause & PVM Math**: *'Why did net margin contract?'*, *'What was the volume effect vs price effect?'*\n"
            "- **Granular Products & Regions**: *'What are the products sold in the South and their turnover?'*\n"
            "- **Logistics Drag**: *'Which states had the highest freight burden?'*\n"
            "- **Category Performance**: *'Which categories contributed the most to margin expansion?'*\n\n"
            "What commercial inquiry would you like to explore?"
        )

    # Fast Zero-API Guard for Out-of-Context Questions
    if not in_scope:
        return (
            "⚠️ **Out of Context Inquiry (Zero-API Guard)**\n\n"
            "Your question appears to be outside the scope of commercial revenue, variance decomposition, "
            "and e-commerce analytics. To save API costs and protect model quotas, this request was "
            "intercepted locally without contacting the AI model.\n\n"
            "**What you can ask Metric Copilot:**\n"
            "- **PVM Variance**: *'Why did net margin contract?'*, *'What was the price vs volume effect?'*\n"
            "- **Granular Products & Regions**: *'What are the products sold in the South and their turnover?'*, *'Top categories in São Paulo'*\n"
            "- **Logistics & Freight**: *'Which states had the highest freight burden?'*, *'Total freight cost in 2017-11'*\n"
            "- **Commercial KPIs**: *'How did AOV shift between baseline and compare periods?'*\n\n"
            "*Please submit a commercial analytics or metric-related question!*"
        )

    resolved_api_key = _resolve_groq_api_key(api_key)
    if not resolved_api_key:
        return (
            "⚠️ **Groq API Key Required**: A valid Groq API Key was not detected in the deployment environment.\n\n"
            "**To enable live AI Copilot:**\n"
            "1. In **Streamlit Cloud**: Click **Manage app** (bottom-right) ➔ **⋮ ➔ Settings ➔ Secrets**, and add:\n"
            "   ```toml\n"
            "   GROQ_API_KEY = \"gsk_your_key_here\"\n"
            "   ```\n"
            "2. **Or directly in the sidebar**: Enter your Groq API Key in the sidebar under **🔑 Groq AI Key Setup**."
        )


    payload = report.model_dump()
    payload_json = json.dumps(payload, indent=2)

    system_instruction = (
        "You are Metricsbridge AI Copilot, an expert Commercial Finance & Analytics Director embedded in an enterprise decision platform.\n\n"
        f"TIME WINDOW CONTEXT:\n"
        f"- Baseline Period (A): {report.baseline_period}\n"
        f"- Comparison Period (B): {report.comparison_period}\n\n"
        "HIGH-LEVEL ROOT CAUSE REPORT PAYLOAD:\n"
        f"```json\n{payload_json}\n```\n\n"
        "OPERATIONAL INSTRUCTIONS & STRICT RULES:\n"
        "1. NEVER output SQL queries, Python scripts, database schemas, or instructions on how to write code. "
        "The user is a business executive who expects direct, clear commercial answers and data tables, NOT SQL code.\n"
        "2. If the user asks for specific products, categories, turnover, unit counts, or sales by region/state/city, "
        "ALWAYS execute the `query_commercial_data` function tool to retrieve the actual numbers, and summarize them directly in clean markdown tables.\n"
        "3. NEVER guess, estimate, or hallucinate numbers. Rely strictly on the summary JSON or tool query results.\n"
        "4. Format all currency figures in Brazilian Reais (e.g., R$ 123,456.78) and format large numbers with commas.\n"
        "5. Keep responses executive, structured, concise, and actionable using markdown tables or bullet points."
    )

    messages = [{"role": "system", "content": system_instruction}]

    # Append recent chat history (up to last 8 messages)
    for msg in chat_history[-8:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Append current question
    messages.append({"role": "user", "content": query})

    has_engine = engine is not None and hasattr(engine, "query_fact_table")
    tools = [QUERY_COMMERCIAL_DATA_TOOL] if has_engine else None

    # Detect if query asks for dimensional breakdown requiring tool execution
    ql = clean_q.lower()
    tool_triggers = [
        "product", "products", "item", "items", "turnover", "sold in",
        "south", "north", "southeast", "northeast", "central",
        "city", "cities", "by state", "per product", "category in", "categories in",
        "highest selling", "top selling", "sales in", "ranking", "rank", "list",
        "who sold", "how much sold"
    ]
    needs_data_tool = any(t in ql for t in tool_triggers)

    try:
        client = Groq(api_key=resolved_api_key.strip())
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
        }
        if tools:
            kwargs["tools"] = tools
            if needs_data_tool:
                kwargs["tool_choice"] = {"type": "function", "function": {"name": "query_commercial_data"}}
                kwargs["max_tokens"] = 250
            else:
                kwargs["tool_choice"] = "auto"
                kwargs["max_tokens"] = 650
        else:
            kwargs["max_tokens"] = 650

        response = client.chat.completions.create(**kwargs)
        response_msg = response.choices[0].message

        # Handle tool calling if requested or forced
        if response_msg.tool_calls and tools:
            messages.append(response_msg)
            for tool_call in response_msg.tool_calls:
                fn_name = tool_call.function.name
                if fn_name == "query_commercial_data":
                    try:
                        raw_args = json.loads(tool_call.function.arguments or "{}")
                    except Exception:
                        raw_args = {}

                    gb = raw_args.get("group_by", ["category"])
                    mets = raw_args.get("metrics", ["gross_revenue", "units"])
                    flts = raw_args.get("filters", {})
                    ob = raw_args.get("order_by")
                    lim = min(raw_args.get("limit", 10), 15)

                    tool_output_data = engine.query_fact_table(
                        group_by=gb,
                        metrics=mets,
                        filters=flts,
                        order_by=ob,
                        limit=lim,
                    )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_output_data),
                    })

            # Re-call model to synthesize final grounded response without SQL
            final_response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=650,
            )
            return final_response.choices[0].message.content or "No response received."

        raw_content = response_msg.content or ""

        # Safety Net: If model still outputted SQL text instead of the final business answer
        if ("```sql" in raw_content or re.search(r"\bSELECT\b[\s\S]+\bFROM\b", raw_content, re.IGNORECASE)) and has_engine:
            flts = {}
            if "south" in ql:
                flts["region"] = "South"
            elif "north" in ql and "northeast" not in ql:
                flts["region"] = "North"
            elif "northeast" in ql:
                flts["region"] = "Northeast"
            elif "southeast" in ql:
                flts["region"] = "Southeast"
            elif "central" in ql:
                flts["region"] = "Central-West"

            for st_code in ["sp", "rj", "mg", "rs", "pr", "sc", "ba", "pe", "ce", "df", "go", "es"]:
                if re.search(rf"\b{st_code}\b", ql):
                    flts["state"] = st_code.upper()
                    break

            gb = ["category"]
            if "city" in ql:
                gb = ["city"]
            elif "state" in ql:
                gb = ["state"]

            data = engine.query_fact_table(
                group_by=gb,
                metrics=["gross_revenue", "units", "orders"],
                filters=flts,
                order_by="gross_revenue",
                limit=10,
            )

            messages.append({"role": "assistant", "content": "I will retrieve the exact figures from the database."})
            messages.append({
                "role": "user",
                "content": (
                    f"Here is the exact data retrieved from the database:\n```json\n{json.dumps(data)}\n```\n"
                    "Provide the executive answer to the user's question directly with a markdown table and business observations. "
                    "DO NOT write or display any SQL code."
                ),
            })
            fallback_res = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=650,
            )
            return fallback_res.choices[0].message.content or "No response received."

        return raw_content or "No response received."
    except Exception as e:
        return f"*Error contacting Groq API:* {str(e)}"

