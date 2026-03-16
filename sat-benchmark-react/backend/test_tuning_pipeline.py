import sys
import unittest

def test_imports():
    try:
        import smac
        import ConfigSpace
        print("[OK] SMAC and ConfigSpace imported successfully.")
    except ImportError as e:
        print(f"[FAIL] Missing dependencies: {e}")
        sys.exit(1)

def test_tuning_module():
    try:
        from app.analysis.tuning import AlgorithmTuner, KissatTunable, AblationAnalyzer
        print("[OK] Tuning module imports successfully.")
        
        tuner = AlgorithmTuner("kissat", instances=["dummy1", "dummy2"])
        cs = tuner.get_solver_config_space()
        
        hyperparameters = cs.get_hyperparameter_names()
        if "restartint" in hyperparameters:
            print("[OK] ConfigSpace for Kissat generated correctly with restartint.")
        else:
            print("[FAIL] ConfigSpace mapping incorrect.")
            sys.exit(1)
            
        analyzer = AblationAnalyzer("kissat", instances=["dummy1"])
        print("[OK] Ablation analyzer instantiated.")
    except Exception as e:
        print(f"[FAIL] Tuning module test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("--- Running Pipeline Verification Tests ---")
    test_imports()
    test_tuning_module()
    print("--- All tests passed! ---")
