import React from 'react';

interface Result {
    type: string;
    path: string;
    score?: number;
    content_snippet?: string;
}

interface ResultsListProps {
    results: Result[];
    answer?: string;
}

export default function ResultsList({ results, answer }: ResultsListProps) {
    return (
        <div style={{ padding: '0 20px 20px', overflowY: 'auto', height: 'calc(100vh - 150px)' }}>
            {answer && (
                <div style={{
                    background: '#f8f9fa',
                    padding: '15px',
                    borderRadius: '8px',
                    marginBottom: '20px',
                    borderLeft: '4px solid #007AFF'
                }}>
                    <h3 style={{ marginTop: 0, fontSize: '1rem' }}>Answer</h3>
                    <p style={{ lineHeight: '1.5', color: '#333' }}>{answer}</p>
                </div>
            )}

            {results.length > 0 && (
                <div>
                    <h3 style={{ fontSize: '1rem', color: '#555', marginBottom: '10px' }}>Relevant Files</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {results.map((res, i) => (
                            <div key={i} style={{
                                padding: '12px',
                                border: '1px solid #eee',
                                borderRadius: '6px',
                                background: 'white',
                                cursor: 'pointer'
                            }}>
                                <div style={{ fontWeight: 'bold', fontSize: '0.9rem', marginBottom: '4px' }}>
                                    {res.path.split(/[\\/]/).pop()}
                                </div>
                                <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '6px' }}>
                                    {res.path}
                                </div>
                                {res.content_snippet && (
                                    <div style={{ fontSize: '0.85rem', color: '#444', fontStyle: 'italic' }}>
                                        "{res.content_snippet}..."
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
