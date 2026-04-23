"""
Engenharia reversa do 02250421.dat usando o protocolo DAS III real.
Baseado no parser.ts que identifica tags no fluxo de bytes:
- 0xEB = sincronização de tempo (1 segundo)
- [0x26, 0x82, 0x80] = EG (Brake Pipe / Encanamento Geral)
- [0x84, 0xA8, 0x8A] = BC (Brake Cylinder / Freio Independente)
- [0x82] + [0xB0-0xB8] = Notch (aceleração)
- [0x81, 0x82] = Buzina
- [0x81, 0x84] = Sino

Objetivo: Encontrar evento de abastecimento de ~13 min (BP > 1 min)
"""

import struct
import os
import json

FILE = 'c:/Users/nayla/.antigravity/Painel-Rot/02250421.dat'

with open(FILE, 'rb') as f:
    raw = f.read()

print(f"Tamanho do arquivo: {len(raw)} bytes")

# ============================================
# 1. Contar marcadores 0xEB (cada um = 1 segundo)
# ============================================
eb_positions = [i for i in range(len(raw)) if raw[i] == 0xEB]
print(f"\nTotal de marcadores 0xEB: {len(eb_positions)}")
if eb_positions:
    print(f"Primeiro 0xEB: offset {eb_positions[0]}")
    print(f"Ultimo 0xEB: offset {eb_positions[-1]}")
    print(f"Duração estimada: {len(eb_positions)} segundos = {len(eb_positions)/60:.1f} minutos")

# ============================================
# 2. Buscar tags EG [0x26, 0x82, 0x80]
# ============================================
eg_tag = bytes([0x26, 0x82, 0x80])
eg_positions = []
for i in range(len(raw) - 3):
    if raw[i:i+3] == eg_tag:
        eg_positions.append(i)

print(f"\nTotal de tags EG: {len(eg_positions)}")
if eg_positions:
    print(f"Primeiros 10 offsets EG: {eg_positions[:10]}")
    # Mostrar valores de EG
    print("\nPrimeiros 20 valores EG decodificados (PSI):")
    for j, pos in enumerate(eg_positions[:20]):
        if pos + 3 < len(raw):
            raw_val = raw[pos + 3]
            psi = (raw_val - 64) * 0.625
            print(f"  EG[{j:3d}] offset={pos:6d}: raw=0x{raw_val:02X} ({raw_val:3d}) -> {psi:.1f} PSI")

# ============================================
# 3. Buscar tags BC [0x84, 0xA8, 0x8A]
# ============================================
bc_tag = bytes([0x84, 0xA8, 0x8A])
bc_positions = []
for i in range(len(raw) - 3):
    if raw[i:i+3] == bc_tag:
        bc_positions.append(i)

print(f"\nTotal de tags BC: {len(bc_positions)}")
if bc_positions:
    print("Primeiros 10 valores BC:")
    for j, pos in enumerate(bc_positions[:10]):
        if pos + 3 < len(raw):
            raw_val = raw[pos + 3]
            psi = raw_val - 64
            print(f"  BC[{j:3d}] offset={pos:6d}: raw=0x{raw_val:02X} ({raw_val:3d}) -> {psi} PSI")

# ============================================
# 4. PARSER COMPLETO - segundo a segundo
# ============================================
print("\n\n" + "="*100)
print("PARSER COMPLETO SEGUNDO A SEGUNDO")
print("="*100)

TAGS_EG = [0x26, 0x82, 0x80]
TAGS_BC = [0x84, 0xA8, 0x8A]
TAGS_NOTCH = 0x82
TAGS_HORN = [0x81, 0x82]
TAGS_BELL = [0x81, 0x84]
TAGS_HORN_BELL = [0x81, 0x86]
TAGS_FWD = [0x8C, 0x84, 0x80, 0x80, 0x80]
TAGS_REV = [0x8C, 0x84, 0x80, 0x80, 0x90]
TIME_SYNC = 0xEB

current_second = 0
last_values = {
    'eg': 90.0, 'bc': 0, 'notch': 0, 'buzina': 0, 'sino': 0, 'direcao': 1, 'velocidade': 0
}

seconds_data = []

