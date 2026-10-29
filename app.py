import streamlit as st
import pandas as pd
import numpy as np
import json, re
from pathlib import Path

st.set_page_config(page_title='FinClarity | AI Financial Co-pilot', page_icon='📈', layout='wide')
ROOT = Path(__file__).parent
DATA = ROOT / 'data'

st.markdown('''<style>
.block-container{padding-top:1.3rem;max-width:1400px}.hero{padding:1.35rem 1.6rem;border-radius:18px;background:linear-gradient(120deg,#10243a,#174d60);color:white;margin-bottom:1rem}.hero h1{color:white;margin:0}.hero p{color:#d6e7ef;margin:.4rem 0 0}.pill{display:inline-block;padding:4px 10px;border-radius:20px;background:#d8f3e8;color:#145c43;font-size:.8rem;font-weight:600}.warn{padding:12px 14px;border-left:4px solid #d97706;background:#fff7e6;border-radius:8px}
</style>''', unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>📈 FinClarity</h1><p>AI-powered financial clarity · Suitability-first · Evidence-linked · Human approval required</p></div>', unsafe_allow_html=True)
st.markdown('<div class="warn"><b>Prototype notice:</b> This is a hackathon demonstration, not investment advice. The bundled fund rows are illustrative and must not be treated as real or current scheme data. No recommendation can be sent to a client without a qualified adviser reviewing it.</div>', unsafe_allow_html=True)

@st.cache_data
def load_funds():
    path=DATA/'demo_funds.csv'
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=['scheme','category','expense_ratio','aum_cr','tracking_error','manager_tenure_years','illustrative_5y_return','source','is_demo'])

def future_value_monthly(pmt, annual_rate, years):
    n=max(0,int(round(years*12))); r=(1+annual_rate)**(1/12)-1
    if n==0:return 0.0
    if abs(r)<1e-10:return pmt*n
    return pmt*(((1+r)**n-1)/r)*(1+r)

def monthly_sip(target, annual_rate, years):
    n=max(0,int(round(years*12))); r=(1+annual_rate)**(1/12)-1
    if n==0:return target
    if abs(r)<1e-10:return target/n
    return target*r/(((1+r)**n-1)*(1+r))

def profile_risk(age, income, expenses, liabilities, dependants, horizon, behaviour, emergency_months):
    # Transparent heuristic, deliberately conservative: capacity is a ceiling, not a prediction.
    capacity=0
    capacity += 2 if income-expenses >= 50000 else 1 if income-expenses >= 15000 else 0
    capacity += 2 if horizon >= 10 else 1 if horizon >= 5 else 0
    capacity += 1 if liabilities < income*12 else 0
    capacity += 1 if dependants == 0 else 0
    capacity += 1 if emergency_months >= 6 else 0
    capacity += 1 if age < 40 else 0
    capacity_label='High' if capacity>=6 else 'Moderate' if capacity>=4 else 'Low'
    tolerance_score={'Very uncomfortable':0,'Somewhat uncomfortable':1,'Neutral':2,'Comfortable':3,'Very comfortable':4}[behaviour]
    tolerance='High' if tolerance_score>=3 else 'Moderate' if tolerance_score==2 else 'Low'
    # Conflict rule: use the more conservative of capacity and tolerance.
    rank={'Low':0,'Moderate':1,'High':2}
    final=min(capacity_label,tolerance,key=lambda x:rank[x])
    return capacity_label,tolerance,final,capacity

def guardrail(age, horizon, risk, request, emergency_months, liabilities, monthly_income):
    reasons=[]
    text=request.lower()
    if re.search(r'guarantee|guaranteed|sure[- ]?shot|fixed 20%|20% return',text): reasons.append('Return guarantee requested: no investment return can be guaranteed.')
    if age>=60 and ('small-cap only' in text or 'small cap only' in text or '100% small-cap' in text): reasons.append('Concentrated small-cap-only exposure may be unsuitable for a retiree; adviser review required.')
    if ('borrow' in text or 'loan' in text) and ('invest' in text or 'trade' in text): reasons.append('Borrowing to invest/trade requires escalation and suitability review.')
    if emergency_months<3: reasons.append('Emergency reserve is below 3 months; prioritize liquidity before high-risk investing.')
    if liabilities>monthly_income*24: reasons.append('Liabilities exceed 24 months of income; reduce risk and review cash-flow resilience.')
    if risk=='Low' and any(w in text for w in ['aggressive','high risk','small-cap','small cap','f&o','options trading']): reasons.append('Requested risk appears inconsistent with the low-risk profile.')
    return reasons

