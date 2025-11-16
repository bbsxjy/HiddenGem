"""
快速测试FastAPI是否能正常启动

Usage:
    python scripts/test_api.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_import():
    """测试导入"""
    print("[TEST] Testing imports...")
    try:
        from api.main import app
        print("[PASS] FastAPI app imported successfully")

        from api.routers import agents, market
        print("[PASS] Routers imported successfully")

        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_creation():
    """测试应用创建"""
    print("\n[TEST] Testing app creation...")
    try:
        from api.main import app

        # 检查路由
        routes = [route.path for route in app.routes]
        print(f"[INFO] Total routes: {len(routes)}")

        expected_routes = ["/health", "/", "/api/v1/agents/status", "/api/v1/market/data/{symbol}"]
        for route in expected_routes:
            if route in routes or any(route in r for r in routes):
                print(f"[PASS] Route exists: {route}")
            else:
                print(f"[WARN] Route not found: {route}")

        return True
    except Exception as e:
        print(f"[FAIL] App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_health_endpoint():
    """测试健康检查端点"""
    print("\n[TEST] Testing health endpoint...")
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        response = client.get("/health")

        if response.status_code == 200:
            print(f"[PASS] Health check returned 200")
            print(f"[INFO] Response: {response.json()}")
            return True
        else:
            print(f"[FAIL] Health check returned {response.status_code}")
            return False

    except Exception as e:
        print(f"[FAIL] Health endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("="*80)
    print("FastAPI Quick Test Suite")
    print("="*80)

    results = []

    results.append(("Import Test", test_import()))
    results.append(("App Creation Test", test_app_creation()))
    results.append(("Health Endpoint Test", test_health_endpoint()))

    # 打印总结
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {name}")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n[SUCCESS] All tests passed! API is ready to start.")
        print("\nTo start the API server, run:")
        print("    python start_api.py")
        print("\nOr:")
        print("    uvicorn api.main:app --reload")
    else:
        print("\n[WARNING] Some tests failed. Please fix the issues above.")

    return passed_count == total_count


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
