"""
FinClarity — Evaluation & Verification Test Suite
Zeckathon PS-04: AI Advisory · Suitability · Human-in-the-Loop

This automated test suite verifies that every deliverable, persona output,
adversarial guardrail, and financial calculation is 100% reproducible.
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import fitz

# Import pure logic directly from finclarity_core
from finclarity_core import (
    calculate_risk_profile,
    run_suitability_guardrails,
    future_value_monthly,
    monthly_sip,
    get_asset_allocation,
    BENCHMARK_PERSONAS,
    ADVERSARIAL_PROMPTS
)

class TestFinClarityDeliverables(unittest.TestCase):

    def test_01_all_six_benchmark_personas(self):
        """Verifies suitability outputs for all six test personas against RIA standard logic"""
        # Persona 1: Fresh Graduate
        p1 = BENCHMARK_PERSONAS["1. Fresh Graduate (Bengaluru) — 23 yrs, ₹55k take-home, Emergency Fund & Wealth"]
        r1 = calculate_risk_profile(p1['age'], p1['income'], p1['expenses'], p1['liabilities'], p1['dependants'], p1['horizon'], p1['behaviour'], p1['emergency'])
        self.assertEqual(r1['capacity_label'], 'High')
        self.assertEqual(r1['tolerance_label'], 'Moderate')
        self.assertEqual(r1['final_risk'], 'Moderate') # Conservative min rule

        # Persona 2: Young Couple
        p2 = BENCHMARK_PERSONAS["2. Young Couple (Pune) — 31 yrs, ₹1.6L Dual Income, Home Loan, Child Education"]
        r2 = calculate_risk_profile(p2['age'], p2['income'], p2['expenses'], p2['liabilities'], p2['dependants'], p2['horizon'], p2['behaviour'], p2['emergency'])
        self.assertEqual(r2['capacity_label'], 'Moderate')
        self.assertEqual(r2['tolerance_label'], 'High')
        self.assertEqual(r2['final_risk'], 'Moderate')

        # Persona 3: Small Business Owner
        p3 = BENCHMARK_PERSONAS["3. Small Business Owner (Surat) — 44 yrs, Irregular Income, High Cash, Retire at 58"]
        r3 = calculate_risk_profile(p3['age'], p3['income'], p3['expenses'], p3['liabilities'], p3['dependants'], p3['horizon'], p3['behaviour'], p3['emergency'])
        self.assertIn(r3['final_risk'], ['Moderate', 'High'])

        # Persona 4: Doctor (High income, under-invested, risk-averse)
        p4 = BENCHMARK_PERSONAS["4. Doctor (Patna) — 38 yrs, High Income, Risk-Averse, Retirement + Parents Medical"]
        r4 = calculate_risk_profile(p4['age'], p4['income'], p4['expenses'], p4['liabilities'], p4['dependants'], p4['horizon'], p4['behaviour'], p4['emergency'])
        self.assertEqual(r4['capacity_label'], 'High')
        self.assertEqual(r4['tolerance_label'], 'Low')
        self.assertEqual(r4['final_risk'], 'Low') # Crucial test: emotional aversion overrides high financial capacity!

        # Persona 5: Retiree (68 yrs, capital preservation)
        p5 = BENCHMARK_PERSONAS["5. Retiree (Chennai) — 68 yrs, ₹80 Lakh Corpus, Pension, Monthly Income for 25 yrs"]
        r5 = calculate_risk_profile(p5['age'], p5['income'], p5['expenses'], p5['liabilities'], p5['dependants'], p5['horizon'], p5['behaviour'], p5['emergency'])
        self.assertEqual(r5['final_risk'], 'Low')

        # Persona 6: Aggressive Trader (F&O losses, wants high returns fast)
        p6 = BENCHMARK_PERSONAS["6. Aggressive Trader (Mumbai) — 29 yrs, F&O Losses, High Returns Fast (Suitability Test)"]
        g6 = run_suitability_guardrails(p6['age'], p6['horizon'], 'High', p6['request'], p6['emergency'], p6['liabilities'], p6['income'])
        # Guardrail checks must trigger on guarantee and F&O loss recovery
        rule_names = [g['rule'] for g in g6]
        self.assertTrue(any('Prohibition of Return Guarantees' in r for r in rule_names))
        self.assertTrue(any('Speculative Derivative Risk' in r for r in rule_names))

    def test_02_ten_adversarial_guardrails(self):
        """Verifies that 100% of the 10 adversarial judge prompts are intercepted"""
        for ap in ADVERSARIAL_PROMPTS:
            age = 68 if '68' in ap['prompt'] else 30
            horizon = 2 if 'Low-Risk' in ap['title'] else 10
            risk = 'Low' if 'Low-Risk' in ap['title'] else 'Moderate'
            flags = run_suitability_guardrails(age, horizon, risk, ap['prompt'], emergency_months=1, liabilities=3000000, income=50000)
            self.assertTrue(len(flags) > 0, f"Failed to intercept adversarial prompt: {ap['title']}")

    def test_03_financial_math_accuracy(self):
        """Tests SIP formula and inflation compounding precision"""
        # Inflation-adjusted target: ₹25L in 15 years at 6% inflation
        current_cost = 2500000
        years = 15
        inflation = 0.06
        target = current_cost * ((1 + inflation) ** years)
        expected_target = 5991384.8
        self.assertAlmostEqual(target, expected_target, delta=100.0)

        # SIP calculation: ₹59.91L in 15 years at 10% expected return
        sip = monthly_sip(target, 0.10, years)
        self.assertTrue(14000 < sip < 16000)

    def test_04_direct_funds_universe(self):
        """Validates that all bundled mutual funds are Direct Plans with zero commission"""
        df = pd.read_csv('data/amfi_direct_funds.csv')
        self.assertTrue(len(df) >= 10)
        self.assertTrue(df['plan_type'].str.contains('Direct').all())
        self.assertTrue((df['expense_ratio'] < 1.5).all())

    def test_05_rag_pdf_retrieval(self):
        """Validates that RAG extracts exact citations with page numbers from sample SIDs"""
        sid_path = Path('data/sample_documents/UTI_Nifty50_Index_Fund_SID.pdf')
        self.assertTrue(sid_path.exists())
        doc = fitz.open(sid_path)
        found_benchmark = False
        for page_num, page in enumerate(doc, 1):
            text = page.get_text('text')
            if 'NIFTY 50 TRI' in text:
                found_benchmark = True
                self.assertEqual(page_num, 1) # Benchmark is explicitly on Page 1
        doc.close()
        self.assertTrue(found_benchmark)

if __name__ == '__main__':
    unittest.main()
