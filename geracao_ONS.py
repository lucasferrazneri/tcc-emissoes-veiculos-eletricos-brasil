# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# Geracao efetiva por subsistema (ONS)
#
# Geracao verificada por subsistema do SIN 
#
# Fonte: ONS, Balanco de Energia nos Subsistemas, 2023 a 2025.
# Baixar em https://dados.ons.org.br e salvar em tcc_ve/dados/brutos/
#
# Diferente da capacidade instalada, que indica quanto as usinas
# poderiam gerar. Este conjunto traz o que efetivamente geraram e o dado
# adequado para estimar emissoes.
# =============================================================================

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os

os.makedirs('tcc_ve/dados/tratados', exist_ok=True)
os.makedirs('tcc_ve/graficos', exist_ok=True)

PASTA = 'tcc_ve/dados/brutos'
ANOS  = [2023, 2024, 2025]

COLS_GERACAO = {
    'val_gerhidraulica': 'Hidráulica',
    'val_gertermica':    'Térmica',
    'val_gereolica':     'Eólica',
    'val_gersolar':      'Solar',
}

NOME_SUB = {
    'N':  'Norte',
    'NE': 'Nordeste',
    'SE': 'Sudeste/C-Oeste',
    'S':  'Sul',
}
ORDEM_SUB = ['Norte', 'Nordeste', 'Sudeste/C-Oeste', 'Sul']

# -----------------------------------------------------------------------------
# PASSO 1 — Carregar os tres anos
# -----------------------------------------------------------------------------
print("="*72)
print("CARREGANDO DADOS DO ONS")
print("="*72)

frames = []
for ano in ANOS:
    caminho = f'{PASTA}/BALANCO_ENERGIA_SUBSISTEMA_{ano}.csv'
    d = pd.read_csv(caminho, sep=';', encoding='utf-8')
    d['ano'] = ano
    horas_esperadas = 8784 if ano % 4 == 0 else 8760
    horas_reais = d['din_instante'].nunique()
    print(f"  {ano}: {len(d):>7,} linhas | {horas_reais:,} horas distintas "
          f"(esperado {horas_esperadas:,})")
    if horas_reais != horas_esperadas:
        print(f"       AVISO: faltam {horas_esperadas - horas_reais} horas neste ano.")
    frames.append(d)

df = pd.concat(frames, ignore_index=True)

# -----------------------------------------------------------------------------
# PASSO 2 — Separar linhas SIN (agregado) das linhas de subsistema
# -----------------------------------------------------------------------------
df_sin_ref = df[df['id_subsistema'] == 'SIN'].copy()   # usado so p/ validacao
df_sub     = df[df['id_subsistema'] != 'SIN'].copy()

df_sub['Subsistema'] = df_sub['id_subsistema'].map(NOME_SUB)

nao_mapeado = df_sub[df_sub['Subsistema'].isna()]['id_subsistema'].unique()
if len(nao_mapeado):
    print(f"\nERRO: subsistemas nao mapeados: {nao_mapeado}")
    raise SystemExit(1)

print(f"\n  Linhas de subsistema: {len(df_sub):,}")
print(f"  Linhas agregadas SIN: {len(df_sin_ref):,} (excluidas do calculo)")

# -----------------------------------------------------------------------------
# PASSO 3 — VALIDACAO: soma dos subsistemas deve bater com a linha SIN
# -----------------------------------------------------------------------------
print("\n" + "="*72)
print("VALIDACAO 1 — soma dos 4 subsistemas vs linha SIN do proprio arquivo")
print("="*72)

soma_sub = df_sub.groupby('ano')[list(COLS_GERACAO)].sum()
soma_sin = df_sin_ref.groupby('ano')[list(COLS_GERACAO)].sum()

print(f"\n{'Ano':<6}{'Fonte':<14}{'Soma subsist.':>16}{'Linha SIN':>16}{'Difer.':>10}")
for ano in ANOS:
    for col, nome in COLS_GERACAO.items():
        a = soma_sub.loc[ano, col]
        b = soma_sin.loc[ano, col]
        dif = (a - b) / b * 100 if b else 0
        flag = '  <-- ATENCAO' if abs(dif) > 1 else ''
        print(f"{ano:<6}{nome:<14}{a/1e6:>15,.1f}M{b/1e6:>15,.1f}M{dif:>9.2f}%{flag}")

