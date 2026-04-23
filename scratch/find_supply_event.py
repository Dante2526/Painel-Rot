"""
Engenharia reversa do arquivo 02250421.dat
Objetivo: Encontrar evento de abastecimento de ar (BP supply) 
prolongado (~13 minutos), que excedeu o limite de 1 minuto.

Condições do desvio:
- Trem PARADO (velocidade = 0)
- Sem aceleração (notch = 0)
- Fluxo de ar alto caindo até zero
- Tempo total > 1 minuto
"""

import json
from collections import Counter

FILE = 'c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json'

with open(FILE, 'r') as f:
    data = json.load(f)

packets = data['data']
print(f"Total pacotes: {len(packets)}")
print(f"Primeiro offset: {packets[0]['offset']}")
print(f"Ultimo offset: {packets[-1]['offset']}")

# ============================================
# 1. Determinar intervalo entre pacotes
# ============================================
diffs = [packets[i+1]['offset'] - packets[i]['offset'] for i in range(len(packets)-1)]
print(f"\nDiferencas entre offsets (top 10):")
for d, c in Counter(diffs).most_common(10):
    print(f"  {d} bytes: {c}x")

# O tamanho total do arquivo eh 114816 bytes
# Com 719 pacotes, cada pacote tem ~159.7 bytes de espaco medio
# Se o rate eh 1 pacote/segundo, a viagem dura ~719 segundos (~12 minutos)
# Se o rate eh 1 pacote a cada 3 seg, ~36 minutos
# Precisamos verificar pelo contexto

# ============================================
# 2. Extrair todos os canais relevantes
# ============================================
print("\n\n" + "="*120)
print("ANALISE COMPLETA - TODOS OS PACOTES")
print("="*120)

# Mapeamento de canais conhecidos dos scripts anteriores:
# offset_1 + offset_2 = Fluxo de ar (high byte + low byte)
# offset_3 = ER (Equalizing Reservoir)
# offset_4 = Velocidade
# offset_5 = ? 
# offset_6 = ?
# offset_7 = BC (Brake Cylinder / Freio Independente)
# offset_11 = EG (Brake Pipe / Encanamento Geral)

header = (f"{'Idx':>4} | {'Flow':>7} | {'Spd':>5} | {'EG':>5} | {'ER':>5} | "
          f"{'BC':>5} | {'O5':>5} | {'O6':>5} | {'O8':>5} | {'O9':>5} | {'O10':>5}")
print(header)
print("-" * len(header))

flows = []
speeds = []
egs = []
ers = []
bcs = []

for i, p in enumerate(packets):
    c = p['channels']
    f_val = (c.get('offset_1', 128) - 128) * 256 + (c.get('offset_2', 128) - 128)
    s_val = c.get('offset_4', 128) - 128
    eg_val = c.get('offset_11', 128) - 128
    er_val = c.get('offset_3', 128) - 128
    bc_val = c.get('offset_7', 128) - 128
    o5_val = c.get('offset_5', 128) - 128
    o6_val = c.get('offset_6', 128) - 128
    o8_val = c.get('offset_8', 128) - 128
    o9_val = c.get('offset_9', 128) - 128
    o10_val = c.get('offset_10', 128) - 128
    
    flows.append(f_val)
    speeds.append(s_val)
    egs.append(eg_val)
    ers.append(er_val)
    bcs.append(bc_val)
    
    print(f"{i:4} | {f_val:7} | {s_val:5} | {eg_val:5} | {er_val:5} | "
          f"{bc_val:5} | {o5_val:5} | {o6_val:5} | {o8_val:5} | {o9_val:5} | {o10_val:5}")

# ============================================
# 3. Detectar evento de abastecimento prolongado
# ============================================
print("\n\n" + "="*80)
print("DETECCAO DE EVENTO DE ABASTECIMENTO PROLONGADO")
print("="*80)

# Procurar periodos onde:
# - Velocidade <= 2 (parado)
# - Fluxo > 0 (ar fluindo)
# O evento comeca quando fluxo sobe acima de threshold E trem parado
# O evento inclui quando fluxo cai ate zero, E o tempo continua (trem segue parado)

FLOW_THRESHOLD = 50  # Fluxo minimo para considerar abastecimento ativo
SPEED_THRESHOLD = 5  # Velocidade maxima para considerar "parado"

supply_events = []
event_start = None
flow_was_high = False
flow_reached_zero = False