with st.sidebar:
    st.header('Workspace')
    page=st.radio('Open module',['Client profile','Goal planner','Fund shortlist','Research desk (RAG)','Backtest lab','Adviser approval queue'])
    st.divider()
    st.caption('Demo data only · Replace with verified AMFI/AMC/RBI/SEBI sources before real use.')

if 'plans' not in st.session_state: st.session_state.plans=[]
if 'approval' not in st.session_state: st.session_state.approval=[]
if 'profile' not in st.session_state: st.session_state.profile=None

if page=='Client profile':
    st.subheader('01 · Risk capacity and risk tolerance')
    st.write('Capacity reflects the client’s financial ability to take risk. Tolerance reflects their emotional willingness. The final profile uses the more conservative of the two.')
    c1,c2,c3=st.columns(3)
    with c1:
        client=st.text_input('Client label','Client 001')
        age=st.number_input('Age',18,100,31)
        income=st.number_input('Monthly take-home income (₹)',0,100000000,100000,step=5000)
        expenses=st.number_input('Monthly essential expenses (₹)',0,100000000,45000,step=5000)
    with c2:
        liabilities=st.number_input('Total liabilities (₹)',0,1000000000,500000,step=50000)
        dependants=st.number_input('Dependants',0,20,1)
        horizon=st.number_input('Investment horizon (years)',1,60,10)
        emergency=st.number_input('Emergency fund (months of expenses)',0,60,4)
    with c3:
        behaviour=st.select_slider('Reaction to a temporary 20% portfolio fall',options=['Very uncomfortable','Somewhat uncomfortable','Neutral','Comfortable','Very comfortable'],value='Neutral')
        goal=st.selectbox('Primary goal',['Emergency fund','Long-term wealth','Child education','Retirement','Medical corpus','Monthly retirement income'])
        request=st.text_area('Client request / free-text prompt','I want a diversified plan for my long-term goal.')
    if st.button('Assess suitability',type='primary'):
        cap,tol,final,score=profile_risk(age,income,expenses,liabilities,dependants,horizon,behaviour,emergency)
        reasons=guardrail(age,horizon,final,request,emergency,liabilities,income)
        st.session_state.profile={'client':client,'age':age,'income':income,'expenses':expenses,'liabilities':liabilities,'dependants':dependants,'horizon':horizon,'emergency':emergency,'behaviour':behaviour,'goal':goal,'request':request,'capacity':cap,'tolerance':tol,'risk':final,'guardrails':reasons}
    p=st.session_state.profile
    if p:
        a,b,c=st.columns(3); a.metric('Risk capacity',p['capacity']); b.metric('Risk tolerance',p['tolerance']); c.metric('Conservative final profile',p['risk'])
        st.info('Conflict-resolution rule: final risk level = the lower of capacity and tolerance. This is a transparent prototype heuristic, not a SEBI-approved questionnaire.')
        if p['guardrails']:
            for r in p['guardrails']: st.warning(r)
        else: st.success('No rule-based alert fired. This does not prove the request is suitable.')
        if st.button('Add profile to adviser queue'):
            st.session_state.approval.append({'client':p['client'],'type':'Risk profile','status':'Pending review','summary':f"{p['risk']} risk; goal: {p['goal']}; alerts: {len(p['guardrails'])}"})
            st.success('Added to the approval queue.')

