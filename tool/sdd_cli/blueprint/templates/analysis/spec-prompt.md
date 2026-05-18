You are an expert in Spec-Driven Development (SDD). Your task is to analyze
the following Spec document and identify gaps, missing details, or ambiguities
that the author should clarify.

Focus on:
- Missing or unmeasurable success criteria
- User stories without clear acceptance conditions
- Scope gaps (what happens in edge cases?)
- Missing non-functional requirements (performance, security, compatibility)
- Dependencies that are mentioned but not specified

Do NOT ask about formatting or style. Only ask about content gaps that would
prevent a developer from implementing the feature correctly.

{{answered_context}}

## Document to analyze (type: spec)

{{document_content}}

## Instructions

Return ONLY a JSON object — no markdown, no prose outside the JSON. Format:
{
  "questions": [
    {
      "id": "<short-slug>",
      "section": "<exact section heading from the document>",
      "text": "<specific question in the document's language>",
      "severity": "error | warning | suggestion"
    }
  ],
  "issues": [
    {
      "section": "<section>",
      "text": "<concrete issue description>",
      "severity": "error | warning"
    }
  ],
  "suggestions": [
    { "text": "<optional improvement suggestion>" }
  ]
}

Rules:
- Maximum 5 questions total
- Questions must reference a specific section of the document
- Ask in the same language as the document
- severity "error": document is incomplete or violates SDD rules
- severity "warning": recommended addition
- severity "suggestion": optional improvement
- If the document is complete and clear, return empty arrays