def fill_second():
    seconds_data.append({
        'second': current_second,
        'eg': last_values['eg'],
        'bc': last_values['bc'],
        'notch': last_values['notch'],
        'buzina': last_values['buzina'],
        'sino': last_values['sino'],
        'direcao': last_values['direcao'],
        'velocidade': last_values['velocidade'],
    })

i = 0
while i < len(raw):
    # Verifica EG tag
    is_eg = (i + 3 < len(raw) and 
             raw[i] == TAGS_EG[0] and raw[i+1] == TAGS_EG[1] and raw[i+2] == TAGS_EG[2])
    
    # Time sync ou EG
    if raw[i] == TIME_SYNC or is_eg:
        if i > 0 or raw[i] == TIME_SYNC:
            fill_second()
            current_second += 1
            last_values['buzina'] = 0
            last_values['sino'] = 0
        
        if raw[i] == TIME_SYNC:
            i += 1
            continue
    
    # Tags
    if i + 3 < len(raw) and raw[i] == TAGS_EG[0] and raw[i+1] == TAGS_EG[1] and raw[i+2] == TAGS_EG[2]:
        last_values['eg'] = (raw[i+3] - 64) * 0.625
        i += 4
        continue
    elif i + 3 < len(raw) and raw[i] == TAGS_BC[0] and raw[i+1] == TAGS_BC[1] and raw[i+2] == TAGS_BC[2]:
        last_values['bc'] = raw[i+3] - 64
        i += 4
        continue
    elif i + 1 < len(raw) and raw[i] == TAGS_HORN_BELL[0] and raw[i+1] == TAGS_HORN_BELL[1]:
        last_values['buzina'] = 1
        last_values['sino'] = 1
        i += 2
        continue
    elif i + 1 < len(raw) and raw[i] == TAGS_HORN[0] and raw[i+1] == TAGS_HORN[1]:
        last_values['buzina'] = 1
        i += 2
        continue
    elif i + 1 < len(raw) and raw[i] == TAGS_BELL[0] and raw[i+1] == TAGS_BELL[1]:
        last_values['sino'] = 1
        i += 2
        continue
    elif raw[i] == TAGS_NOTCH:
        if i + 1 < len(raw):
            next_byte = raw[i+1]
            if 0xB0 <= next_byte <= 0xB8:
                last_values['notch'] = next_byte - 0xB0
        i += 2
        continue
    elif (i + 4 < len(raw) and raw[i] == TAGS_FWD[0] and raw[i+1] == TAGS_FWD[1] and 
          raw[i+2] == TAGS_FWD[2]):
        if raw[i+4] == 0xC0:
            last_values['direcao'] = 1
        elif raw[i+4] == 0xD0:
            last_values['direcao'] = -1
        i += 5
        continue
    
    i += 1

# Fill final
fill_second()

print(f"\nTotal de segundos processados: {len(seconds_data)}")
print(f"Duração total: {len(seconds_data)} seg = {len(seconds_data)/60:.1f} min")

# ============================================
# 5. Tabela resumida (a cada 30 segundos)
# ============================================
print(f"\n{'Seg':>5} | {'Min':>6} | {'EG':>6} | {'BC':>4} | {'Notch':>5} | {'Buz':>3} | {'Dir':>3}")
print("-" * 50)
for d in seconds_data[::30]:
    mins = d['second'] / 60
    print(f"{d['second']:5d} | {mins:6.1f} | {d['eg']:6.1f} | {d['bc']:4d} | {d['notch']:5d} | {d['buzina']:3d} | {d['direcao']:3d}")

# ============================================
# 6. DETECTAR EVENTO DE ABASTECIMENTO PROLONGADO
# ============================================
print("\n\n" + "="*100)
print("DETECÇÃO DE ABASTECIMENTO PROLONGADO (EG subindo sem Notch, trem parado)")
print("="*100)

# O abastecimento é quando:
# - EG está subindo ou estável em valor alto (pressão sendo restaurada)
# - Notch = 0 (sem aceleração)
# - O evento dura mais de 60 segundos

# Vamos procurar períodos onde EG > 70 PSI (abastecendo BP) com Notch = 0
# e duracao > 60 segundos