# -----------------------------------------------------------------------------
# PASSO 4 — Geracao anual por subsistema e fonte (MWh -> TWh)
# -----------------------------------------------------------------------------
ger = (df_sub.groupby(['ano', 'Subsistema'])[list(COLS_GERACAO)]
       .sum()
       .rename(columns=COLS_GERACAO))

ger_twh = (ger / 1e6).round(2)   # MWh -> TWh

print("\n" + "="*72)
print("GERACAO EFETIVA POR SUBSISTEMA E FONTE (TWh/ano)")
print("="*72)
for ano in ANOS:
    print(f"\n--- {ano} ---")
    bloco = ger_twh.loc[ano].reindex(ORDEM_SUB)
    bloco['TOTAL'] = bloco.sum(axis=1).round(2)
    print(bloco.to_string())
    print(f"{'BRASIL (SIN)':<18}{bloco['TOTAL'].sum():>8.2f} TWh")

# -----------------------------------------------------------------------------
# PASSO 5 — Media dos tres anos e participacao percentual
# -----------------------------------------------------------------------------
media = ger.groupby('Subsistema').mean().reindex(ORDEM_SUB)
media_pct = (media.div(media.sum(axis=1), axis=0) * 100).round(2)

print("\n" + "="*72)
print(f"MEDIA {ANOS[0]}-{ANOS[-1]} — participacao de cada fonte na geracao (%)")
print("="*72)
print(media_pct.to_string())
print("\nVerificacao das somas por linha (deve dar 100%):")
print(media_pct.sum(axis=1).round(1).to_string())

media_twh = (media / 1e6).round(2)
media_twh['TOTAL'] = media_twh.sum(axis=1).round(2)
print("\nEnergia media anual (TWh):")
print(media_twh.to_string())

media_pct.to_csv('tcc_ve/dados/tratados/ons_geracao_pct_subsistema.csv',
                 encoding='utf-8-sig')
media_twh.to_csv('tcc_ve/dados/tratados/ons_geracao_twh_subsistema.csv',
                 encoding='utf-8-sig')

# -----------------------------------------------------------------------------
# PASSO 6 — CAPACIDADE INSTALADA vs GERACAO EFETIVA
# -----------------------------------------------------------------------------
print("\n" + "="*72)
print("VALIDACAO 2 — capacidade instalada (ANEEL) vs geracao efetiva (ONS)")
print("="*72)

caminho_aneel = 'tcc_ve/dados/tratados/aneel_matriz_subsistema.csv'
if os.path.exists(caminho_aneel):
    aneel = pd.read_csv(caminho_aneel, index_col=0)
    # Agrupar a ANEEL nas mesmas 4 categorias do ONS
    comp = pd.DataFrame(index=ORDEM_SUB)
    comp['Hidr_ANEEL_cap%'] = aneel['Hidrelétrica'].reindex(ORDEM_SUB)
    comp['Hidr_ONS_ger%']   = media_pct['Hidráulica']
    comp['Eol_ANEEL_cap%']  = aneel['Eólica'].reindex(ORDEM_SUB)
    comp['Eol_ONS_ger%']    = media_pct['Eólica']
    comp['Sol_ANEEL_cap%']  = aneel['Solar'].reindex(ORDEM_SUB)
    comp['Sol_ONS_ger%']    = media_pct['Solar']
    # Termica ONS = biomassa + gas + petroleo + carvao + outros + nuclear
    termicas_aneel = ['Biomassa','Gás Natural','Petróleo/Diesel',
                      'Carvão Mineral','Outros Fósseis','Nuclear']
    cols_ok = [c for c in termicas_aneel if c in aneel.columns]
    comp['Term_ANEEL_cap%'] = aneel[cols_ok].sum(axis=1).reindex(ORDEM_SUB)
    comp['Term_ONS_ger%']   = media_pct['Térmica']
    print("\n" + comp.round(1).to_string())
    print("\nDiferencas grandes sao esperadas: capacidade e potencial,")
    print("geracao e o que de fato foi produzido (fator de capacidade).")
