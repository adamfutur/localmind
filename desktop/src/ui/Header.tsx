import React from 'react';

export default function Header() {
    return (
        <header style={{
            padding: '20px',
            borderBottom: '1px solid #eee',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
        }}>
            <h1 style={{ margin: 0, fontSize: '1.2rem', color: '#333' }}>🧠 LocalMind</h1>
            <div style={{ fontSize: '0.8rem', color: '#666' }}>Active</div>
        </header>
    );
}
