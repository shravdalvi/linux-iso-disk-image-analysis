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

const ExplanationBox = ({ text }) => {
  if (!text) return null;
  return (
    <div className="explanation-box" style={{ padding: '0.75rem', background: 'rgba(0,100,255,0.1)', borderRadius: '6px', marginTop: '0.5rem', borderLeft: '3px solid #007bff' }}>
      <strong>Explanation:</strong> {text}
    </div>
  );
};

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
        <ExplanationBox text={data.explanation} />
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
        <ExplanationBox text={data.explanation} />
      </div>
    );
  }
  
  if (agentName === 'Checksum') {
    return (
      <div className="agent-details">
        <DataRow label="SHA256" value={data.calculated_sha256} />
        <DataRow label="Status" value={data.status} />
        <ExplanationBox text={data.explanation} />
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
        <ExplanationBox text={data.explanation} />
      </div>
    );
  }

  if (agentName === 'OCR') {
    return (
      <div className="agent-details">
        <DataRow label="Scanned" value={data.ocr_scanned ? 'Yes' : 'No'} />
        <div className="badge-grid">
          <BooleanBadge label="Suspicious Text Found" value={data.suspicious_text_found} />
        </div>
        <ArrayList label="Found Words" items={data.found_words} />
        <ExplanationBox text={data.explanation} />
      </div>
    );
  }

  if (agentName === 'Alerting') {
    return (
      <div className="agent-details">
        <DataRow label="Final Status" value={data.status} />
        <DataRow label="Severity" value={data.severity} />
        <DataRow label="Risk Score" value={data.risk_score} />
        {data.risk_percentage !== undefined && (
          <DataRow label="Risk Percentage" value={`${data.risk_percentage}%`} />
        )}
        <ArrayList label="Reasons" items={data.reasons} />
        {data.formula_used && (
          <div className="command-output" style={{ marginTop: '0.5rem' }}>
            <span className="data-label">Calculation Formula Used</span>
            <code>{data.formula_used}</code>
          </div>
        )}
        <ExplanationBox text={data.explanation} />
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
  const [testFiles, setTestFiles] = useState([]);
  const [view, setView] = useState('upload'); // upload, results, history

  useEffect(() => {
    if (view === 'history') {
      fetch('http://localhost:8000/scans')
        .then(res => res.json())
        .then(data => setScans(data))
        .catch(err => console.error(err));
    }
    
    // Fetch test files on mount
    fetch('http://localhost:8000/test-files')
      .then(res => res.json())
      .then(data => setTestFiles(data))
      .catch(err => console.error(err));
  }, [view]);

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const processStream = async (response) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    
    let agentsData = {};
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      
      for (const line of lines) {
        if (line.trim()) {
          const data = JSON.parse(line);
          if (data.step === 'complete') {
            setResult(prev => ({
              ...prev,
              ...data,
              agents: agentsData,
              current_agent: null
            }));
          } else if (data.step !== 'init') {
            if (data.status === 'running') {
              setResult(prev => ({ ...prev, current_agent: data.step }));
            } else if (data.status === 'done') {
              agentsData[data.step] = data.result;
              setResult(prev => ({ 
                ...prev, 
                agents: { ...prev.agents, [data.step]: data.result },
                current_agent: null 
              }));
            }
          }
        }
      }
    }
  };

  const handleTestScan = async (fileName) => {
    setScanning(true);
    setView('results');
    setResult({ file_name: fileName, status: "scanning", agents: {}, current_agent: null });
    
    try {
      const response = await fetch('http://localhost:8000/scan-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_name: fileName })
      });
      await processStream(response);
    } catch (err) {
      alert('Error during test scan: ' + err.message);
    } finally {
      setScanning(false);
    }
  };

  const handleScan = async () => {
    if (!file) return;
    setScanning(true);
    setView('results');
    setResult({ file_name: file.name, status: "scanning", agents: {}, current_agent: null });
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/scan', {
        method: 'POST',
        body: formData,
      });
      await processStream(response);
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

          <hr style={{ margin: '2rem 0', opacity: 0.2 }} />
          <h2>Test Agents Pipeline</h2>
          <p style={{ opacity: 0.8, marginBottom: '1rem' }}>Select a predefined test file to test the agents.</p>
          <div className="test-files-grid" style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
            {testFiles.map(tf => (
              <button 
                key={tf} 
                className="secondary-btn" 
                onClick={() => handleTestScan(tf)}
                disabled={scanning}
                style={{ padding: '0.75rem 1rem', background: '#2c3e50', border: '1px solid #34495e', borderRadius: '4px', color: 'white', cursor: scanning ? 'not-allowed' : 'pointer' }}
              >
                {tf}
              </button>
            ))}
            {testFiles.length === 0 && <p className="muted">No test files found.</p>}
          </div>
          {scanning && <div className="loader" style={{ marginTop: '1rem' }}></div>}
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
            {result.final_status ? (
              <div className="badges">
                <span className={`badge big ${result.severity?.toLowerCase()}`}>
                  Status: {result.final_status}
                </span>
                <span className={`badge big ${result.severity?.toLowerCase()}`}>
                  Severity: {result.severity}
                </span>
                <span className="badge big neutral">
                  Risk Score: {result.risk_score}/100
                </span>
              </div>
            ) : (
              <div className="badges">
                <span className="badge big neutral">Scanning in progress...</span>
              </div>
            )}
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
            
            {result.current_agent && (
              <div className="card agent-card running">
                <div className="agent-header">
                  <div className="agent-icon">{getAgentIcon(result.current_agent)}</div>
                  <h3>{result.current_agent} Agent</h3>
                  <div className="loader-small"></div>
                </div>
                <div className="agent-details">
                  <p>Processing...</p>
                </div>
              </div>
            )}
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
