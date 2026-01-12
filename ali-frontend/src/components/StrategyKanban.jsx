import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { FaGripVertical, FaBolt, FaCheckCircle, FaUserEdit } from 'react-icons/fa';
import api from '../api/axiosInterceptor';

// Columns Configuration
const COLUMNS = {
    proposed: { id: 'proposed', title: '💡 Proposed', color: 'bg-blue-50 text-blue-700 border-blue-200' },
    active: { id: 'active', title: '⚡ In Progress', color: 'bg-amber-50 text-amber-700 border-amber-200' },
    completed: { id: 'completed', title: '✅ Completed', color: 'bg-green-50 text-green-700 border-green-200' }
};

export default function StrategyKanban({ initialActions }) {

    // Initialize columns logic handles both old format (strings) and new format (objects)
    const [columns, setColumns] = useState({
        proposed: {
            ...COLUMNS.proposed,
            items: (initialActions || []).map((action, i) => ({
                id: `item-${i}`,
                // Handle both simple string (legacy) and object (new) formats
                content: typeof action === 'string' ? action : action.description,
                tool: typeof action === 'object' ? action.tool : 'manual',
                params: typeof action === 'object' ? action.params : {}
            }))
        },
        active: { ...COLUMNS.active, items: [] },
        completed: { ...COLUMNS.completed, items: [] }
    });

    const [executingId, setExecutingId] = useState(null);

    // Update effect if props change (re-generation)
    useEffect(() => {
        if (initialActions && initialActions.length > 0) {
            setColumns(prev => ({
                ...prev,
                proposed: {
                    ...prev.proposed,
                    items: initialActions.map((action, i) => ({
                        id: `item-${i}`,
                        content: typeof action === 'string' ? action : action.description,
                        tool: typeof action === 'object' ? action.tool : 'manual',
                        params: typeof action === 'object' ? action.params : {}
                    }))
                }
            }));
        }
    }, [initialActions]);

    const onDragEnd = (result) => {
        if (!result.destination) return;

        const { source, destination } = result;

        const sourceColumn = columns[source.droppableId];
        const destColumn = columns[destination.droppableId];
        const sourceItems = [...sourceColumn.items];
        const destItems = source.droppableId === destination.droppableId ? sourceItems : [...destColumn.items];

        const [removed] = sourceItems.splice(source.index, 1);
        destItems.splice(destination.index, 0, removed);

        setColumns({
            ...columns,
            [source.droppableId]: { ...sourceColumn, items: sourceItems },
            [destination.droppableId]: { ...destColumn, items: destItems }
        });
    };

    const handleExecute = async (item) => {
        if (item.tool === 'manual') return;

        setExecutingId(item.id);
        try {
            const res = await api.post('/api/execute', { tool: item.tool, params: item.params });

            alert(res.data.message);

            // Auto-move to completed if successful
            // Find current column
            let currentColId = Object.keys(columns).find(key => columns[key].items.find(i => i.id === item.id));
            if (currentColId && currentColId !== 'completed') {
                const col = columns[currentColId];
                const newItems = col.items.filter(i => i.id !== item.id);

                setColumns(prev => ({
                    ...prev,
                    [currentColId]: { ...col, items: newItems },
                    completed: { ...prev.completed, items: [item, ...prev.completed.items] }
                }));
            }

        } catch (err) {
            alert("Execution failed: " + err.message);
        } finally {
            setExecutingId(null);
        }
    };

    return (
        <DragDropContext onDragEnd={onDragEnd}>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-full mt-8">
                {Object.entries(columns).map(([columnId, column]) => (
                    <div key={columnId} className="flex flex-col h-full min-h-[300px] rounded-xl bg-slate-50/50 border border-slate-200 backdrop-blur-sm">
                        <div className={`p-4 rounded-t-xl font-bold flex items-center gap-2 border-b ${column.color}`}>
                            {column.title}
                            <span className="ml-auto text-xs bg-white/60 px-2 py-1 rounded-full shadow-sm">
                                {column.items.length}
                            </span>
                        </div>

                        <Droppable droppableId={columnId}>
                            {(provided, snapshot) => (
                                <div
                                    {...provided.droppableProps}
                                    ref={provided.innerRef}
                                    className={`flex-1 p-4 space-y-3 transition-colors rounded-b-xl ${snapshot.isDraggingOver ? 'bg-slate-100/80 ring-2 ring-primary/10' : ''}`}
                                >
                                    {column.items.map((item, index) => (
                                        <Draggable key={item.id} draggableId={item.id} index={index}>
                                            {(provided, snapshot) => (
                                                <div
                                                    ref={provided.innerRef}
                                                    {...provided.draggableProps}
                                                    {...provided.dragHandleProps}
                                                    className={`p-4 bg-white rounded-lg shadow-sm border border-slate-200 group hover:shadow-md transition-all
                            ${snapshot.isDragging ? 'shadow-xl rotate-2 ring-2 ring-primary scale-105 z-50' : ''}
                          `}
                                                >
                                                    <div className="flex items-start justify-between gap-3">
                                                        <div className="flex items-start gap-3">
                                                            <FaGripVertical className="text-slate-300 mt-1 flex-shrink-0" />
                                                            <div>
                                                                <p className="text-sm text-slate-700 font-medium leading-relaxed">{item.content}</p>
                                                                <div className="flex gap-2 mt-2">
                                                                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${item.tool === 'manual' ? 'bg-slate-100 text-slate-500' : 'bg-blue-100 text-blue-600'}`}>
                                                                        {item.tool === 'manual' ? 'Manual' : 'Automated'}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        {/* Execute Button */}
                                                        {item.tool !== 'manual' && columnId !== 'completed' && (
                                                            <button
                                                                onClick={() => handleExecute(item)}
                                                                disabled={executingId === item.id}
                                                                className="p-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-600 hover:text-white transition-colors"
                                                                title="Auto-Execute"
                                                            >
                                                                {executingId === item.id ? <div className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full" /> : <FaBolt />}
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </Draggable>
                                    ))}
                                    {provided.placeholder}
                                </div>
                            )}
                        </Droppable>
                    </div>
                ))}
            </div>
        </DragDropContext>
    );
}