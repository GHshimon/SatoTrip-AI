import { apiClient } from './client';
import { PlanFolder } from '../../types';

export interface FolderCreateRequest {
    name: string;
    parent_id?: string | null;
}

export interface FolderUpdateRequest {
    name?: string;
    parent_id?: string | null;
}

/**
 * フォルダ一覧取得
 */
export async function getFolders(): Promise<PlanFolder[]> {
    const response = await apiClient.get<any[]>('/api/folders');
    return response.map(transformFolderResponse);
}

/**
 * フォルダ作成
 */
export async function createFolder(data: FolderCreateRequest): Promise<PlanFolder> {
    const response = await apiClient.post<any>('/api/folders', data);
    return transformFolderResponse(response);
}

/**
 * フォルダ更新
 */
export async function updateFolder(id: string, data: FolderUpdateRequest): Promise<PlanFolder> {
    const response = await apiClient.put<any>(`/api/folders/${id}`, data);
    return transformFolderResponse(response);
}

/**
 * フォルダ削除
 */
export async function deleteFolder(id: string): Promise<void> {
    await apiClient.delete(`/api/folders/${id}`);
}

function transformFolderResponse(data: any): PlanFolder {
    return {
        id: data.id,
        name: data.name,
        parentId: data.parent_id,
        createdAt: data.created_at,
    };
}
