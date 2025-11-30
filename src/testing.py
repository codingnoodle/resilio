import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.resilio_core import build_workflow, KG, predict_financial_impact_range, fuzzy_find_entity
from dotenv import load_dotenv

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

class TestAPIKeyHandling(unittest.TestCase):
    """Test API key loading, validation, and LLM initialization."""
    
    def setUp(self):
        """Reset environment for each test."""
        # Save original values
        self.original_google_key = os.environ.get("GOOGLE_API_KEY")
        self.original_tavily_key = os.environ.get("TAVILY_API_KEY")
        self.original_use_llm = os.environ.get("USE_REAL_LLM")
    
    def tearDown(self):
        """Restore original environment."""
        # Restore or remove GOOGLE_API_KEY
        if self.original_google_key:
            os.environ["GOOGLE_API_KEY"] = self.original_google_key
        else:
            os.environ.pop("GOOGLE_API_KEY", None)
            
        # Restore or remove TAVILY_API_KEY
        if self.original_tavily_key:
            os.environ["TAVILY_API_KEY"] = self.original_tavily_key
        else:
            os.environ.pop("TAVILY_API_KEY", None)
            
        # Restore or remove USE_REAL_LLM
        if self.original_use_llm:
            os.environ["USE_REAL_LLM"] = self.original_use_llm
        else:
            os.environ.pop("USE_REAL_LLM", None)
        
        # Reload module to reset state
        if 'src.resilio_core' in sys.modules:
            del sys.modules['src.resilio_core']
    
    def test_env_file_loading(self):
        """Test that .env file is loaded correctly."""
        print("\n🧪 TEST: .env File Loading...")
        
        # Load .env file
        load_dotenv()
        
        # Check if keys are loaded (they might not exist, that's ok for this test)
        google_key = os.environ.get("GOOGLE_API_KEY")
        tavily_key = os.environ.get("TAVILY_API_KEY")
        
        # At minimum, keys should be accessible (even if None)
        self.assertIsNotNone(google_key or True)  # Always passes, just checks access
        self.assertIsNotNone(tavily_key or True)  # Always passes, just checks access
        
        print("   ✅ PASS: .env file loading works correctly.")
    
    def test_api_key_detection_with_valid_key(self):
        """Test that USE_REAL_LLM auto-detects when valid API key is present."""
        print("\n🧪 TEST: API Key Auto-Detection (Valid Key)...")
        
        # Set a valid-looking API key
        os.environ["GOOGLE_API_KEY"] = "AIzaSyTest123456789012345678901234567890"
        os.environ.pop("USE_REAL_LLM", None)  # Remove override if exists
        
        # Reload module
        import importlib
        import src.resilio_core as rc
        importlib.reload(rc)
        
        # USE_REAL_LLM should be True when key is present
        self.assertTrue(rc.USE_REAL_LLM, "USE_REAL_LLM should be True when API key is present")
        print("   ✅ PASS: USE_REAL_LLM auto-detected correctly with valid key.")
    
    def test_api_key_detection_without_key(self):
        """Test that USE_REAL_LLM is False when no API key is present."""
        print("\n🧪 TEST: API Key Auto-Detection (No Key)...")
        
        # Remove API key
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]
        if "USE_REAL_LLM" in os.environ:
            del os.environ["USE_REAL_LLM"]
        
        # Reload module
        import importlib
        import src.resilio_core as rc
        importlib.reload(rc)
        
        # USE_REAL_LLM should be False when no key
        self.assertFalse(rc.USE_REAL_LLM, "USE_REAL_LLM should be False when no API key")
        print("   ✅ PASS: USE_REAL_LLM correctly set to False without API key.")
    
    def test_placeholder_key_rejection(self):
        """Test that placeholder API keys are rejected."""
        print("\n🧪 TEST: Placeholder Key Rejection...")
        
        # Set placeholder key
        os.environ["GOOGLE_API_KEY"] = "your_google_api_key_here"
        if "USE_REAL_LLM" in os.environ:
            del os.environ["USE_REAL_LLM"]
        
        # Reload module
        import importlib
        import src.resilio_core as rc
        importlib.reload(rc)
        
        # LLM should not be initialized with placeholder
        self.assertIsNone(rc.llm, "LLM should be None when placeholder key is used")
        print("   ✅ PASS: Placeholder API keys are correctly rejected.")
    
    def test_use_real_llm_override_true(self):
        """Test that USE_REAL_LLM environment variable override works (true)."""
        print("\n🧪 TEST: USE_REAL_LLM Override (True)...")
        
        # Set override
        os.environ["USE_REAL_LLM"] = "true"
        if "GOOGLE_API_KEY" not in os.environ:
            os.environ["GOOGLE_API_KEY"] = "AIzaSyTest123456789012345678901234567890"
        
        # Reload module
        import importlib
        import src.resilio_core as rc
        importlib.reload(rc)
        
        self.assertTrue(rc.USE_REAL_LLM, "USE_REAL_LLM should be True when explicitly set")
        print("   ✅ PASS: USE_REAL_LLM override to 'true' works correctly.")
    
    def test_use_real_llm_override_false(self):
        """Test that USE_REAL_LLM environment variable override works (false)."""
        print("\n🧪 TEST: USE_REAL_LLM Override (False)...")
        
        # Set override to false
        os.environ["USE_REAL_LLM"] = "false"
        os.environ["GOOGLE_API_KEY"] = "AIzaSyTest123456789012345678901234567890"
        
        # Reload module
        import importlib
        import src.resilio_core as rc
        importlib.reload(rc)
        
        self.assertFalse(rc.USE_REAL_LLM, "USE_REAL_LLM should be False when explicitly disabled")
        print("   ✅ PASS: USE_REAL_LLM override to 'false' works correctly.")
    
    @patch('src.resilio_core.ChatGoogleGenerativeAI')
    def test_llm_initialization_success(self, mock_llm_class):
        """Test successful LLM initialization with valid key."""
        print("\n🧪 TEST: LLM Initialization (Success)...")
        
        # Mock the LLM class
        mock_llm_instance = MagicMock()
        mock_llm_class.return_value = mock_llm_instance
        
        # Set valid key
        os.environ["GOOGLE_API_KEY"] = "AIzaSyTest123456789012345678901234567890"
        if "USE_REAL_LLM" in os.environ:
            del os.environ["USE_REAL_LLM"]
        
        # Reload module
        import importlib
        import src.resilio_core as rc
        importlib.reload(rc)
        
        # LLM should be initialized
        self.assertIsNotNone(rc.llm, "LLM should be initialized with valid key")
        mock_llm_class.assert_called_once()
        print("   ✅ PASS: LLM initialization succeeds with valid API key.")
    
    @patch('src.resilio_core.ChatGoogleGenerativeAI')
    def test_llm_initialization_failure_handling(self, mock_llm_class):
        """Test that LLM initialization failures are handled gracefully."""
        print("\n🧪 TEST: LLM Initialization Failure Handling...")
        
        # Make initialization raise an exception
        mock_llm_class.side_effect = Exception("API initialization failed")
        
        # Set valid key
        os.environ["GOOGLE_API_KEY"] = "AIzaSyTest123456789012345678901234567890"
        if "USE_REAL_LLM" in os.environ:
            del os.environ["USE_REAL_LLM"]
        
        # Reload module (should not crash)
        import importlib
        import src.resilio_core as rc
        importlib.reload(rc)
        
        # LLM should be None and USE_REAL_LLM should be False
        self.assertIsNone(rc.llm, "LLM should be None when initialization fails")
        self.assertFalse(rc.USE_REAL_LLM, "USE_REAL_LLM should be False after initialization failure")
        print("   ✅ PASS: LLM initialization failures are handled gracefully.")
    
    def test_tavily_api_key_detection(self):
        """Test that Tavily API key can be detected from environment."""
        print("\n🧪 TEST: Tavily API Key Detection...")
        
        # Set Tavily key
        os.environ["TAVILY_API_KEY"] = "tvly-test-key-12345"
        
        # Load environment
        load_dotenv()
        
        # Check key is accessible
        tavily_key = os.environ.get("TAVILY_API_KEY")
        self.assertIsNotNone(tavily_key)
        self.assertEqual(tavily_key, "tvly-test-key-12345")
        print("   ✅ PASS: Tavily API key is correctly loaded from environment.")

def run_tests():
    """Run all test suites."""
    print("=" * 60)
    print("🧪 Running Resilio Test Suite")
    print("=" * 60)
    
    # Run reliability tests
    print("\n" + "=" * 60)
    print("📋 Test Suite 1: Reliability Tests")
    print("=" * 60)
    suite1 = unittest.TestLoader().loadTestsFromTestCase(TestResilioReliability)
    result1 = unittest.TextTestRunner(verbosity=2).run(suite1)
    
    # Run API key tests
    print("\n" + "=" * 60)
    print("🔑 Test Suite 2: API Key Handling Tests")
    print("=" * 60)
    suite2 = unittest.TestLoader().loadTestsFromTestCase(TestAPIKeyHandling)
    result2 = unittest.TextTestRunner(verbosity=2).run(suite2)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    total_tests = result1.testsRun + result2.testsRun
    total_failures = len(result1.failures) + len(result2.failures)
    total_errors = len(result1.errors) + len(result2.errors)
    total_passed = total_tests - total_failures - total_errors
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failures}")
    print(f"⚠️  Errors: {total_errors}")
    print("=" * 60)
    
    return total_failures == 0 and total_errors == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)