import React, { useEffect, useState } from 'react';
import { getSearchStatus, triggerIndex } from '../api';
import type { SearchStatus } from '../api';

function errorText(err: unknown, fallback: string): string {
    return err instanceof Error ? err.message : fallback;
}

export default function IndexBar() {
    const [path, setPath] = useState('');
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState('');
    const [status, setStatus] = useState<SearchStatus | null>(null);

    const refresh = async () => {
        try {
            setStatus(await getSearchStatus());
        } catch {
            // The main search box already reports a backend connection error.
        }
    };

    useEffect(() => {
        refresh();
    }, []);

    const handleIndex = async () => {
        setBusy(true);
        setMessage('Starting indexing...');

        try {
            const result = await triggerIndex(path.trim() || undefined);
            setMessage(`${result.status} Results appear as files are processed.`);

            // Show progress for a short while; indexing continues in the
            // backend even after this loop ends.
            for (let i = 0; i < 8; i += 1) {
                await new Promise((resolve) => setTimeout(resolve, 1500));
                await refresh();
            }
        } catch (err) {
            setMessage(errorText(err, 'Could not start indexing.'));
        } finally {
            setBusy(false);
        }
    };

    return (
        <div style={{ padding: '0 20px 20px' }}>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <input
                    type="text"
                    value={path}
                    onChange={(e) => setPath(e.target.value)}
                    placeholder="Folder to index (blank = Documents + Desktop)"
                    style={{
                        flex: 1,
                        minWidth: '260px',
                        padding: '10px 12px',
                        borderRadius: '8px',
                        border: '1px solid #ddd',
                        fontSize: '0.9rem',
                        outline: 'none',
                    }}
                />
                <button
                    type="button"
                    onClick={handleIndex}
                    disabled={busy}
                    style={{
                        padding: '0 18px',
                        borderRadius: '8px',
                        border: 'none',
                        background: busy ? '#ccc' : '#34A853',
                        color: 'white',
                        cursor: busy ? 'default' : 'pointer',
                        fontWeight: 'bold',
                    }}
                >
                    {busy ? 'Indexing...' : 'Index'}
                </button>
                <button
                    type="button"
                    onClick={refresh}
                    style={{
                        padding: '0 14px',
                        borderRadius: '8px',
                        border: '1px solid #ddd',
                        background: 'white',
                        cursor: 'pointer',
                    }}
                >
                    Refresh status
                </button>
            </div>

            <div style={{ marginTop: '8px', fontSize: '0.8rem', color: '#666' }}>
                {status
                    ? `${status.files} files indexed, ${status.vectors} vectors`
                    : 'Index status unavailable'}
                {message ? ` — ${message}` : ''}
            </div>
        </div>
    );
}
