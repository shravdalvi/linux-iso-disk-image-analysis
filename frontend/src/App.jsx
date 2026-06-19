import { useState, useEffect } from 'react';
import './index.css';

const BooleanBadge = ({ label, value }) => (
  <div className={`bool-badge ${value ? 'true' : 'false'}`}>
    <span className="bool-label">{label}</span>
    <span className="bool-value">{value ? '✓ Yes' : '✗ No'}</span>
  </div>
);

const DataRow = ({ label, value }) => (
  <div className="data-row">
    <span className="data-label">{label}</span>
    <span className={`data-value ${!value ? 'muted' : ''}`}>{value || 'N/A'}</span>
  </div>
);

const ArrayList = ({ label, items }) => (
  <div className="array-list">
    <span className="data-label">{label}</span>
    {items && items.length > 0 ? (
      <ul>
        {items.map((item, i) => <li key={i}>{item}</li>)}
      </ul>
    ) : (
      <span className="data-value muted" style={{ display: 'block', marginTop: '0.5rem' }}>None</span>
    )}
  </div>
);

const AgentDetails = ({ agentName, data }) => {
  if (agentName === 'Ingestion') {
    return (
      <div className="agent-details">
        <DataRow label="Filename" value={data.filename} />
        <DataRow label="Size" value={data.size_bytes ? `${(data.size_bytes / 1024 / 1024).toFixed(2)} MB` : 'Unknown'} />
        <DataRow label="Extension" value={data.extension} />
        <div className="badge-grid">
          <BooleanBadge label="Readable" value={data.is_readable} />
          <BooleanBadge label="Valid Ext" value={data.valid_iso_extension} />
          <BooleanBadge label="Large Enough" value={data.is_large_enough} />
          <BooleanBadge label="Fake ISO" value={data.fake_iso_detected} />
        </div>
        {data.file_command_output && (
          <div className="command-output">
            <span className="data-label">File Command Output</span>
            <code>{data.file_command_output}</code>
          </div>
        )}
      </div>
    );
  }
  
  if (agentName === 'Metadata') {
    return (
      <div className="agent-details">
        <DataRow label="Volume ID" value={data.volume_id} />
        <div className="badge-grid">
          <BooleanBadge label="Bootable" value={data.is_bootable} />
          <BooleanBadge label="Suspicious" value={data.suspicious_metadata} />
        </div>
        <ArrayList label="Warnings" items={data.warnings} />
      </div>
    );
  }
  
  if (agentName === 'Checksum') {
    return (
      <div className="agent-details">
        <DataRow label="SHA256" value={data.calculated_sha256} />
        <DataRow label="Status" value={data.status} />
      </div>
    );
  }
  
  if (agentName === 'Filesystem') {
    return (
      <div className="agent-details">
        <div className="badge-grid">
          <BooleanBadge label="RPM Sig Failure" value={data.rpm_signature_failure} />
        </div>
        <ArrayList label="Missing Folders" items={data.missing_folders} />
        <ArrayList label="Suspicious Files" items={data.suspicious_files} />
        <ArrayList label="Extracted Images" items={data.extracted_images} />
      </div>
    );
  }
  
  return (
    <div className="agent-details">
      <pre style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px', overflowX: 'auto' }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
};

const getAgentIcon = (name) => {
  switch (name) {
    case 'Ingestion': return '📥';
    case 'Metadata': return '📋';
    case 'Checksum': return '🔢';
    case 'Filesystem': return '📁';
    default: return '🤖';
  }
};

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
                <div className="agent-header">
                  <div className="agent-icon">{getAgentIcon(agentName)}</div>
                  <h3>{agentName} Agent</h3>
                </div>
                <AgentDetails agentName={agentName} data={data} />
              </div>
            ))}
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
