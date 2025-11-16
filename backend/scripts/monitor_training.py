"""
监控训练进度并自动检查Memory Bank
"""

import time
import requests
from datetime import datetime

API_BASE = "http://192.168.31.147:8000/api/v1"

def check_memory_stats():
    """检查Memory Bank统计"""
    try:
        response = requests.get(f"{API_BASE}/memory/statistics", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f" 获取统计失败: {e}")
        return None

def get_episodes(limit=10):
    """获取Episodes列表"""
    try:
        response = requests.get(f"{API_BASE}/memory/episodes?limit={limit}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f" 获取Episodes失败: {e}")
        return []

def get_episode_detail(episode_id):
    """获取单个Episode详情"""
    try:
        response = requests.get(f"{API_BASE}/memory/episodes/{episode_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f" 获取Episode详情失败: {e}")
        return None

def validate_episode(episode):
    """验证Episode数据完整性"""
    issues = []

    # 检查必填字段
    required_fields = ['episode_id', 'date', 'symbol', 'price', 'lesson']
    for field in required_fields:
        if field not in episode or episode[field] is None:
            issues.append(f"缺少字段: {field}")

    # 检查lesson长度
    if 'lesson' in episode and episode['lesson']:
        lesson_len = len(episode['lesson'])
        if lesson_len < 500:
            issues.append(f"Lesson过短: {lesson_len}字符 (应该包含完整的markdown格式分析)")

        # 检查是否包含关键部分
        lesson = episode['lesson']
        expected_sections = [
            '市场环境',
            '决策过程',
            '风险分析',
            '最终决策',
            '结果分析',
            '关键经验'
        ]
        missing_sections = [s for s in expected_sections if s not in lesson]
        if missing_sections:
            issues.append(f"Lesson缺少部分: {', '.join(missing_sections)}")

    # 检查success字段
    if 'success' not in episode or episode['success'] is None:
        issues.append("缺少success标记")

    # 检查percentage_return
    if 'percentage_return' in episode and episode['percentage_return'] is not None:
        ret = episode['percentage_return']
        if episode.get('success') == True and ret <= 0:
            issues.append(f"Success为True但收益率={ret*100:.2f}% (应该>0)")
        elif episode.get('success') == False and ret > 0:
            issues.append(f"Success为False但收益率={ret*100:.2f}% (应该<=0)")

    return issues

def monitor_and_validate():
    """主监控函数"""
    print("=" * 80)
    print(" Memory Bank 训练监控")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("正在监控训练进度...\n")

    last_count = 0
    check_interval = 60  # 每60秒检查一次

    while True:
        stats = check_memory_stats()

        if stats:
            current_count = stats['total_episodes']

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 当前统计:")
            print(f"   Episodes总数: {current_count}")
            print(f"   成功: {stats['successful_episodes']}")
            print(f"   失败: {stats['failed_episodes']}")
            print(f"   成功率: {stats['success_rate']*100:.1f}%")
            print(f"   平均收益: {stats['average_return']*100:.2f}%")

            # 如果有新Episode，显示详情
            if current_count > last_count:
                print(f"\n   新增 {current_count - last_count} 个Episode!")

                # 获取最新的Episodes
                episodes = get_episodes(limit=current_count - last_count)

                for episode in episodes:
                    print(f"\n  Episode: {episode['episode_id']}")
                    print(f"    日期: {episode['date']}")
                    print(f"    股票: {episode['symbol']}")
                    print(f"    操作: {episode.get('action', 'N/A')}")
                    print(f"    收益率: {episode.get('percentage_return', 0)*100:.2f}%")
                    print(f"    成功: {episode.get('success', 'N/A')}")

                    # 验证数据完整性
                    issues = validate_episode(episode)
                    if issues:
                        print(f"      数据问题:")
                        for issue in issues:
                            print(f"       - {issue}")
                    else:
                        print(f"     数据完整")

                last_count = current_count

            # 如果达到预期数量（7-8月大约40个交易日）
            if current_count >= 35:
                print("\n" + "=" * 80)
                print(" 训练完成！开始详细验证...")
                print("=" * 80)

                # 获取所有Episodes进行详细验证
                all_episodes = get_episodes(limit=100)

                print(f"\n验证 {len(all_episodes)} 个Episodes:")
                valid_count = 0
                invalid_count = 0

                for ep in all_episodes:
                    issues = validate_episode(ep)
                    if not issues:
                        valid_count += 1
                    else:
                        invalid_count += 1
                        print(f"\n Episode {ep['episode_id']} 有问题:")
                        for issue in issues:
                            print(f"   - {issue}")

                print(f"\n" + "=" * 80)
                print(f"验证结果:")
                print(f"   有效Episodes: {valid_count}")
                print(f"   有问题Episodes: {invalid_count}")
                print(f"   数据完整率: {valid_count/(valid_count+invalid_count)*100:.1f}%")
                print("=" * 80)

                # 检查一个完整的Episode
                if all_episodes:
                    print(f"\n检查第一个Episode的完整信息:")
                    first_ep = all_episodes[0]
                    detail = get_episode_detail(first_ep['episode_id'])

                    if detail:
                        print(f"\nEpisode ID: {detail['episode_id']}")
                        print(f"日期: {detail['date']}")
                        print(f"股票: {detail['symbol']}")
                        print(f"成功: {detail.get('success')}")
                        print(f"\nLesson长度: {len(detail.get('lesson', ''))} 字符")
                        print(f"Lesson前200字符:\n{detail.get('lesson', '')[:200]}...")

                break
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ 等待训练开始...")

        time.sleep(check_interval)

if __name__ == "__main__":
    try:
        monitor_and_validate()
    except KeyboardInterrupt:
        print("\n\n⏹  监控已停止")
    except Exception as e:
        print(f"\n\n 监控出错: {e}")