elif page=='Goal planner':
    st.subheader('02 · Inflation-adjusted goal planning')
    c1,c2,c3=st.columns(3)
    with c1:
        goal_name=st.text_input('Goal name','Child education')
        current_cost=st.number_input('Goal cost in today’s ₹',0,1000000000,2500000,step=100000)
        years=st.slider('Years until goal',1,50,15)
    with c2:
        inflation=st.slider('Assumed annual inflation (%)',0.0,15.0,6.0,0.5)/100
        expected=st.slider('Illustrative annual return assumption (%)',0.0,15.0,8.0,0.5)/100
        existing=st.number_input('Existing savings for this goal (₹)',0,1000000000,200000,step=10000)
    with c3:
        monthly_contribution=st.number_input('Current monthly contribution (₹)',0,10000000,5000,step=500)
        glide_years=st.slider('Years before goal to begin de-risking',0,min(10,years),5)
    target=current_cost*((1+inflation)**years)
    remaining=max(0,target-existing*((1+expected)**years))
    sip=monthly_sip(remaining,expected,years)
    projected=future_value_monthly(monthly_contribution,expected,years)+existing*((1+expected)**years)
    x,y,z=st.columns(3); x.metric('Inflation-adjusted target',f'₹{target:,.0f}'); y.metric('Indicative monthly SIP',f'₹{sip:,.0f}'); z.metric('Projected value at current contribution',f'₹{projected:,.0f}')
    st.caption('Assumptions are editable estimates, not promised returns. SIP calculation assumes end-of-month contributions with monthly compounding. Existing savings are assumed to grow at the same illustrative rate.')
    st.markdown('**Illustrative glide path**')
    rows=[]
    for yrs_left in sorted(set([years, max(1,years-glide_years), max(1,years-2), 1])):
        equity=max(10,min(80,20+6*(yrs_left-1)))
        rows.append({'Years remaining':yrs_left,'Illustrative growth assets':f'{equity}%','Illustrative defensive assets':f'{100-equity}%'})
    st.dataframe(pd.DataFrame(rows).drop_duplicates(),use_container_width=True,hide_index=True)
    if st.button('Queue goal plan for adviser approval'):
        st.session_state.plans.append({'goal':goal_name,'target':target,'sip':sip,'years':years,'assumption':expected})
        st.session_state.approval.append({'client':st.session_state.profile['client'] if st.session_state.profile else 'Unassigned client','type':'Goal plan','status':'Pending review','summary':f'{goal_name}: target ₹{target:,.0f}; SIP ₹{sip:,.0f}'})
        st.success('Plan queued. No client-facing output has been sent.')

elif page=='Fund shortlist':
    st.subheader('03 · Mutual fund screening')
    st.warning('The bundled fund universe is explicitly synthetic demo data. Do not interpret names, returns, costs, AUM, or manager tenure as real fund facts. Upload a verified current scheme master before using this module for actual research.')
    funds=load_funds()
    if funds.empty: st.error('Demo fund CSV is missing.'); st.stop()
    categories=st.multiselect('Categories',sorted(funds['category'].unique()),default=sorted(funds['category'].unique()))
    max_fee=st.slider('Maximum expense ratio (%)',0.0,2.0,1.0,0.05)
    min_aum=st.slider('Minimum AUM (₹ crore)',0,100000,100,100)
    screened=funds[funds.category.isin(categories)&(funds.expense_ratio<=max_fee)&(funds.aum_cr>=min_aum)].copy()
    screened=screened.sort_values(['expense_ratio','tracking_error'],ascending=True)
    st.dataframe(screened,use_container_width=True,hide_index=True)
    st.caption('Screening criteria shown for transparency. A real implementation should add rolling returns, drawdowns, benchmark comparisons, direct-plan verification, source timestamps, and suitability filtering before ranking.')
    if st.button('Queue shortlist for adviser review'):
        st.session_state.approval.append({'client':st.session_state.profile['client'] if st.session_state.profile else 'Unassigned client','type':'Fund shortlist','status':'Pending review','summary':f'{len(screened)} illustrative rows matched; verified data required'})
        st.success('Shortlist queued for review.')

