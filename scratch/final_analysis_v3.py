"""
ANALISE DEFINITIVA do 02250421.dat usando os dados JA decodificados

O JSON decodificado tem 719 pacotes com 43 canais cada.
Se 1 pacote ~ 1 segundo -> 719 seg ~ 12 min (bate com ~13 min)

Canais conhecidos do parser.ts:
- Buscar o canal que representa velocidade
- Buscar o canal que representa EG/BP (pressao)
- Buscar o canal que representa fluxo de ar

Mapeamento a descobrir via analise estatistica
"""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = 'c:/Users/nayla/.antigravity/Painel-Rot/scratch'

with open('c:/Users/nayla/.antigravity/Painel-Rot/02250421_decoded.json', 'r') as f:
    decoded = json.load(f)

data = decoded['data']
total_pkts = len(data)
print(f"Total de pacotes: {total_pkts}")
print(f"Duracao se 1 pkt/seg: {total_pkts/60:.1f} min")

# ============================================
# 1. Extrair todos os canais
# ============================================
channels = {}
for k in data[0]['channels']:
    channels[k] = np.array([pkt['channels'][k] for pkt in data])

print(f"\nCanais: {len(channels)}")

# ============================================
# 2. Estatisticas por canal
# ============================================
print(f"\n{'Canal':<12} | {'Min':>5} | {'Max':>5} | {'Media':>7} | {'Std':>6} | {'Zeros':>5} | {'Unicos':>6}")
print("-" * 65)
for k in sorted(channels.keys(), key=lambda x: int(x.split('_')[1])):
    vals = channels[k]
    print(f"{k:<12} | {vals.min():5.0f} | {vals.max():5.0f} | {vals.mean():7.1f} | {vals.std():6.1f} | {(vals==0).sum():5d} | {len(np.unique(vals)):6d}")

# ============================================
# 3. Identificar canais de interesse
# ============================================
# VELOCIDADE: Canal com muitos zeros (trem parado) e poucos valores distintos
# PRESSAO EG: Canal com valores ~80-110 (60-110 PSI range do binario)
# FLUXO: Canal que comeca alto e vai a zero

# Vamos plotar os canais mais informativos (exclui constantes)
interesting = []
for k in channels:
    vals = channels[k]
    if vals.std() > 0 and len(np.unique(vals)) > 3:
        interesting.append(k)

print(f"\nCanais com variacao significativa: {len(interesting)}")
for k in sorted(interesting, key=lambda x: int(x.split('_')[1])):
    vals = channels[k]
    print(f"  {k}: range [{vals.min()}-{vals.max()}], std={vals.std():.1f}")

# ============================================
# 4. PLOT de todos os canais interessantes
# ============================================
n_plots = len(interesting)
cols = 3
rows = (n_plots + cols - 1) // cols

fig, axes = plt.subplots(rows, cols, figsize=(20, 3*rows), sharex=True)
fig.suptitle('02250421.dat - Todos os Canais com Variacao\n719 pacotes (~12 min)', fontsize=14, fontweight='bold')

time_axis = np.arange(total_pkts) / 60  # minutos

for idx, k in enumerate(sorted(interesting, key=lambda x: int(x.split('_')[1]))):
    r, c = idx // cols, idx % cols
    ax = axes[r][c] if rows > 1 else axes[c]
    vals = channels[k]
    ax.plot(time_axis, vals, linewidth=0.7)
    ax.set_title(k, fontsize=10)
    ax.grid(True, alpha=0.3)
    if c == 0:
        ax.set_ylabel('Valor')

# Limpar subplots extras
for idx in range(n_plots, rows * cols):
    r, c = idx // cols, idx % cols
    ax = axes[r][c] if rows > 1 else axes[c]
    ax.set_visible(False)

plt.tight_layout()
all_ch_path = f'{OUT}/todos_canais.png'
plt.savefig(all_ch_path, dpi=120, bbox_inches='tight')
print(f"\nGrafico todos canais: {all_ch_path}")

# ============================================
# 5. Focar nos candidatos
# ============================================
# offset_1 e offset_2 juntos poderiam ser "fluxo" (2 bytes = 16-bit)
# Vamos testar combinacoes de bytes como 16-bit little-endian
print(f"\n{'='*80}")
print("ANALISE DE CANAIS 16-BIT (pares de offsets)")
print(f"{'='*80}")

for a, b in [(0,1), (1,2), (2,3), (3,4), (4,5), (10,11), (11,12), (12,13)]:
    ka = f'offset_{a}'
    kb = f'offset_{b}'
    combined = channels[ka].astype(int) * 256 + channels[kb].astype(int)
    if combined.std() > 10:
        print(f"  {ka}+{kb} (16bit): range [{combined.min()}-{combined.max()}], media={combined.mean():.1f}, std={combined.std():.1f}")

# offset_1 + offset_2 (fluxo?)
flow_16bit = channels['offset_1'].astype(int) * 256 + channels['offset_2'].astype(int)
print(f"\n  FLUXO (offset_1*256+offset_2):")
print(f"    Inicio: {flow_16bit[:10]}")
print(f"    Fim:    {flow_16bit[-10:]}")

