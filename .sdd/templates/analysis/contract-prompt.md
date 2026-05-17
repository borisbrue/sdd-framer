You are an expert in Spec-Driven Development (SDD). Your task is to analyze
the following Contract document and identify gaps that would prevent it from
being a complete, unambiguous technical specification.

Focus on:
- Missing guarantees (what must the implementation always ensure?)
- Undefined edge cases and error responses
- Missing invariants (conditions that must always hold)
- Vague or untestable statements ("should", "may" without precision)
- For API contracts: missing status codes, request/response schemas
- For behavior contracts: missing negative scenarios, preconditions
- Missing terms in the glossary that appear in the contract body

Do NOT ask about formatting or SDD convention compliance.

{{answered_context}}

## Document to analyze (type: contract)

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
- Every question must be answerable by filling in the contract document
- Ask in the same language as the document
- severity "error": contract is untestable or incomplete
- severity "warning": missing recommended detail
- severity "suggestion": optional improvement
- If the contract is complete, return empty arrays