elif page=='Research desk (RAG)':
    st.subheader('04 · Research assistant with page-level citations')
    st.write(
        'Upload factsheets, Scheme Information Documents (SIDs), or portfolio disclosures. '
        'This prototype ranks text passages from the uploaded PDFs and shows the source page. '
        'It does not generate answers or verify whether the document is current.'
    )
    files = st.file_uploader(
        'Upload source PDFs', type=['pdf'], accept_multiple_files=True, key='research_pdfs'
    )
    question = st.text_input(
        'Research question',
        'What does the scheme say about its benchmark and risk?',
        key='research_question'
    )

    if st.button('Search uploaded sources', type='primary', key='search_research_sources'):
        if not files:
            st.error('Upload at least one PDF first.')
        elif not question.strip():
            st.error('Enter a research question first.')
        else:
            try:
                import fitz

                # Remove generic document terms so that words like "scheme" do not
                # make a table of contents rank as highly as actual evidence.
                stopwords = {
                    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'does', 'for', 'from',
                    'how', 'i', 'in', 'into', 'is', 'it', 'its', 'me', 'of', 'on', 'or',
                    'please', 'say', 'says', 'that', 'the', 'their', 'this', 'to', 'was',
                    'what', 'when', 'where', 'which', 'who', 'why', 'with', 'about', 'does',
                    'scheme', 'fund', 'product', 'investor', 'investors', 'document'
                }

                def research_tokens(text):
                    return [
                        token for token in re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
                        if len(token) > 1 and token not in stopwords
                    ]

                question_lower = question.lower()
                query_terms = list(dict.fromkeys(research_tokens(question)))
                if not query_terms:
                    st.warning('Please use a more specific question, such as asking about benchmark, risk, fees, or investment objective.')
                    st.stop()

                # Model the concepts explicitly requested. This helps a question such as
                # "benchmark and risk" favor passages that address BOTH concepts.
                concept_terms = {
                    'benchmark': {'benchmark', 'index', 'indices', 'nifty', 'bse', 'sensex', 'benchmarking'},
                    'risk': {'risk', 'riskometer', 'meter', 'principal', 'loss', 'risky'},
                    'fees': {'fee', 'fees', 'expense', 'expenses', 'charges', 'load'},
                    'objective': {'objective', 'aim', 'goal', 'appreciation'},
                    'returns': {'return', 'returns', 'performance', 'growth', 'cagr'},
                }
                requested_concepts = []
                if any(term in question_lower for term in ['benchmark', 'index', 'indices']):
                    requested_concepts.append('benchmark')
                if any(term in question_lower for term in ['risk', 'risk-o-meter', 'riskometer', 'risk meter']):
                    requested_concepts.append('risk')
                if any(term in question_lower for term in ['fee', 'fees', 'expense', 'expenses', 'charges', 'exit load']):
                    requested_concepts.append('fees')
                if any(term in question_lower for term in ['objective', 'aim', 'invests in', 'investment strategy']):
                    requested_concepts.append('objective')
                if any(term in question_lower for term in ['return', 'returns', 'performance', 'growth']):
                    requested_concepts.append('returns')
                if not requested_concepts:
                    requested_concepts = [term for term in query_terms if term in concept_terms]

                passages = []
                for uploaded_file in files:
                    document = fitz.open(stream=uploaded_file.getvalue(), filetype='pdf')
                    try:
                        for page_number, page in enumerate(document, start=1):
                            page_text = page.get_text('text').strip()
                            if not page_text:
                                continue

                            page_lower = page_text.lower()
                            # A pure table-of-contents page is not substantive evidence.
                            if re.search(r'\btable of contents\b', page_lower) and page_lower.find('table of contents') < 100:
                                continue

                            # Short overlapping chunks keep the result focused while preserving
                            # the actual PDF page number for citation.
                            chunk_size = 1000
                            overlap = 140
                            for start_pos in range(0, len(page_text), chunk_size - overlap):
                                chunk = page_text[start_pos:start_pos + chunk_size].strip()
                                if not chunk:
                                    continue

                                chunk_lower = chunk.lower()
                                tokens = research_tokens(chunk)
                                token_set = set(tokens)
                                matched_direct = set(query_terms).intersection(token_set)
                                matched_expanded = set()
                                for concept in requested_concepts:
                                    if token_set.intersection(concept_terms.get(concept, set())):
                                        matched_expanded.update(token_set.intersection(concept_terms.get(concept, set())))
                                matched = matched_direct | matched_expanded
                                if not matched:
                                    continue

                                direct_coverage = len(matched_direct) / max(1, len(set(query_terms)))
                                concept_hits = 0
                                for concept in requested_concepts:
                                    aliases = concept_terms.get(concept, set())
                                    if token_set.intersection(aliases):
                                        concept_hits += 1
                                concept_coverage = concept_hits / max(1, len(requested_concepts)) if requested_concepts else direct_coverage

                                # Boost direct, scheme-specific evidence: benchmark names, risk-o-meter
                                # labels, and explicit statements about investor/principal risk.
                                specificity = 0.0
                                direct_benchmark_statement = False
                                if 'benchmark' in requested_concepts:
                                    if re.search(r'\bbenchmark\b.{0,100}\b(nifty|bse|sensex|index|indices|tr)\b', chunk_lower, re.S):
                                        specificity += 0.12
                                    if re.search(r'\b(nifty|bse|sensex)\b.{0,45}\b(tri|tr|index)\b', chunk_lower, re.S):
                                        specificity += 0.05
                                    # Strongly prioritize a direct statement naming the scheme's
                                    # benchmark, rather than generic references to benchmark rates.
                                    direct_benchmark_statement = bool(re.search(
                                        r'(?:performance of the\s+(?:scheme|fund)\s+will be benchmarked|'
                                        r'(?:scheme|fund)\s+(?:will be benchmarked|is benchmarked|shall be benchmarked)|'
                                        r'benchmark(?:ed)?\s+(?:with|against)\s+(?:the\s+)?(?:nifty|bse|sensex))',
                                        chunk_lower, re.S
                                    ))
                                    if direct_benchmark_statement:
                                        specificity += 0.26
                                if 'risk' in requested_concepts:
                                    if re.search(r'risk\s*[-–]?\s*o\s*[-–]?\s*meter|riskometer|risk meter', chunk_lower):
                                        specificity += 0.10
                                    if re.search(r'principal.{0,100}(very high|high|moderate|low).{0,40}risk|principal.{0,100}risk', chunk_lower, re.S):
                                        specificity += 0.12
                                    if 'risk' in chunk_lower and 'investors understand' in chunk_lower:
                                        specificity += 0.05

                                frequency_bonus = min(sum(tokens.count(term) for term in matched), 6) * 0.006
                                score = (0.25 * direct_coverage) + (0.35 * concept_coverage) + specificity + frequency_bonus

                                # Down-rank general regulatory boilerplate and unrelated uses of
                                # "benchmark rate" (for example, floating-rate bond discussions).
                                boilerplate_markers = [
                                    'in accordance with circular', 'shall be disclosed',
                                    'website of the amc', 'periodic disclosures',
                                    'annual report in the format', 'transparency/nav disclosure'
                                ]
                                if any(marker in chunk_lower for marker in boilerplate_markers):
                                    score -= 0.28
                                if 'benchmark' in requested_concepts:
                                    # Penalize bond-risk passages that mention a benchmark rate but
                                    # do not identify the scheme's performance benchmark.
                                    generic_rate_context = (
                                        re.search(r'\b(underlying benchmark|benchmark rate)\b', chunk_lower)
                                        and any(term in chunk_lower for term in [
                                            'spread', 'yield', 'coupon', 'fixed income', 'bond', 'security'
                                        ])
                                    )
                                    if generic_rate_context and not direct_benchmark_statement:
                                        score -= 0.30
                                    # Index-derivative explanations are not the same as naming
                                    # the scheme's benchmark or stating its risk level.
                                    if re.search(r'\b(index futures|index options|index futures/options|tracking error)\b', chunk_lower) and not direct_benchmark_statement:
                                        score -= 0.16
                                if any(marker in chunk_lower for marker in ['floating rate security', 'spread risk', 'coupon is expressed in terms of a spread']):
                                    if 'benchmark' in requested_concepts:
                                        score -= 0.30
                                if len(tokens) < 12:
                                    score -= 0.08

                                score = max(0.0, min(1.0, score))
                                if score < 0.12:
                                    continue
                                passages.append({
                                    'score': score,
                                    'filename': uploaded_file.name,
                                    'page': page_number,
                                    'text': chunk,
                                    'matched': sorted(matched),
                                })
                    finally:
                        document.close()

                # Sort by score and avoid near-duplicate chunks or multiple results from
                # the same page of a source, so the list shows distinct evidence locations.
                passages.sort(key=lambda item: item['score'], reverse=True)
                hits = []
                seen_text = set()
                seen_pages = set()
                for item in passages:
                    normalized = re.sub(r'\W+', ' ', item['text'].lower()).strip()
                    fingerprint = (item['filename'], normalized[:220])
                    page_key = (item['filename'], item['page'])
                    if fingerprint in seen_text or page_key in seen_pages:
                        continue
                    seen_text.add(fingerprint)
                    seen_pages.add(page_key)
                    hits.append(item)
                    if len(hits) == 5:
                        break

                if not hits:
                    st.warning(
                        'No matching evidence was found in the extractable text. Try more specific terms, '
                        'or check whether the PDF is scanned and requires OCR.'
                    )
                else:
                    st.markdown('**Ranked evidence passages — check the full context before using them**')
                    for rank, item in enumerate(hits, start=1):
                        with st.container(border=True):
                            st.markdown(
                                f"**{rank}. {item['filename']} · PDF page {item['page']}**  \n"
                                f"Relevance score (heuristic): {item['score']:.2f} · Matched terms: {', '.join(item['matched'])}"
                            )
                            text_to_show = item['text']
                            st.write(text_to_show + ('…' if len(text_to_show) >= 1400 else ''))
                            st.caption(f"Source citation: {item['filename']}, PDF page {item['page']}")

                    st.caption(
                        'This is ranked extractive retrieval, not a generative AI answer. '
                        'Relevance scores are heuristic and do not establish factual correctness. '
                        'For scanned PDFs, OCR may be required.'
                    )
            except ImportError:
                st.error('PyMuPDF is required. Install it in your project environment with: python -m pip install pymupdf')
            except Exception as exc:
                st.error(f'Could not search the uploaded PDF(s): {exc}')

    st.info(
        'Prototype limitation: the desk ranks extracted PDF passages only. It does not verify source freshness '
        'or provide financial advice; cite and check the original document before relying on any passage.'
    )

