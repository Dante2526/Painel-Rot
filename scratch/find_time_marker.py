"""
Investigação do verdadeiro intervalo de tempo no 02250421.dat

O parser TS usa 0xEB como time sync, mas só encontramos 3 no arquivo.
As 283 tags EG cobrem ~4.8 min se 1 tag/seg, mas precisamos de ~13 min de dados.

Hipótese: cada tag EG NÃO é 1 segundo. O tempo pode vir de:
1. Distância entre tags
2. Outro marcador no stream
3. O arquivo pode ter múltiplas "páginas" de tempo
"""

import os

FILE = 'c:/Users/nayla/.antigravity/Painel-Rot/02250421.dat'

with open(FILE, 'rb') as f:
    raw = f.read()

print(f"Tamanho: {len(raw)} bytes")

# ============================================
# 1. Buscar TODOS os bytes 0xEB e ver contexto
# ============================================
print("\n=== Posições de 0xEB ===")
for i in range(len(raw)):
    if raw[i] == 0xEB:
        context_before = raw[max(0,i-5):i]
        context_after = raw[i+1:i+6]
        print(f"  Offset {i}: ...{' '.join(f'{b:02X}' for b in context_before)} [EB] {' '.join(f'{b:02X}' for b in context_after)}...")

# ============================================
# 2. Encontrar o espaçamento entre tags EG
# ============================================
eg_tag = bytes([0x26, 0x82, 0x80])
eg_positions = []
for i in range(len(raw) - 3):
    if raw[i:i+3] == eg_tag:
        eg_positions.append(i)

print(f"\n=== Espaçamento entre tags EG (283 tags) ===")
eg_diffs = [eg_positions[i+1] - eg_positions[i] for i in range(len(eg_positions)-1)]
from collections import Counter
print("Top 15 espaçamentos:")
for d, c in Counter(eg_diffs).most_common(15):
    print(f"  {d} bytes: {c}x")

print(f"\nMédia: {sum(eg_diffs)/len(eg_diffs):.1f} bytes")
print(f"Min: {min(eg_diffs)}, Max: {max(eg_diffs)}")

# ============================================
# 3. Talvez o time marker seja diferente
#    Vamos procurar bytes que aparecem regularmente
# ============================================
print("\n=== Bytes mais comuns no arquivo ===")
byte_counts = Counter(raw)
for b, c in byte_counts.most_common(20):
    print(f"  0x{b:02X} ({b:3d}): {c:5d}x ({c/len(raw)*100:.1f}%)")

# ============================================
# 4. Vamos procurar padrões de 2 bytes que se repetem regularmente
# ============================================
print("\n=== Procurando time marker alternativo ===")
# O arquivo tem 114816 bytes
# Se a viagem dura 13 minutos = 780 segundos
# Um time marker a cada ~147 bytes

# Procurar bytes que aparecem a cada ~140-160 bytes
for target_byte in range(256):
    positions = [i for i in range(len(raw)) if raw[i] == target_byte]
    if len(positions) > 500 and len(positions) < 1000:
        diffs = [positions[j+1] - positions[j] for j in range(len(positions)-1)]
        avg_diff = sum(diffs) / len(diffs)
        if 100 < avg_diff < 200:
            std_dev = (sum((d - avg_diff)**2 for d in diffs) / len(diffs)) ** 0.5
            if std_dev < 50:
                print(f"  0x{target_byte:02X} ({target_byte:3d}): {len(positions)} ocorrências, "
                      f"espaçamento médio: {avg_diff:.1f} bytes (std: {std_dev:.1f})")

# ============================================
# 5. O marcador 0x03 que aparece a cada ~154 bytes!
#    Relembrando o decode_evo.py que usava 0x03 como marker
# ============================================
print("\n\n=== Analisando marcador 0x03 ===")
marker_03 = [i for i in range(len(raw)) if raw[i] == 0x03]
print(f"Total de 0x03: {len(marker_03)}")

