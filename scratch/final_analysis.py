"""
Analise final do 02250421.dat

Descobertas:
- 402 pacotes validos com marcador 0x03
- Se ~2 seg/pacote -> ~13.4 min (coincide com o desvio relatado!)
- Tags EG [0x26, 0x82, 0x80] dispersas no stream = pressao BP
- Tags BC [0x84, 0xA8, 0x8A] = pressao BC

Objetivo: plotar perfil completo e encontrar o evento de abastecimento
"""
import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

FILE = 'c:/Users/nayla/.antigravity/Painel-Rot/02250421.dat'
OUTPUT_DIR = 'c:/Users/nayla/.antigravity/Painel-Rot/scratch'

with open(FILE, 'rb') as f:
    raw = f.read()

# ============================================
# 1. Parser baseado em tags DAS III
# ============================================
TAGS_EG = [0x26, 0x82, 0x80]
TAGS_BC = [0x84, 0xA8, 0x8A]

# Extrair TODAS as tags EG e BC com suas posicoes
eg_events = []
bc_events = []

i = 0
while i < len(raw) - 4:
    if raw[i] == TAGS_EG[0] and raw[i+1] == TAGS_EG[1] and raw[i+2] == TAGS_EG[2]:
        raw_val = raw[i+3]
        psi = (raw_val - 64) * 0.625
        eg_events.append({'offset': i, 'raw': raw_val, 'psi': psi})
        i += 4
    elif raw[i] == TAGS_BC[0] and raw[i+1] == TAGS_BC[1] and raw[i+2] == TAGS_BC[2]:
        raw_val = raw[i+3]
        psi = raw_val - 64
        bc_events.append({'offset': i, 'raw': raw_val, 'psi': psi})
        i += 4
    else:
        i += 1

print(f"Tags EG encontradas: {len(eg_events)}")
print(f"Tags BC encontradas: {len(bc_events)}")

# ============================================
# 2. Mapear tags para tempo
#    Hipotese: 402 pacotes 0x03 cobrem ~13 min
#    Cada tag mapeada proporcionalmente pelo offset no arquivo
# ============================================
file_size = len(raw)
total_duration_sec = 13 * 60  # 780 segundos (estimativa 13 min)

def offset_to_time(offset):
    """Converte offset no arquivo para tempo estimado em segundos"""
    return (offset / file_size) * total_duration_sec

# Criar series temporais
eg_times = [offset_to_time(e['offset']) for e in eg_events]
eg_psi = [e['psi'] for e in eg_events]

bc_times = [offset_to_time(e['offset']) for e in bc_events]
bc_psi = [e['psi'] for e in bc_events]

# ============================================
# 3. Encontrar pacotes 0x03 para notch/velocidade
# ============================================
# Vamos buscar tags de notch [0x82, 0xB0-0xB8]
notch_events = []
i = 0
while i < len(raw) - 2:
    if raw[i] == 0x82 and 0xB0 <= raw[i+1] <= 0xB8:
        notch_val = raw[i+1] - 0xB0
        notch_events.append({'offset': i, 'notch': notch_val})
        i += 2
    else:
        i += 1

notch_times = [offset_to_time(e['offset']) for e in notch_events]
notch_vals = [e['notch'] for e in notch_events]

print(f"Tags Notch encontradas: {len(notch_events)}")

# ============================================
# 4. PLOTAR GRAFICOS
# ============================================
fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True)
fig.suptitle('Telemetria DAS III - 02250421.dat\nEngenharia Reversa', fontsize=14, fontweight='bold')

# EG (Brake Pipe / Encanamento Geral)
ax1 = axes[0]
ax1.plot([t/60 for t in eg_times], eg_psi, 'b-', linewidth=0.8, alpha=0.7, label='EG (Brake Pipe)')
ax1.axhline(y=90, color='g', linestyle='--', alpha=0.5, label='Nominal (90 PSI)')
ax1.set_ylabel('Pressao (PSI)')
ax1.set_title('Pressao do Encanamento Geral (EG / Brake Pipe)')
ax1.legend(loc='upper right')
ax1.grid(True, alpha=0.3)
ax1.set_ylim(0, 120)

