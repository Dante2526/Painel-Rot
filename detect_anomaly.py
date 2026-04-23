
import json
import os

def detect_anomaly(file_path, flow_threshold=300, time_limit_seconds=60):
    if not os.path.exists(file_path): return
    with open(file_path, 'r') as f:
        data = json.load(f)

    packets = data.get('data', [])
    if not packets: return

    # Filtramos o fluxo com uma média móvel simples para evitar resets por ruído
    flows = []
    for p in packets:
        c = p['channels']
        f1, f2 = c.get('offset_1', 128), c.get('offset_2', 128)
        # Se os dados parecem válidos (offset_0 == 3 ou próximo de 128)
        val = (f1 - 128) * 256 + (f2 - 128)
        # Limitamos valores absurdos causados por erro de decodificação
        if val > 30000 or val < -1000: val = 0
        flows.append(val)

    # Suavização por média móvel de 5 segundos
    window = 5
    smooth_flows = []
    for i in range(len(flows)):
        start = max(0, i - window)
        subset = flows[start:i+1]
        smooth_flows.append(sum(subset) / len(subset))

    anomaly_detected = False
    start_idx = -1
    
    for i, flow in enumerate(smooth_flows):
        if flow > flow_threshold:
            if start_idx == -1: start_idx = i
        else:
            if start_idx != -1:
                duration = i - start_idx
                if duration > time_limit_seconds:
                    print(f"\n[!] ANOMALIA DETECTADA em {file_path}")
                    print(f"    Período: Pacote {start_idx} até {i}")
                    print(f"    Duração: {duration}s ({duration/60:.1f} min)")
                    anomaly_detected = True
                start_idx = -1
                
    if start_idx != -1:
        duration = len(smooth_flows) - start_idx
        if duration > time_limit_seconds:
            print(f"\n[!] ANOMALIA DETECTADA (Até o fim) em {file_path}")
            print(f"    Início: Pacote {start_idx} | Duração: {duration}s")
            anomaly_detected = True

    if not anomaly_detected:
        print(f"OK: Nenhuma anomalia detectada em {file_path}")

if __name__ == "__main__":
    detect_anomaly('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json')
