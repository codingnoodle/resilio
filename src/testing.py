import unittest
import sys
import os
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.resilio_core import build_workflow, KG, predict_financial_impact_range, fuzzy_find_entity

class TestResilioReliability(unittest.TestCase):
    
    def setUp(self):
        self.app = build_workflow()

    def test_fuzzy_grounding(self):
        """Test entity grounding with current entity names."""
        print("\n🧪 TEST: Entity Grounding...")
        # Test India/Mumbai mapping
        match = fuzzy_find_entity("factory in mumbai", KG)
        self.assertEqual(match, "PharmaCorp_D_Tier2")
        print("   ✅ PASS: Mumbai correctly maps to PharmaCorp_D_Tier2.")
        
        # Test Mock Town/NJ mapping
        match2 = fuzzy_find_entity("nj facility", KG)
        self.assertEqual(match2, "PharmaCorp_A_Internal")
        print("   ✅ PASS: NJ correctly maps to PharmaCorp_A_Internal.")
        
        # Test Rocky Mount mapping
        match3 = fuzzy_find_entity("rocky mount", KG)
        self.assertEqual(match3, "PharmaCorp_C_Tier1")
        print("   ✅ PASS: Rocky Mount correctly maps to PharmaCorp_C_Tier1.")

    def test_location_priority_logic(self):
        """Test that location-specific keywords are prioritized before generic event types."""
        print("\n🧪 TEST: Location-Priority Logic...")
        
        # Test: "NJ fire" should map to PharmaCorp_A_Internal, not Mumbai
        state1 = self.app.invoke({"input_news": "NJ fire"}, config={'recursion_limit': 10})
        self.assertEqual(state1['detected_entity'], "PharmaCorp_A_Internal")
        self.assertIn("Fire", state1['detected_event'])
        print("   ✅ PASS: 'NJ fire' correctly maps to PharmaCorp_A_Internal (not Mumbai).")
        
        # Test: "Hurricane in New Jersey" should map to PharmaCorp_A_Internal
        state2 = self.app.invoke({"input_news": "Hurricane in New Jersey"}, config={'recursion_limit': 10})
        self.assertEqual(state2['detected_entity'], "PharmaCorp_A_Internal")
        self.assertIn("Hurricane", state2['detected_event'])
        print("   ✅ PASS: 'Hurricane in New Jersey' correctly maps to PharmaCorp_A_Internal.")
        
        # Test: "Fire in Mumbai" should map to PharmaCorp_D_Tier2
        state3 = self.app.invoke({"input_news": "Fire in Mumbai"}, config={'recursion_limit': 10})
        self.assertEqual(state3['detected_entity'], "PharmaCorp_D_Tier2")
        self.assertIn("Fire", state3['detected_event'])
        print("   ✅ PASS: 'Fire in Mumbai' correctly maps to PharmaCorp_D_Tier2.")

    def test_probabilistic_math(self):
        """Test if P95 (Worst Case) is greater than P50 (Expected)."""
        print("\n🧪 TEST: Monte Carlo Integrity...")
        # Updated to use current product names and function signature
        risk = predict_financial_impact_range(
            products=["Product_X_BioTherapy"],
            event_text="Fire",
            source_entity="PharmaCorp_A_Internal",
            graph=KG,
            simulations=100
        )
        self.assertGreater(risk['total_p95'], risk['total_expected'])
        print("   ✅ PASS: Probabilistic range generated correctly (P95 > Expected).")

    def test_hallucination_prevention(self):
        """Test that unknown entities are rejected."""
        print("\n🧪 TEST: Guardrails...")
        state = self.app.invoke({"input_news": "Explosion at Wonka Factory"}, config={'recursion_limit': 10})
        # The entity might be None or "Unknown" depending on implementation
        self.assertIn(state.get('detected_entity'), [None, "Unknown"])
        print("   ✅ PASS: Resilio rejected hallucinated entity.")

    def test_internal_biotherapy_scenario(self):
        """Test Internal BioTherapy Logistics scenario."""
        print("\n🧪 TEST: Internal BioTherapy Scenario...")
        state = self.app.invoke({
            "input_news": "Logistics disruption: Cryogenic delivery truck for BioTherapy delayed."
        }, config={'recursion_limit': 10})
        self.assertEqual(state['detected_entity'], "PharmaCorp_A_Internal")
        self.assertIn("Logistics", state['detected_event'])
        self.assertIn("Product_X_BioTherapy", state.get('impacted_products', []))
        print("   ✅ PASS: Internal BioTherapy scenario correctly detected.")

    def test_multiple_event_types_per_location(self):
        """Test that different event types can be detected for the same location."""
        print("\n🧪 TEST: Multiple Event Types Per Location...")
        
        # Test fire in NJ
        state1 = self.app.invoke({"input_news": "Fire at facility in New Jersey"}, config={'recursion_limit': 10})
        self.assertEqual(state1['detected_entity'], "PharmaCorp_A_Internal")
        self.assertIn("Fire", state1['detected_event'])
        
        # Test hurricane in NJ
        state2 = self.app.invoke({"input_news": "Hurricane hits New Jersey facility"}, config={'recursion_limit': 10})
        self.assertEqual(state2['detected_entity'], "PharmaCorp_A_Internal")
        self.assertIn("Hurricane", state2['detected_event'])
        
        # Test tornado in NJ
        state3 = self.app.invoke({"input_news": "Tornado damages New Jersey facility"}, config={'recursion_limit': 10})
        self.assertEqual(state3['detected_entity'], "PharmaCorp_A_Internal")
        self.assertIn("Tornado", state3['detected_event'])
        
        print("   ✅ PASS: Multiple event types correctly detected for same location.")

def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestResilioReliability)
    unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == "__main__":
    run_tests()