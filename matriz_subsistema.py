# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# Matriz eletrica por subsistema do SIN
# Capacidade instalada por subsistema do SIN.
#
# Fonte: ANEEL/SIGA, cadastro de empreendimentos de geracao.
# Baixar em https://dadosabertos.aneel.gov.br
#
# Rodar antes o script auditoria_dados.py, que verifica a codificacao do
# arquivo e lista as fontes de combustivel presentes.
#==============================================================================
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os
import sys

os.makedirs('tcc_ve/dados/tratados', exist_ok=True)
os.makedirs('tcc_ve/graficos', exist_ok=True)

ARQUIVO  = 'tcc_ve/dados/brutos/siga-empreendimentos-geracao.csv'
ENCODING = 'latin1'

# -----------------------------------------------------------------------------
# Mapeamento explicito das fontes
# -----------------------------------------------------------------------------
MAPA_FONTES = {
    'Potencial hidráulico':      'Hidrelétrica',
    'Cinética do vento':         'Eólica',
    'Radiação solar':            'Solar',
    'Agroindustriais':           'Biomassa',
    'Floresta':                  'Biomassa',
    'Biocombustíveis líquidos':  'Biomassa',
    'Resíduos sólidos urbanos':  'Biomassa',
    'Resíduos animais':          'Biomassa',
    'Gás natural':               'Gás Natural',
    'Petróleo':                  'Petróleo/Diesel',
    'Carvão mineral':            'Carvão Mineral',
    'Outros Fósseis':            'Outros Fósseis',
    'Urânio':                    'Nuclear',
}

GRUPO_RENOVAVEL = ['Hidrelétrica', 'Eólica', 'Solar', 'Biomassa']
GRUPO_FOSSIL    = ['Gás Natural', 'Petróleo/Diesel', 'Carvão Mineral', 'Outros Fósseis']
GRUPO_NUCLEAR   = ['Nuclear']

# -----------------------------------------------------------------------------
# Mapeamento UF -> subsistema do SIN
# -----------------------------------------------------------------------------
SUBSISTEMAS = {
    # Subsistema NORTE (inclui Maranhao)
    'AP':'Norte', 'AM':'Norte', 'PA':'Norte', 'TO':'Norte', 'MA':'Norte',

    # Subsistema NORDESTE (Nordeste exceto Maranhao)
    'AL':'Nordeste', 'BA':'Nordeste', 'CE':'Nordeste', 'PB':'Nordeste',
    'PE':'Nordeste', 'PI':'Nordeste', 'RN':'Nordeste', 'SE':'Nordeste',

    # Subsistema SUDESTE/CENTRO-OESTE (inclui Acre e Rondonia)
    'ES':'Sudeste/C-Oeste', 'MG':'Sudeste/C-Oeste', 'RJ':'Sudeste/C-Oeste',
    'SP':'Sudeste/C-Oeste', 'DF':'Sudeste/C-Oeste', 'GO':'Sudeste/C-Oeste',
    'MS':'Sudeste/C-Oeste', 'MT':'Sudeste/C-Oeste',
    'AC':'Sudeste/C-Oeste', 'RO':'Sudeste/C-Oeste',

    # Subsistema SUL
    'PR':'Sul', 'SC':'Sul', 'RS':'Sul',

    # Roraima — historicamente Sistema Isolado
    'RR':'Sistema Isolado',
}

# -----------------------------------------------------------------------------
# PASSO 1 — Carregar, filtrar e classificar
# -----------------------------------------------------------------------------
print("Carregando ANEEL/SIGA...")
df = pd.read_csv(ARQUIVO, sep=';', encoding=ENCODING)

df_op = df[df['DscFaseUsina'].str.contains('Opera', case=False, na=False)].copy()
df_op['PotenciaMW'] = pd.to_numeric(
    df_op['MdaPotenciaFiscalizadaKw'], errors='coerce') / 1000
df_op = df_op.dropna(subset=['PotenciaMW'])

# Trava: toda fonte precisa estar mapeada
nao_mapeadas = set(df_op['DscFonteCombustivel'].dropna().unique()) - set(MAPA_FONTES)
if nao_mapeadas:
    print("\nERRO: fontes nao mapeadas encontradas:")
    for f in sorted(nao_mapeadas):
        print(f"   '{f}'")
    sys.exit(1)

df_op['Fonte']      = df_op['DscFonteCombustivel'].map(MAPA_FONTES)
df_op['Subsistema'] = df_op['SigUFPrincipal'].map(SUBSISTEMAS)

# Trava: toda UF precisa estar mapeada
ufs_sem_mapa = df_op[df_op['Subsistema'].isna()]['SigUFPrincipal'].dropna().unique()
if len(ufs_sem_mapa):
    print(f"\nERRO: UFs nao mapeadas: {sorted(ufs_sem_mapa)}")
    sys.exit(1)

total_geral = df_op['PotenciaMW'].sum()
print(f"Usinas em operacao: {len(df_op):,}  |  {total_geral:,.0f} MW")

# -----------------------------------------------------------------------------
# PASSO 2 — Roraima / Sistema Isolado: quanto representa
# -----------------------------------------------------------------------------
iso = df_op[df_op['Subsistema'] == 'Sistema Isolado']
mw_iso = iso['PotenciaMW'].sum()

print("\n" + "="*70)
print("SISTEMA ISOLADO (Roraima)")
print("="*70)
print(f"  Usinas   : {len(iso)}")
print(f"  Potencia : {mw_iso:,.1f} MW  ({mw_iso/total_geral*100:.2f}% do total nacional)")
if len(iso):
    print("\n  Composicao:")
    print(iso.groupby('Fonte')['PotenciaMW'].sum()
          .sort_values(ascending=False).round(1).to_string())