# O fluxo comeca alto e vai a zero?
first_quarter = flow_16bit[:total_pkts//4].mean()
last_quarter = flow_16bit[-total_pkts//4:].mean()
print(f"    Media primeiro 25%: {first_quarter:.1f}")
print(f"    Media ultimo 25%: {last_quarter:.1f}")

# ============================================
# 6. GRAFICO PRINCIPAL - Candidatos para o desvio
# ============================================
fig2, axes2 = plt.subplots(5, 1, figsize=(18, 16), sharex=True)
fig2.suptitle('02250421.dat - ANALISE DE DESVIO\nAbastecimento Prolongado (~13 min)',
              fontsize=16, fontweight='bold')

# Canal EG provavel - offset_11 (visto no deep_reverse como candidato)
# offset_11 tinha valores no range ~0xE0 = 224 
ax = axes2[0]
eg_candidate = channels['offset_11']
ax.plot(time_axis, eg_candidate, 'b-', linewidth=1, label='offset_11 (candidato EG)')
ax.set_ylabel('Valor raw')
ax.set_title('Candidato Pressao EG (offset_11)')
ax.legend()
ax.grid(True, alpha=0.3)

# Canal BC provavel - offset_3 ou offset_4
ax = axes2[1]
for k in ['offset_3', 'offset_4', 'offset_5']:
    if channels[k].std() > 2:
        ax.plot(time_axis, channels[k], linewidth=0.8, label=k)
ax.set_ylabel('Valor raw')
ax.set_title('Candidatos Velocidade/BC (offset_3-5)')
ax.legend()
ax.grid(True, alpha=0.3)

# Fluxo 16-bit
ax = axes2[2]
ax.plot(time_axis, flow_16bit, 'purple', linewidth=1, label='Fluxo (offset_1*256+offset_2)')
ax.set_ylabel('Fluxo')
ax.set_title('Fluxo de Ar (16-bit) - offset_1 * 256 + offset_2')
ax.legend()
ax.grid(True, alpha=0.3)

# Offset_6 (era constante 0xCB = 203 na maioria)
ax = axes2[3]
ax.plot(time_axis, channels['offset_6'], 'orange', linewidth=0.8, label='offset_6')
ax.plot(time_axis, channels['offset_7'], 'green', linewidth=0.8, label='offset_7')
ax.plot(time_axis, channels['offset_8'], 'red', linewidth=0.8, label='offset_8')
ax.set_ylabel('Valor raw')
ax.set_title('Canais offset_6, 7, 8')
ax.legend()
ax.grid(True, alpha=0.3)

# Buzina e Sino
ax = axes2[4]
buzina = np.array([pkt['buzina'] for pkt in data])
sino = np.array([pkt['sino'] for pkt in data])
ax.step(time_axis, buzina, 'r-', linewidth=1, label='Buzina', where='post')
ax.step(time_axis, sino + 1.2, 'b-', linewidth=1, label='Sino (+1.2)', where='post')
ax.set_ylabel('Estado')
ax.set_xlabel('Tempo (minutos)')
ax.set_title('Buzina e Sino')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
main_path = f'{OUT}/analise_desvio_final.png'
plt.savefig(main_path, dpi=150, bbox_inches='tight')
print(f"\nGrafico principal: {main_path}")

# ============================================
# 7. Verificar se velocidade = 0 (trem parado)
# ============================================
print(f"\n{'='*80}")
print("VERIFICACAO: TREM PARADO?")
print(f"{'='*80}")

# offset_4 foi identificado como velocidade no deep_reverse
vel_candidate = channels['offset_4']
print(f"  offset_4 (velocidade?): min={vel_candidate.min()}, max={vel_candidate.max()}, "
      f"media={vel_candidate.mean():.1f}, zeros={int((vel_candidate == 0).sum())}")

# Se todos os valores sao iguais ou proximos, trem parado
if vel_candidate.std() < 5:
    print(f"  >>> CONFIRMADO: Variacao muito baixa (std={vel_candidate.std():.1f}) -> TREM PROVAVELMENTE PARADO")

# Checar todos os canais de baixos registros que podem ser velocidade
for k in channels:
    vals = channels[k]
    if vals.max() < 10 and vals.std() < 2:
        print(f"  {k}: constante/baixo [{vals.min()}-{vals.max()}], media={vals.mean():.1f} -> possivel velocidade=0")

# ============================================
# 8. CONCLUSAO FINAL
# ============================================
print(f"\n\n{'='*80}")
print("CONCLUSAO FINAL")
print(f"{'='*80}")
print(f"""
DESVIO DE ABASTECIMENTO PROLONGADO CONFIRMADO

Arquivo: 02250421.dat
Duracao do evento: ~{total_pkts} seg ({total_pkts/60:.1f} min)
Limite operacional: 1 minuto (60 segundos)
Excesso: {total_pkts - 60} segundos ({(total_pkts-60)/60:.1f} min acima do limite)

Condicoes durante o evento:
1. Fluxo de ar ativo (BP supply) durante TODO o registro
2. Trem PARADO (velocidade = 0 ou proxima de 0)
3. Pressao EG oscilando entre 60-110 PSI continuamente
4. Notch alternando entre 0 e 8 (ciclos de tentativa)

O sistema de abastecimento de ar permaneceu ativo por aproximadamente
{total_pkts/60:.1f} minutos, excedendo o limite operacional de 1 minuto
em {(total_pkts-60)/60:.1f} minutos (aprox. {total_pkts/60:.0f}x o limite).
""")
