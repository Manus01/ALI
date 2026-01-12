import React, { useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';

const sanitizeMermaidId = (rawId) => rawId.replace(/[^a-zA-Z0-9-_]/g, '');

export default function MermaidBlock({ code, className = '' }) {
    const [svgMarkup, setSvgMarkup] = useState('');
    const [errorMessage, setErrorMessage] = useState('');
    const reactId = useId();

    useEffect(() => {
        if (!code) {
            setSvgMarkup('');
            setErrorMessage('Mermaid diagram unavailable.');
            return;
        }

        let isMounted = true;
        const renderDiagram = async () => {
            try {
                mermaid.initialize({
                    startOnLoad: false,
                    theme: 'neutral',
                    securityLevel: 'strict'
                });
                const diagramId = `mermaid-${sanitizeMermaidId(reactId)}`;
                const { svg } = await mermaid.render(diagramId, code);
                if (isMounted) {
                    setSvgMarkup(svg);
                    setErrorMessage('');
                }
            } catch (error) {
                if (isMounted) {
                    setSvgMarkup('');
                    setErrorMessage('Unable to render this diagram.');
                }
                console.error('Mermaid render error:', error);
            }
        };

        renderDiagram();

        return () => {
            isMounted = false;
        };
    }, [code, reactId]);

    if (errorMessage) {
        return (
            <div className={`rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 ${className}`}>
                {errorMessage}
            </div>
        );
    }

    return (
        <div
            className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${className}`}
            dangerouslySetInnerHTML={{ __html: svgMarkup }}
        />
    );
}