# BC (Brake Cylinder)
ax2 = axes[1]
ax2.plot([t/60 for t in bc_times], bc_psi, 'r-', linewidth=0.8, alpha=0.7, label='BC (Brake Cylinder)')
ax2.set_ylabel('Pressao (PSI)')
ax2.set_title('Pressao do Cilindro de Freio (BC)')
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3)

# Notch
ax3 = axes[2]
if notch_times:
    # Criar step plot
    ax3.step([t/60 for t in notch_times], notch_vals, 'k-', linewidth=1.0, where='post', label='Notch')
ax3.set_ylabel('Notch')
ax3.set_xlabel('Tempo (minutos)')
ax3.set_title('Aceleracao (Notch)')
ax3.legend(loc='upper right')
ax3.grid(True, alpha=0.3)
ax3.set_ylim(-0.5, 9)

plt.tight_layout()
plot_path = os.path.join(OUTPUT_DIR, 'das3_analysis.png')
plt.savefig(plot_path, dpi=150)
print(f"\nGrafico salvo: {plot_path}")

# ============================================
# 5. DETECTAR EVENTO DE ABASTECIMENTO PROLONGADO
# ============================================
print("\n" + "="*80)
print("DETECCAO DE DESVIO DE ABASTECIMENTO")
print("="*80)

# Criterios do desvio:
# 1. Trem PARADO (sem aceleracao, notch = 0)
# 2. Fluxo de ar alto (EG > 70 PSI = BP sendo carregada)
# 3. Fluxo cai para zero eventualmente
# 4. Duracao > 1 minuto

# Vamos usar uma janela deslizante sobre as tags EG
# Procurar periodo continuo onde EG esta acima de um limiar

# Primeiro, verificar periodos sem notch (trem parado)
print("\nPeriodos SEM aceleracao (notch = 0):")
# Criar timeline de notch
if notch_events:
    # Interpolar notch para cada posicao EG
    eg_notch = []
    notch_idx = 0
    current_notch = 0
    for eg in eg_events:
        while notch_idx < len(notch_events) - 1 and notch_events[notch_idx + 1]['offset'] <= eg['offset']:
            notch_idx += 1
        if notch_idx < len(notch_events) and notch_events[notch_idx]['offset'] <= eg['offset']:
            current_notch = notch_events[notch_idx]['notch']
        eg_notch.append(current_notch)
else:
    eg_notch = [0] * len(eg_events)

# Encontrar periodos de abastecimento
# - EG >= 60 PSI (BP sendo carregada/mantida)
# - Notch = 0
# - Duracao significativa
EG_MIN = 60  # PSI minimo
supply_start = None
supply_events_found = []

for idx in range(len(eg_events)):
    eg_val = eg_psi[idx]
    notch = eg_notch[idx]
    
    is_supply = eg_val >= EG_MIN and notch == 0
    
    if is_supply:
        if supply_start is None:
            supply_start = idx
    else:
        if supply_start is not None:
            duration_idx = idx - supply_start
            time_start = eg_times[supply_start]
            time_end = eg_times[idx - 1]
            duration_sec = time_end - time_start
            
            supply_events_found.append({
                'start_idx': supply_start,
                'end_idx': idx - 1,
                'start_sec': time_start,
                'end_sec': time_end,
                'duration_sec': duration_sec,
                'num_samples': duration_idx,
                'avg_eg': sum(eg_psi[supply_start:idx]) / duration_idx,
                'max_eg': max(eg_psi[supply_start:idx]),
                'min_eg': min(eg_psi[supply_start:idx]),
            })
            supply_start = None

