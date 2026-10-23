import React from 'react';
import type { SearchResult } from '../api';

interface ResultsListProps {
    results: SearchResult[];
    query: string;
    loading: boolean;
    error?: string;
}

export default function ResultsList({ results, query, loading, error }: ResultsListProps) {
    return (
        <div style={{ padding: '0 20px 20px', overflowY: 'auto', height: 'calc(100vh - 150px)' }}>
            {error && (
                <div style={{
                    background: '#fff1f0',
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '20px',
                    borderLeft: '4px solid #d93025',
                    color: '#8a1c16'
                }}>
                    {error}
                </div>
            )}

            {!error && loading && (
                <p style={{ color: '#666' }}>Searching files...</p>
            )}

            {!error && !loading && !query && (
                <p style={{ color: '#666' }}>
                    Type a filename or keyword to search your indexed files.
                </p>
            )}

            {!error && !loading && query && results.length === 0 && (
                <p style={{ color: '#666' }}>
                    No files found for "{query}". Make sure your files are indexed first.
                </p>
            )}

            {results.length > 0 && (
                <div>
                    <h3 style={{ fontSize: '1rem', color: '#555', marginBottom: '10px' }}>
                        {results.length} result{results.length === 1 ? '' : 's'} for "{query}"
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {results.map((res, i) => (
                            <div key={res.path || i} style={{
                                padding: '12px',
                                border: '1px solid #eee',
                                borderRadius: '6px',
                                background: 'white'
                            }}>
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    fontWeight: 'bold',
                                    fontSize: '0.9rem',
                                    marginBottom: '4px'
                                }}>
                                    <span>{res.path.split(/[\\/]/).pop()}</span>
                                    <span style={{
                                        fontSize: '0.7rem',
                                        fontWeight: 'normal',
                                        color: '#666',
                                        background: '#f1f3f4',
                                        borderRadius: '4px',
                                        padding: '2px 6px'
                                    }}>
                                        {res.type}
                                    </span>
                                </div>
                                <div style={{
                                    fontSize: '0.8rem',
                                    color: '#888',
                                    marginBottom: '6px',
                                    wordBreak: 'break-all'
                                }}>
                                    {res.path}
                                </div>
                                {res.content_snippet && (
                                    <div style={{
                                        fontSize: '0.85rem',
                                        color: '#444',
                                        fontStyle: 'italic',
                                        whiteSpace: 'pre-wrap'
                                    }}>
                                        {res.content_snippet}
                                        {res.content_snippet.length >= 200 ? '...' : ''}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
