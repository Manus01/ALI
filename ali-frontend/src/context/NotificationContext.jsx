import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
    const [confirmations, setConfirmations] = useState([]);
    const [lastConfirmationId, setLastConfirmationId] = useState(null);
    const idCounter = useRef(0);

    const requestConfirmation = useCallback(({
        title,
        message,
        confirmLabel = 'Confirm',
        cancelLabel = 'Cancel',
        onConfirm,
        onCancel
    }) => {
        const id = `confirm_${Date.now()}_${idCounter.current++}`;
        const nextConfirmation = {
            id,
            title,
            message,
            confirmLabel,
            cancelLabel,
            onConfirm,
            onCancel
        };
        setConfirmations(prev => [nextConfirmation, ...prev]);
        setLastConfirmationId(id);
        return id;
    }, []);

    const dismissConfirmation = useCallback((id) => {
        setConfirmations(prev => prev.filter(note => note.id !== id));
    }, []);

    const value = useMemo(() => ({
        confirmations,
        lastConfirmationId,
        requestConfirmation,
        dismissConfirmation
    }), [confirmations, lastConfirmationId, requestConfirmation, dismissConfirmation]);

    return (
        <NotificationContext.Provider value={value}>
            {children}
        </NotificationContext.Provider>
    );
};

export const useNotification = () => {
    const context = useContext(NotificationContext);
    if (!context) {
        throw new Error('useNotification must be used within a NotificationProvider');
    }
    return context;
};