else:
    print("\n  Arquivo da ANEEL por subsistema nao encontrado.")
    print("  Rode antes o script matriz_subsistema.py.")

# -----------------------------------------------------------------------------
# PASSO 7 — O PROBLEMA DO INTERCAMBIO
# -----------------------------------------------------------------------------
print("\n" + "="*72)
print("VALIDACAO 3 — intercambio: geracao propria cobre o consumo local?")
print("="*72)

bal = (df_sub.groupby(['ano','Subsistema'])
       .agg(geracao=('val_gerhidraulica','sum'),
            carga=('val_carga','sum'),
            interc=('val_intercambio','sum')))
# geracao total = soma das 4 fontes
bal['geracao'] = df_sub.groupby(['ano','Subsistema'])[list(COLS_GERACAO)].sum().sum(axis=1)
bal['autossuf_%'] = (bal['geracao'] / bal['carga'] * 100).round(1)
bal['saldo_TWh']  = ((bal['geracao'] - bal['carga']) / 1e6).round(1)

resumo_bal = bal.groupby('Subsistema')[['autossuf_%','saldo_TWh']].mean().reindex(ORDEM_SUB)
resumo_bal['situacao'] = np.where(resumo_bal['saldo_TWh'] > 0, 'EXPORTADOR', 'IMPORTADOR')

print("\n" + resumo_bal.round(1).to_string())
print("""
LEITURA: autossuficiencia acima de 100 indica que o subsistema gera mais
do que consome; abaixo, que depende de energia importada de outros
subsistemas. Isso significa que o mix GERADO em um subsistema nao e
identico ao mix CONSUMIDO nele.
""")

resumo_bal.to_csv('tcc_ve/dados/tratados/ons_intercambio_subsistema.csv',
                  encoding='utf-8-sig')

# -----------------------------------------------------------------------------
# GRAFICO — composicao da geracao efetiva por subsistema
# -----------------------------------------------------------------------------
CORES = {
    'Hidráulica': '#1565C0',
    'Eólica':     '#2E7D32',
    'Solar':      '#F9A825',
    'Térmica':    '#E64A19',
}
fontes = ['Hidráulica', 'Eólica', 'Solar', 'Térmica']

fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor('white')
ax.set_facecolor('#F8F9FA')

bottom = pd.Series([0.0]*len(media_pct), index=media_pct.index)
for f in fontes:
    vals = media_pct[f]
    ax.bar(media_pct.index, vals, bottom=bottom, color=CORES[f],
           edgecolor='white', linewidth=1.2, width=0.55, label=f)
    for i, (v, b) in enumerate(zip(vals, bottom)):
        if v >= 4:
            ax.text(i, b + v/2, f'{v:.0f}%', ha='center', va='center',
                    fontsize=12, fontweight='bold', color='white')
    bottom = bottom + vals

for s in ['top','right']:
    ax.spines[s].set_visible(False)
ax.spines['left'].set_color('#CCCCCC')
ax.spines['bottom'].set_color('#CCCCCC')

ax.set_ylim(0, 108)
ax.set_ylabel('Participação na geração (%)', fontsize=12, color='#444444')
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f%%'))
ax.tick_params(axis='x', labelsize=12, colors='#333333')
ax.tick_params(axis='y', labelsize=10, colors='#888888')
ax.grid(axis='y', alpha=0.3, linestyle='--', color='#CCCCCC')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.07),
          ncol=4, fontsize=11, framealpha=0.9, edgecolor='#CCCCCC')

ax.set_title(f'Composição da geração efetiva por subsistema do SIN\n'
             f'Média {ANOS[0]}–{ANOS[-1]} — ONS',
             fontsize=14, fontweight='bold', color='#1A1A2E', pad=15)

plt.tight_layout()
plt.savefig('tcc_ve/graficos/ons_geracao_subsistema.png',
            dpi=180, bbox_inches='tight', facecolor='white')
plt.show()

print("\n" + "="*72)
print("CONCLUIDO")
print("="*72)
print("""
LEMBRETE: a coluna 'Térmica' do ONS agrega usinas fosseis, nucleares e a
biomassa. Sem decompor esse mix (dados do IEMA) nao e possivel converter
geracao em emissoes.
""")
