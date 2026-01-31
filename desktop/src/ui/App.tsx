import React, { useState } from 'react';
import Header from './Header';
import SearchBox from './SearchBox';
import ResultsList from './ResultsList';
import { askQuestion } from '../api';

export default function App() {
    const [results, setResults] = useState([]);
    const [answer, setAnswer] = useState<string | undefined>(undefined);
    const [loading, setLoading] = useState(false);

    const handleSearch = async (query: string) => {
        setLoading(true);
        setAnswer(undefined);
        setResults([]);

        try {
            const response = await askQuestion(query);
            setAnswer(response.answer);
            // For now we don't have direct access to "sources" metadata in the same structure as search
            // but in a real app we'd map sources to file objects
            if (response.sources) {
                setResults(response.sources.map((s: string) => ({ path: s, type: 'source' })));
            }
        } catch (err) {
            console.error(err);
            setAnswer("Error communicating with LocalMind core.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', color: '#333' }}>
            <Header />
            <SearchBox onSearch={handleSearch} isLoading={loading} />
            <ResultsList results={results} answer={answer} />
        </div>
    );
}
