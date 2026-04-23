"""
Engenharia reversa profunda do arquivo 02250421.dat
Analise direta do binario para encontrar estrutura real dos pacotes.

Objetivo: encontrar padrão de abastecimento (BP supply) prolongado de ~13 min
"""

import struct
import os

FILE = 'c:/Users/nayla/.antigravity/Painel-Rot/02250421.dat'

with open(FILE, 'rb') as f:
    raw = f.read()

print(f"Tamanho total: {len(raw)} bytes")

# ============================================
# 1. Analise do cabecalho
# ============================================
print("\n=== PRIMEIROS 50 BYTES (HEX) ===")
for i in range(0, min(50, len(raw)), 16):
    hex_str = ' '.join(f'{b:02X}' for b in raw[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
    print(f'{i:6d}: {hex_str:<48} {ascii_str}')

# ============================================
# 2. Procurar patterns de byte repetidos (delimitadores de pacote)
# ============================================
print("\n=== BUSCA DE DELIMITADORES ===")

# Procurar bytes que aparecem em intervalos regulares
from collections import Counter

# Tentar encontrar tamanho de pacote analisando repeticoes de padroes
for packet_size in range(40, 200):
    # Contar quantos vezes o byte na posicao 0 se repete a cada packet_size
    if len(raw) < packet_size * 10:
        continue
    matches = 0
    first_byte = raw[25]  # primeiro pacote comeca no offset 25 pelo JSON
    for i in range(25, len(raw) - packet_size, packet_size):
        if raw[i] == first_byte:
            matches += 1
    total = (len(raw) - 25) // packet_size
    ratio = matches / total if total > 0 else 0
    if ratio > 0.7 and total > 10:
        print(f"  Tamanho {packet_size}: {matches}/{total} = {ratio:.1%} matches")

# Verificar a cada byte de 0x03 (marker 3) qual e a distancia
print("\n=== DISTANCIAS ENTRE MARCADORES 0x03 ===")
marker_positions = [i for i in range(len(raw)) if raw[i] == 0x03]
if len(marker_positions) > 2:
    m_diffs = [marker_positions[i+1] - marker_positions[i] for i in range(min(100, len(marker_positions)-1))]
    for d, c in Counter(m_diffs).most_common(15):
        print(f"  Distancia {d}: {c}x")

# ============================================
# 3. Verificar se 0x03 nos offsets do JSON sao realmente marcadores
# ============================================
print("\n=== VERIFICACAO DOS OFFSETS DO JSON ===")
import json
with open('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json', 'r') as f:
    decoded = json.load(f)

json_offsets = [p['offset'] for p in decoded['data']]
print(f"Primeiros 15 offsets: {json_offsets[:15]}")
print(f"Diffs entre offsets:")
offset_diffs = [json_offsets[i+1] - json_offsets[i] for i in range(len(json_offsets)-1)]
for d, c in Counter(offset_diffs).most_common(10):
    print(f"  {d}: {c}x")

# ============================================
# 4. Dump detalhado em torno dos offsets 25 e 179 (primeiros 2 pacotes)
# ============================================
print("\n=== PACOTES RAW - PRIMEIROS 5 ===")
for pkt_idx in range(min(5, len(json_offsets))):
    off = json_offsets[pkt_idx]
    pkt = raw[off:off+50]
    print(f"\nPacote {pkt_idx} (offset {off}):")
    hex_str = ' '.join(f'{b:02X}' for b in pkt)
    print(f"  HEX: {hex_str}")
    # Tentar decodificar como valores
    vals = [f'{b:3d}' for b in pkt[:43]]
    print(f"  DEC: {' '.join(vals[:22])}")
    print(f"       {' '.join(vals[22:43])}")

# ============================================
# 5. Tentar abordagem diferente: pacote de 154 bytes (mais comum)
# ============================================
# A diff mais comum entre offsets era ~154 (ou proximo)
# Vamos ver se os pacotes sao realmente de 154 bytes

# Verificar se o dado no meio dos pacotes (entre pos 43 e 154) tem informacao
print("\n\n=== DADOS ALEM DO BYTE 43 (offset 25, primeiro pacote) ===")
pkt = raw[25:25+160]
for i in range(0, 160, 16):
    hex_str = ' '.join(f'{b:02X}' for b in pkt[i:i+16])
    dec_str = ' '.join(f'{b:3d}' for b in pkt[i:i+16])
    print(f"  byte {i:3d}: {hex_str:<48} | {dec_str}")

# ============================================
# 6. Analisar segundo pacote para comparar
# ============================================
print("\n=== DADOS ALEM DO BYTE 43 (offset 179, segundo pacote) ===")
pkt2 = raw[179:179+160]
for i in range(0, 160, 16):
    hex_str = ' '.join(f'{b:02X}' for b in pkt2[i:i+16])
    dec_str = ' '.join(f'{b:3d}' for b in pkt2[i:i+16])
    print(f"  byte {i:3d}: {hex_str:<48} | {dec_str}")

# Comparar os dois pacotes
print("\n=== DIFERENCAS ENTRE PACOTE 0 e PACOTE 1 ===")
for i in range(min(len(pkt), len(pkt2), 160)):
    if pkt[i] != pkt2[i]:
        print(f"  Byte {i}: {pkt[i]:3d} (0x{pkt[i]:02X}) -> {pkt2[i]:3d} (0x{pkt2[i]:02X})")

# ============================================
# 7. Estimar taxa de amostragem
# ============================================
print("\n\n=== ESTIMATIVA DE TAXA DE AMOSTRAGEM ===")
# O arquivo eh 02250421 = provavel data 02/25/04/21 (25 abril 2021? ou 02 25 04:21?)
# Se sao 719 pacotes e a viagem dura ~30 min, rate ~ 1/2.5s
# Se viagem dura ~2 horas, rate ~ 1/10s
# Vamos olhar a velocidade para estimar
print("Velocidade (offset_4 - 128) ao longo do arquivo:")
for i in range(0, len(json_offsets), 50):
    off = json_offsets[i]
    spd = raw[off + 4] - 128
    print(f"  Pacote {i:4d}: velocidade = {spd}")
