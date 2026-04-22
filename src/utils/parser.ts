
/**
 * Parser para os binários proprietários da Wabtec (DAS III / Evolution)
 * Baseado em busca de tags e frames por segundo (0xEB).
 */

export interface TelemetryData {
  [key: string]: number[];
}

export const parseWabtecBinary = (buffer: ArrayBuffer): TelemetryData => {
  const data = new Uint8Array(buffer);
  const channels: TelemetryData = {};
  
  // Inicialização de canais conforme especificação DAS III
  const keys = ['eg', 'bc', 'notch', 'buzina', 'sino', 'direcao', 'velocidade', 'reversora'];
  keys.forEach(k => channels[k] = []);

  const TAGS = {
    EG: [0x26, 0x82, 0x80],
    BC: [0x84, 0xE8, 0x8A],
    NOTCH: [0xC2],
    HORN: [0xC1, 0xC2],
    BELL: [0xC1, 0xC4],
    HORN_BELL: [0xC1, 0xC6],
    FWD: [0xCC, 0xC4, 0xC0, 0xC0, 0xC0],
    REV: [0xCC, 0xC4, 0xC0, 0xC0, 0xD0],
    TIME_SYNC: 0xEB
  };

  let currentSecond = 0;
  let lastValues: { [key: string]: number } = {
    eg: 90, bc: 0, notch: 0, buzina: 0, sino: 0, direcao: 1, velocidade: 0
  };

  const fillSecond = () => {
    channels['eg'].push(lastValues.eg);
    channels['bc'].push(lastValues.bc);
    channels['notch'].push(lastValues.notch);
    channels['buzina'].push(lastValues.buzina);
    channels['sino'].push(lastValues.sino);
    channels['direcao'].push(lastValues.direcao);
    channels['velocidade'].push(lastValues.velocidade);
  };

  for (let i = 0; i < data.length; i++) {
    // Sincronia de Tempo (0xEB)
    if (data[i] === TAGS.TIME_SYNC) {
      fillSecond();
      currentSecond++;
      // Reset de flags momentâneas (buzina/sino)
      lastValues.buzina = 0;
      lastValues.sino = 0;
      continue;
    }

    // Busca por Tags
    // EG (&BA)
    if (data[i] === TAGS.EG[0] && data[i+1] === TAGS.EG[1] && data[i+2] === TAGS.EG[2]) {
      lastValues.eg = data[i+3] - 64; // Fórmula: Byte - 64
      i += 3;
    }
    // BC (ДиК)
    else if (data[i] === TAGS.BC[0] && data[i+1] === TAGS.BC[1] && data[i+2] === TAGS.BC[2]) {
      lastValues.bc = data[i+3]; // Assumindo valor bruto por enquanto
      i += 3;
    }
    // HORN+BELL (БЖ)
    else if (data[i] === TAGS.HORN_BELL[0] && data[i+1] === TAGS.HORN_BELL[1]) {
      lastValues.buzina = 1;
      lastValues.sino = 1;
      i += 1;
    }
    // HORN (БВ)
    else if (data[i] === TAGS.HORN[0] && data[i+1] === TAGS.HORN[1]) {
      lastValues.buzina = 1;
      i += 1;
    }
    // BELL (БД)
    else if (data[i] === TAGS.BELL[0] && data[i+1] === TAGS.BELL[1]) {
      lastValues.sino = 1;
      i += 1;
    }
    // NOTCH (В)
    else if (data[i] === TAGS.NOTCH[0]) {
      const nextByte = data[i+1];
      // Mapeamento simplificado de Notch (0xB0 = P0, 0xB3 = P3, etc)
      if (nextByte >= 0xB0 && nextByte <= 0xB8) {
        lastValues.notch = nextByte - 0xB0;
      }
      i += 1;
    }
    // SENTIDO (FWD/REV)
    else if (data[i] === TAGS.FWD[0] && data[i+1] === TAGS.FWD[1] && data[i+2] === TAGS.FWD[2]) {
      if (data[i+4] === 0xC0) lastValues.direcao = 1; // FWD
      else if (data[i+4] === 0xD0) lastValues.direcao = -1; // REV
      i += 4;
    }
  }

  // Se o arquivo não tiver 0xEB, fazemos um fill final para garantir que temos dados
  if (channels['eg'].length === 0) {
    fillSecond();
  }

  console.log(`[Parser DAS III] Scan Finalizado: ${channels['eg'].length} segundos processados.`);
  return channels;
};
