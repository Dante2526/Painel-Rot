
/**
 * Parser para os binários proprietários da Wabtec (.dat)
 * Suporta formatos legados (IFCD) e o novo formato LDP identificado.
 */

export interface TelemetryData {
  [key: string]: number[];
}

export const parseWabtecBinary = (buffer: ArrayBuffer): TelemetryData => {
  const data = new Uint8Array(buffer);
  const channels: TelemetryData = {};
  
  // Inicialização de canais essenciais
  const essentialKeys = [
    'offset_1', 'offset_3', 'offset_4', 'offset_7', 'offset_11', 
    'offset_14', 'offset_15', 'offset_21', 'offset_22', 'buzina', 'sino'
  ];
  essentialKeys.forEach(k => channels[k] = []);

  // Detector de Formato: LDP ou Legado
  const isLDP = data[0] === 0x49 && data[1] === 0x46 && data[2] === 0x43; // "IFCD" header of LDP file

  if (isLDP) {
    console.log("[Parser] Formato LDP Detectado");
    return parseLDP(data);
  } else {
    console.log("[Parser] Formato Legado Detectado");
    return parseLegacy(data);
  }
};

const unescape = (data: Uint8Array) => {
  const out = [];
  for (let j = 0; j < data.length; j++) {
    if (data[j] === 0x10 && j + 1 < data.length) {
      out.push(data[j+1]);
      j++;
    } else {
      out.push(data[j]);
    }
  }
  return new Uint8Array(out);
};

const parseLDP = (data: Uint8Array): TelemetryData => {
  const channels: TelemetryData = {};
  const mapping: Record<string, number> = {
    'offset_4': 0,  // Speed
    'offset_11': 1, // EG
    'offset_14': 2, // FI
    'offset_15': 3, // Current
    'offset_22': 6, // Throttle
  };
  
  Object.keys(mapping).concat(['buzina', 'sino', 'offset_1', 'offset_3', 'offset_7', 'offset_21']).forEach(k => channels[k] = []);

  let i = 0;
  while (i < data.length - 1) {
    if (data[i] === 0x02 && data[i+1] === 0x30) {
      let start = i + 2;
      let j = start;
      let found = false;
      while (j < data.length) {
        if (data[j] === 0x10) { j += 2; continue; }
        if (data[j] === 0x03) {
          const payload = unescape(data.slice(start, j));
          if (payload.length === 9) {
            Object.entries(mapping).forEach(([key, idx]) => {
              channels[key].push(payload[idx]);
            });
            channels['buzina'].push((payload[7] & 0x10) ? 1 : 0);
            channels['sino'].push((payload[7] & 0x01) ? 1 : 0);
            // Preenchimento de compatibilidade
            channels['offset_1'].push(payload[1]);
            channels['offset_3'].push(payload[1]);
            channels['offset_7'].push(payload[2]);
            channels['offset_21'].push(128); // Neutro padrão
          }
          i = j + 1;
          found = true;
          break;
        }
        j++;
      }
      if (!found) break;
    } else {
      i++;
    }
  }
  return channels;
};

const parseLegacy = (data: Uint8Array): TelemetryData => {
  const channels: TelemetryData = {};
  const essentialKeys = [
    'offset_1', 'offset_3', 'offset_4', 'offset_7', 'offset_11', 
    'offset_14', 'offset_15', 'offset_21', 'offset_22', 'buzina', 'sino'
  ];
  essentialKeys.forEach(k => channels[k] = []);

  const VALID_MARKERS = [0x01, 0x03];
  let packetsFound = 0;

  for (let i = 0; i < data.length - 43; i++) {
    const marker = data[i];
    const magic = data[i + 3];

    if (VALID_MARKERS.includes(marker) && (magic >= 0x80 && magic <= 0x9F)) {
      packetsFound++;
      const packet = data.slice(i, i + 43);
      const b20 = packet[20];

      for (let j = 0; j < 43; j++) {
        const key = `offset_${j}`;
        if (!channels[key]) channels[key] = [];
        channels[key].push(packet[j]);
      }
      
      channels['buzina'].push((b20 & 0x20) ? 1 : 0);
      channels['sino'].push((b20 & 0x40) ? 1 : 0);
      i += 25; 
    }
  }

  console.log(`[Parser Evo/Legacy] Scan Finalizado: ${packetsFound} pacotes detectados.`);
  return channels;
};
