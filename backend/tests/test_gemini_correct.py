#!/usr/bin/env python3
"""
使用正确的模型名称测试Gemini
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

# 推荐的模型列表（按优先级排序）
RECOMMENDED_MODELS = [
    "gemini-2.0-flash",      # 最新的2.0版本
    "gemini-1.5-flash",      # 稳定的1.5版本
    "gemini-1.5-pro",        # 更强大的1.5版本
    "gemini-2.5-flash",      # 2.5版本
]

def test_model(model_name):
    """测试特定模型"""
    try:
        print(f"\n 测试模型: {model_name}")
        print("=" * 60)
        
        import google.generativeai as genai
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        # 配置API密钥
        google_api_key = os.getenv('GOOGLE_API_KEY')
        genai.configure(api_key=google_api_key)
        
        # 测试1: 直接API
        print(" 测试直接API...")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("请用中文简单介绍一下苹果公司的主要业务")
            
            if response and response.text:
                print(" 直接API调用成功")
                print(f"   响应长度: {len(response.text)} 字符")
                print(f"   响应预览: {response.text[:150]}...")
                direct_success = True
            else:
                print(" 直接API调用失败：无响应内容")
                direct_success = False
        except Exception as e:
            print(f" 直接API调用失败: {e}")
            direct_success = False
        
        # 测试2: LangChain集成
        print("\n 测试LangChain集成...")
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.1,
                max_tokens=500,
                google_api_key=google_api_key
            )
            
            response = llm.invoke("请用中文分析苹果公司的投资价值，包括优势和风险")
            
            if response and response.content:
                print(" LangChain调用成功")
                print(f"   响应长度: {len(response.content)} 字符")
                print(f"   响应预览: {response.content[:150]}...")
                langchain_success = True
            else:
                print(" LangChain调用失败：无响应内容")
                langchain_success = False
        except Exception as e:
            print(f" LangChain调用失败: {e}")
            langchain_success = False
        
        return direct_success, langchain_success
        
    except Exception as e:
        print(f" 模型测试失败: {e}")
        return False, False

def test_tradingagents_with_gemini(model_name):
    """测试TradingAgents中使用Gemini"""
    try:
        print(f"\n 测试TradingAgents中使用 {model_name}")
        print("=" * 60)
        
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG
        
        # 创建使用Gemini的配置
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "google"
        config["deep_think_llm"] = model_name
        config["quick_think_llm"] = model_name
        config["online_tools"] = True
        config["memory_enabled"] = True
        
        # 修复路径
        config["data_dir"] = str(project_root / "data")
        config["results_dir"] = str(project_root / "results")
        config["data_cache_dir"] = str(project_root / "tradingagents" / "dataflows" / "data_cache")
        
        # 创建目录
        os.makedirs(config["data_dir"], exist_ok=True)
        os.makedirs(config["results_dir"], exist_ok=True)
        os.makedirs(config["data_cache_dir"], exist_ok=True)
        
        print(" 配置创建成功")
        print(f"   模型: {model_name}")
        
        # 创建TradingAgentsGraph实例
        print(" 初始化TradingAgents图...")
        graph = TradingAgentsGraph(["market"], config=config, debug=False)
        
        print(" TradingAgents图初始化成功")
        
        # 测试简单分析
        print(" 测试股票分析...")
        try:
            state, decision = graph.propagate("AAPL", "2025-06-27")
            
            if state and decision:
                print(" Gemini驱动的股票分析成功")
                print(f"   决策结果: {decision}")
                
                # 检查市场报告
                if "market_report" in state and state["market_report"]:
                    market_report = state["market_report"]
                    print(f"   市场报告长度: {len(market_report)} 字符")
                    print(f"   报告预览: {market_report[:150]}...")
                
                return True
            else:
                print(" 分析完成但结果为空")
                return False
                
        except Exception as e:
            print(f" 股票分析失败: {e}")
            return False
            
    except Exception as e:
        print(f" TradingAgents集成测试失败: {e}")
        return False

def main():
    """主函数"""
    print(" Gemini模型完整测试")
    print("=" * 70)
    
    # 检查API密钥
    google_api_key = os.getenv('GOOGLE_API_KEY')
    if not google_api_key:
        print(" Google API密钥未配置")
        return
    
    print(f" Google API密钥已配置: {google_api_key[:20]}...")
    
    # 测试推荐的模型
    best_model = None
    best_score = 0
    
    for model_name in RECOMMENDED_MODELS:
        print(f"\n{'='*70}")
        print(f" 测试模型: {model_name}")
        
        direct_success, langchain_success = test_model(model_name)
        
        # 计算得分
        score = int(direct_success) + int(langchain_success)
        
        print(f"\n {model_name} 测试结果:")
        print(f"   直接API: {' 通过' if direct_success else ' 失败'}")
        print(f"   LangChain: {' 通过' if langchain_success else ' 失败'}")
        print(f"   得分: {score}/2")
        
        if score > best_score:
            best_score = score
            best_model = model_name
        
        # 如果找到完全可用的模型，就使用它
        if score == 2:
            print(f"\n 找到完全可用的模型: {model_name}")
            break
    
    # 使用最佳模型测试TradingAgents
    if best_model and best_score > 0:
        print(f"\n{'='*70}")
        print(f" 使用最佳模型测试TradingAgents: {best_model}")
        
        tradingagents_success = test_tradingagents_with_gemini(best_model)
        
        # 最终总结
        print(f"\n 最终测试结果总结:")
        print("=" * 50)
        print(f"  最佳模型: {best_model}")
        print(f"  基础功能得分: {best_score}/2")
        print(f"  TradingAgents集成: {' 通过' if tradingagents_success else ' 失败'}")
        
        if best_score == 2 and tradingagents_success:
            print(f"\n Gemini模型 {best_model} 完全可用！")
            print(f"\n 使用建议:")
            print(f"   1. 在Web界面配置中选择Google作为LLM提供商")
            print(f"   2. 使用模型名称: {best_model}")
            print(f"   3. 可以进行完整的股票分析")
            print(f"   4. 支持中文输入和输出")
        else:
            print(f"\n 模型部分可用，建议检查网络连接和API配额")
    else:
        print(f"\n 所有推荐模型都不可用，请检查API密钥和网络连接")

if __name__ == "__main__":
    main()
