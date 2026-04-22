
import React, { useState, useEffect, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine 
} from 'recharts';
import { 
  AlertCircle, Train, Settings, FileText, Activity, ShieldCheck, Gauge, Clock, LayoutDashboard, Database, ChevronRight, CheckCircle2, History
} from 'lucide-react';

import { parseWabtecBinary, TelemetryData } from './utils/parser';
import { auditConduction, AuditResult } from './utils/auditor';
import FileUploader from './components/FileUploader';
import InfractionModal from './components/InfractionModal';
import rulesData from './rules.json';

const BIAS = 54;

const CHANNEL_NAMES: Record<string, string> = {
  offset_11: "Encanamento Geral (EG)",
  offset_3: "Reservatório Equilibrante (ER)",
  offset_4: "Velocidade (km/h)",
  offset_7: "Cilindro de Freio (BC)",
  offset_14: "Freio Independente",
  offset_15: "Amperagem (Amp)",
  offset_21: "Sentido (Reversora)",
  offset_0: "Acelerador (Notch)",
  offset_9: "Buzina (Horn)",
  sino: "Sino (Bell)"
};


const App = () => {
  const [fileData, setFileData] = useState<any>(null);
  const [fileName, setFileName] = useState<string>("");
  const [selectedOffset, setSelectedOffset] = useState('offset_1');
  const [viewMode, setViewMode] = useState<'single' | 'multi'>('multi');
  const [activeTab, setActiveTab] = useState<'telemetry' | 'compliance'>('telemetry');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [auditResults, setAuditResults] = useState<AuditResult | null>(null);
  const [showDebug, setShowDebug] = useState(false);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // Estados para Controle de Tempo
  const [fileStartTime, setFileStartTime] = useState<string>("08:00:00");
  const [auditWindow, setAuditWindow] = useState({ start: "00:00:00", end: "23:59:59" });

  const timeToSeconds = (timeStr: string) => {
    const [h, m, s] = timeStr.split(':').map(Number);
    return (h * 3600) + (m * 60) + (s || 0);
  };

  const secondsToTime = (totalSecs: number) => {
    const h = Math.floor(totalSecs / 3600) % 24;
    const m = Math.floor((totalSecs % 3600) / 60);
    const s = totalSecs % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const CHANNEL_CONFIG: Record<string, { bias: number, mult: number }> = {
    offset_11: { bias: 0, mult: 0.5 },    // Calibrado: 178 -> 89 PSI (EG)
    offset_3: { bias: 0, mult: 0.5 },     // Reservatório Equilibrante
    offset_4: { bias: 0, mult: 0.25 },    // Velocidade
    offset_7: { bias: 0, mult: 0.5 },     // Cilindro de Freio
    offset_14: { bias: 0, mult: 0.5 },    // Freio Indep
    offset_15: { bias: 128, mult: 11 },    // Amperagem Evo
    offset_21: { bias: 0, mult: 1 },      // Reversora
    offset_0: { bias: 0, mult: 1 },       // Acelerador Evo (OFF_0)
    offset_9: { bias: 0, mult: 1 }        // Buzina Evo (OFF_9)
  };


  const handleFileLoaded = (buffer: ArrayBuffer, name: string) => {
    const telemetry = parseWabtecBinary(buffer);
    const results = auditConduction(telemetry);
    
    setFileData(telemetry);
    setFileName(name);
    setAuditResults(results);
    setIsModalOpen(true);
    setSelectedOffset('offset_11');
  };

  // Prepara dados formatados para múltiplos canais
  const syncedData = useMemo(() => {
    if (!fileData) return [];
    
    const refChannel = fileData['offset_11'] ? 'offset_11' : Object.keys(fileData)[0];
    const fullLength = fileData[refChannel]?.length || 0;
    
    const windowStartAbs = timeToSeconds(auditWindow.start);
    const windowEndAbs = timeToSeconds(auditWindow.end);
    const logStartBase = timeToSeconds(fileStartTime);

    const dataPoints = [];
    for (let i = 0; i < fullLength; i++) {
      const currentAbsoluteSecs = logStartBase + i; 
      
      if (currentAbsoluteSecs >= windowStartAbs && currentAbsoluteSecs <= windowEndAbs) {
        const entry: any = { 
          index: i,
          timestamp: secondsToTime(currentAbsoluteSecs)
        };
        
        Object.keys(fileData).forEach(offset => {
          const raw = fileData[offset][i];
          const config = CHANNEL_CONFIG[offset] || { bias: 0, mult: 1 };
          let converted = (raw - config.bias) * config.mult;
          
          if (offset === 'offset_7' || offset === 'offset_14') converted = Math.max(0, converted);
          if (offset === 'offset_11' || offset === 'offset_3') converted = Math.min(110, Math.max(0, converted));
          
          entry[offset] = Math.round(converted);
        });
        dataPoints.push(entry);
      }
    }

    // Se o filtro for muito restrito, mostra tudo para evitar tela vazia
    if (dataPoints.length === 0) return [{ timestamp: 'Sem Dados', index: 0 }];

    // Downsampling para performance (max 2000 pontos no gráfico)
    const MAX_POINTS = 2000;
    if (dataPoints.length > MAX_POINTS) {
      const step = Math.ceil(dataPoints.length / MAX_POINTS);
      return dataPoints.filter((_, idx) => idx % step === 0);
    }

    return dataPoints;
  }, [fileData, auditWindow, fileStartTime]);

  // Filtra eventos da auditoria com base na janela selecionada (Tempo Absoluto)
  const filteredEvents = useMemo(() => {
    if (!auditResults) return [];
    const windowStartAbs = timeToSeconds(auditWindow.start);
    const windowEndAbs = timeToSeconds(auditWindow.end);
    const logStartBase = timeToSeconds(fileStartTime);

    return auditResults.events.filter(event => {
      const eventAbsSecs = logStartBase + event.timestamp;
      return eventAbsSecs >= windowStartAbs && eventAbsSecs <= windowEndAbs;
    });
  }, [auditResults, auditWindow, fileStartTime]);


  if (!fileData) {
    return (
      <div className="min-h-screen bg-[#020617] text-slate-100 flex items-center justify-center p-8 font-sans overflow-hidden">
        <div className="max-w-xl w-full text-center">
          <div className="w-20 h-20 bg-blue-600 rounded-3xl flex items-center justify-center shadow-2xl mx-auto mb-8 shadow-blue-600/30">
            <Train size={44} className="text-white" />
          </div>
          <h1 className="text-5xl font-black mb-4 tracking-tighter italic text-transparent bg-clip-text bg-gradient-to-r from-white to-blue-400">PAINEL-ROT</h1>
          <p className="text-slate-400 mb-12 text-lg font-medium leading-relaxed">
            Auditoria avançada de telemetria Wabtec. <br/>
            Carregue os dados da locomotiva para iniciar.
          </p>
          <div className="h-[300px]">
            <FileUploader onFileLoaded={handleFileLoaded} />
          </div>
        </div>
      </div>
    );
  }


  const ESSENTIAL_CHANNELS = ['offset_11', 'offset_7', 'offset_4', 'offset_15', 'offset_9', 'sino'];
  const COLORS: Record<string, string> = {
    offset_11: "#38bdf8", // Sky Blue (EG)
    offset_7: "#f87171",  // Red (BC)
    offset_4: "#fbbf24",  // Amber (Vel)
    offset_15: "#2dd4bf", // Teal (Amperagem)
    offset_9: "#818cf8",    // Indigo (Buzina)
    sino: "#fb923c"       // Orange
  };

  const getUnit = (offset: string) => {
    if (['offset_11', 'offset_3', 'offset_7', 'offset_14'].includes(offset)) return 'PSI';
    if (offset === 'offset_4') return 'km/h';
    if (offset === 'offset_15') return 'Amp';
    if (['offset_9', 'sino'].includes(offset)) return '';
    return '';
  };

  const SyncedChartRow = ({ offset, height = 220, showX = false }: { offset: string, height?: number, showX?: boolean }) => {
    const isBinary = ['offset_9', 'sino', 'offset_21'].includes(offset);
    const currentValue = syncedData[syncedData.length - 1]?.[offset] || 0;
    
    // Escalas fixas para pressões
    const domain = (['offset_11', 'offset_3', 'offset_7', 'offset_14'].includes(offset)) ? [0, 100] : 
                   (offset === 'offset_4') ? [0, 120] : ['auto', 'auto'];
    return (
      <div className={`multi-chart-grid ${isBinary ? 'h-[120px]' : 'h-[240px]'}`}>
        <div className="chart-label-container" style={{ borderLeftColor: COLORS[offset] || '#475569' }}>
          <p className="text-[10px] text-slate-500 uppercase font-black mb-1">CANAL</p>
          <h3 className="text-sm font-bold text-white mb-2">{CHANNEL_NAMES[offset] || offset.toUpperCase()}</h3>
          <div className="flex items-baseline gap-2 mt-auto">
            {isBinary ? (
              <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${currentValue === 1 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                {currentValue === 1 ? 'LIGADO' : 'DESLIGADO'}
              </span>
            ) : (
              <>
                <span className="text-2xl font-black leading-none" style={{ color: COLORS[offset] }}>
                  {currentValue}
                </span>
                <span className="text-[10px] text-slate-500 font-bold uppercase">{getUnit(offset)}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex-1 bg-slate-900/40 rounded-[1.5rem] p-4 relative overflow-hidden">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={syncedData} syncId="wabtec" onMouseMove={(e) => e.activePayload && setHoverIndex(e.activePayload[0].payload.index)}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.02)" vertical={false} />
              <XAxis 
                dataKey="timestamp" 
                hide={!showX} 
                stroke="rgba(255,255,255,0.1)" 
                tick={{fill: 'rgba(255,255,255,0.3)', fontSize: 9}}
                minTickGap={60}
              />
              <YAxis 
                stroke="rgba(255,255,255,0.1)" 
                tick={{fill: 'rgba(255,255,255,0.3)', fontSize: 10}} 
                domain={domain as any}
                width={35}
                hide={isBinary}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                itemStyle={{ color: COLORS[offset] || '#fff', fontWeight: 'bold', fontSize: '12px' }}
                labelStyle={{ color: '#64748b', fontSize: '10px', marginBottom: '4px' }}
              />
              <Line 
                type={isBinary ? "stepAfter" : "monotone"} 
                dataKey={offset} 
                stroke={COLORS[offset] || '#475569'} 
                strokeWidth={isBinary ? 2 : 3} 
                dot={false}
                activeDot={{ r: 6, fill: COLORS[offset] || '#fff', stroke: '#020617', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 p-8 font-sans scroll-smooth">
      <InfractionModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        infractions={auditResults?.events || []}
        totalSamples={syncedData.length}
      />

      {/* Header Premium */}
      <header className="flex justify-between items-center mb-10 border-b border-white/5 pb-8">
        <div className="flex items-center gap-6">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-500/20 cursor-pointer" onClick={() => setFileData(null)}>
            <Train size={36} className="text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-3">
              <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-[10px] font-bold uppercase tracking-widest rounded-full border border-blue-500/20">
                Monitoramento em Tempo Real
              </span>
            </div>
            <div className="flex items-center gap-6">
              <h1 className="text-4xl font-black tracking-tight text-white uppercase italic">Painel-Rot</h1>
              
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => setShowDebug(!showDebug)}
                  className={`px-4 py-2 rounded-full text-[10px] font-black transition-all ${showDebug ? 'bg-orange-500 text-white shadow-[0_0_15px_rgba(249,115,22,0.4)]' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}
                >
                  {showDebug ? 'MODO ENGENHARIA ATIVO' : 'CALIBRAR OFFSETS'}
                </button>
                <div className="px-6 py-2 bg-blue-600/20 border border-blue-500/30 rounded-full">
                  <span className="text-blue-400 text-[10px] font-black tracking-widest animate-pulse uppercase">
                    MODO EVO ATIVO: {Object.values(fileData)[0]?.length || 0} AMOSTRAS
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Navigation Tabs */}
        <nav className="flex bg-slate-900/50 p-1.5 rounded-2xl border border-white/5 mx-8">
          <button 
            onClick={() => setActiveTab('telemetry')}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'telemetry' ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'text-slate-400 hover:text-white'}`}
          >
            <Activity size={18} /> Telemetria
          </button>
          <button 
            onClick={() => setActiveTab('compliance')}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'compliance' ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20' : 'text-slate-400 hover:text-white'}`}
          >
            <ShieldCheck size={18} /> Auditoria de Condução
          </button>
        </nav>

        <div className="flex gap-4">
           {/* Seletores de Tempo */}
           <div className="flex bg-white/5 p-1 rounded-xl border border-white/5 items-center px-3 gap-4">
             <div className="flex items-center gap-2">
               <Clock size={14} className="text-blue-400" />
               <span className="text-[10px] font-bold text-slate-500 uppercase">Início Log:</span>
               <input 
                 type="text" 
                 value={fileStartTime} 
                 onChange={(e) => setFileStartTime(e.target.value)}
                 className="bg-transparent border-b border-blue-500/30 text-xs font-mono w-20 focus:outline-none focus:border-blue-500 text-center"
               />
             </div>
             <div className="w-px h-4 bg-white/10" />
             <div className="flex items-center gap-2">
               <History size={14} className="text-emerald-400" />
               <span className="text-[10px] font-bold text-slate-500 uppercase">Janela:</span>
               <input 
                 type="text" 
                 value={auditWindow.start} 
                 onChange={(e) => setAuditWindow({...auditWindow, start: e.target.value})}
                 className="bg-transparent border-b border-emerald-500/30 text-xs font-mono w-20 focus:outline-none focus:border-emerald-500 text-center"
               />
               <span className="text-[10px] text-slate-600">até</span>
               <input 
                 type="text" 
                 value={auditWindow.end} 
                 onChange={(e) => setAuditWindow({...auditWindow, end: e.target.value})}
                 className="bg-transparent border-b border-emerald-500/30 text-xs font-mono w-20 focus:outline-none focus:border-emerald-500 text-center"
               />
             </div>
           </div>

           {/* View Mode Switcher */}
          <div className="flex bg-white/5 p-1 rounded-xl border border-white/5 mr-4">
            <button 
              onClick={() => setViewMode('single')}
              className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all ${viewMode === 'single' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-300'}`}
            >
              Único
            </button>
            <button 
              onClick={() => setViewMode('multi')}
              className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-wider transition-all ${viewMode === 'multi' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-300'}`}
            >
              Multi
            </button>
          </div>

          <button className="bg-white/5 border border-white/10 hover:bg-white/10 text-white px-6 py-3 rounded-2xl font-bold flex items-center gap-3 transition-all">
            <FileText size={20} />
            Gerar Parecer
          </button>
        </div>
      </header>

      {/* Seção de Calibração (Debug) */}
      {showDebug && fileData && (
        <div className="mb-12 p-8 bg-orange-500/5 border border-orange-500/20 rounded-[2.5rem] backdrop-blur-xl">
           <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-orange-500 font-black italic uppercase tracking-tighter text-xl">Painel de Calibração Raw</h3>
                <p className="text-slate-500 text-xs">Passe o mouse no gráfico para ver os valores brutos de cada offset (0-42)</p>
              </div>
              <div className="text-right">
                <span className="block text-[10px] text-slate-500 uppercase font-bold">Amostra Atual</span>
                <span className="text-2xl font-mono font-black text-orange-500">#{hoverIndex ?? 0}</span>
              </div>
           </div>
           
           <div className="grid grid-cols-8 gap-2">
              {Array.from({ length: 43 }).map((_, i) => {
                const offset = `offset_${i}`;
                const val = fileData[offset]?.[hoverIndex ?? 0] ?? 0;
                const isMapped = !!CHANNEL_CONFIG[offset];
                return (
                  <div key={i} className={`p-3 rounded-xl border ${isMapped ? 'bg-blue-500/10 border-blue-500/20' : 'bg-white/5 border-white/5'} flex flex-col items-center justify-center`}>
                    <span className="text-[9px] text-slate-500 font-bold">OFF_{i}</span>
                    <span className={`text-lg font-mono font-black ${isMapped ? 'text-blue-400' : 'text-slate-300'}`}>{val}</span>
                  </div>
                );
              })}
           </div>
        </div>
      )}

      {activeTab === 'telemetry' ? (
        <div className="animate-in fade-in duration-500">
          {viewMode === 'multi' ? (
            <div className="space-y-6">
              {ESSENTIAL_CHANNELS.map((offset, idx) => (
                <SyncedChartRow 
                  key={offset} 
                  offset={offset} 
                  showX={idx === ESSENTIAL_CHANNELS.length - 1} 
                />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-12 gap-8">
               <div className="col-span-3 space-y-8">
                <div className="bg-slate-900/40 border border-white/5 rounded-3xl p-6 backdrop-blur-xl">
                  <h2 className="font-bold mb-6 flex items-center gap-2 opacity-80 uppercase tracking-tighter">
                    <LayoutDashboard size={18} /> Sumário de Dados
                  </h2>
                  <div className="space-y-4">
                    <div className="p-4 bg-white/5 rounded-2xl border border-white/5">
                      <p className="text-[10px] text-slate-500 uppercase font-black mb-1">Amostras</p>
                      <p className="text-2xl font-black">{syncedData.length}</p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 mt-6">
                    <button 
                      onClick={() => setShowDebug(!showDebug)}
                      className={`px-4 py-2 rounded-full text-[10px] font-black transition-all ${showDebug ? 'bg-orange-500 text-white shadow-[0_0_15px_rgba(249,115,22,0.4)]' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}
                    >
                      {showDebug ? 'MODO ENGENHARIA ATIVO' : 'CALIBRAR OFFSETS'}
                    </button>
                  </div>
                </div>

                <div className="bg-slate-900/40 border border-white/5 rounded-3xl p-6">
                  <h2 className="font-bold mb-4 flex items-center gap-2 opacity-80 uppercase tracking-tighter">
                    <Database size={18} /> Seletor de Sinal
                  </h2>
                  <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                    {Object.keys(fileData).map(offset => (
                      <button 
                        key={offset}
                        onClick={() => setSelectedOffset(offset)}
                        className={`w-full text-left px-4 py-2.5 rounded-xl text-xs font-bold transition-all border ${selectedOffset === offset ? 'bg-blue-600/20 border-blue-500/50 text-white' : 'bg-white/5 border-transparent text-slate-400 hover:border-white/10 hover:text-white'}`}
                      >
                        {CHANNEL_NAMES[offset] || `Canal ${offset.split('_')[1]}`}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="col-span-9">
                 <SyncedChartRow offset={selectedOffset} height={500} showX={true} />
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Aba de Conformidade de Condução */
        <div className="grid grid-cols-12 gap-8 animate-in slide-in-from-bottom duration-500">
           <div className="col-span-4 space-y-8">
              <div className="bg-slate-900/40 border border-white/5 rounded-[2.5rem] p-8">
                <h2 className="text-2xl font-black mb-8 flex items-center gap-3">
                  <ShieldCheck size={28} className="text-emerald-500" />
                  Conformidade Operacional
                </h2>
                
                <div className="space-y-4">
                  {[
                    { id: 'arrancada', name: 'Arrancada Segura', desc: 'EG 88-90 PSI, Buzina prévia e Sino ligado.', ok: auditResults?.compliance.arrancada_segura },
                    { id: 'reducao_forte', name: 'Redução Strong (<18 PSI)', desc: 'Evita choques bruscos na composição.', ok: auditResults?.compliance.reducao_forte },
                    { id: 'alivio_rodagem', name: 'Alívio de Rodagem', desc: 'Não aliviar com V < 16 km/h.', ok: auditResults?.compliance.alivio_rodagem },
                    { id: 'teste_marcha', name: 'Teste de Marcha', desc: 'V < 10 km/h, Notch 1-3, queda 6-8 PSI.', ok: auditResults?.compliance.teste_marcha },
                    { id: 'emergencia', name: 'Procedimento Emergência', desc: 'Siga o protocolo de 6 pontos de segurança.', ok: auditResults?.compliance.emergencia_correta }
                  ].map(item => (
                    <div key={item.id} className={`p-5 rounded-3xl border transition-all ${item.ok ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20 shadow-lg shadow-red-500/5'}`}>
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-3">
                           <h3 className={`font-bold ${item.ok ? 'text-emerald-500' : 'text-red-500'}`}>{item.name}</h3>
                        </div>
                        <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-full ${item.ok ? 'bg-emerald-500/20 text-emerald-500' : 'bg-red-500/20 text-red-500'}`}>
                           {item.ok ? 'Conforme' : 'Violação'}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 font-medium mb-3">{item.desc}</p>
                      
                      {/* Detalhamento do Checklist de Emergência se houver erro */}
                      {item.id === 'emergencia' && (
                        <div className="grid grid-cols-2 gap-2 mt-2 pt-3 border-t border-red-500/10">
                          {[
                            { label: 'EG 0 PSI', key: 'eg_zero' },
                            { label: 'Amp 0', key: 'amp_zero' },
                            { label: 'Indep. 72', key: 'indep_ok' },
                            { label: 'Rev. Neutro', key: 'rev_neutro' },
                            { label: 'Sino Off', key: 'sino_off' },
                            { label: 'Notch 0', key: 'notch_zero' },
                          ].map((check, i) => {
                            const pass = (auditResults as any)?.summaryChecklist?.[check.key] ?? auditResults?.compliance.emergencia_correta;
                            return (
                              <div key={i} className="flex items-center gap-1.5">
                                <div className={`w-1.5 h-1.5 rounded-full ${pass ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} />
                                <span className={`text-[9px] ${pass ? 'text-emerald-500/70 font-medium' : 'text-red-500 font-black'}`}>{check.label}</span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
           </div>

           {/* Timeline de Eventos */}
           <div className="col-span-8 bg-slate-900/40 border border-white/5 rounded-[2.5rem] p-10 backdrop-blur-xl">
             <div className="flex justify-between items-center mb-10">
                <h2 className="text-2xl font-black flex items-center gap-3 italic">
                  <History size={26} className="text-blue-500" />
                  Timeline de Eventos Detectados
                </h2>
                <span className="text-xs text-slate-500 font-mono">Mostrando: {filteredEvents.length} de {auditResults?.events.length || 0} eventos</span>
             </div>

             <div className="space-y-4 max-h-[600px] overflow-y-auto px-4 custom-scrollbar">
                {filteredEvents.length ? filteredEvents.map((event, idx) => (
                  <div key={idx} className="group relative flex gap-6 p-6 bg-white/5 hover:bg-white/10 border border-white/5 rounded-[1.8rem] transition-all cursor-crosshair">
                     <div className="flex flex-col items-center">
                        <div className={`w-3 h-3 rounded-full mt-2 ${event.severity === 'INFRAÇÃO' ? 'bg-red-500' : 'bg-blue-500'}`} />
                        <div className="w-px h-full bg-white/10 mt-2" />
                     </div>
                     <div className="flex-1">
                        <div className="flex justify-between items-center mb-2">
                           <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                             {secondsToTime(timeToSeconds(fileStartTime) + event.timestamp)}
                           </span>
                           <span className={`text-[9px] font-black px-2 py-0.5 rounded shadow-sm ${event.severity === 'INFRAÇÃO' ? 'bg-red-600 text-white' : 'bg-blue-600 text-white'}`}>
                              {event.type.replace('_', ' ')}
                           </span>
                        </div>
                        <p className="text-sm font-bold text-slate-200 group-hover:text-white transition-colors">{event.description}</p>
                     </div>
                     <ChevronRight size={20} className="text-slate-800 group-hover:text-blue-500 transition-all self-center" />
                  </div>
                )) : (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-600">
                     <ShieldCheck size={64} className="opacity-10 mb-4" />
                     <p className="text-lg font-black uppercase tracking-tighter italic">Nenhuma anomalia na janela selecionada</p>
                  </div>
                )}
             </div>
           </div>
        </div>
      )}
    </div>
  );
};

export default App;
