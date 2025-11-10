/**
 * Memory Bank API
 * Manage trading experiences (episodes) and statistics
 */

import { apiClient } from './client';
import type {
  Episode,
  EpisodeDetail,
  EpisodeCreate,
  EpisodeUpdate,
  MemoryStatistics,
  EpisodesQuery,
} from '@/types/memory';

const BASE_PATH = '/api/v1/memory';

/**
 * Get all episodes with optional filtering and pagination
 */
export async function getEpisodes(query?: EpisodesQuery): Promise<Episode[]> {
  const response = await apiClient.get<Episode[]>(`${BASE_PATH}/episodes`, {
    params: query,
  });
  return response.data;
}

/**
 * Get a single episode by ID
 */
export async function getEpisodeDetail(episodeId: string): Promise<EpisodeDetail> {
  const response = await apiClient.get<EpisodeDetail>(`${BASE_PATH}/episodes/${episodeId}`);
  return response.data;
}

/**
 * Create a new episode
 */
export async function createEpisode(episode: EpisodeCreate): Promise<{ success: boolean; episode_id: string; message: string }> {
  const response = await apiClient.post<{ success: boolean; episode_id: string; message: string }>(
    `${BASE_PATH}/episodes`,
    episode
  );
  return response.data;
}

/**
 * Update an existing episode
 */
export async function updateEpisode(
  episodeId: string,
  update: EpisodeUpdate
): Promise<{ success: boolean; episode_id: string; message: string }> {
  const response = await apiClient.put<{ success: boolean; episode_id: string; message: string }>(
    `${BASE_PATH}/episodes/${episodeId}`,
    update
  );
  return response.data;
}

/**
 * Delete an episode
 */
export async function deleteEpisode(episodeId: string): Promise<{ success: boolean; episode_id: string; message: string }> {
  const response = await apiClient.delete<{ success: boolean; episode_id: string; message: string }>(
    `${BASE_PATH}/episodes/${episodeId}`
  );
  return response.data;
}

/**
 * Get memory bank statistics
 */
export async function getStatistics(): Promise<MemoryStatistics> {
  const response = await apiClient.get<MemoryStatistics>(`${BASE_PATH}/statistics`);
  return response.data;
}

/**
 * Clear all episodes (dangerous operation)
 */
export async function clearAllEpisodes(): Promise<{ success: boolean; deleted_count: number; message: string }> {
  const response = await apiClient.delete<{ success: boolean; deleted_count: number; message: string }>(
    `${BASE_PATH}/episodes/bulk/clear`,
    {
      params: { confirm: true },
    }
  );
  return response.data;
}
