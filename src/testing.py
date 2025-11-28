import unittest
from unittest.mock import patch
from src.resilio_core import build_workflow, KG, predict_financial_impact_range, fuzzy_find_entity

class TestResilioReliability(unittest.TestCase):
    
    def setUp(self):
        self.app = build_workflow()

    def test_fuzzy_grounding(self):
        print("\n🧪 TEST: Entity Grounding...")
        match = fuzzy_find_entity("Chemical Corporation India", KG)
        self.assertEqual(match, "PharmaCorp_India")
        print("   ✅ PASS: Fuzzy Match resolved entity correctly.")

    def test_probabilistic_math(self):
        """Test if P95 (Worst Case) is greater than P50 (Expected)."""
        print("\n🧪 TEST: Monte Carlo Integrity...")
        risk = predict_financial_impact_range(["Advil_Max_200mg"], severity=1.5, graph=KG, simulations=100)
        self.assertGreater(risk['total_p95'], risk['total_expected'])
        print("   ✅ PASS: Probabilistic range generated correctly (P95 > Expected).")

    def test_hallucination_prevention(self):
        print("\n🧪 TEST: Guardrails...")
        state = self.app.invoke({"input_news": "Explosion at Wonka Factory"})
        self.assertIsNone(state['detected_entity'])
        print("   ✅ PASS: Resilio rejected hallucinated entity.")

def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestResilioReliability)
    unittest.TextTestRunner(verbosity=0).run(suite)

if __name__ == "__main__":
    run_tests()