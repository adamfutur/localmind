import React, { useState } from 'react';
import Header from './Header';
import IndexBar from './IndexBar';
import SearchBox from './SearchBox';
import ResultsList from './ResultsList';
import { searchFiles } from '../api';
import type { SearchResult } from '../api';

export default function App() {
    const [results, setResults] = useState<SearchResult[]>([]);
    const [query, setQuery] = useState('');
    const [error, setError] = useState<string | undefined>(undefined);
    const [loading, setLoading] = useState(false);

    const handleSearch = async (nextQuery: string) => {
        setLoading(true);
        setError(undefined);
        setResults([]);
        setQuery(nextQuery);

        try {
            const items = await searchFiles(nextQuery);
            setResults(items);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Could not reach the LocalMind backend. Is it running on port 8001?"
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', color: '#333' }}>
            <Header />
            <IndexBar />
            <SearchBox onSearch={handleSearch} isLoading={loading} />
            <ResultsList
                results={results}
                query={query}
                loading={loading}
                error={error}
            />
        </div>
    );
}
