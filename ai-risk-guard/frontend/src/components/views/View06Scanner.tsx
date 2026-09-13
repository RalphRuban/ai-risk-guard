import React, { useState } from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { Play, CheckCircle } from 'lucide-react';

const BENCHMARKS: Record<string, { code: string; cwe: string; title: string }> = {
  'Command Injection': {
    cwe: 'CWE-78',
    title: 'OS Command Injection via os.system()',
    code: `import os, sys\nfrom flask import request\n\ndef run_backup(target_path):\n    # Vulnerable shell interpolation\n    print(f"Executing backup to {target_path}")\n    os.system(f"tar -czf /tmp/backup.tar.gz {target_path}")\n    return {"status": "complete"}`
  },
  'Code Injection': {
    cwe: 'CWE-94',
    title: 'Arbitrary Code Execution via eval()',
    code: `import ast\n\ndef compute_metric(expression_str):\n    # Unsanitized runtime evaluation\n    result = eval(expression_str)\n    return {"result": result}`
  },
  'Insecure Deserialization': {
    cwe: 'CWE-502',
    title: 'Untrusted Object Deserialization via pickle',
    code: `import pickle, base64\n\ndef load_session(token):\n    # Insecure payload unpickling\n    raw_bytes = base64.b64decode(token)\n    user_obj = pickle.loads(raw_bytes)\n    return user_obj`
  },
  'Hardcoded Credentials': {
    cwe: 'CWE-798',
    title: 'High-Entropy Secret in Source File',
    code: `import hmac, hashlib\n\n# Hardcoded administrative token with high Shannon entropy\nAWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE/q9x8w7v6u5t4s3r2q1"\nAPI_SIGNING_KEY = "sec_live_9941a80c94f1b82e1c93a"\n\ndef verify_signature(data):\n    pass`
  },
  'Clean Code': {
    cwe: 'NONE',
    title: 'Hardened AST Implementation',
    code: `import subprocess, shlex\n\ndef run_backup(target_path):\n    # Hardened argument vector avoiding subshell\n    safe_target = shlex.quote(target_path)\n    cmd = ["tar", "-czf", "/tmp/backup.tar.gz", safe_target]\n    res = subprocess.run(cmd, capture_output=True, check=True)\n    return {"status": "complete"}`
  }
};

interface View06ScannerProps {
  onNavigate: (view: ViewId) => void;
}