for i in range(len(packets)):
    speed_low = abs(speeds[i]) <= SPEED_THRESHOLD
    flow_high = flows[i] > FLOW_THRESHOLD
    flow_zero = flows[i] <= 10
    
    if speed_low:
        if flow_high and event_start is None:
            event_start = i
            flow_was_high = True
            flow_reached_zero = False
        elif event_start is not None:
            if flow_zero and flow_was_high:
                flow_reached_zero = True
            # Continua o evento mesmo com fluxo zerado
    else:
        # Trem comecou a se mover - finalizar evento se existir
        if event_start is not None:
            duration = i - event_start
            supply_events.append({
                'start': event_start,
                'end': i - 1,
                'duration_packets': duration,
                'flow_reached_zero': flow_reached_zero,
                'max_flow': max(flows[event_start:i]),
                'avg_flow': sum(flows[event_start:i]) / duration if duration > 0 else 0,
            })
            event_start = None
            flow_was_high = False
            flow_reached_zero = False

# Fechar evento em aberto no final
if event_start is not None:
    duration = len(packets) - event_start
    supply_events.append({
        'start': event_start,
        'end': len(packets) - 1,
        'duration_packets': duration,
        'flow_reached_zero': flow_reached_zero,
        'max_flow': max(flows[event_start:len(packets)]),
        'avg_flow': sum(flows[event_start:len(packets)]) / duration if duration > 0 else 0,
    })

print(f"\nTotal de eventos de abastecimento encontrados: {len(supply_events)}")
for idx, evt in enumerate(supply_events):
    marker = " *** DESVIO!" if evt['duration_packets'] > 60 else ""
    print(f"\nEvento {idx + 1}:{marker}")
    print(f"  Inicio: pacote {evt['start']}")
    print(f"  Fim:    pacote {evt['end']}")
    print(f"  Duracao: {evt['duration_packets']} pacotes")
    print(f"  Fluxo max: {evt['max_flow']}")
    print(f"  Fluxo medio: {evt['avg_flow']:.1f}")
    print(f"  Fluxo chegou a zero: {'SIM' if evt['flow_reached_zero'] else 'NAO'}")
    
    # Mostrar detalhes pacote a pacote do evento
    if evt['duration_packets'] > 30:
        print(f"\n  --- Detalhes do evento ---")
        print(f"  {'Pkt':>4} | {'Flow':>7} | {'Spd':>5} | {'EG':>5} | {'ER':>5} | {'BC':>5}")
        for j in range(evt['start'], min(evt['end'] + 1, evt['start'] + 200)):
            c = packets[j]['channels']
            f_val = flows[j]
            s_val = speeds[j]
            eg_val = egs[j]
            er_val = ers[j]
            bc_val = bcs[j]
            print(f"  {j:4} | {f_val:7} | {s_val:5} | {eg_val:5} | {er_val:5} | {bc_val:5}")


# ============================================
# 4. Analise alternativa: procurar qualquer periodo 
#    prolongado com trem parado (independente do fluxo)
# ============================================
print("\n\n" + "="*80)
print("PERIODOS COM TREM PARADO (VELOCIDADE <= 5)")
print("="*80)

stopped_start = None
for i in range(len(packets)):
    if abs(speeds[i]) <= SPEED_THRESHOLD:
        if stopped_start is None:
            stopped_start = i
    else:
        if stopped_start is not None:
            duration = i - stopped_start
            if duration >= 10:
                max_flow_period = max(flows[stopped_start:i])
                min_flow_period = min(flows[stopped_start:i])
                print(f"\nParado de {stopped_start} ate {i-1} ({duration} pacotes)")
                print(f"  Fluxo: min={min_flow_period}, max={max_flow_period}")
                # Verificar se fluxo caiu durante o periodo
                first_half_flow = sum(flows[stopped_start:stopped_start + duration//2]) / (duration//2) if duration > 1 else 0
                second_half_flow = sum(flows[stopped_start + duration//2:i]) / (duration - duration//2) if duration > 1 else 0
                print(f"  Fluxo medio 1a metade: {first_half_flow:.1f}")
                print(f"  Fluxo medio 2a metade: {second_half_flow:.1f}")
                if first_half_flow > 100 and second_half_flow < first_half_flow * 0.3:
                    print(f"  >>> PADRAO DE ABASTECIMENTO DETECTADO! Fluxo alto -> baixo")
            stopped_start = None

if stopped_start is not None:
    duration = len(packets) - stopped_start
    if duration >= 10:
        max_flow_period = max(flows[stopped_start:])
        min_flow_period = min(flows[stopped_start:])
        print(f"\nParado de {stopped_start} ate FIM ({duration} pacotes)")
        print(f"  Fluxo: min={min_flow_period}, max={max_flow_period}")
