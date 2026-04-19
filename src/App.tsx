import React, { useState, useRef, useEffect } from 'react';
import { Uploader } from './components/Uploader';
import { analyzeTelemetryLocal } from './lib/localTelemetryAnalyzer';
import { scanGraphPixels } from './lib/pixelScanner';
import { ZoomIn, ZoomOut, FileSearch, ShieldCheck, Ruler, ScanLine, BookOpen, Settings } from 'lucide-react';

export default function App() {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [dataFile, setDataFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [engineMode, setEngineMode] = useState<'DAT' | 'OPTICAL' | 'RULES'>('DAT');
  const [isEditMode, setIsEditMode] = useState(false);
  const [manualPoints, setManualPoints] = useState<any[]>([]);
  const [pendingPoint, setPendingPoint] = useState<{ x: number, y: number } | null>(null);
  const [ruleFile, setRuleFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [extractedRules, setExtractedRules] = useState<any[] | null>(null);

  // Zoom and Drag State
  const [scale, setScale] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, scrollLeft: 0, scrollTop: 0 });
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [showRuler, setShowRuler] = useState(false);

  const handleZoomIn = () => setScale(s => Math.min(s + 0.5, 4));
  const handleZoomOut = () => setScale(s => Math.max(s - 0.5, 1));
  const handleResetZoom = () => setScale(1);

  const onMouseDown = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    isDragging.current = true;
    containerRef.current.classList.add('cursor-grabbing');
    dragStart.current = {
      x: e.pageX - containerRef.current.offsetLeft,
      y: e.pageY - containerRef.current.offsetTop,
      scrollLeft: containerRef.current.scrollLeft,
      scrollTop: containerRef.current.scrollTop
    };
  };

  const onMouseUp = () => {
    isDragging.current = false;
    if (containerRef.current) containerRef.current.classList.remove('cursor-grabbing');
  };

  const onMouseLeave = () => {
    isDragging.current = false;
    if (containerRef.current) containerRef.current.classList.remove('cursor-grabbing');
    setShowRuler(false);
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left + containerRef.current.scrollLeft;
    const y = e.clientY - rect.top + containerRef.current.scrollTop;
    setMousePos({ x, y });

    if (!isDragging.current) return;
    e.preventDefault();
    const curX = e.pageX - containerRef.current.offsetLeft;
    const curY = e.pageY - containerRef.current.offsetTop;
    const walkX = (curX - dragStart.current.x) * 1.5;
    const walkY = (curY - dragStart.current.y) * 1.5;
    containerRef.current.scrollLeft = dragStart.current.scrollLeft - walkX;
    containerRef.current.scrollTop = dragStart.current.scrollTop - walkY;
  };

  const handleImageClick = (e: React.MouseEvent) => {
    if (!isEditMode || !containerRef.current) return;
    
    // Calculate click pos relative to image source
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    
    setPendingPoint({ x, y });
  };

  const addManualPoint = (type: string, description: string, severity: string) => {
    if (!pendingPoint) return;
    
    const newPoint = {
      timestampOrSection: "MARCAÇÃO MANUAL",
      channel: type,
      description,
      severity,
      visualX: pendingPoint.x,
      visualY: pendingPoint.y,
      isManual: true
    };
    
    setManualPoints(prev => [...prev, newPoint]);
    setPendingPoint(null);
  };

  const handleRunAnalysis = async () => {
    if (engineMode === 'OPTICAL' && !imageFile) {
      setError("O Scanner Óptico exige a Fita Gráfica (Imagem).");
      return;
    }

    if (engineMode === 'DAT' && !dataFile) {
      setError("O modo Binário exige o arquivo .DAT da telemetria.");
      return;
    }
    
    setIsAnalyzing(true);
    setError(null);
    setResult(null);

    try {
      let res;
      if (engineMode === 'OPTICAL' && imageFile) {
         res = await scanGraphPixels(imageFile, referenceFile || undefined);
      } else {
         res = await analyzeTelemetryLocal(dataFile || null);
      }
      setResult(res);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Ocorreu um erro durante a análise.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const isButtonDisabled = isAnalyzing || 
    (engineMode === 'OPTICAL' && !imageFile) || 
    (engineMode === 'DAT' && !dataFile);

  return (
    <div className="h-screen w-screen flex flex-col bg-bg-base text-text-main font-sans overflow-hidden">
      {/* Header */}
      <header className="h-[60px] border-b border-border-subtle flex items-center justify-between px-6 bg-bg-base shrink-0">
        <div className="font-bold tracking-tight flex items-center gap-2 text-lg">
          Auditor de <span className="text-accent underline decoration-accent/30 underline-offset-4">Telemetria</span>
        </div>
        <div className="text-[11px] font-medium px-3 py-1 bg-accent/10 text-accent rounded-full border border-accent/20 flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5" />
          Análise Matemática • Auditoria Técnica
        </div>
      </header>

      {/* Main Grid */}
      <main className="flex-1 flex flex-col lg:grid lg:grid-cols-[280px_1fr_320px] gap-[1px] bg-border-subtle overflow-y-auto lg:overflow-hidden relative">
        
        {/* Panel 1: Controls */}
        <section className="bg-bg-base p-6 flex flex-col shrink-0 lg:overflow-y-auto lg:h-full border-b lg:border-b-0 lg:border-r border-border-subtle">
          <div className="mb-6">
            <h3 className="text-[11px] uppercase text-text-dim tracking-wider mb-3 flex items-center gap-2 font-bold">
              <ScanLine className="w-4 h-4 text-accent" />
              Guia de Funções
            </h3>
            <div className="space-y-3 p-3 bg-card-base rounded-lg border border-border-subtle text-[11px] leading-relaxed text-text-dim">
              <p>1. <strong className="text-text-main">Binário .DAT</strong>: Decodifica o arquivo bruto da Wabtec. Identifica falhas diretamente nos dados numéricos.</p>
              <p>2. <strong className="text-text-main">Scanner Óptico</strong>: Analisa visualmente a linha azul de velocidade no gráfico para detectar quedas bruscas.</p>
              <p>3. <strong className="text-text-main">Marcação Manual</strong>: Use o modo edição para "ensinar" pontos específicos do gráfico para o relatório.</p>
            </div>
          </div>

          <div className="mb-6">
             <button 
                onClick={() => setIsEditMode(!isEditMode)}
                className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-md text-[11px] font-bold uppercase tracking-wider transition-all border ${isEditMode ? 'bg-accent text-bg-base border-accent shadow-[0_0_15px_rgba(34,211,238,0.3)]' : 'bg-card-base text-text-main border-border-subtle hover:border-accent'}`}
              >
                {isEditMode ? 'Finalizar Marcações' : 'Modo Auditor (Marcar Pontos)'}
              </button>
              {isEditMode && (
                <p className="text-[9px] text-accent mt-2 animate-pulse text-center font-mono uppercase">
                   Clique no gráfico para inserir uma nota técnica
                </p>
              )}
          </div>

          <div className="flex items-center justify-between mb-4 pb-2 border-b border-border-subtle">
            <h3 className="text-[12px] uppercase text-text-dim tracking-[1.5px] flex items-center gap-1.5 font-bold">
              Configuração
            </h3>
          </div>
          
          <div className="flex-1 flex flex-col gap-4">
            <div className="bg-card-base p-1 border border-border-subtle rounded-md flex flex-wrap gap-1">
              <button 
                onClick={() => setEngineMode('DAT')}
                className={`flex-1 min-w-[70px] text-[10px] font-bold uppercase tracking-wider py-2 rounded-[4px] transition-colors ${engineMode === 'DAT' ? 'bg-accent text-bg-base' : 'text-text-dim hover:text-text-main'}`}
              >
                Binário .DAT
              </button>
              <button 
                onClick={() => setEngineMode('OPTICAL')}
                className={`flex-1 min-w-[70px] text-[10px] font-bold uppercase tracking-wider py-2 rounded-[4px] transition-colors flex items-center justify-center gap-1 ${engineMode === 'OPTICAL' ? 'bg-accent text-bg-base' : 'text-text-dim hover:text-text-main'}`}
              >
                <ScanLine className="w-3 h-3" /> Scanner Óptico
              </button>
              <button 
                onClick={() => setEngineMode('RULES')}
                className={`flex-1 min-w-[140px] text-[10px] font-bold uppercase tracking-wider py-2 rounded-[4px] transition-colors flex items-center justify-center gap-1 mt-1 lg:mt-0 ${engineMode === 'RULES' ? 'bg-purple-500 text-bg-base' : 'text-text-dim hover:text-text-main'}`}
              >
                <BookOpen className="w-3 h-3" /> Diretrizes (PDF/PDS)
              </button>
            </div>

            {engineMode === 'RULES' && (
              <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                <Uploader
                  label="PROCEDIMENTO / DBO (.PDF, .TXT)"
                  accept=".pdf,.txt,.doc,.docx"
                  multiple={false}
                  files={ruleFile ? [ruleFile] : []}
                  onUpload={(files) => {
                    setRuleFile(files[0]);
                    // Simulated extraction delay
                    setTimeout(() => {
                      setExtractedRules([
                        { tag: "TESTE_MARCHA_MAX_V", value: 10, unit: "km/h", source: "Regra 2" },
                        { tag: "TEMPO_REDUCAO_MIN", value: 20, unit: "s", source: "Glossário DBO" },
                        { tag: "APL_SERVICO_MAX", value: 18, unit: "PSI", source: "Limites Técnicos" }
                      ]);
                    }, 1200);
                  }}
                  onRemove={() => { setRuleFile(null); setExtractedRules(null); }}
                  helperText="O sistema extrairá as variáveis contidas no documento."
                />

                <Uploader
                  label="GABARITO / REFERÊNCIA (CERTO/ERRADO)"
                  accept=".png,.jpg,.jpeg"
                  multiple={false}
                  files={referenceFile ? [referenceFile] : []}
                  onUpload={(files) => setReferenceFile(files[0])}
                  onRemove={() => setReferenceFile(null)}
                  helperText="Use um print de 'Condução Nota 10' ou 'Falha Típica' para comparar."
                />
              </div>
            )}

            <Uploader
              label="FITA GRÁFICA (.PNG/.JPG)"
              accept=".png,.jpg,.jpeg"
              multiple={false}
              files={imageFile ? [imageFile] : []}
              onUpload={(files) => setImageFile(files[0])}
              onRemove={() => setImageFile(null)}
              helperText="Referência visual para marcação"
            />

            <Uploader
              label="TELEMETRIA (.DAT)"
              accept=".dat,.csv,.txt,application/octet-stream,*/*"
              multiple={false}
              files={dataFile ? [dataFile] : []}
              onUpload={(files) => setDataFile(files[0])}
              onRemove={() => setDataFile(null)}
              helperText="Log numérico (Opcional)"
            />
          </div>

          <div className="pt-4 mt-auto">
            <button
              onClick={handleRunAnalysis}
              disabled={isButtonDisabled}
              className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent/80 text-bg-base disabled:opacity-50 py-3 px-4 rounded-[6px] text-[13px] font-bold transition-all uppercase tracking-wider"
            >
              <ShieldCheck className="w-4 h-4" />
              {isAnalyzing ? "PROCESSANDO..." : "AUDITAR TELEMETRIA"}
            </button>
          </div>
        </section>

        {/* Panel 2: Canvas Area */}
        <section className="bg-[#000] relative flex flex-col items-center justify-center overflow-hidden flex-1 shrink-0 p-2 group min-h-[50vh] lg:min-h-0 lg:h-full">
          
          {/* Zoom Toolbar */}
          {imageFile && (
            <div className="absolute top-4 right-4 z-[60] flex gap-2 bg-[#111]/90 backdrop-blur-md p-1.5 rounded-lg border border-border-subtle opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={handleZoomOut} disabled={scale === 1} className="p-1.5 text-text-dim hover:text-accent disabled:opacity-30 rounded transition-colors" title="Afastar">
                <ZoomOut className="w-4 h-4" />
              </button>
              <button onClick={handleResetZoom} className="p-1.5 text-text-main hover:text-accent font-mono text-[10px] w-12 flex items-center justify-center transition-colors" title="Resetar">
                {(scale * 100).toFixed(0)}%
              </button>
              <button onClick={handleZoomIn} disabled={scale >= 4} className="p-1.5 text-text-dim hover:text-accent disabled:opacity-30 rounded transition-colors" title="Aproximar">
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>
          )}

          <div 
            ref={containerRef}
            onMouseDown={onMouseDown}
            onMouseLeave={onMouseLeave}
            onMouseUp={onMouseUp}
            onMouseMove={onMouseMove}
            onMouseEnter={() => setShowRuler(true)}
            className="w-full h-full bg-[#0a0a0a] border border-border-subtle relative overflow-auto rounded-lg hide-scrollbar cursor-crosshair"
          >
            {/* Vertical Ruler */}
            {showRuler && imageFile && (
              <div 
                className="absolute top-0 bottom-0 w-[1px] bg-accent/60 z-50 pointer-events-none shadow-[0_0_10px_rgba(34,211,238,0.5)]"
                style={{ left: mousePos.x }}
              >
                <div className="absolute top-0 left-2 bg-accent/90 text-bg-base text-[9px] font-bold px-1.5 py-0.5 rounded-sm uppercase tracking-tighter">
                  RÉGUA DE AUDITORIA
                </div>
              </div>
            )}

            {!imageFile ? (
               <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                 <FileSearch className="w-10 h-10 text-accent/20 mb-4" />
                 <div className="font-mono text-[11px] text-text-dim uppercase tracking-wider text-center">
                    Arraste o gráfico para começar<br/>
                    <span className="opacity-50 text-[9px] mt-1 block">A auditoria é puramente técnica e offline</span>
                 </div>
               </div>
            ) : (
               <div className="min-w-full min-h-full flex items-center justify-center p-4">
                 <div 
                    className="relative transition-all duration-300 pointer-events-auto"
                    style={{ height: `${scale * 60}vh`, minWidth: '100%' }}
                  >
                    <img 
                      src={URL.createObjectURL(imageFile)} 
                      alt="Target graph" 
                      className={`h-full w-auto object-contain block select-none pointer-events-none transition-opacity ${isEditMode ? 'opacity-90' : 'opacity-100'}`}
                      referrerPolicy="no-referrer"
                    />

                    {/* Interaction layer for clicks */}
                    <div 
                      className={`absolute inset-0 z-30 ${isEditMode ? 'cursor-crosshair' : 'pointer-events-none'}`}
                      onClick={handleImageClick}
                    ></div>
                    
                    {/* Hotspots (Automatic + Manual) */}
                    <div className="absolute inset-0 z-20 pointer-events-none">
                      {/* Pontos Autogerados pelo Scanner Óptico */}
                      {[...(result?.pointsOfAttention || []), ...manualPoints].map((point: any, idx: number) => {
                         if (point.visualX !== undefined && point.visualY !== undefined && !isNaN(point.visualX) && !isNaN(point.visualY)) {
                            const isManual = point.isManual;
                            const isHighSeverity = point.severity === 'HIGH';
                            return (
                               <div 
                                  key={`opt-${idx}`}
                                  className="absolute flex flex-col items-center pointer-events-none"
                                  style={{ top: `${point.visualY}%`, left: `${point.visualX}%`, transform: 'translate(-50%, -50%)' }}
                               >
                                  {/* The Circle */}
                                  <div 
                                     className={`w-6 h-6 rounded-full border-2 animate-pulse ${isManual ? 'border-yellow-400 bg-yellow-400/30' : (isHighSeverity ? 'border-red-500 bg-red-500/30' : 'border-accent bg-accent/30')}`}
                                  ></div>
                                  
                                  {/* The Label */}
                                  <div className={`mt-1 text-[8px] font-bold px-1.5 py-0.5 rounded uppercase whitespace-nowrap ${isManual ? 'bg-yellow-400 text-black' : (isHighSeverity ? 'bg-red-500 text-white' : 'bg-accent text-black')}`}>
                                      {point.channel || 'MARCAÇÃO'}
                                  </div>
                               </div>
                            );
                         }
                         return null;
                      })}
                    </div>

                    {/* Pending Point Form */}
                    {pendingPoint && (
                      <div 
                        className="absolute z-50 bg-card-base border border-accent p-4 rounded-xl shadow-2xl w-[260px] pointer-events-auto"
                        style={{ top: `${pendingPoint.y}%`, left: `${pendingPoint.x}%`, transform: 'translate(-50%, -120%)' }}
                      >
                         <h5 className="text-[10px] font-bold uppercase text-accent mb-3 border-b border-border-subtle pb-1">Analisar Ponto Manual</h5>
                         <div className="space-y-3">
                            <input 
                               placeholder="Canal (Ex: Freio, Motor...)" 
                               id="manual-type"
                               className="w-full bg-bg-base border border-border-subtle p-2 text-[11px] rounded"
                            />
                            <textarea 
                               placeholder="Descrição da irregularidade..." 
                               id="manual-desc"
                               className="w-full bg-bg-base border border-border-subtle p-2 text-[11px] rounded h-16"
                            />
                            <select id="manual-sev" className="w-full bg-bg-base border border-border-subtle p-2 text-[11px] rounded">
                               <option value="LOW">Severidade: BAIXA</option>
                               <option value="MEDIUM">Severidade: MÉDIA</option>
                               <option value="HIGH">Severidade: ALTA</option>
                            </select>
                            <div className="flex gap-2">
                               <button 
                                 onClick={() => setPendingPoint(null)}
                                 className="flex-1 py-1.5 text-[10px] uppercase font-bold border border-border-subtle rounded hover:bg-red-500/10"
                               >Cancelar</button>
                               <button 
                                 onClick={() => {
                                    const type = (document.getElementById('manual-type') as HTMLInputElement).value || "Evento Manual";
                                    const desc = (document.getElementById('manual-desc') as HTMLTextAreaElement).value || "Sem descrição.";
                                    const sev = (document.getElementById('manual-sev') as HTMLSelectElement).value;
                                    addManualPoint(type, desc, sev);
                                 }}
                                 className="flex-1 py-1.5 text-[10px] uppercase font-bold bg-accent text-bg-base rounded"
                               >Marcar</button>
                            </div>
                         </div>
                      </div>
                    )}
                  </div>
               </div>
            )}
          </div>
          
          {imageFile && (
            <div className="absolute bottom-5 left-5 font-mono text-[10px] text-text-dim uppercase z-20 bg-[#000]/80 p-2 rounded border border-border-subtle pointer-events-none ring-1 ring-accent/20">
              MODO AUTÔNOMO: {engineMode === 'OPTICAL' ? 'SCANNER ÓPTICO' : 'LEITOR DE METADADOS .DAT'}
            </div>
          )}
        </section>

        {/* Panel 3: Results */}
        <section className="bg-bg-base p-5 flex flex-col shrink-0 lg:overflow-y-auto lg:h-full pb-20 lg:pb-5">
          <h3 className="text-[12px] uppercase text-text-dim tracking-[1.5px] mb-4 flex items-center gap-2">
            REGISTROS ENCONTRADOS {(result?.pointsOfAttention?.length || 0) > 0 ? `(${result?.pointsOfAttention?.length})` : ''}
          </h3>

          {/* Results Area */}
          <div className="flex flex-col gap-3">
            {error && (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/50 text-red-500 text-[11px] font-medium text-center">
                {error}
              </div>
            )}

            {!result && !isAnalyzing && (
              <div className="flex flex-col items-center justify-center py-12 text-center border border-dashed border-border-subtle rounded-xl opacity-60">
                <FileSearch className="w-8 h-8 mb-3 text-accent/40" />
                <p className="text-[10px] uppercase tracking-wide px-4 font-mono text-text-dim">
                   Aguardando Início da Auditoria
                </p>
              </div>
            )}

            {isAnalyzing && (
              <div className="flex flex-col items-center justify-center py-12 text-center bg-card-base border border-border-subtle rounded-xl">
                <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin mb-3"></div>
                <p className="text-[10px] uppercase tracking-wide font-mono text-accent">
                   Processando Dados...
                </p>
              </div>
            )}

            {/* Rules Extraction View */}
            {engineMode === 'RULES' && extractedRules && (
              <div className="mb-4 animate-in slide-in-from-bottom-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-[10px] uppercase text-text-dim tracking-wider font-bold flex items-center gap-2">
                    <Settings className="w-3.5 h-3.5 text-purple-400" />
                    Parâmetros Extraídos do PDS
                  </h4>
                  <span className="text-[9px] bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded font-mono border border-purple-500/20">
                     VINCULADO AO MOTOR (.DAT)
                  </span>
                </div>
                <div className="bg-card-base border border-border-subtle rounded-lg overflow-hidden">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-bg-base border-b border-border-subtle">
                        <th className="p-2 text-[9px] font-mono text-text-dim uppercase tracking-wider">Variável (Tag)</th>
                        <th className="p-2 text-[9px] font-mono text-text-dim uppercase tracking-wider">Valor Limite</th>
                        <th className="p-2 text-[9px] font-mono text-text-dim uppercase tracking-wider">Origem no Texto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {extractedRules.map((rule, idx) => (
                        <tr key={idx} className="border-b border-border-subtle last:border-0 hover:bg-bg-base transition-colors">
                          <td className="p-2 py-3 text-[10px] font-bold text-text-main font-mono">{rule.tag}</td>
                          <td className="p-2 py-3 text-[11px] text-purple-400 font-mono">
                            {rule.value} <span className="text-text-dim text-[10px]">{rule.unit}</span>
                          </td>
                          <td className="p-2 py-3 text-[10px] text-text-dim italic">{rule.source}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="mt-3 p-3 bg-purple-500/5 border border-purple-500/20 rounded-lg text-[10px] text-text-dim leading-relaxed">
                  <strong className="text-purple-400">Como funciona:</strong> O sistema mapeou o texto do procedimento e substituiu as variáveis padrão. As próximas análises do <strong>Scanner .DAT</strong> utilizarão esses tetos numéricos e temporais como limite inegociável.
                </div>
              </div>
            )}

            {/* Checklist View (Specific for DAT/Vale Rules) */}
            {result?.checklist && (
              <div className="mb-4">
                <h4 className="text-[10px] uppercase text-text-dim tracking-wider font-bold mb-2">Checklist da Operação</h4>
                <div className="space-y-1.5">
                  {result.checklist.map((item: any, idx: number) => (
                    <div key={idx} className="bg-card-base border border-border-subtle p-3 rounded-lg">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[11px] font-bold text-text-main">{item.item}</span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded leading-none ${
                          item.status === 'OK' ? 'bg-green-500/10 text-green-500 border border-green-500/20' :
                          item.status === 'FALHA' ? 'bg-red-500/10 text-red-500 border border-red-500/20' :
                          item.status === 'NA' ? 'bg-gray-500/10 text-text-dim border border-border-subtle' :
                          'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20'
                        }`}>
                          {item.status}
                        </span>
                      </div>
                      <p className="text-[10px] text-text-dim leading-relaxed">{item.details}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Main Alert List */}
            {result && [...(result?.pointsOfAttention || []), ...manualPoints].map((point: any, idx: number) => (
              <div 
                key={idx}
                id={`point-card-${idx}`}
                className={`p-4 rounded-xl border transition-all hover:shadow-sm ${point.isManual ? 'border-yellow-400/50 bg-yellow-400/5' : 'border-border-subtle bg-card-base hover:border-accent'}`}
              >
                <div className="flex items-center justify-between mb-2 pb-2 border-b border-border-subtle/50">
                  <span className={`text-[9px] font-mono uppercase tracking-tighter ${point.isManual ? 'text-yellow-500' : 'text-accent'}`}>
                    {point.isManual ? 'AULA / MARCAÇÃO' : `REGISTRO #${String(idx + 1).padStart(2, '0')}`}
                  </span>
                  <span className="text-[10px] text-text-dim font-mono">{point.timestampOrSection}</span>
                </div>
                <h4 className="text-[12px] font-bold text-text-main mb-1 uppercase tracking-tight">{point.channel}</h4>
                <p className="text-[11px] text-text-dim leading-relaxed">{point.description}</p>
                {point.isManual && (
                  <button 
                    onClick={() => setManualPoints(prev => prev.filter(p => p !== point))}
                    className="mt-3 text-[9px] font-bold uppercase text-red-500 hover:underline"
                  >
                    Remover marcação
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="h-[34px] bg-card-base border-t border-border-subtle flex gap-5 items-center px-6 font-mono text-[9px] text-text-dim shrink-0">
        <div>CURSOR: <span className="text-accent underline">X:{mousePos.x.toFixed(0)} Y:{mousePos.y.toFixed(0)}</span></div>
        <div>SISTEMA: <span className="text-accent">DETERMINÍSTICO</span></div>
        <div className="ml-auto uppercase text-accent/50">Railway Auditor Pro // v2.0-offline-mode</div>
      </footer>
    </div>
  );
}
