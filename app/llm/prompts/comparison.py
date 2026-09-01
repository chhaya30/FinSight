RISK_COMPARISON_SYSTEM_PROMPT = """You are an expert risk analyst comparing risk disclosures across two consecutive years for the same company. Your task is to identify what changed, what's new, what's removed, and assess the significance of changes.

Change Types:
- NEW: Risk appears in current year but not previous
- REMOVED: Risk appeared in previous year but not current
- SEVERITY_UP: Same risk, severity increased
- SEVERITY_DOWN: Same risk, severity decreased
- MODIFIED: Same risk, language/description changed meaningfully"""

RISK_MATCHING_PROMPT = """Compare the following risk statements from two consecutive years and determine if they represent the same underlying risk.

Previous Year Risk: "{prev_risk}"
Current Year Risk: "{curr_risk}"

Previous Category: {prev_category}, Severity: {prev_severity}
Current Category: {curr_category}, Severity: {curr_severity}

Semantic Similarity Score: {similarity_score}/1.0

Determine:
1. Are these the same risk? (yes/no)
2. If yes, what type of change? (SEVERITY_UP/SEVERITY_DOWN/MODIFIED)
3. Brief explanation of the change

Respond in JSON format."""

EVOLUTION_SUMMARY_PROMPT = """Generate an executive summary of risk evolution for {company_name} comparing FY{prev_year} to FY{curr_year}.

Changes Detected:
- New Risks: {new_count}
- Removed Risks: {removed_count}
- Severity Increased: {severity_up_count}
- Severity Decreased: {severity_down_count}
- Modified: {modified_count}

Key Changes:
{key_changes}

Provide a concise 3-4 paragraph summary covering:
1. Overall risk profile change
2. Most significant new/emerging risks
3. Notable risk mitigations (removed/decreased)
4. Strategic implications"""

EXECUTIVE_RISK_SUMMARY_PROMPT = """Generate an executive risk summary for {company_name} (FY{year}).

Risk Profile:
- Total Risks: {total_risks}
- By Severity: {severity_breakdown}
- By Category: {category_breakdown}
- Top Risks: {top_risks}
- Key Evolution vs Prior Year: {evolution_highlights}
- Financial Health Context: {financial_context}

Write a professional executive summary (3-4 paragraphs) suitable for board-level review. Focus on material risks, significant changes, and strategic implications."""
