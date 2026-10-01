# Sazonalidade dos grupos "Outras Multi-Combustivel" (PQU) — 2025
# Se a geracao concentrar entre abril e novembro, acompanha a safra de cana
# do Centro-Sul e reforca a hipotese de biomassa. Perfil estavel ao longo do
# ano indicaria combustivel fossil.
#
# Referencia de comparacao: as usinas classificadas como Biomassa no proprio
# conjunto do ONS, cuja sazonalidade e conhecida.

import pandas as pd
import numpy as np
import os
from pathlib import Path

ANO   = 2025
PASTA = Path(__file__).resolve().parents[1] / 'dados' / 'brutos' / 'geracao_usina'

NOME_SUB = {'N': 'Norte', 'NE': 'Nordeste', 'SE': 'Sudeste/C-Oeste', 'S': 'Sul'}
MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

# Safra de cana no Centro-Sul: abril a novembro
SAFRA = [4, 5, 6, 7, 8, 9, 10, 11]

linhas = []
for mes in range(1, 13):
    c = f'{PASTA}/GERACAO_USINA-2_{ANO}_{mes:02d}.csv'
    if not os.path.exists(c):
        raise SystemExit(f'Arquivo do mes {mes:02d} ausente.')
    d = pd.read_csv(c, sep=';', encoding='utf-8')
    d['Subsistema'] = d['id_subsistema'].map(NOME_SUB)
    d = d[d['nom_tipocombustivel'].isin(
        ['Outras Multi-Combustível', 'Biomassa', 'Gás', 'Carvão'])]
    ag = d.groupby(['nom_tipocombustivel', 'Subsistema', 'nom_usina'],
                   dropna=False)['val_geracao'].sum().reset_index()
    ag['mes'] = mes
    linhas.append(ag)
    del d

g = pd.concat(linhas, ignore_index=True)
g['GWh'] = g['val_geracao'] / 1e3

# perfil mensal por fonte
print('=' * 74)
print('PERFIL MENSAL POR COMBUSTIVEL (% do total do ano)')
print('=' * 74)

perfil = (g.groupby(['nom_tipocombustivel', 'mes'])['GWh'].sum().unstack())
perfil_pct = (perfil.div(perfil.sum(axis=1), axis=0) * 100).round(1)
perfil_pct.columns = MESES

print()
print(perfil_pct.to_string())

print("""
  Biomassa e a referencia: concentra na safra (abr-nov).
  Gas e carvao respondem ao despacho, nao a sazonalidade agricola.
  Se "Outras Multi-Combustivel" seguir o padrao da biomassa, a hipotese
  de bagaco de cana se sustenta.
""")

# concentracao na safra
print('=' * 74)
print('CONCENTRACAO NA SAFRA DA CANA (abr-nov = 8 dos 12 meses)')
print('=' * 74)
print('\n  Referencia: 8/12 = 66,7% se a geracao fosse uniforme.\n')

for comb in perfil.index:
    tot = perfil.loc[comb].sum()
    safra = perfil.loc[comb, SAFRA].sum()
    pct = safra / tot * 100
    marca = '  <-- padrao de safra' if pct >= 75 else ''
    print(f'  {comb:<30}{pct:>6.1f}%{marca}')

# correlacao com a biomassa
print('\n' + '=' * 74)
print('CORRELACAO DO PERFIL MENSAL COM O DA BIOMASSA')
print('=' * 74)
print()

base = perfil_pct.loc['Biomassa']
for comb in perfil_pct.index:
    if comb == 'Biomassa':
        continue
    corr = np.corrcoef(base.values, perfil_pct.loc[comb].values)[0, 1]
    print(f'  {comb:<30}{corr:>7.3f}')

print("""
  Correlacao proxima de 1 indica sazonalidade semelhante a da biomassa.
  Proxima de 0 ou negativa indica logica de operacao distinta.
""")

# ------------------------------------ onde estao os grupos PQU multi-comb
print('=' * 74)
print('GRUPOS "OUTRAS MULTI-COMBUSTIVEL" — DISTRIBUICAO')
print('=' * 74)

mc = g[g['nom_tipocombustivel'] == 'Outras Multi-Combustível']
por_usina = (mc.groupby(['Subsistema', 'nom_usina'])['GWh'].sum()
             .sort_values(ascending=False))
print(f'\n  Total: {por_usina.sum()/1e3:.2f} TWh em {len(por_usina)} grupos\n')
print(por_usina.head(12).round(1).to_string())

# Sazonalidade dos tres maiores grupos individualmente
print('\n  Perfil mensal dos tres maiores (% do proprio total):\n')
top3 = por_usina.head(3).index.get_level_values('nom_usina')
det = (mc[mc['nom_usina'].isin(top3)]
       .groupby(['nom_usina', 'mes'])['GWh'].sum().unstack())
det_pct = (det.div(det.sum(axis=1), axis=0) * 100).round(1)
det_pct.columns = MESES
print(det_pct.to_string())

print('\n' + '=' * 74)
print('CONCLUSAO')
print('=' * 74)

mc_safra = perfil.loc['Outras Multi-Combustível', SAFRA].sum() / \
           perfil.loc['Outras Multi-Combustível'].sum() * 100
bio_safra = perfil.loc['Biomassa', SAFRA].sum() / perfil.loc['Biomassa'].sum() * 100
corr_mc = np.corrcoef(base.values,
                      perfil_pct.loc['Outras Multi-Combustível'].values)[0, 1]

print(f'\n  Concentracao na safra — biomassa: {bio_safra:.1f}%')
print(f'  Concentracao na safra — multi-comb.: {mc_safra:.1f}%')
print(f'  Correlacao entre os dois perfis: {corr_mc:.3f}')

if corr_mc >= 0.7 and mc_safra >= 75:
    print('\n  Sazonalidade compativel com bagaco de cana.')
    print('  Tratar como biomassa (fator zero) e a hipotese mais sustentada.')
elif corr_mc <= 0.3:
    print('\n  Sazonalidade incompativel com biomassa.')
    print('  A hipotese de bagaco NAO se sustenta.')
else:
    print('\n  Resultado intermediario. A sazonalidade nao decide a questao;')
    print('  manter os dois cenarios na analise de sensibilidade.')
print('=' * 74)
