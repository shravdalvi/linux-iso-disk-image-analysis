import { useState, useEffect } from 'react';
import './index.css';

function App() {
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [scans, setScans] = useState([]);
  const [view, setView] = useState('upload'); // upload, results, history

  useEffect(() => {
    if (view === 'history') {
      fetch('http://localhost:8000/scans')
        .then(res => res.json())
        .then(data => setScans(data))
        .catch(err => console.error(err));
    }
  }, [view]);

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleScan = async () => {
    if (!file) return;
    setScanning(true);
    setView('upload');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/scan', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setResult(data);
      setView('results');
    } catch (err) {
      alert('Error during scan: ' + err.message);
    } finally {
      setScanning(false);
    }
  };

  const viewScanDetails = async (scanId) => {
    try {
      const response = await fetch(`http://localhost:8000/scan/${scanId}`);
      const data = await response.json();
      // format to match upload result struct
      setResult({
        ...data.scan,
        agents: data.agents
      });
      setView('results');
    } catch (err) {
      alert('Error fetching scan details');
    }
  };

  return (
    <div className="container">
      <header>
        <h1>ISO Guardian 🛡️</h1>
        <p>Agent-Based ISO Integrity Verification System with OCR</p>
        <nav>
          <button onClick={() => setView('upload')}>New Scan</button>
          <button onClick={() => setView('history')}>History</button>
          <a href="http://localhost:3001" target="_blank" rel="noreferrer" className="button-link">Grafana Dashboard</a>
        </nav>
      </header>

      {view === 'upload' && (
        <main className="card">
          <h2>Upload ISO Image</h2>
          <div className="upload-box">
            <input type="file" onChange={handleFileChange} accept=".iso" />
            <p>{file ? file.name : "Select an ISO file"}</p>
          </div>
          <button className="primary-btn" onClick={handleScan} disabled={!file || scanning}>
            {scanning ? 'Scanning...' : 'Start Scan'}
          </button>
          {scanning && <div className="loader"></div>}
        </main>
      )}

      {view === 'history' && (
        <main className="card">
          <h2>Previous Scans</h2>
          <table className="scans-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>File Name</th>
                <th>Status</th>
                <th>Risk Score</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {scans.map(s => (
                <tr key={s.scan_id}>
                  <td>{s.scan_id}</td>
                  <td>{s.file_name}</td>
                  <td><span className={`badge ${s.severity.toLowerCase()}`}>{s.final_status}</span></td>
                  <td>{s.risk_score}</td>
                  <td><button onClick={() => viewScanDetails(s.scan_id)}>View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </main>
      )}

      {view === 'results' && result && (
        <main>
          <div className="summary-card card">
            <h2>Scan Report: {result.file_name}</h2>
            <div className="badges">
              <span className={`badge big ${result.severity.toLowerCase()}`}>
                Status: {result.final_status}
              </span>
              <span className={`badge big ${result.severity.toLowerCase()}`}>
                Severity: {result.severity}
              </span>
              <span className="badge big neutral">
                Risk Score: {result.risk_score}/100
              </span>
            </div>
          </div>

          <div className="agents-grid">
            {Object.entries(result.agents).map(([agentName, data]) => (
              <div className="card agent-card" key={agentName}>
                <h3>{agentName} Agent</h3>
                <pre>{JSON.stringify(data, null, 2)}</pre>
              </div>
            ))}
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
