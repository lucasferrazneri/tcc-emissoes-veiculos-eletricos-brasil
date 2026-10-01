# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# SCRIPT: Fator de Emissão de CO2 por Subsistema do SIN — 2025
# =============================================================================
# OBJETIVO: Calcular o fator de emissão médio anual por subsistema, 
#           integrando dados de geração (ONS) e fatores por tecnologia (IEMA).
# NOTA: Grupos "Outras Multi-Combustível" classificados dinamicamente via 
#       perfil sazonal (Limiar: <10% de geração no 1º trimestre = Biomassa).
# =============================================================================
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import os

os.makedirs('tcc_ve/graficos', exist_ok=True)
os.makedirs('tcc_ve/dados/tratados', exist_ok=True)

# ----------------------------------------------------------------- parametros
GASOLINA_A = 2210.0     # gCO2 por litro de gasolina A
FRACAO_A   = 0.70       # gasolina C = 70% gasolina A (mistura E30)
PCI_ETANOL = 21.3       # MJ por litro de etanol hidratado
IC_ETANOL  = 27.38      # gCO2eq/MJ, ciclo do combustivel

GASOLINA_C = GASOLINA_A * FRACAO_A
ETANOL_WTW = IC_ETANOL * PCI_ETANOL

# Fator de emissao da geracao, por subsistema (saida do script 07e)
FATOR    = {'Nordeste': 22.2, 'Sudeste/C-Oeste': 28.8, 'Sul': 85.9, 'Norte': 89.6}
FATOR_BR = 43.4

TOTAL_BEV_2025   = 80184        # ABVE
TOTAL_AUTOS_2025 = 1996531      # Fenabrave

# ------------------------------------------------------------- Tabela 3: BEV
# Consumo ja convertido de MJ/km para kWh/km (divisao por 3,6).
# Media aritmetica entre as versoes de cada modelo.
BEV = [
    # modelo,            emplac.,  kWh/km, versoes
    ('BYD Dolphin Mini',   32459,  0.1120, 3),
    ('BYD Dolphin',        15216,  0.1292, 2),
    ('BYD Yuan Plus',       6019,  0.1556, 2),
    ('Volvo EX30',          3511,  0.1528, 6),
    ('GWM Ora 03',          3237,  0.1454, 3),
    ('Renault E-Kwid',       599,  0.1222, 1),
]

# ------------------------------------------------------- Tabela 4: combustao
# Consumo combinado em km/l: 55% cidade + 45% estrada, media harmonica.
# Todos os modelos sao flex, o que permite comparar os dois combustiveis.
COMB = [
    # modelo,              emplac., etanol, gasolina, versoes
    ('Volkswagen Polo',    122672, 10.01, 14.48, 5),
    ('Fiat Argo',          102630,  9.68, 13.71, 4),
    ('Volkswagen T-Cross',  92837,  9.11, 13.00, 4),
    ('Hyundai HB20',        85029, 10.01, 14.04, 8),
    ('Chevrolet Onix',      79886,  9.56, 13.73, 8),
    ('Hyundai Creta',       76156,  8.66, 12.31, 4),
]

# ------------------------------------------------------------------ Tabela 3
tot_bev = sum(m[1] for m in BEV)
consumo_bev = sum(m[2] * m[1] for m in BEV) / tot_bev

print('=' * 70)
print('TABELA 3 — Veiculos exclusivamente eletricos')
print('=' * 70)
print(f"\n{'Modelo':<20}{'Vers.':>6}{'Empl.':>9}{'Part.':>8}{'kWh/km':>9}")
for nome, empl, cons, nv in BEV:
    print(f'{nome:<20}{nv:>6}{empl:>9,}{empl/tot_bev*100:>7.0f}%{cons:>9.3f}')
print(f"\n{'Media ponderada':<20}{sum(m[3] for m in BEV):>6}{tot_bev:>9,}"
      f"{'100%':>8}{consumo_bev:>9.3f}")
print(f'\nCobertura: {tot_bev/TOTAL_BEV_2025*100:.0f}% dos {TOTAL_BEV_2025:,} BEV de 2025')

# A ponderacao importa: os dois modelos mais vendidos sao os de menor consumo
simples = sum(m[2] for m in BEV) / len(BEV)
print(f'Media simples entre modelos: {simples:.3f} kWh/km '
      f'({(1 - consumo_bev/simples)*100:+.0f}% apos ponderar)')

# ------------------------------------------------------------------ Tabela 4
tot_comb = sum(m[1] for m in COMB)
etanol_kml   = sum(m[2] * m[1] for m in COMB) / tot_comb
gasolina_kml = sum(m[3] * m[1] for m in COMB) / tot_comb