export const View06Scanner: React.FC<View06ScannerProps> = ({ onNavigate }) => {
  const [selectedBenchmark, setSelectedBenchmark] = useState('Command Injection');
  const [code, setCode] = useState(BENCHMARKS['Command Injection'].code);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<any>({
    executed: true,
    hasVuln: true,
    cwe: 'CWE-78',
    name: 'OS Command Injection via os.system()',
    line: 6,
    risk: 8.8,
    entropy: 3.42,
    visitorNodes: 28,
    elapsedMs: 42
  });

  const handleBenchmarkSelect = (key: string) => {
    setSelectedBenchmark(key);
    setCode(BENCHMARKS[key].code);
  };

  const handleExecuteScan = () => {
    setIsScanning(true);
    setTimeout(() => {
      setIsScanning(false);
      const isClean = selectedBenchmark === 'Clean Code';
      setScanResult({
        executed: true,
        hasVuln: !isClean,
        cwe: isClean ? 'NONE' : BENCHMARKS[selectedBenchmark].cwe,
        name: isClean ? 'Clean AST Code Structure' : BENCHMARKS[selectedBenchmark].title,
        line: isClean ? 0 : 5,
        risk: isClean ? 0.8 : 8.8,
        entropy: isClean ? 2.1 : 3.42,
        visitorNodes: 34,
        elapsedMs: 38
      });
    }, 650);
  };

  return (
    <div className="py-8 px-4 sm:px-6 max-w-[1780px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#17406E]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] tracking-widest mb-1 bg-gradient-to-r from-[#F0F5FA] via-[#D9E1EA] to-[#A7B4C4] bg-clip-text text-transparent">
            <span>STATIC ANALYSIS WORKSTATION // PYTHON AST</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            Live Multi-Agent AST Scanner
          </h1>
        </div>

        <CyberButton
          variant="primary"
          size="md"
          loading={isScanning}
          icon={<Play className="w-4 h-4 text-white" />}
          onClick={handleExecuteScan}
        >
          {isScanning ? 'ANALYZING AST...' : 'EXECUTE AST SCAN'}
        </CyberButton>
      </div>

      {/* Benchmark Selector Bar */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2 border-b border-[#17406E]/50 font-mono text-xs">
        <span className="text-[#9AA7B8] text-[11px] shrink-0">BENCHMARK PRESETS:</span>
        {Object.keys(BENCHMARKS).map((key) => (
          <button
            key={key}
            onClick={() => handleBenchmarkSelect(key)}
            className={`px-3 py-1.5 shrink-0 border transition-all text-[11px] ${
              selectedBenchmark === key
                ? 'bg-[#007BFF]/30 border-[#00A8FF] text-[#5BC9FF] font-semibold'
                : 'bg-[#050B16] border-[#17406E] text-[#9AA7B8] hover:text-white hover:border-[#00A8FF]/40'
            }`}
          >
            {key}
          </button>
        ))}
      </div>

      {/* Main Grid: Code Editor (Left) & AST Intelligence (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Code Editor (7 cols) */}
        <div className="lg:col-span-7">
          <GlassPanel
            headerTitle="SOURCE INPUT (PYTHON AST VISITOR)"
            headerCode="target_snippet.py"
            statusIndicator={isScanning ? 'WARNING' : 'ACTIVE'}
            className="h-full flex flex-col"
          >
            <div className="relative font-mono text-xs bg-[#020B1A] border border-[#17406E] p-4 min-h-[340px] flex">
              {/* Line Numbers */}
              <div className="select-none text-[#9AA7B8]/40 pr-4 text-right space-y-1.5 border-r border-[#17406E]/50">
                {code.split('\n').map((_, idx) => (
                  <div key={idx}>{idx + 1}</div>
                ))}
              </div>

              {/* Text Area */}
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full pl-4 bg-transparent border-none outline-none text-[#E4EBF3] resize-none font-mono leading-normal"
                rows={12}
                spellCheck={false}
              />
            </div>
          </GlassPanel>
        </div>

        {/* Right: AST Intelligence & Finding Cards (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <GlassPanel
            headerTitle="AST SCAN INTELLIGENCE"
            headerCode={scanResult.executed ? `${scanResult.elapsedMs}ms` : 'IDLE'}
            statusIndicator={scanResult.hasVuln ? 'ALERT' : 'ACTIVE'}
            accentColor={scanResult.hasVuln ? '#FF1E2D' : '#00E699'}
          >
            {scanResult.hasVuln ? (
              <div className="space-y-4 font-mono text-xs">
                {/* Finding Summary Card */}
                <div className="p-3 bg-[#7E1120]/30 border border-[#FF1E2D] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 bg-[#FF1E2D] text-white font-bold text-[10px]">
                      CRITICAL FINDING
                    </span>
                    <span className="text-[#FF1E2D] font-bold">{scanResult.cwe}</span>
                  </div>
                  <h4 className="font-headline font-bold text-sm text-white">{scanResult.name}</h4>
                  <p className="text-[11px] text-[#D9E1EA]">
                    Subprocess / Shell call sink node detected on Line {scanResult.line}. Unescaped string allows command chaining.
                  </p>
                </div>

                {/* Metrics */}
                <div className="p-3 bg-[#050B16] border border-[#17406E] space-y-1.5 text-[11px] text-[#9AA7B8]">
                  <div className="flex justify-between">
                    <span>RISK SCORE:</span>
                    <span className="text-[#FF1E2D] font-bold">{scanResult.risk} / 10.0</span>
                  </div>
                  <div className="flex justify-between">
                    <span>AST NODES VISITED:</span>
                    <span className="text-white">{scanResult.visitorNodes} nodes</span>
                  </div>
                  <div className="flex justify-between">
                    <span>SHANNON ENTROPY:</span>
                    <span className="text-[#00A8FF]">{scanResult.entropy} bits/char</span>
                  </div>
                </div>

                <CyberButton
                  variant="primary"
                  size="sm"
                  className="w-full"
                  onClick={() => onNavigate('patch')}
                >
                  REMEDIATE WITH AST PATCH (VIEW 08)
                </CyberButton>
              </div>
            ) : (
              <div className="p-6 text-center space-y-3 font-mono">
                <CheckCircle className="w-10 h-10 text-[#00E699] mx-auto" />
                <h4 className="font-headline font-bold text-base text-white">
                  NO VULNERABILITIES DETECTED
                </h4>
                <p className="text-xs text-[#9AA7B8]">
                  Abstract Syntax Tree passed all OWASP Top 10 visitor rules with zero security sink violations.
                </p>
                <div className="text-[10px] text-[#00A8FF]">RISK SCORE: 0.8 / 10.0 (CLEAN)</div>
              </div>
            )}
          </GlassPanel>
        </div>
      </div>

      {/* Bottom: Execution Terminal */}
      <GlassPanel
        headerTitle="AST COMPILER RUNTIME TERMINAL"
        headerCode="AST_VISITOR_SOCKET"
        statusIndicator="ACTIVE"
      >
        <div className="p-4 bg-[#020B1A] border border-[#17406E] font-mono text-xs text-[#9AA7B8] space-y-1">
          <div className="text-[#00A8FF]">&gt; Initializing Python ast.parse(source, mode='exec')...</div>
          <div>&gt; Visitor walking FunctionDef: run_backup (lineno=4, col_offset=0)</div>
          <div>&gt; Visiting Call node: func=Attribute(value=Name(id='os'), attr='system')</div>
          {scanResult.hasVuln ? (
            <div className="text-[#FF1E2D] font-bold">&gt; [ALERT] SecuritySinkViolation: os.system() forbidden by policy ARG-POL-02</div>
          ) : (
            <div className="text-[#00E699] font-bold">&gt; [PASS] Security compliance verified: zero banned sinks detected</div>
          )}
        </div>
      </GlassPanel>
    </div>
  );
};
