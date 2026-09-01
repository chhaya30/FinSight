RISK_EXTRACTION_SYSTEM_PROMPT = """You are an expert risk analyst specializing in extracting material risks from corporate annual reports and regulatory filings. Your task is to identify, classify, and summarize risk disclosures with high precision and explainability.

Guidelines:
1. Extract ONLY risks explicitly disclosed in the provided text
2. Each risk must be traceable to specific source text
3. Classify risks into the provided taxonomy categories
4. Assign severity based on the language used (critical/high/medium/low/informational)
4. Provide confidence scores reflecting certainty
5. Include key entities (companies, amounts, dates, regulations)"""

RISK_EXTRACTION_USER_PROMPT = """Analyze the following text from an annual report's risk factors section and extract all material risk disclosures.

Source Text:
{text}

Taxonomy Categories:
{categories}

For each risk found, provide:
1. Risk statement (verbatim or close paraphrase from source)
2. Category (from taxonomy above)
3. Subcategory (if applicable)
4. Severity: critical/high/medium/low/informational
5. Confidence score (0.0-1.0)
6. Key entities mentioned
7. Source location reference

Output as JSON array of risk objects."""

RISK_EXTRACTION_FEW_SHOT_EXAMPLES = """
Example 1:
Text: "The company faces significant cybersecurity risks including potential data breaches and ransomware attacks that could result in substantial financial losses and reputational damage."
Output: [{
  "statement": "The company faces significant cybersecurity risks including potential data breaches and ransomware attacks",
  "category": "cyber",
  "subcategory": "data_breach",
  "severity": "high",
  "confidence": 0.95,
  "entities": ["data breaches", "ransomware attacks"],
  "source_ref": "cybersecurity risks"
}]

Example 2:
Text: "Changes in environmental regulations, particularly carbon pricing mechanisms, could materially increase our operating costs."
Output: [{
  "statement": "Changes in environmental regulations, particularly carbon pricing mechanisms, could materially increase our operating costs",
  "category": "climate",
  "subcategory": "transition_climate_risk",
  "severity": "medium",
  "confidence": 0.9,
  "entities": ["carbon pricing", "environmental regulations"],
  "source_ref": "environmental regulations"
}]"""

RISK_CLASSIFICATION_PROMPT = """Classify the following risk statement into the most appropriate category and severity level.

Risk Statement: {risk_text}

Available Categories:
{categories}

Provide:
1. Primary category
2. Confidence in category (0.0-1.0)
3. Severity level
4. Reasoning"""

SEVERITY_ASSESSMENT_PROMPT = """Assess the severity of the following risk based on the language used and context.

Risk: {risk_text}
Category: {category}

Severity Levels:
- critical: Existential threat, going concern, material weakness
- high: Significant financial/operational/reputational impact
- medium: Moderate impact, manageable with controls
- low: Minor impact, routine monitoring
- informational: Disclosed for transparency

Provide severity level and confidence (0.0-1.0)."""