print("\n  -> Excluido da analise por subsistema (nao integra o SIN).")
print("     Registre essa exclusao na metodologia do TCC.")

# -----------------------------------------------------------------------------
# PASSO 3 — Matriz por subsistema
# -----------------------------------------------------------------------------
df_sin = df_op[df_op['Subsistema'] != 'Sistema Isolado'].copy()
total_sin = df_sin['PotenciaMW'].sum()

pivot = df_sin.groupby(['Subsistema','Fonte'])['PotenciaMW'].sum().unstack(fill_value=0)
pivot_pct = (pivot.div(pivot.sum(axis=1), axis=0) * 100).round(2)

ORDEM_SUB   = ['Norte','Nordeste','Sudeste/C-Oeste','Sul']
ORDEM_FONTE = ['Hidrelétrica','Eólica','Solar','Biomassa',
               'Gás Natural','Petróleo/Diesel','Carvão Mineral',
               'Outros Fósseis','Nuclear']

for f in ORDEM_FONTE:
    if f not in pivot_pct.columns:
        pivot_pct[f] = 0.0
        pivot[f] = 0.0
pivot_pct = pivot_pct.reindex(ORDEM_SUB)[ORDEM_FONTE]
pivot     = pivot.reindex(ORDEM_SUB)[ORDEM_FONTE]

print("\n" + "="*70)
print("MATRIZ ELETRICA POR SUBSISTEMA DO SIN (% da capacidade instalada)")
print("="*70)
print(pivot_pct.to_string())

resumo = pd.DataFrame({
    'Renovaveis_pct': pivot_pct[GRUPO_RENOVAVEL].sum(axis=1).round(1),
    'Fosseis_pct':    pivot_pct[GRUPO_FOSSIL].sum(axis=1).round(1),
    'Nuclear_pct':    pivot_pct[GRUPO_NUCLEAR].sum(axis=1).round(1),
    'Total_MW':       pivot.sum(axis=1).round(0),
})
resumo['Part_no_SIN_pct'] = (resumo['Total_MW'] / total_sin * 100).round(1)

print("\n--- Resumo por subsistema ---")
print(resumo.to_string())
print(f"\nTotal SIN: {total_sin:,.0f} MW")
print(f"Verificacao das somas por linha (deve dar 100%):")
print((resumo['Renovaveis_pct'] + resumo['Fosseis_pct'] + resumo['Nuclear_pct']).to_string())

pivot_pct.to_csv('tcc_ve/dados/tratados/aneel_matriz_subsistema.csv', encoding='utf-8-sig')
resumo.to_csv('tcc_ve/dados/tratados/aneel_resumo_subsistema.csv', encoding='utf-8-sig')

# -----------------------------------------------------------------------------
# GRAFICO — Fontes por subsistema (barras agrupadas)
# -----------------------------------------------------------------------------
CORES = {
    'Hidrelétrica':    '#1565C0',
    'Eólica':          '#2E7D32',
    'Solar':           '#F9A825',
    'Biomassa':        '#7CB342',
    'Gás Natural':     '#E64A19',
    'Nuclear':         '#8E24AA',
}
fontes_plot = ['Hidrelétrica','Eólica','Solar','Biomassa','Gás Natural']
dados = pivot_pct[fontes_plot]

x = np.arange(len(dados)) * 1.30
largura = 0.21
offs = np.linspace(-(len(fontes_plot)-1)/2*largura,
                    (len(fontes_plot)-1)/2*largura, len(fontes_plot))

fig, ax = plt.subplots(figsize=(13, 7))
fig.patch.set_facecolor('white')
ax.set_facecolor('#F8F9FA')

for fonte, off in zip(fontes_plot, offs):
    vals = dados[fonte].values
    bars = ax.bar(x + off, vals, width=largura, color=CORES[fonte],
                  edgecolor='white', linewidth=0.7, label=fonte)
    for bar, v in zip(bars, vals):
        if v >= 3:
            txt = f'{v:.0f}%'
        elif v >= 0.05:
            txt = f'{v:.1f}%'
        else:
            txt = '~0'
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.9,
                txt, ha='center', va='bottom',
                fontsize=8 if v < 3 else 9,
                fontweight='bold',
                color='#888888' if v < 3 else '#333333')

for s in ['top','right']:
    ax.spines[s].set_visible(False)
ax.spines['left'].set_color('#CCCCCC')
ax.spines['bottom'].set_color('#CCCCCC')

ax.set_xticks(x)
ax.set_xticklabels(dados.index, fontsize=12, color='#333333')
ax.set_ylim(0, 100)
ax.set_ylabel('Participação (%)', fontsize=12, color='#444444')
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))
ax.tick_params(axis='y', labelsize=10, colors='#888888')
ax.grid(axis='y', alpha=0.3, linestyle='--', color='#CCCCCC')
ax.legend(title='Fonte de geração', title_fontsize=10,
          loc='upper center', bbox_to_anchor=(0.5, -0.07),
          ncol=5, fontsize=10, framealpha=0.9, edgecolor='#CCCCCC')

ax.set_title('Principais fontes de geração por subsistema do SIN\n'
             'Capacidade instalada em operação — ANEEL/SIGA (2026)',
             fontsize=14, fontweight='bold', color='#1A1A2E', pad=15)

plt.tight_layout()
plt.savefig('tcc_ve/graficos/aneel_subsistema_fontes.png',
            dpi=180, bbox_inches='tight', facecolor='white')
plt.show()
print("\nGrafico salvo: tcc_ve/graficos/aneel_subsistema_fontes.png")

print("\n" + "="*70)
print("CONCLUIDO")
print("="*70)
