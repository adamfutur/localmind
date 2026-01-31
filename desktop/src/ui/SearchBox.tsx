import React, { useState } from 'react';

interface SearchBoxProps {
    onSearch: (query: string) => void;
    isLoading: boolean;
}

export default function SearchBox({ onSearch, isLoading }: SearchBoxProps) {
    const [query, setQuery] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (query.trim()) {
            onSearch(query);
        }
    };

    return (
        <form onSubmit={handleSubmit} style={{ padding: '20px' }}>
            <div style={{ display: 'flex', gap: '10px' }}>
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask anything about your files..."
                    style={{
                        flex: 1,
                        padding: '12px',
                        borderRadius: '8px',
                        border: '1px solid #ddd',
                        fontSize: '1rem',
                        outline: 'none'
                    }}
                />
                <button
                    type="submit"
                    disabled={isLoading}
                    style={{
                        padding: '0 20px',
                        borderRadius: '8px',
                        border: 'none',
                        background: isLoading ? '#ccc' : '#007AFF',
                        color: 'white',
                        cursor: isLoading ? 'default' : 'pointer',
                        fontWeight: 'bold'
                    }}
                >
                    {isLoading ? 'Thinking...' : 'Ask'}
                </button>
            </div>
        </form>
    );
}