print('\n' + '=' * 70)
print('TABELA 4 — Automoveis a combustao')
print('=' * 70)
print(f"\n{'Modelo':<22}{'Vers.':>6}{'Empl.':>9}{'Etanol':>9}{'Gasolina':>10}")
for nome, empl, et, gs, nv in COMB:
    print(f'{nome:<22}{nv:>6}{empl:>9,}{et:>9.2f}{gs:>10.2f}')
print(f"\n{'Media ponderada':<22}{sum(m[4] for m in COMB):>6}{tot_comb:>9,}"
      f'{etanol_kml:>9.2f}{gasolina_kml:>10.2f}  km/l')
print(f'\nCobertura: {tot_comb/TOTAL_AUTOS_2025*100:.0f}% dos '
      f'{TOTAL_AUTOS_2025:,} automoveis de 2025')

# --------------------------------------------------- emissao por quilometro
emis_gasolina = GASOLINA_C / gasolina_kml
emis_etanol   = ETANOL_WTW / etanol_kml

print('\n' + '=' * 70)
print('EMISSAO POR QUILOMETRO')
print('=' * 70)
print(f'\n  Gasolina C ....................... {emis_gasolina:6.1f} gCO2/km')
print(f'  Etanol, ciclo do combustivel ..... {emis_etanol:6.1f} gCO2eq/km')
print(f'  Etanol, operacao (biogenico) ..... {0.0:6.1f} gCO2/km')

# ------------------------------------------------------------------ Tabela 5
linhas = []
for sub, fat in sorted(FATOR.items(), key=lambda x: x[1]):
    bev = fat * consumo_bev
    linhas.append((sub, fat, bev,
                   (1 - bev/emis_gasolina) * 100,
                   (1 - bev/emis_etanol) * 100))
bev_br = FATOR_BR * consumo_bev
linhas.append(('Brasil (SIN)', FATOR_BR, bev_br,
               (1 - bev_br/emis_gasolina) * 100,
               (1 - bev_br/emis_etanol) * 100))

print('\n' + '=' * 70)
print('TABELA 5 — Reducao do veiculo eletrico por subsistema')
print('=' * 70)
print(f"\n{'Subsistema':<20}{'gCO2e/kWh':>11}{'gCO2e/km':>10}{'vs gasolina':>13}{'vs etanol':>11}")
for sub, fat, bev, rg, re in linhas:
    print(f'{sub:<20}{fat:>11.0f}{bev:>10.1f}{rg:>12.0f}%{re:>10.0f}%')

pd.DataFrame(linhas, columns=['subsistema', 'fator_gCO2e_kWh', 'bev_gCO2e_km',
                              'reducao_gasolina_pct', 'reducao_etanol_pct']) \
  .to_csv('tcc_ve/dados/tratados/comparacao_veicular.csv',
          index=False, encoding='utf-8-sig')

# ------------------------------------------------------------------ Figura 6
subs = [l[0] for l in linhas[:-1]]
bevs = [l[2] for l in linhas[:-1]]

fig, ax = plt.subplots(figsize=(8.2, 4.6))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

rotulos = ['Gasolina C', 'Etanol\n(ciclo do combustível)'] + \
          [f'BEV\n{s.replace("Sudeste/C-Oeste", "Sudeste/Centro-Oeste")}' for s in subs]
valores = [emis_gasolina, emis_etanol] + bevs
cores   = ['#1F77B4'] * len(valores)

barras = ax.bar(rotulos, valores, color=cores,
                 edgecolor='white', linewidth=1.2, width=0.72)
for b, v in zip(barras, valores):
    ax.text(b.get_x() + b.get_width()/2, v + 1.5,
            f'{v:.1f}'.replace('.', ','), va='bottom', ha='center',
            fontsize=10, fontweight='bold', color='#333333')

for s in ('top', 'right'):
    ax.spines[s].set_visible(False)
ax.spines['left'].set_color('#333333')
ax.spines['bottom'].set_color('#333333')
ax.set_ylabel('Emissão (gCO₂e/km)', fontsize=10, color='#333333')
ax.set_xlabel('Tecnologia e referência de recarga', fontsize=10, color='#333333')
ax.set_ylim(0, 125)
ax.tick_params(axis='x', labelsize=9.5, colors='#333333')
ax.tick_params(axis='y', labelsize=9, colors='#333333')
plt.tight_layout()
plt.savefig('tcc_ve/graficos/figura6_comparacao_geral.png', dpi=180,
            bbox_inches='tight', facecolor='white')
plt.close()

print('\n' + '=' * 70)
print('ARQUIVOS GERADOS')
print('=' * 70)
print('  tcc_ve/dados/tratados/comparacao_veicular.csv')
print('  tcc_ve/graficos/figura6_comparacao_geral.png')