EG_THRESHOLD = 70  # PSI minimo para considerar abastecimento ativo
MIN_DURATION = 60  # Segundos (1 minuto)

supply_start = None
supply_events = []

for idx, d in enumerate(seconds_data):
    eg_high = d['eg'] >= EG_THRESHOLD
    no_accel = d['notch'] == 0
    
    if eg_high and no_accel:
        if supply_start is None:
            supply_start = idx
    else:
        if supply_start is not None:
            duration = idx - supply_start
            if duration > MIN_DURATION:
                max_eg = max(s['eg'] for s in seconds_data[supply_start:idx])
                min_eg = min(s['eg'] for s in seconds_data[supply_start:idx])
                supply_events.append({
                    'start_sec': seconds_data[supply_start]['second'],
                    'end_sec': seconds_data[idx-1]['second'],
                    'duration': duration,
                    'max_eg': max_eg,
                    'min_eg': min_eg,
                    'start_idx': supply_start,
                    'end_idx': idx - 1,
                })
            supply_start = None

# Fechar evento em aberto
if supply_start is not None:
    duration = len(seconds_data) - supply_start
    if duration > MIN_DURATION:
        max_eg = max(s['eg'] for s in seconds_data[supply_start:])
        min_eg = min(s['eg'] for s in seconds_data[supply_start:])
        supply_events.append({
            'start_sec': seconds_data[supply_start]['second'],
            'end_sec': seconds_data[-1]['second'],
            'duration': duration,
            'max_eg': max_eg,
            'min_eg': min_eg,
            'start_idx': supply_start,
            'end_idx': len(seconds_data) - 1,
        })

print(f"\nEventos de abastecimento com duração > {MIN_DURATION}s encontrados: {len(supply_events)}")
for idx, evt in enumerate(supply_events):
    minutes = evt['duration'] / 60
    is_anomaly = evt['duration'] > 120  # > 2 minutos é suspeito
    marker = " *** DESVIO DETECTADO! ***" if is_anomaly else ""
    print(f"\n{'='*60}")
    print(f"EVENTO {idx + 1}{marker}")
    print(f"  Início: segundo {evt['start_sec']} ({evt['start_sec']/60:.1f} min)")
    print(f"  Fim:    segundo {evt['end_sec']} ({evt['end_sec']/60:.1f} min)")
    print(f"  Duração: {evt['duration']}s = {minutes:.1f} min")
    print(f"  EG: min={evt['min_eg']:.1f} PSI, max={evt['max_eg']:.1f} PSI")
    
    # Detalhes segundo a segundo
    print(f"\n  --- Detalhes (primeiros 30s e últimos 30s) ---")
    start_i = evt['start_idx']
    end_i = evt['end_idx']
    
    show_range = list(range(start_i, min(start_i + 30, end_i + 1)))
    if end_i - start_i > 60:
        show_range.append(-1)  # separator
        show_range.extend(range(max(end_i - 30, start_i + 30), end_i + 1))
    
    for j in show_range:
        if j == -1:
            print(f"  {'...':>5} | {'...':>6} | {'...':>6} | {'...':>4} | {'...':>5}")
            continue
        d = seconds_data[j]
        print(f"  {d['second']:5d} | {d['second']/60:6.1f}m | EG={d['eg']:6.1f} | BC={d['bc']:4d} | N={d['notch']:d}")

# ============================================
# 7. Análise alternativa: EG descendo (ar saindo)
# ============================================
print("\n\n" + "="*100)
print("PERFIL COMPLETO DE EG AO LONGO DO TEMPO")
print("="*100)

# Encontrar onde EG cai significativamente
prev_eg = seconds_data[0]['eg'] if seconds_data else 90
for idx, d in enumerate(seconds_data):
    eg_diff = d['eg'] - prev_eg
    if abs(eg_diff) > 5 or idx % 60 == 0:
        print(f"  Seg {d['second']:5d} ({d['second']/60:6.1f}m): EG={d['eg']:6.1f} PSI (delta={eg_diff:+.1f}), Notch={d['notch']}, BC={d['bc']}")
    prev_eg = d['eg']
