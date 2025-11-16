#!/usr/bin/env python3
"""
版本号一致性检查工具
确保项目中所有版本号引用都是一致的
"""

import os
import re
from pathlib import Path

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('default')


def get_target_version():
    """从VERSION文件获取目标版本号"""
    version_file = Path("VERSION")
    if version_file.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def check_file_versions(file_path: Path, target_version: str):
    """检查文件中的版本号"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 版本号模式
        version_patterns = [
            r'v?\d+\.\d+\.\d+(?:-\w+)?',  # 基本版本号
            r'Version-v\d+\.\d+\.\d+',    # Badge版本号
            r'版本.*?v?\d+\.\d+\.\d+',     # 中文版本描述
        ]
        
        issues = []
        
        for pattern in version_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                found_version = match.group()
                
                # 跳过一些特殊情况
                if any(skip in found_version.lower() for skip in [
                    'python-3.', 'mongodb', 'redis', 'streamlit', 
                    'langchain', 'pandas', 'numpy'
                ]):
                    continue
                
                # 标准化版本号进行比较
                normalized_found = found_version.lower().replace('version-', '').replace('版本', '').strip()
                normalized_target = target_version.lower()
                
                if normalized_found != normalized_target and not normalized_found.startswith('0.1.'):
                    # 如果不是历史版本号，则报告不一致
                    if not any(hist in normalized_found for hist in ['0.1.1', '0.1.2', '0.1.3', '0.1.4', '0.1.5']):
                        issues.append({
                            'line': content[:match.start()].count('\n') + 1,
                            'found': found_version,
                            'expected': target_version,
                            'context': content[max(0, match.start()-20):match.end()+20]
                        })
        
        return issues
        
    except Exception as e:
        return [{'error': str(e)}]

def main():
    """主检查函数"""
    logger.debug(f" 版本号一致性检查")
    logger.info(f"=")
    
    # 获取目标版本号
    target_version = get_target_version()
    if not target_version:
        logger.error(f" 无法读取VERSION文件")
        return
    
    logger.info(f" 目标版本: {target_version}")
    
    # 需要检查的文件
    files_to_check = [
        "README.md",
        "docs/PROJECT_INFO.md",
        "docs/releases/CHANGELOG.md",
        "docs/overview/quick-start.md",
        "docs/configuration/dashscope-config.md",
        "docs/data/data-sources.md",
    ]
    
    total_issues = 0
    
    for file_path in files_to_check:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f" 文件不存在: {file_path}")
            continue
        
        logger.info(f"\n 检查文件: {file_path}")
        issues = check_file_versions(path, target_version)
        
        if not issues:
            logger.info(f"    版本号一致")
        else:
            for issue in issues:
                if 'error' in issue:
                    logger.error(f"    检查错误: {issue['error']}")
                else:
                    logger.error(f"    第{issue['line']}行: 发现 '{issue['found']}', 期望 '{issue['expected']}'")
                    logger.info(f"      上下文: ...{issue['context']}...")
                total_issues += len(issues)
    
    # 总结
    logger.info(f"\n 检查总结")
    logger.info(f"=")
    
    if total_issues == 0:
        logger.info(f" 所有版本号都是一致的！")
        logger.info(f" 当前版本: {target_version}")
    else:
        logger.warning(f" 发现 {total_issues} 个版本号不一致问题")
        logger.info(f"请手动修复上述问题")
    
    # 版本号规范提醒
    logger.info(f"\n 版本号规范:")
    logger.info(f"   - 主版本文件: VERSION")
    logger.info(f"   - 当前版本: {target_version}")
    logger.info(f"   - 格式要求: v0.1.x")
    logger.info(f"   - 历史版本: 可以保留在CHANGELOG中")

if __name__ == "__main__":
    main()