# Fechar evento em aberto
if supply_start is not None:
    duration_idx = len(eg_events) - supply_start
    time_start = eg_times[supply_start]
    time_end = eg_times[-1]
    supply_events_found.append({
        'start_idx': supply_start,
        'end_idx': len(eg_events) - 1,
        'start_sec': time_start,
        'end_sec': time_end,
        'duration_sec': time_end - time_start,
        'num_samples': duration_idx,
        'avg_eg': sum(eg_psi[supply_start:]) / duration_idx,
        'max_eg': max(eg_psi[supply_start:]),
        'min_eg': min(eg_psi[supply_start:]),
    })

# Filtrar eventos significativos (> 30 segundos)
significant_events = [e for e in supply_events_found if e['duration_sec'] > 30]

print(f"\nEventos de abastecimento (> 30s): {len(significant_events)}")
for idx, evt in enumerate(significant_events):
    mins = evt['duration_sec'] / 60
    is_desvio = evt['duration_sec'] > 60
    label = " >>> DESVIO (> 1 min) <<<" if is_desvio else ""
    print(f"\nEvento {idx + 1}{label}")
    print(f"  Inicio: {evt['start_sec']/60:.1f} min")
    print(f"  Fim:    {evt['end_sec']/60:.1f} min")
    print(f"  Duracao: {evt['duration_sec']:.0f}s ({mins:.1f} min)")
    print(f"  Amostras: {evt['num_samples']}")
    print(f"  EG: media={evt['avg_eg']:.1f}, min={evt['min_eg']:.1f}, max={evt['max_eg']:.1f} PSI")

# ============================================
# 6. Segundo grafico focado no evento
# ============================================
if significant_events:
    # Encontrar o maior evento
    longest = max(significant_events, key=lambda e: e['duration_sec'])
    
    print(f"\n\nMAIOR EVENTO DE ABASTECIMENTO:")
    print(f"  Inicio: {longest['start_sec']/60:.1f} min")
    print(f"  Fim:    {longest['end_sec']/60:.1f} min")
    print(f"  Duracao: {longest['duration_sec']/60:.1f} min")
    
    # Plot focado
    fig2, ax = plt.subplots(figsize=(14, 6))
    
    margin = 60  # 1 min antes/depois
    start_t = max(0, longest['start_sec'] - margin)
    end_t = min(total_duration_sec, longest['end_sec'] + margin)
    
    # Filtrar EG no range
    mask_eg = [(start_t <= t <= end_t) for t in eg_times]
    filtered_eg_t = [t/60 for t, m in zip(eg_times, mask_eg) if m]
    filtered_eg_v = [v for v, m in zip(eg_psi, mask_eg) if m]
    
    ax.plot(filtered_eg_t, filtered_eg_v, 'b-o', markersize=3, linewidth=1, label='EG (Brake Pipe)')
    ax.axhline(y=90, color='g', linestyle='--', alpha=0.5, label='Nominal')
    ax.axvspan(longest['start_sec']/60, longest['end_sec']/60, 
               alpha=0.2, color='red', label=f'DESVIO ({longest["duration_sec"]/60:.1f} min)')
    
    ax.set_xlabel('Tempo (minutos)')
    ax.set_ylabel('Pressao (PSI)')
    ax.set_title(f'DESVIO DETECTADO - Abastecimento Prolongado ({longest["duration_sec"]/60:.1f} min)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    detail_path = os.path.join(OUTPUT_DIR, 'desvio_abastecimento.png')
    plt.savefig(detail_path, dpi=150)
    print(f"Grafico detalhado salvo: {detail_path}")

# ============================================
# 7. Tabela resumo
# ============================================
print("\n\n" + "="*80)
print("TABELA COMPLETA - EG vs TEMPO (cada 10 amostras)")
print("="*80)
print(f"{'#':>4} | {'T(min)':>7} | {'EG(PSI)':>8} | {'Notch':>5}")
print("-" * 35)
for idx in range(0, len(eg_events), 10):
    t_min = eg_times[idx] / 60
    eg_v = eg_psi[idx]
    n = eg_notch[idx]
    print(f"{idx:4d} | {t_min:7.2f} | {eg_v:8.1f} | {n:5d}")
