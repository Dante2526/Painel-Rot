
import json
import os

input_path = 'C:/Users/nayla/gravity/Painel-Rot/02250421.dat'
output_path = 'C:/Users/nayla/gravity/Painel-Rot/02250421_decoded.json'

def decode_wabtec_evo(path):
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    
    with open(path, 'rb') as f:
        data = f.read()

    packets = []
    VALID_MARKERS = [0x01, 0x03]
    
    i = 0
    while i < len(data) - 43:
        marker = data[i]
        if marker in VALID_MARKERS:
            packet = data[i:i+43]
            
            # Decodificação básica baseada no parser.ts
            decoded_packet = {
                "offset": i,
                "marker": marker,
                "channels": {f"offset_{j}": packet[j] for j in range(43)},
                "buzina": 1 if (packet[20] & 0x20) else 0,
                "sino": 1 if (packet[20] & 0x40) else 0
            }
            packets.append(decoded_packet)
            i += 43 # Pula o pacote
        else:
            i += 1 # Procura o próximo marcador

    return {
        "filename": os.path.basename(path),
        "total_packets": len(packets),
        "data": packets
    }

if __name__ == "__main__":
    result = decode_wabtec_evo(input_path)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Decodificação concluída. {result['total_packets']} pacotes salvos em {output_path}")
