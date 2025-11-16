# -*- coding: utf-8 -*-
"""
Memory Bank API路由
管理交易经验库（Episodes和Maxims）
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import chromadb
import json
from datetime import datetime

router = APIRouter(prefix="/memory", tags=["Memory Bank"])


# ==================== Pydantic Models ====================

class EpisodeResponse(BaseModel):
    """Episode响应模型"""
    episode_id: str
    date: str
    symbol: str
    price: float
    action: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    percentage_return: Optional[float] = None
    holding_period_days: Optional[int] = None
    lesson: Optional[str] = None
    success: Optional[bool] = None
    market_regime: Optional[str] = None


class EpisodeDetail(BaseModel):
    """Episode完整详情"""
    episode_id: str
    date: str
    symbol: str
    market_state: Dict[str, Any]
    agent_analyses: Dict[str, Any]
    decision_chain: Dict[str, Any]
    outcome: Optional[Dict[str, Any]] = None
    lesson: Optional[str] = None
    key_lesson: Optional[str] = None
    success: Optional[bool] = None
    created_at: str
    mode: str
    metadata: Optional[Dict[str, Any]] = None


class EpisodeCreate(BaseModel):
    """创建Episode请求"""
    episode_id: str
    date: str
    symbol: str
    market_state: Dict[str, Any]
    agent_analyses: Dict[str, Any]
    decision_chain: Dict[str, Any]
    outcome: Optional[Dict[str, Any]] = None
    lesson: Optional[str] = None
    key_lesson: Optional[str] = None
    success: Optional[bool] = None
    mode: str = "manual"
    metadata: Optional[Dict[str, Any]] = None


class EpisodeUpdate(BaseModel):
    """更新Episode请求"""
    lesson: Optional[str] = None
    key_lesson: Optional[str] = None
    success: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class StatisticsResponse(BaseModel):
    """统计响应"""
    total_episodes: int
    successful_episodes: int
    failed_episodes: int
    success_rate: float
    average_return: float
    symbols: Dict[str, int]
    date_range: Dict[str, str]


# ==================== Helper Functions ====================

def get_episodes_collection():
    """获取Episodes集合"""
    try:
        client = chromadb.PersistentClient(path="./memory_db/episodes")
        collection = client.get_or_create_collection(name="trading_episodes")
        return collection
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to database: {str(e)}")


def parse_episode(doc: str, metadata: Dict) -> Dict[str, Any]:
    """解析Episode文档"""
    try:
        ep_data = json.loads(doc)

        # 提取关键字段
        outcome = ep_data.get('outcome', {})
        market = ep_data.get('market_state', {})

        return {
            'episode_id': ep_data.get('episode_id'),
            'date': ep_data.get('date'),
            'symbol': ep_data.get('symbol'),
            'price': market.get('price', 0),
            'action': outcome.get('action') if outcome else None,
            'entry_price': outcome.get('entry_price') if outcome else None,
            'exit_price': outcome.get('exit_price') if outcome else None,
            'percentage_return': outcome.get('percentage_return') if outcome else None,
            'holding_period_days': outcome.get('holding_period_days') if outcome else None,
            'lesson': ep_data.get('lesson'),
            'success': ep_data.get('success'),
            'market_regime': market.get('market_regime'),
            'full_data': ep_data  # 保留完整数据
        }
    except Exception as e:
        return {'episode_id': 'error', 'error': str(e)}


# ==================== API Endpoints ====================

@router.get("/episodes", response_model=List[EpisodeResponse])
async def get_all_episodes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    symbol: Optional[str] = None,
    success: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """
    获取所有Episodes（支持过滤和分页）

    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    - **symbol**: 按股票代码过滤
    - **success**: 按成功/失败过滤
    - **date_from**: 起始日期
    - **date_to**: 结束日期
    """
    try:
        collection = get_episodes_collection()

        # 构建查询条件
        where_conditions = {}
        if symbol:
            where_conditions['symbol'] = symbol
        if success is not None:
            where_conditions['success'] = str(success)

        # 获取数据
        if where_conditions:
            results = collection.get(where=where_conditions)
        else:
            results = collection.get()

        if not results or not results['documents']:
            return []

        # 解析episodes
        episodes = []
        for doc, metadata in zip(results['documents'], results['metadatas']):
            ep = parse_episode(doc, metadata)

            # 日期过滤
            if date_from and ep.get('date', '') < date_from:
                continue
            if date_to and ep.get('date', '') > date_to:
                continue

            episodes.append(ep)

        # 按日期排序（最新的在前）
        episodes.sort(key=lambda x: x.get('date', ''), reverse=True)

        # 分页
        paginated = episodes[skip:skip + limit]

        return paginated

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve episodes: {str(e)}")


@router.get("/episodes/{episode_id}", response_model=EpisodeDetail)
async def get_episode_detail(episode_id: str):
    """
    获取单个Episode的完整详情

    - **episode_id**: Episode ID
    """
    try:
        collection = get_episodes_collection()

        results = collection.get(ids=[episode_id])

        if not results or not results['documents']:
            raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

        # 解析完整数据
        ep_data = json.loads(results['documents'][0])

        return ep_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve episode: {str(e)}")


@router.post("/episodes", status_code=201)
async def create_episode(episode: EpisodeCreate):
    """
    创建新的Episode

    - **episode**: Episode数据
    """
    try:
        collection = get_episodes_collection()

        # 检查是否已存在
        existing = collection.get(ids=[episode.episode_id])
        if existing and existing['documents']:
            raise HTTPException(status_code=409, detail=f"Episode {episode.episode_id} already exists")

        # 构建完整episode数据
        episode_data = {
            **episode.dict(),
            'created_at': datetime.now().isoformat(),
            'metadata': episode.metadata or {}
        }

        # 生成embedding（简化版，使用key_lesson）
        text_for_embedding = episode.key_lesson or episode.lesson or f"{episode.symbol} {episode.date}"

        # 准备metadata
        outcome = episode.outcome or {}
        market = episode.market_state

        metadata = {
            'date': episode.date,
            'symbol': episode.symbol,
            'market_regime': market.get('market_regime', 'unknown'),
            'action': outcome.get('action', 'unknown'),
            'mode': episode.mode,
            'success': str(episode.success) if episode.success is not None else 'unknown'
        }

        # 存入ChromaDB（使用空向量，因为没有embedding模型）
        collection.add(
            ids=[episode.episode_id],
            embeddings=[[0.0] * 384],  # 占位符
            documents=[json.dumps(episode_data, ensure_ascii=False)],
            metadatas=[metadata]
        )

        return {"success": True, "episode_id": episode.episode_id, "message": "Episode created successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create episode: {str(e)}")


@router.put("/episodes/{episode_id}")
async def update_episode(episode_id: str, update_data: EpisodeUpdate):
    """
    更新Episode

    - **episode_id**: Episode ID
    - **update_data**: 更新的字段
    """
    try:
        collection = get_episodes_collection()

        # 获取现有episode
        results = collection.get(ids=[episode_id])
        if not results or not results['documents']:
            raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

        # 解析现有数据
        ep_data = json.loads(results['documents'][0])

        # 更新字段
        if update_data.lesson is not None:
            ep_data['lesson'] = update_data.lesson
        if update_data.key_lesson is not None:
            ep_data['key_lesson'] = update_data.key_lesson
        if update_data.success is not None:
            ep_data['success'] = update_data.success
        if update_data.metadata is not None:
            ep_data['metadata'] = {**ep_data.get('metadata', {}), **update_data.metadata}

        # 更新metadata
        metadata = results['metadatas'][0]
        if update_data.success is not None:
            metadata['success'] = str(update_data.success)

        # 删除旧的
        collection.delete(ids=[episode_id])

        # 添加更新后的
        collection.add(
            ids=[episode_id],
            embeddings=[[0.0] * 384],
            documents=[json.dumps(ep_data, ensure_ascii=False)],
            metadatas=[metadata]
        )

        return {"success": True, "episode_id": episode_id, "message": "Episode updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update episode: {str(e)}")


@router.delete("/episodes/{episode_id}")
async def delete_episode(episode_id: str):
    """
    删除Episode

    - **episode_id**: Episode ID
    """
    try:
        collection = get_episodes_collection()

        # 检查是否存在
        results = collection.get(ids=[episode_id])
        if not results or not results['documents']:
            raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

        # 删除
        collection.delete(ids=[episode_id])

        return {"success": True, "episode_id": episode_id, "message": "Episode deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete episode: {str(e)}")


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """
    获取Memory Bank统计信息
    """
    try:
        collection = get_episodes_collection()

        results = collection.get()

        if not results or not results['documents']:
            return StatisticsResponse(
                total_episodes=0,
                successful_episodes=0,
                failed_episodes=0,
                success_rate=0.0,
                average_return=0.0,
                symbols={},
                date_range={}
            )

        # 解析episodes
        episodes = []
        for doc, metadata in zip(results['documents'], results['metadatas']):
            ep = parse_episode(doc, metadata)
            episodes.append(ep)

        # 计算统计
        total = len(episodes)
        successful = sum(1 for ep in episodes if ep.get('success'))
        failed = total - successful
        success_rate = successful / total if total > 0 else 0.0

        # 平均回报
        returns = [ep.get('percentage_return', 0) for ep in episodes if ep.get('percentage_return') is not None]
        avg_return = sum(returns) / len(returns) if returns else 0.0

        # 股票分布
        symbols = {}
        for ep in episodes:
            symbol = ep.get('symbol', 'Unknown')
            symbols[symbol] = symbols.get(symbol, 0) + 1

        # 日期范围
        dates = [ep.get('date', '') for ep in episodes if ep.get('date')]
        date_range = {
            'earliest': min(dates) if dates else '',
            'latest': max(dates) if dates else ''
        }

        return StatisticsResponse(
            total_episodes=total,
            successful_episodes=successful,
            failed_episodes=failed,
            success_rate=success_rate,
            average_return=avg_return,
            symbols=symbols,
            date_range=date_range
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")


@router.delete("/episodes/bulk/clear")
async def clear_all_episodes(confirm: bool = Query(False)):
    """
    清空所有Episodes（危险操作！）

    - **confirm**: 必须设置为true才能执行
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to clear all episodes")

    try:
        collection = get_episodes_collection()

        # 获取所有IDs
        results = collection.get()
        if results and results['ids']:
            collection.delete(ids=results['ids'])
            count = len(results['ids'])
        else:
            count = 0

        return {"success": True, "deleted_count": count, "message": f"Cleared {count} episodes"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear episodes: {str(e)}")
