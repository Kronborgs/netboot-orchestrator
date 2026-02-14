import React, { useState } from 'react';
import { Dashboard } from './pages/Dashboard';
import { Inventory } from './pages/Inventory';
import './styles/index.css';

type Page = 'dashboard' | 'inventory';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');

  return (
    <div className="app">
      <header className="header" style={{ 
        padding: '16px 24px', 
        background: '#0066cc', 
        color: 'white',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ margin: 0 }}>RPi Netboot Orchestrator</h1>
          <nav style={{ display: 'flex', gap: '16px' }}>
            <button
              className={currentPage === 'dashboard' ? 'active' : ''}
              onClick={() => setCurrentPage('dashboard')}
              style={{
                background: currentPage === 'dashboard' ? 'rgba(255,255,255,0.3)' : 'transparent',
                border: 'none',
                color: 'white',
                cursor: 'pointer',
                padding: '8px 16px'
              }}
            >
              Dashboard
            </button>
            <button
              className={currentPage === 'inventory' ? 'active' : ''}
              onClick={() => setCurrentPage('inventory')}
              style={{
                background: currentPage === 'inventory' ? 'rgba(255,255,255,0.3)' : 'transparent',
                border: 'none',
                color: 'white',
                cursor: 'pointer',
                padding: '8px 16px'
              }}
            >
              Inventory
            </button>
          </nav>
        </div>
      </header>

      <main style={{ padding: '24px' }}>
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'inventory' && <Inventory />}
      </main>

      <footer style={{
        padding: '16px 24px',
        background: '#f5f5f5',
        textAlign: 'center',
        borderTop: '1px solid #ddd',
        marginTop: '40px'
      }}>
        <p>RPi Netboot Orchestrator v0.1.0</p>
      </footer>
    </div>
  );
}

export default App;
