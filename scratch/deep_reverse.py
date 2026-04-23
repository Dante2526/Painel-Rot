"""
Re-decodificacao do 02250421.dat com analise de pacote COMPLETO.
O decoder original lia apenas 43 bytes, mas os pacotes tem ~154 bytes.

Agora vamos:
1. Decodificar os pacotes corretamente  
2. Entender qual canal realmente representa o fluxo BP
3. Encontrar o evento de abastecimento de ~13 minutos
"""

import struct
import json
import os

FILE = 'c:/Users/nayla/.antigravity/Painel-Rot/02250421.dat'

with open(FILE, 'rb') as f:
    raw = f.read()

print(f"Tamanho total: {len(raw)} bytes")

# ============================================
# 1. Re-decodificar encontrando todos os marcadores 0x03
# ============================================
markers = []
i = 0
while i < len(raw):
    if raw[i] == 0x03:
        # Verificar se parece um pacote valido
        # Os bytes 6-11 devem estar no range tipico
        if i + 26 < len(raw):
            # Heuristica: byte 6 costuma ser 0xCB (203) e byte 9 0xFF (255)
            if raw[i+6] == 0xCB or (raw[i+1] >= 0x80 and raw[i+3] >= 0x80):
                markers.append(i)
    i += 1

print(f"Marcadores 0x03 validos encontrados: {len(markers)}")

# Calcular tamanhos de pacote
packet_sizes = [markers[j+1] - markers[j] for j in range(len(markers)-1)]
from collections import Counter
print("\nTamanhos de pacote:")
for sz, cnt in Counter(packet_sizes).most_common(10):
    print(f"  {sz} bytes: {cnt}x")

# ============================================
# 2. Extrair dados de telemetria usando os primeiros 26 bytes
#    (parte "fixa" do pacote) e tentar entender a parte variavel
# ============================================

# Canais fixos baseados na analise:
# Byte 0: Marker (sempre 0x03)
# Byte 1-2: Possivel fluxo (high/low)  
# Byte 3: Possivel ER
# Byte 4: Possivel velocidade  
# Byte 5: ?
# Byte 6: Sempre ~0xCB (203) - possivel constante/identificador
# Byte 7: Possivel BC
# Byte 8: ?
# Byte 9: Quase sempre 0xFF (255)
# Byte 10: ?
# Byte 11: Possivel EG (Brake Pipe pressure)

# VAMOS testar uma hipotese diferente baseada na Wabtec EVO:
# O valor de pressao BP (brake pipe) geralmente fica entre 80-110 PSI
# Vamos procurar canais que ficam estaveis em torno de ~90 psi

print("\n\n=== VALORES ESTAVEIS NOS PRIMEIROS 26 BYTES (primeiros 20 pacotes) ===")
print(f"{'Byte':>4}", end="")
for i in range(20):
    print(f" | P{i:2d}", end="")
print()

for b in range(26):
    print(f"B{b:2d}:", end="")
    for idx in range(min(20, len(markers))):
        off = markers[idx]
        val = raw[off + b]
        print(f" | {val:3d}", end="")
    print()

# ============================================
# 3. Agora olhar os bytes 1-5 com decodificacao correta
#    e plotar com matplotlib
# ============================================
print("\n\n=== DECODIFICACAO DOS CANAIS PRINCIPAIS ===")

# Extrair todos os valores
all_data = []
for idx, off in enumerate(markers):
    if off + 26 > len(raw):
        break
    pkt = raw[off:off+26]
    
    # Byte 1 e 2 juntos podem formar um valor de 16 bits
    # Ou podem ser dois canais separados de 8 bits
    b1 = pkt[1]  # Varia entre 128-231 -> (b1-128) = 0-103
    b2 = pkt[2]  # Varia entre 0-226
    b3 = pkt[3]  # Varia entre 0-224  
    b4 = pkt[4]  # Varia entre 0-254 (velocidade candidate)
    b5 = pkt[5]  # Varia entre 0-225
    b6 = pkt[6]  # Quase constante ~203
    b7 = pkt[7]  # Varia entre 0-254 (BC candidate)
    b8 = pkt[8]  # Varia entre 0-240
    b9 = pkt[9]  # Quase sempre 255
    b10 = pkt[10] # Varia
    b11 = pkt[11] # Varia entre 0-231 (EG candidate)
    
    # Hipotese: os valores analogicos usam base 128 (0x80)
    # Valor real = byte_value - 128
    ch1 = b1 - 128  # Canal 1
    ch2 = b2 - 128  # Canal 2
    ch3 = b3 - 128  # Canal 3 (ER?)
    ch4 = b4 - 128  # Canal 4 (Speed?)
    ch5 = b5 - 128  # Canal 5
    ch6 = b6 - 128  # Canal 6 (constante)
    ch7 = b7 - 128  # Canal 7 (BC?)
    ch8 = b8 - 128  # Canal 8
    ch9 = b9 - 128  # Canal 9 (constante)
    ch10 = b10 - 128  # Canal 10
    ch11 = b11 - 128  # Canal 11 (EG/BP?)
    
    all_data.append({
        'idx': idx,
        'offset': off,
        'ch1_raw': b1, 'ch2_raw': b2,
        'ch1': ch1, 'ch2': ch2, 'ch3': ch3, 'ch4': ch4,
        'ch5': ch5, 'ch6': ch6, 'ch7': ch7, 'ch8': ch8,
        'ch9': ch9, 'ch10': ch10, 'ch11': ch11,
        'flow_16bit': ch1 * 256 + ch2,  # Fluxo como 16-bit
        'b1': b1, 'b2': b2, 'b3': b3, 'b4': b4, 'b5': b5,
        'b7': b7, 'b8': b8, 'b10': b10, 'b11': b11,
    })

