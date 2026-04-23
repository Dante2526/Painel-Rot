"""
Recalibracao do EG - Maximo = 90 PSI

Problema: formula (val-64)*0.625 gera valores ate 110 PSI
Realidade: EG nunca passa de 90 PSI

Vamos investigar os valores raw e encontrar a escala correta.
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

FILE = 'c:/Users/nayla/.antigravity/Painel-Rot/02250421.dat'
OUT = 'c:/Users/nayla/.antigravity/Painel-Rot/scratch'

with open(FILE, 'rb') as f:
    raw = f.read()

# ============================================
# 1. Coletar TODOS os raw values das tags EG
# ============================================
eg_tag = bytes([0x26, 0x82, 0x80])
eg_raw_values = []
eg_offsets = []

i = 0
while i < len(raw) - 4:
    if raw[i] == 0x26 and raw[i+1] == 0x82 and raw[i+2] == 0x80:
        raw_val = raw[i+3]
        eg_raw_values.append(raw_val)
        eg_offsets.append(i)
        i += 4
    else:
        i += 1

eg_raw = np.array(eg_raw_values)
print(f"Tags EG encontradas: {len(eg_raw)}")
print(f"Raw values: min={eg_raw.min()}, max={eg_raw.max()}, media={eg_raw.mean():.1f}")
print(f"\nDistribuicao de raw values:")

from collections import Counter
for val, count in sorted(Counter(eg_raw_values).items()):
    # Testar diferentes formulas
    f1 = (val - 64) * 0.625       # Formula original do parser.ts
    f2 = val * 90 / eg_raw.max()  # Escala linear 0-90
    f3 = (val - 64) * (90 / (eg_raw.max() - 64))  # Offset 64, max=90
    f4 = val / 256 * 90           # Proporcional a 256
    f5 = (val - 0x80) * 90 / (eg_raw.max() - 0x80)  # Offset 0x80
    print(f"  raw=0x{val:02X} ({val:3d}): {count:3d}x | "
          f"f1={f1:5.1f} | f2={f2:5.1f} | f3={f3:5.1f} | f4={f4:5.1f} | f5={f5:5.1f}")

# ============================================
# 2. Testar: se max_raw = 90 PSI, qual e a escala?
# ============================================
print(f"\n{'='*80}")
print("FORMULAS DE CALIBRACAO (max = 90 PSI)")
print(f"{'='*80}")

max_raw = eg_raw.max()
min_raw = eg_raw.min()

print(f"\nRaw range: {min_raw} (0x{min_raw:02X}) - {max_raw} (0x{max_raw:02X})")

# Se considerarmos que os valores raw mapeiam linearmente para 0-90 PSI:
# PSI = (raw - min_raw) / (max_raw - min_raw) * 90
print(f"\nFormula A: PSI = (raw - {min_raw}) / ({max_raw} - {min_raw}) * 90")
print(f"  raw={min_raw} -> 0 PSI")
print(f"  raw={max_raw} -> 90 PSI")

# Se offset fixo em 0x80 (128):
# PSI = (raw - 128) / (max_raw - 128) * 90
if min_raw >= 128:
    print(f"\nFormula B: PSI = (raw - 128) / ({max_raw} - 128) * 90")
    for v in [128, 160, 192, 208, max_raw]:
        if v <= max_raw:
            psi = (v - 128) / (max_raw - 128) * 90
            print(f"  raw={v} (0x{v:02X}) -> {psi:.1f} PSI")

# Se fator = 90 / (max_raw - 64):
factor = 90 / (max_raw - 64)
print(f"\nFormula C: PSI = (raw - 64) * {factor:.4f}")
print(f"  raw=64  -> 0 PSI")
print(f"  raw={max_raw} -> {(max_raw-64)*factor:.1f} PSI")

# Talvez a conversao BCD ou outra
# raw / 2.56 -> 0-100 range
print(f"\nFormula D: PSI = raw / 2.8444 (= max/90)")
for v in sorted(set(eg_raw_values)):
    psi = v / (max_raw / 90)
    # print only extremes
    if psi < 5 or psi > 85 or abs(psi - 45) < 2 or abs(psi - 90) < 2:
        print(f"  raw={v} -> {psi:.1f} PSI")

# ============================================
# 3. Plotar com TODAS as formulas possiveis
# ============================================
time_axis = np.arange(len(eg_raw))  # indice da amostra

fig, axes = plt.subplots(3, 1, figsize=(18, 12), sharex=True)
fig.suptitle('02250421.dat - Calibracao EG (max = 90 PSI)', fontsize=16, fontweight='bold')

# Formula original (errada - vai ate 110)
ax = axes[0]
psi_original = (eg_raw - 64) * 0.625
ax.plot(time_axis, psi_original, 'r-', linewidth=0.8, alpha=0.7, label='Original: (raw-64)*0.625')
ax.axhline(y=90, color='green', linestyle='--', linewidth=2, label='Limite 90 PSI')
ax.set_ylabel('PSI')
ax.set_title('Formula ORIGINAL do parser.ts (INCORRETA - valores > 90)')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_ylim(0, 120)

# Formula corrigida: escala para max=90
ax = axes[1]
psi_corrected = (eg_raw - min_raw) / (max_raw - min_raw) * 90
ax.plot(time_axis, psi_corrected, 'b-', linewidth=0.8, alpha=0.7,
        label=f'Corrigida: (raw-{min_raw})/({max_raw}-{min_raw})*90')
ax.axhline(y=90, color='green', linestyle='--', linewidth=2, label='Limite 90 PSI')
ax.set_ylabel('PSI')
ax.set_title('Formula CORRIGIDA - Escala linear 0-90 PSI')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_ylim(0, 100)

# Formula com clamp
ax = axes[2]
psi_clamped = np.clip((eg_raw - 64) * 0.625, 0, 90)
# Media movel
window = 10
if len(psi_corrected) > window:
    kernel = np.ones(window) / window
    smooth = np.convolve(psi_corrected, kernel, mode='valid')
    ax.plot(time_axis[:len(smooth)], smooth, 'b-', linewidth=2, label='Media movel (10)')
ax.plot(time_axis, psi_corrected, 'b-', linewidth=0.4, alpha=0.3, label='Bruto')
ax.axhline(y=90, color='green', linestyle='--', linewidth=2, label='Limite 90 PSI')
ax.set_ylabel('PSI')
ax.set_xlabel('Amostra (#)')
ax.set_title('EG Corrigido com Media Movel')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_ylim(0, 100)

plt.tight_layout()
path = f'{OUT}/calibracao_eg.png'
plt.savefig(path, dpi=150, bbox_inches='tight')
print(f"\nGrafico salvo: {path}")

# ============================================
# 4. GRAFICO PRINCIPAL RECALIBRADO
# ============================================
# Usar formula C: (raw - 64) * factor onde factor = 90/(max-64)
factor_c = 90 / (max_raw - 64)
eg_psi = np.clip((eg_raw - 64) * factor_c, 0, 90)

# BC
bc_events = []
i = 0
while i < len(raw) - 4:
    if raw[i] == 0x84 and raw[i+1] == 0xA8 and raw[i+2] == 0x8A:
        bc_events.append((i, raw[i+3] - 64))
        i += 4
    else:
        i += 1

# Notch
notch_events = []
i = 0
while i < len(raw) - 2:
    if raw[i] == 0x82 and 0xB0 <= raw[i+1] <= 0xB8:
        notch_events.append((i, raw[i+1] - 0xB0))
        i += 2
    else:
        i += 1

# Tempo proporcional (719 pkts ~ 12 min)
total_duration = 12 * 60  # 720 seg
file_size = len(raw)

eg_time = np.array([off / file_size * total_duration for off in eg_offsets])
bc_time = np.array([e[0] / file_size * total_duration for e in bc_events])
bc_psi = np.array([e[1] for e in bc_events])
notch_time = np.array([e[0] / file_size * total_duration for e in notch_events])
notch_val = np.array([e[1] for e in notch_events])

fig2, axes2 = plt.subplots(3, 1, figsize=(18, 12), sharex=True)
fig2.suptitle('02250421.dat - DESVIO DE ABASTECIMENTO\nEG calibrado (max 90 PSI)',
              fontsize=16, fontweight='bold')

# EG
ax = axes2[0]
ax.plot(eg_time/60, eg_psi, 'b-', linewidth=0.5, alpha=0.4, label='EG bruto')
if len(eg_psi) > 10:
    kernel = np.ones(10) / 10
    smooth = np.convolve(eg_psi, kernel, mode='valid')
    smooth_t = eg_time[5:-4] if len(smooth) == len(eg_time) - 9 else eg_time[:len(smooth)]
    ax.plot(smooth_t/60, smooth, 'b-', linewidth=2.5, label='EG (media movel)')
ax.axhline(y=90, color='green', linestyle='--', linewidth=2, label='Max 90 PSI')
ax.axhline(y=0, color='red', linestyle='-', linewidth=0.5)
ax.fill_between(eg_time/60, 0, eg_psi, alpha=0.15, color='blue', label='Pressao ativa')
ax.set_ylabel('PSI', fontsize=12)
ax.set_title('Encanamento Geral (EG) - Abastecimento de Ar', fontsize=14)
ax.legend(loc='lower right', fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_ylim(-5, 100)

# BC
ax = axes2[1]
ax.plot(bc_time/60, bc_psi, 'r-', linewidth=1, alpha=0.7, label='BC')
ax.set_ylabel('PSI', fontsize=12)
ax.set_title('Cilindro de Freio (BC)', fontsize=14)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

# Notch
ax = axes2[2]
if len(notch_time) > 0:
    ax.step(notch_time/60, notch_val, 'k-', linewidth=1.5, where='post', label='Notch')
    ax.fill_between(notch_time/60, 0, notch_val, step='post', alpha=0.2, color='orange')
ax.set_ylabel('Notch', fontsize=12)
ax.set_xlabel('Tempo (minutos)', fontsize=12)
ax.set_title('Aceleracao (Notch) - 0=parado, 8=maximo', fontsize=14)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_ylim(-0.5, 9)

# Fundo vermelho indicando desvio
for ax in axes2:
    ax.axvspan(0, total_duration/60, alpha=0.04, color='red')

plt.tight_layout()
final_path = f'{OUT}/desvio_calibrado_90psi.png'
plt.savefig(final_path, dpi=150, bbox_inches='tight')
print(f"Grafico final salvo: {final_path}")

# ============================================
# 5. RESUMO
# ============================================
print(f"\n{'='*80}")
print("EG RECALIBRADO (max 90 PSI)")
print(f"{'='*80}")
print(f"  Formula: (raw - 64) * {factor_c:.4f}")
print(f"  Min: {eg_psi.min():.1f} PSI")
print(f"  Max: {eg_psi.max():.1f} PSI")
print(f"  Media: {eg_psi.mean():.1f} PSI")
print(f"  Std: {eg_psi.std():.1f} PSI")
print(f"\n  Pressao media sugere: {'abastecimento ativo' if eg_psi.mean() > 40 else 'pressao baixa'}")
print(f"  Evento total: ~{total_duration/60:.0f} min (limite: 1 min)")
