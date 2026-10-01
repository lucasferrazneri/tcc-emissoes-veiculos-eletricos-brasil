# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# SCRIPT 03 — Série histórica de emplacamentos de veículos eletrificados
# Fonte: https://abve.org.br/abve-data/
# =============================================================================

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parents[2]
TCC_DIR = BASE_DIR / 'tcc_ve'
DADOS_DIR = TCC_DIR / 'dados' / 'tratados'
GRAFICOS_DIR = TCC_DIR / 'graficos'

DADOS_DIR.mkdir(parents=True, exist_ok=True)
GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# PASSO 1 — Série histórica TOTAL de eletrificados (2012–2025)
# Usado para CONTEXTUALIZAÇÃO — inclui BEV, PHEV, HEV e HEV Flex 
# A ABVE só separou por tecnologia a partir de 2022
# -----------------------------------------------------------------------------
dados_contexto = {
    'Ano':   [2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019,
              2020, 2021, 2022, 2023, 2024, 2025],
    'Total_Eletrificados': [117, 491, 855, 846, 1091, 3296, 3970, 11858,
                            19745, 34990, 49245, 93927, 177358, 223912]
}
df_contexto = pd.DataFrame(dados_contexto)
df_contexto['Frota_Acumulada'] = df_contexto['Total_Eletrificados'].cumsum()

output_csv = DADOS_DIR / 'abve_contexto_eletrificados.csv'
df_contexto.to_csv(output_csv, index=False, encoding='utf-8-sig')
print(f"Arquivo salvo: {output_csv}")

# -----------------------------------------------------------------------------
# PASSO 2 — Figura 5: Contextualização — crescimento dos eletrificados
# (todos os tipos, 2012–2025)
# -----------------------------------------------------------------------------
fig, ax1 = plt.subplots(figsize=(13, 7))
fig.patch.set_facecolor('white')
ax1.set_facecolor('#F8F9FA')

bars = ax1.bar(
    df_contexto['Ano'], df_contexto['Total_Eletrificados'] / 1000,
    color='#78909C', edgecolor='white', linewidth=0.8, width=0.7,
    alpha=0.8
)

for bar, (_, row) in zip(bars, df_contexto.iterrows()):
    val = row['Total_Eletrificados']
    if val >= 10000:
        label = f'{val/1000:.0f}k'
    elif val >= 1000:
        label = f'{val/1000:.1f}k'
    else:
        label = f'{val:,.0f}'
    ax1.text(
        bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
        label, ha='center', va='bottom',
        fontsize=8, fontweight='bold', color='#333333'
    )

# Eixo secundário — frota acumulada
ax2 = ax1.twinx()
ax2.plot(
    df_contexto['Ano'], df_contexto['Frota_Acumulada'] / 1000,
    color='#E64A19', marker='o', markersize=5,
    linewidth=2.5, label='Frota acumulada'
)
ax2.set_ylabel('Frota acumulada (mil veículos)', fontsize=11, color='#E64A19')
ax2.tick_params(axis='y', labelcolor='#E64A19', labelsize=10)

for spine in ['top']:
    ax1.spines[spine].set_visible(False)
    ax2.spines[spine].set_visible(False)
ax1.spines['left'].set_color('#CCCCCC')
ax1.spines['bottom'].set_color('#CCCCCC')

ax1.set_xlabel('Ano', fontsize=11, color='#444444')
ax1.set_ylabel('Emplacamentos anuais (mil veículos)', fontsize=11, color='#555555')
ax1.set_xticks(df_contexto['Ano'])
ax1.set_xticklabels(df_contexto['Ano'], rotation=45, fontsize=10)
ax1.tick_params(axis='y', labelsize=10, colors='#888888')
ax1.grid(axis='y', alpha=0.3, linestyle='--', color='#CCCCCC')

from matplotlib.lines import Line2D
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#78909C', alpha=0.8, label='Emplacamentos no ano (todos os eletrificados)'),
    Line2D([0], [0], color='#E64A19', marker='o', label='Frota acumulada')
]
ax1.legend(handles=legend_elements, loc='upper left', fontsize=9,
           framealpha=0.9, edgecolor='#CCCCCC')

ax1.set_title(
    'Crescimento dos veículos eletrificados no Brasil (2012–2025)\n'
    'Contextualização — inclui BEV, PHEV, HEV e HEV Flex — ABVE Data',
    fontsize=13, fontweight='bold', color='#1A1A2E', pad=15
)

plt.tight_layout()
fig_output = GRAFICOS_DIR / 'abve_contexto_eletrificados.png'
plt.savefig(fig_output, dpi=180, bbox_inches='tight', facecolor='white')

if plt.get_backend().lower() != 'agg':
    plt.show()

print(f"\nFigura 5 salva: {fig_output}")

# -----------------------------------------------------------------------------
# RESUMO
# -----------------------------------------------------------------------------
print("\n" + "="*60)
print("CONCLUÍDO!")
print("="*60)
print(f"Emplacamentos em 2012 : {df_contexto['Total_Eletrificados'].iloc[0]:,}")
print(f"Emplacamentos em 2025 : {df_contexto['Total_Eletrificados'].iloc[-1]:,}")
print(f"Frota acumulada       : {df_contexto['Frota_Acumulada'].iloc[-1]:,}")
print("\nArquivos gerados:")
print(f"  {output_csv}")
print(f"  {fig_output}")
print("="*60)