# Filtrar: 0x03 seguido de bytes no range 0x80-0xA0 (como vimos nos pacotes)
valid_03 = []
for pos in marker_03:
    if pos + 6 < len(raw):
        # O byte após 0x03 deve ser no range 0x80-0xC0 (canal 1)
        if 0x80 <= raw[pos+1] <= 0xC0:
            # E byte 6 deve ser 0xCB (constante que vimos)
            if raw[pos+6] == 0xCB or raw[pos+6] in range(0xC0, 0xD0):
                valid_03.append(pos)

print(f"Marcadores 0x03 válidos (seguidos por padrão típico): {len(valid_03)}")
if valid_03:
    diffs_03 = [valid_03[j+1] - valid_03[j] for j in range(len(valid_03)-1)]
    print(f"Espaçamento médio: {sum(diffs_03)/len(diffs_03):.1f} bytes")
    print(f"Min: {min(diffs_03)}, Max: {max(diffs_03)}")
    print(f"\nSe 1 pacote = 1 segundo: {len(valid_03)} seg = {len(valid_03)/60:.1f} min")
    print(f"Se 1 pacote = 3 segundos: {len(valid_03)*3/60:.1f} min")
    
# ============================================
# 6. Olhar para os bytes do cabeçalho do arquivo
#    para encontrar metadata de tempo
# ============================================
print("\n\n=== Cabeçalho do arquivo (primeiros 25 bytes) ===")
for i in range(0, 25, 16):
    hex_str = ' '.join(f'{b:02X}' for b in raw[i:i+16])
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
    print(f"  {i:4d}: {hex_str:<48} {ascii_str}")

# ============================================
# 7. O nome do arquivo "02250421" pode ser 
#    02/25/04:21 = 25 de fevereiro, 04:21
#    Hora de início da viagem?
# ============================================
print("\n=== Análise do nome do arquivo ===")
print("02250421 -> possível: mês 02, dia 25, hora 04:21")
print("Ou: locomotiva 0225, viagem 0421")

# ============================================
# 8. Verificar se há timestamp em segundos BCD nos pacotes
# ============================================
print("\n=== Procurando timestamp nos pacotes 0x03 ===")
if len(valid_03) >= 5:
    for idx in range(5):
        pos = valid_03[idx]
        pkt = raw[pos:pos+26]
        print(f"\nPacote {idx} (offset {pos}):")
        # Bytes 26-42 nos offsets originais poderiam ter tempo
        if pos + 50 < len(raw):
            extra = raw[pos+26:pos+50]
            print(f"  Bytes 26-49: {' '.join(f'{b:02X}' for b in extra)}")
            # Tentar BCD
            for j in range(0, len(extra)-3):
                h = extra[j]
                m = extra[j+1]
                s = extra[j+2]
                if (h >> 4) < 3 and (h & 0xF) < 10 and (m >> 4) < 6 and (m & 0xF) < 10:
                    bcd_h = (h >> 4) * 10 + (h & 0xF)
                    bcd_m = (m >> 4) * 10 + (m & 0xF)
                    bcd_s = (s >> 4) * 10 + (s & 0xF) if (s >> 4) < 6 and (s & 0xF) < 10 else -1
                    if 0 <= bcd_h <= 23 and 0 <= bcd_m <= 59 and 0 <= bcd_s <= 59:
                        print(f"  Possível BCD time em extra[{j}:{j+3}]: {bcd_h:02d}:{bcd_m:02d}:{bcd_s:02d}")

# ============================================
# 9. Análise de fluxo entre tags EG
#    Se as 283 tags EG cobrem ~13 min, cada tag ~ 2.75 seg
# ============================================
print("\n\n=== Assumindo 283 tags EG = ~13 minutos ===")
print("Cada tag EG ~ 2.75 segundos")
print("\nPerfil de EG (cada 10 tags):")
for idx in range(0, len(eg_positions), 10):
    pos = eg_positions[idx]
    if pos + 3 < len(raw):
        raw_val = raw[pos + 3]
        psi = (raw_val - 64) * 0.625
        time_est = idx * 2.75  # estimativa
        print(f"  Tag {idx:3d} (t≈{time_est/60:5.1f}min): EG={psi:6.1f} PSI (raw={raw_val})")
