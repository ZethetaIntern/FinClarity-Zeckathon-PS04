# NiveshPilot — Zeckathon PS-04 MVP

A local Streamlit prototype for an AI investment-adviser co-pilot. Built around the problem statement's five deliverables: risk profiling, goal-based planning, fund screening, source-grounded research, and adviser approval.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Modules

1. **Client profile:** transparent heuristic separating risk capacity and behavioural risk tolerance; conservative conflict resolution; rule-based guardrails.
2. **Goal planner:** inflation-adjusted target corpus, indicative monthly SIP, projected contribution value, and illustrative glide path.
3. **Fund shortlist:** expense ratio/AUM filters over a deliberately synthetic dataset. Replace it with a verified AMFI/AMC source before real use.
4. **Research desk:** upload PDFs and retrieve relevant passages with PDF page citations. This is extractive keyword retrieval, not a full LLM/embedding RAG pipeline yet.
5. **Backtest lab:** upload historical monthly NAV/total-return data to calculate annualized return, volatility, and maximum drawdown. No fake performance data is generated.
6. **Approval queue:** local approve/reject flow and JSON audit export.

## Important limitations

- This is a hackathon MVP, not a registered investment-adviser service or financial advice.
- The built-in scheme names and figures are synthetic placeholders, clearly marked as demo data.
- Risk scoring is a transparent prototype heuristic, not a validated or SEBI-approved questionnaire.
- For real research, source and timestamp all data; use official AMFI scheme master/NAV history, AMC factsheets/SIDs/portfolio disclosures, RBI inflation data, and applicable SEBI regulations.
- The PDF search currently uses keyword overlap. A production RAG implementation should add chunking, embeddings, vector search, reranking, grounded answer generation, citations per factual claim, and abstention when evidence is missing.
- The backtest requires a user-supplied CSV. Use total-return-adjusted data, document data provenance, and include costs/taxes/benchmark comparisons before presenting results.
- The approval queue is session-local and does not send client communications.

## Suggested CSV format for backtest

A `date` column plus one NAV or total-return-index column per fund/asset, with monthly observations. For accurate portfolio return calculations, use total-return adjusted series and document whether rebalancing is monthly.
