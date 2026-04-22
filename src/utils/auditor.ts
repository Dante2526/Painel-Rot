
/**
 * Motor de Auditoria de Condução
 * Analisa padrões de pressão e tempo para detectar infrações de condução.
 */

export interface AuditEvent {
  type: 'REDUCAO_FORTE' | 'CICLICA' | 'ALIVIO_RODAGEM' | 'FRACIONADA';
  timestamp: number;
  description: string;
  severity: 'ALERTA' | 'INFRAÇÃO';
}

export interface AuditResult {
  events: AuditEvent[];
  compliance: {
    [key: string]: boolean;
  };
  summaryChecklist?: any;
}

interface TelemetryData {
  [key: string]: number[];
}

const BIAS_EG = 54;
const BIAS_BC = 144;
const BIAS_VEL = 120;

export const auditConduction = (data: TelemetryData): AuditResult => {
  const events: AuditEvent[] = [];
  const compliance = {
    reducao_forte: true,
    ciclica: true,
    alivio_rodagem: true,
    fracionada: true,
    arrancada_segura: true,
    emergencia_correta: true,
    teste_marcha: false
  };

  const egRaw = data['offset_11'] || [];
  const erRaw = data['offset_3'] || [];
  const velRaw = data['offset_4'] || [];
  const bcRaw = data['offset_7'] || [];
  const indepRaw = data['offset_14'] || [];
  const ampRaw = data['offset_15'] || [];
  const reverserRaw = data['offset_21'] || [];
  const throttleRaw = data['offset_22'] || [];
  const buzina = data['buzina'] || [];
  const sino = data['sino'] || [];

  const eg = egRaw.map(v => v * 0.5);
  const er = erRaw.map(v => v * 0.5);
  const vel = velRaw.map(v => Math.max(0, v - 128));
  const bc = bcRaw.map(v => v * 0.5);
  const indep = indepRaw.map(v => v * 0.5);
  const amps = ampRaw.map(v => (v - 128) * 11); 

  // --- Cálculo de Imobilização Anterior ---
  let initialStationarySamples = 0;
  for (let i = 0; i < vel.length; i++) {
    if (vel[i] <= 0) initialStationarySamples++;
    else break;
  }
  const stationaryDurationHours = initialStationarySamples / 3600;
  const isTestMandatory = stationaryDurationHours >= 4;

  let lastPressure = eg[0] || 0;
  let lastReleaseTime = -1;
  let isReleased = true;
  let egInitialTest = -1;

  let lastReductionIndex = -30;
  let summaryChecklist: any = null;

  for (let i = 1; i < eg.length; i++) {
    const currentSpeed = vel[i];
    const currentP = eg[i];
    const notch = throttleRaw[i];
    const isNeutral = reverserRaw[i] === 0 || reverserRaw[i] === 136 || reverserRaw[i] === 128;

    // Lógica Teste de Marcha
    if (currentSpeed > 0 && currentSpeed <= 10 && notch >= 1 && notch <= 3 && !isNeutral) {
      if (egInitialTest === -1) egInitialTest = currentP;
      const drop = egInitialTest - currentP;
      if (drop >= 6 && drop <= 12) {
        compliance.teste_marcha = true;
      }
    } else {
      egInitialTest = -1;
    }

    // Se o teste foi detectado ou se a parada não foi comprovadamente > 4h
    if (!isTestMandatory) {
      compliance.teste_marcha = true; 
    }

    // Arrancada Segura
    if (i > 5 && (vel[i-1] <= 0) && (vel[i] > 0)) {
      const pHeader = eg[i];
      const isHorn = buzina[i] === 1 || buzina[i-1] === 1 || buzina[i-2] === 1;
      const isBell = sino[i] === 1;

      if (pHeader < 80 || !isHorn) { // Margem de 80 PSI
        compliance.arrancada_segura = false;
        events.push({
          timestamp: i,
          type: 'ARRANCADA_REGULAR' as any,
          severity: 'ALERTA' as any,
          description: `Arrancada: EG ${pHeader.toFixed(1)} PSI, Buzina: ${isHorn?'OK':'FALTA'}`
        });
      }
    }

    // Emergência
    if (currentP < 15 && lastPressure >= 15) {
      const checkResult = auditEmergencyCheck(i, {
        eg, amps, bc, indep, throttle: throttleRaw, reverser: reverserRaw, buzina, sino
      });
      
      summaryChecklist = checkResult.details;
      if (!checkResult.isPerfect) {
        compliance.emergencia_correta = false;
        events.push({
          timestamp: i,
          type: 'EMERGENCIA_INCORRETA' as any,
          severity: 'INFRAÇÃO' as any,
          description: `Falha no procedimento de emergência: ${checkResult.fails.join(', ')}`,
          details: checkResult
        } as any);
      }
    }

    // Redução Forte (com cooldown de 30s)
    const drop = lastPressure - currentP;
    if (drop > 18 && currentP > 30 && (i - lastReductionIndex > 30)) {
      compliance.reducao_forte = false;
      lastReductionIndex = i;
      events.push({
        timestamp: i,
        type: 'REDUCAO_FORTE' as any,
        severity: 'ALERTA' as any,
        description: `Queda de pressão no EG (${drop.toFixed(1)} PSI).`
      });
    }

    // Outros eventos (cíclica, alívio) suprimidos para limpeza se necessário
    // ... mantendo lógica básica
    lastPressure = currentP;
  }

  return { events, compliance, summaryChecklist };
};

const auditEmergencyCheck = (index: number, data: any) => {
  const windowEnd = Math.min(data.eg.length, index + 30);
  
  const results = {
    eg_zero: data.eg[index] <= 10,
    amp_zero: Math.abs(data.amps[index]) < 50, 
    indep_ok: data.bc.slice(index, windowEnd).some((p: number) => p >= 60) || 
              data.indep.slice(index, windowEnd).some((p: number) => p >= 60), 
    rev_neutro: data.reverser[index] === 0 || data.reverser[index] === 136 || data.reverser[index] === 128,
    notch_zero: data.throttle[index] === 0 || data.throttle[index] === 128,
    sino_off: data.sino[index] === 0,
    buzina_off: data.buzina[index] === 0
  };

  const fails = [];
  if (!results.eg_zero) fails.push("EG não caiu para zero");
  if (!results.amp_zero) fails.push("Acelerador não cortado (Amperagem)");
  if (!results.indep_ok) fails.push("Falta Freio Independente");
  if (!results.rev_neutro) fails.push("Reversora fora do neutro");
  if (!results.notch_zero) fails.push("Ponto do acelerador > 0");

  return {
    isPerfect: Object.values(results).every(v => v === true),
    details: results,
    fails
  };
};
