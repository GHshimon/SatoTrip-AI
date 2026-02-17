import React, { useState, useMemo } from 'react';
import { PlanFolder } from '../types';
import * as folderApi from '../src/api/folders';
import { useToast } from './Toast';

interface FolderTreeProps {
    folders: PlanFolder[];
    selectedFolderId: string | null;
    onSelect: (folderId: string | null) => void;
    onUpdate: () => void;
}

interface TreeNode extends PlanFolder {
    children?: TreeNode[];
}

export const FolderTree: React.FC<FolderTreeProps> = ({ folders, selectedFolderId, onSelect, onUpdate }) => {
    const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
    const [isCreating, setIsCreating] = useState(false);
    const [newFolderName, setNewFolderName] = useState('');
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editName, setEditName] = useState('');

    const { showSuccess, showError } = useToast();

    // Build Tree
    const treeData = useMemo(() => {
        const buildTree = (parentId: string | null = null): TreeNode[] => {
            return folders
                .filter(f => f.parentId === parentId || (parentId === null && !f.parentId))
                .map(f => ({
                    ...f,
                    children: buildTree(f.id)
                }));
        };
        return buildTree();
    }, [folders]);

    const toggleExpand = (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setExpandedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const handleCreate = async () => {
        // #region agent log
        fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:52',message:'handleCreate called',data:{newFolderName,isCreating,trimmedLength:newFolderName.trim().length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
        // #endregion
        if (!newFolderName.trim()) {
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:54',message:'Validation failed - empty name',data:{newFolderName,isCreating},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
            // #endregion
            return;
        }
        try {
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:58',message:'Creating folder - before API call',data:{name:newFolderName.trim(),parent_id:null},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
            // #endregion
            // UI shows input at root level, so always create at root for now
            await folderApi.createFolder({ name: newFolderName, parent_id: null });
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:60',message:'Folder created successfully',data:{name:newFolderName.trim()},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
            // #endregion
            // Improving: If a folder is selected, create inside it? Or simpler: Root creation only initially.
            // Let's stick to Root creation for the main input.
            onUpdate();
            setNewFolderName('');
            setIsCreating(false);
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:65',message:'State updated after success',data:{isCreating:false,newFolderName:''},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
            // #endregion
            showSuccess('フォルダを作成しました');
        } catch (err) {
            // #region agent log
            fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:68',message:'Folder creation failed',data:{error:String(err),isCreating},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
            // #endregion
            console.error(err);
            showError('フォルダ作成に失敗しました');
        }
    };

    const handleRename = async (id: string) => {
        if (!editName.trim()) return;
        try {
            await folderApi.updateFolder(id, { name: editName });
            onUpdate();
            setEditingId(null);
            showSuccess('フォルダ名を変更しました');
        } catch (err) {
            console.error(err);
            showError('変更に失敗しました');
        }
    };

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!window.confirm('フォルダを削除しますか？\n中のプランは削除されませんが、フォルダ分けは解除されます。')) return;
        try {
            await folderApi.deleteFolder(id);
            if (selectedFolderId === id) onSelect(null);
            onUpdate();
            showSuccess('フォルダを削除しました');
        } catch (err) {
            console.error(err);
            showError('削除に失敗しました');
        }
    };

    const renderNode = (node: TreeNode, level: number = 0) => {
        const isExpanded = expandedIds.has(node.id);
        const isSelected = selectedFolderId === node.id;
        const isEditing = editingId === node.id;

        return (
            <div key={node.id}>
                <div
                    className={`flex items-center gap-2 py-1.5 px-2 cursor-pointer transition-colors rounded-lg group ${isSelected ? 'bg-primary/10 text-primary font-bold' : 'hover:bg-gray-100 text-text'}`}
                    style={{ paddingLeft: `${level * 16 + 8}px` }}
                    onClick={() => onSelect(node.id)}
                >
                    {node.children && node.children.length > 0 ? (
                        <button
                            onClick={(e) => toggleExpand(node.id, e)}
                            className="p-0.5 hover:bg-black/5 rounded"
                        >
                            <span className={`material-symbols-outlined text-lg transition-transform ${isExpanded ? 'rotate-90' : ''}`}>arrow_right</span>
                        </button>
                    ) : (
                        <span className="w-[18px]"></span>
                    )}

                    <span className="material-symbols-outlined text-yellow-500 text-xl font-variation-settings-fill">folder</span>

                    {isEditing ? (
                        <input
                            autoFocus
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') handleRename(node.id);
                                if (e.key === 'Escape') setEditingId(null);
                            }}
                            onBlur={() => setEditingId(null)}
                            className="flex-1 bg-white border border-primary px-1 rounded text-sm min-w-0"
                        />
                    ) : (
                        <span className="flex-1 truncate text-sm">{node.name}</span>
                    )}

                    {/* Actions */}
                    {!isEditing && (
                        <div className="hidden group-hover:flex items-center gap-1">
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setEditingId(node.id);
                                    setEditName(node.name);
                                }}
                                className="p-1 hover:bg-black/10 rounded text-gray-500"
                                title="名前変更"
                            >
                                <span className="material-symbols-outlined text-base">edit</span>
                            </button>
                            <button
                                onClick={(e) => handleDelete(node.id, e)}
                                className="p-1 hover:bg-red-100 rounded text-gray-500 hover:text-red-500"
                                title="削除"
                            >
                                <span className="material-symbols-outlined text-base">delete</span>
                            </button>
                        </div>
                    )}
                </div>

                {isExpanded && node.children && node.children.map(child => renderNode(child, level + 1))}
            </div>
        );
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="p-4 bg-gray-50 border-b border-gray-100 flex justify-between items-center">
                <h3 className="font-bold text-gray-700">フォルダ</h3>
                <button
                    onClick={() => setIsCreating(true)}
                    className="p-1 hover:bg-gray-200 rounded-full text-gray-600 transition-colors"
                    title="新規フィルダ"
                >
                    <span className="material-symbols-outlined">create_new_folder</span>
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
                <div
                    className={`flex items-center gap-2 py-2 px-3 mb-1 cursor-pointer transition-colors rounded-lg ${selectedFolderId === null ? 'bg-primary/10 text-primary font-bold' : 'hover:bg-gray-100 text-text'}`}
                    onClick={() => onSelect(null)}
                >
                    <span className="material-symbols-outlined text-xl">home</span>
                    <span className="flex-1 text-sm">すべてのプラン</span>
                </div>

                {isCreating && (
                    <div className="px-2 mb-2">
                        <div className="flex items-center gap-2 border border-primary rounded-lg p-1">
                            <span className="material-symbols-outlined text-yellow-500 text-xl font-variation-settings-fill">folder</span>
                            <input
                                autoFocus
                                placeholder="フォルダ名"
                                value={newFolderName}
                                onChange={(e) => {
                                    // #region agent log
                                    fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:198',message:'Folder name input changed',data:{newValue:e.target.value,isCreating},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
                                    // #endregion
                                    setNewFolderName(e.target.value);
                                }}
                                onKeyDown={(e) => {
                                    // #region agent log
                                    fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:204',message:'Key pressed in folder input',data:{key:e.key,newFolderName,isCreating},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
                                    // #endregion
                                    if (e.key === 'Enter') handleCreate();
                                    if (e.key === 'Escape') {
                                        // #region agent log
                                        fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:207',message:'Escape pressed - canceling creation',data:{isCreating},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
                                        // #endregion
                                        setIsCreating(false);
                                    }
                                }}
                                onBlur={() => {
                                    // #region agent log
                                    fetch('http://127.0.0.1:7243/ingest/0154fa29-b553-4de4-8ba1-d0609672b9f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'FolderTree.tsx:213',message:'Input blurred',data:{newFolderName,isCreating,trimmedLength:newFolderName.trim().length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
                                    // #endregion
                                    if (!newFolderName.trim()) {
                                        setIsCreating(false);
                                    }
                                }}
                                className="flex-1 text-sm outline-none min-w-0"
                            />
                        </div>
                    </div>
                )}

                {treeData.map(node => renderNode(node))}
            </div>
        </div>
    );
};