elif page=='Backtest lab':
    st.subheader('05 · Historical portfolio backtest')
    st.write('Upload a monthly total-return/NAV CSV with a date column and one column per asset or fund. The prototype calculates historical portfolio growth from the supplied series; it cannot verify the data provider.')
    navfile=st.file_uploader('Upload monthly NAV/total-return CSV',type=['csv'])
    if navfile:
        try:
            df=pd.read_csv(navfile)
            st.write('Detected columns:',', '.join(df.columns))
            date_col=st.selectbox('Date column',df.columns,index=0)
            numeric=[c for c in df.columns if c!=date_col and pd.to_numeric(df[c],errors='coerce').notna().sum()>2]
            assets=st.multiselect('Choose asset/NAV columns',numeric,default=numeric[:min(3,len(numeric))])
            weights={}
            if assets:
                st.caption('Enter portfolio weights; they will be normalized to sum to 100%.')
                cols=st.columns(min(3,len(assets)))
                for i,a in enumerate(assets): weights[a]=cols[i%len(cols)].number_input(f'{a} weight (%)',0,100,round(100/len(assets)),key=f'w_{a}')/100
                if st.button('Run backtest'):
                    if not assets:
                        st.error('Choose at least one asset/NAV column before running the backtest.')
                    elif len(set(assets)) != len(assets):
                        st.error('Choose each asset column only once.')
                    else:
                        d = df[[date_col] + assets].copy()
                        d[date_col] = pd.to_datetime(d[date_col], errors='coerce')
                        d = d.dropna(subset=[date_col]).sort_values(date_col).set_index(date_col)
                        for asset in assets:
                            d[asset] = pd.to_numeric(d[asset], errors='coerce')
                        d = d.dropna(subset=assets)
                        d = d[~d.index.duplicated(keep='last')]

                        if len(d) < 24:
                            st.error('Need at least 24 valid monthly observations after cleaning the CSV.')
                        elif (d[assets] <= 0).any().any():
                            st.error('NAV/total-return values must be positive.')
                        elif d.index[-1] <= d.index[0]:
                            st.error('The date column must contain at least two distinct dates in chronological order.')
                        else:
                            w = np.array([weights[asset] for asset in assets], dtype=float)
                            if not np.isfinite(w).all() or w.sum() <= 0:
                                st.error('Please assign a positive weight to at least one asset.')
                            else:
                                w = w / w.sum()
                                returns = d[assets].pct_change().dropna()
                                portfolio_returns = (returns * w).sum(axis=1)

                                # Include the initial portfolio value on the first NAV date.
                                # Portfolio weights are reset to the target weights each month.
                                growth = (1 + portfolio_returns).cumprod()
                                equity = pd.concat([
                                    pd.Series([1.0], index=[d.index[0]]),
                                    growth
                                ])
                                years = (equity.index[-1] - equity.index[0]).days / 365.25

                                cagr = float(equity.iloc[-1] ** (1 / years) - 1) if years > 0 else 0.0
                                vol = float(portfolio_returns.std(ddof=1) * np.sqrt(12)) if len(portfolio_returns) > 1 else 0.0
                                drawdown = float((equity / equity.cummax() - 1).min())
                                a, b, c = st.columns(3)
                                a.metric('Annualized return (CAGR)', f'{cagr:.2%}')
                                b.metric('Annualized volatility', f'{vol:.2%}')
                                c.metric('Maximum drawdown', f'{drawdown:.2%}')
                                chart_data = equity.rename('Growth of ₹1 (illustrative, historical data)').to_frame()
                                st.line_chart(chart_data, x_label='Date', y_label='Portfolio value', height=350)
                                st.caption(
                                    f'Period: {equity.index[0].date()} to {equity.index[-1].date()}. '
                                    'Portfolio weights are reset to target weights each month. Metrics assume the supplied series '
                                    'are valid monthly total-return/NAV data and ignore taxes, transaction costs, exit loads, '
                                    'cash flows, and survivorship bias. Results are historical, not predictive.'
                                )
        except Exception as e: st.error(f'Could not read the CSV: {e}')
    else: st.info('No backtest is run until a source dataset is uploaded. This avoids presenting fabricated historical performance as fact.')

elif page=='Adviser approval queue':
    st.subheader('06 · Human-in-the-loop approval')
    st.write('All outputs remain pending until a human adviser explicitly reviews them. This demo approval action is local to this session and does not transmit anything to a client.')
    if not st.session_state.approval: st.info('Nothing in the queue yet. Create a profile, goal plan, or shortlist first.')
    else:
        for i,item in enumerate(st.session_state.approval):
            with st.container(border=True):
                a,b=st.columns([4,1]); a.markdown(f"**{item['type']} · {item['client']}**  \n{item['summary']}  \nStatus: **{item['status']}**")
                if item['status']=='Pending review':
                    if b.button('Approve',key=f'approve_{i}'):
                        st.session_state.approval[i]['status']='Approved by demo reviewer'; st.rerun()
                    if b.button('Reject',key=f'reject_{i}'):
                        st.session_state.approval[i]['status']='Rejected'; st.rerun()
    if st.session_state.approval:
        st.download_button('Export review log (JSON)',json.dumps(st.session_state.approval,indent=2),file_name='adviser_review_log.json',mime='application/json')

st.divider()
st.caption('FinClarity · Zeckathon PS-04 prototype · Not investment advice · Verify every dataset and source before real-world use.')