total = len(all_data)
print(f"Total pacotes decodificados: {total}")

# ============================================
# 4. Analise estatistica de cada canal
# ============================================
print("\n=== ESTATISTICAS POR CANAL ===")
for ch_name in ['ch1','ch2','ch3','ch4','ch5','ch6','ch7','ch8','ch9','ch10','ch11']:
    vals = [d[ch_name] for d in all_data]
    mn = min(vals)
    mx = max(vals)
    avg = sum(vals)/len(vals)
    # Contar quantos sao zero ou negativos
    zeros = sum(1 for v in vals if v == 0)
    negatives = sum(1 for v in vals if v < 0)
    print(f"  {ch_name:5}: min={mn:6}, max={mx:5}, avg={avg:7.1f}, zeros={zeros:4}, neg={negatives:4}")

# ============================================  
# 5. Imprimir tabela completa reduzida
# ============================================
print("\n\n=== TABELA DE CANAIS (cada 5 pacotes) ===")
print(f"{'Idx':>4} | {'ch1':>5} | {'ch2':>5} | {'ch3':>5} | {'ch4':>5} | {'ch5':>5} | "
      f"{'ch7':>5} | {'ch8':>5} | {'ch10':>5} | {'ch11':>5} | {'flow16':>7}")
print("-" * 90)

for d in all_data[::5]:
    print(f"{d['idx']:4} | {d['ch1']:5} | {d['ch2']:5} | {d['ch3']:5} | {d['ch4']:5} | {d['ch5']:5} | "
          f"{d['ch7']:5} | {d['ch8']:5} | {d['ch10']:5} | {d['ch11']:5} | {d['flow_16bit']:7}")

# ============================================
# 6. Agora vamos focar em encontrar o periodo de ~13 minutos
#    Hipotese: 1 pacote = 1 segundo
#    13 minutos = 780 pacotes (se 1/seg)  
#    Mas temos so 719 pacotes = ~12 min com rate 1/seg
#    Ou ~36 min com rate 3/seg?
#
#    Melhor hipotese: o rate NAO eh 1/seg
#    O espacamento medio entre pacotes eh ~154 bytes no arquivo
#    Nao temos info de tempo direta nos dados
#    
#    Mas sabemos que a viagem tem um perfil tipico:
#    - Parada -> aceleracao -> viagem -> desaceleracao -> parada
#    - O evento de abastecimento de ~13 min ocorre PARADO
# ============================================

print("\n\n=== PERFIL DE VELOCIDADE COMPLETO ===")
speeds = [d['ch4'] for d in all_data]
# Encontrar mudancas significativas
print("Periodos parado (ch4 <= 2):")
stopped_start = None
for i, s in enumerate(speeds):
    if abs(s) <= 2:
        if stopped_start is None:
            stopped_start = i
    else:
        if stopped_start is not None:
            dur = i - stopped_start
            if dur >= 5:
                print(f"  Pacote {stopped_start}-{i-1} ({dur} pacotes)")
            stopped_start = None
if stopped_start is not None:
    dur = len(speeds) - stopped_start
    if dur >= 5:
        print(f"  Pacote {stopped_start}-{len(speeds)-1} ({dur} pacotes)")

# ============================================
# 7. Verificar velocidade com valores UNSIGNED (sem -128)
#    Talvez velocidade nao use base 128
# ============================================
print("\n\n=== PERFIL DE VELOCIDADE RAW (sem offset 128) ===")
speeds_raw = [d['b4'] for d in all_data]
print("Periodos com b4 perto de zero ou 128:")
for i, s in enumerate(speeds_raw):
    if i % 25 == 0:
        print(f"  Pacote {i:4d}: b4_raw={s:3d}, b4-128={s-128:4d}")
