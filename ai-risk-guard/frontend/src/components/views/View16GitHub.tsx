import React from 'react';
import { GlassPanel } from '../common/GlassPanel';
import { CyberButton } from '../common/CyberButton';
import { ViewId } from '../../types';
import { Github, Radio, CheckCircle2, GitPullRequest, ArrowRight, Shield } from 'lucide-react';

export const View16GitHub: React.FC<{ onNavigate: (view: ViewId) => void }> = ({ onNavigate }) => {
  const events = [
    { event: 'pull_request.opened', repo: 'enterprise/payment-api', pr: '#142', time: '8m ago', result: 'SCAN_DISPATCHED' },
    { event: 'pull_request.synchronize', repo: 'enterprise/auth-gateway', pr: '#89', time: '18m ago', result: 'CHECK_PASSED' },
    { event: 'check_suite.requested', repo: 'enterprise/analytics-service', pr: '#54', time: '34m ago', result: 'CHECK_PASSED' },
  ];

  return (
    <div className="py-8 px-4 sm:px-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#1E3C5C]">
        <div>
          <div className="flex items-center space-x-2 font-mono text-[10px] text-[#00CFFF] tracking-widest mb-1">
            <span>INTEGRATION GATEWAY // GITHUB APP RUNTIME</span>
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-white">
            GitHub App & Webhook Ingestion
          </h1>
        </div>

        <CyberButton
          variant="secondary"
          size="sm"
          onClick={() => onNavigate('settings')}
        >
          OPERATOR SETTINGS (VIEW 17)
        </CyberButton>
      </div>

      {/* Connection Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-[#06101F] border border-[#1E3C5C] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#8D9AAA]">
            <Github className="w-4 h-4 text-[#00CFFF]" />
            <span>APP INSTALLATION</span>
          </div>
          <div className="font-headline font-bold text-xl text-white">AUREX Core</div>
          <span className="font-mono text-[10px] text-[#00E699]">● App ID: 948201 (Active)</span>
        </div>

        <div className="p-4 bg-[#06101F] border border-[#1E3C5C] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#8D9AAA]">
            <Radio className="w-4 h-4 text-[#00CFFF]" />
            <span>WEBHOOK LISTENER</span>
          </div>
          <div className="font-headline font-bold text-xl text-[#00CFFF]">POST /webhook</div>
          <span className="font-mono text-[10px] text-[#00E699]">100% Delivery Success</span>
        </div>

        <div className="p-4 bg-[#06101F] border border-[#1E3C5C] space-y-1">
          <div className="flex items-center space-x-2 font-mono text-xs text-[#8D9AAA]">
            <Shield className="w-4 h-4 text-[#00E699]" />
            <span>SECRET VALIDATION</span>
          </div>
          <div className="font-headline font-bold text-xl text-white">HMAC-SHA256</div>
          <span className="font-mono text-[10px] text-[#65E7FF]">Payload verification active</span>
        </div>
      </div>

      {/* Recent Webhook Events */}
      <GlassPanel
        headerTitle="LIVE WEBHOOK DISPATCH INGESTION LOG"
        headerCode="SOCKET_200_OK"
        statusIndicator="ACTIVE"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead className="border-b border-[#1E3C5C] text-[#8D9AAA] text-[10px]">
              <tr>
                <th className="py-2 px-3">EVENT TYPE</th>
                <th className="py-2 px-3">REPOSITORY</th>
                <th className="py-2 px-3">PULL REQUEST</th>
                <th className="py-2 px-3">RECEIVED</th>
                <th className="py-2 px-3 text-right">DISPATCH RESULT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E3C5C]/50 text-[#D7DEE7]">
              {events.map((ev, i) => (
                <tr key={i} className="hover:bg-[#06101F] transition-colors">
                  <td className="py-2.5 px-3 font-semibold text-white">{ev.event}</td>
                  <td className="py-2.5 px-3 text-[#00CFFF]">{ev.repo}</td>
                  <td className="py-2.5 px-3 text-[#65E7FF]">{ev.pr}</td>
                  <td className="py-2.5 px-3 text-[#8D9AAA]">{ev.time}</td>
                  <td className="py-2.5 px-3 text-right">
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-[#00E699]/20 text-[#00E699]">
                      {ev.result}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>
    </div>
  );
};
