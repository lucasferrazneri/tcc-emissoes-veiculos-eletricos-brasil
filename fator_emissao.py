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

import pandas as pd
import numpy as np
import os

ANO   = 2025
PASTA = 'tcc_ve/dados/brutos/geracao_usina'
SAIDA = 'tcc_ve/dados/tratados'
os.makedirs(SAIDA, exist_ok=True)

NOME_SUB  = {'N': 'Norte', 'NE': 'Nordeste', 'SE': 'Sudeste/C-Oeste', 'S': 'Sul'}
ORDEM_SUB = ['Norte', 'Nordeste', 'Sudeste/C-Oeste', 'Sul']
REF_MCTI  = 46.1

# Fatores do IEMA - tCO2e/GWh
F_GAS_CC    = 419.0
F_GAS_MOTOR = 506.0
F_CARVAO    = 1064.0
F_OLEO      = 674.0
LIMITE_CC_GWH = 1000.0

# Siderurgicas entram apenas com o excedente injetado no SIN
FRACAO_INJETADA = {'CSP': 50/218, 'Do Atlântico': 200/490}
F_SIDERURGIA = {'CSP': F_CARVAO,
                'Do Atlântico': (2231.7*F_OLEO + 460.9*F_CARVAO)/2692.6}

# Critério sazonal para grupos Multi-Combustível (PQU)
LIMIAR_ENTRESSAFRA = 10.0
F_PQU_FOSSIL = F_GAS_MOTOR     # grupos sem padrao de safra


blocos = []
for mes in range(1, 13):
    c = f'{PASTA}/GERACAO_USINA-2_{ANO}_{mes:02d}.csv'
    if not os.path.exists(c):
        raise SystemExit(f'Arquivo do mes {mes:02d} ausente.')
    d = pd.read_csv(c, sep=';', encoding='utf-8')
    d['Subsistema'] = d['id_subsistema'].map(NOME_SUB)
    ag = d.groupby(['Subsistema', 'nom_tipousina', 'nom_tipocombustivel',
                    'nom_usina'], dropna=False)['val_geracao'].sum().reset_index()
    ag['mes'] = mes
    blocos.append(ag)
    del d

mensal = pd.concat(blocos, ignore_index=True)
mensal['GWh'] = mensal['val_geracao'] / 1e3

g = (mensal.groupby(['Subsistema', 'nom_tipousina', 'nom_tipocombustivel',
                     'nom_usina'], dropna=False)['GWh'].sum().reset_index())

print('=' * 74)
print(f'FATOR DE EMISSAO POR SUBSISTEMA — {ANO}')
print('=' * 74)
print(f'\nGeracao total: {g["GWh"].sum()/1e3:.2f} TWh')

#  classificar cada grupo multi-comb.
mc = mensal[mensal['nom_tipocombustivel'] == 'Outras Multi-Combustível']
tot_grupo = mc.groupby('nom_usina')['GWh'].sum()
jan_mar   = mc[mc['mes'].isin([1, 2, 3])].groupby('nom_usina')['GWh'].sum()
pct_jm    = (jan_mar / tot_grupo * 100).fillna(0)

grupos_cana   = pct_jm[pct_jm < LIMIAR_ENTRESSAFRA].index.tolist()
grupos_outros = pct_jm[pct_jm >= LIMIAR_ENTRESSAFRA].index.tolist()

print(f'\nGrupos "Outras Multi-Combustivel": {len(tot_grupo)} '
      f'({tot_grupo.sum()/1e3:.2f} TWh)')
print(f'  jan-mar < {LIMIAR_ENTRESSAFRA:.0f}% do ano -> bagaco de cana (fator 0)')
print(f'  jan-mar >= {LIMIAR_ENTRESSAFRA:.0f}% -> sem padrao de safra '
      f'(fator {F_PQU_FOSSIL:.0f})\n')

comp = pd.DataFrame({'GWh_ano': tot_grupo.round(1),
                     'jan_mar_%': pct_jm.round(1)})
comp['classe'] = np.where(comp.index.isin(grupos_cana), 'cana', 'outros')
print(comp.sort_values('GWh_ano', ascending=False).head(12).to_string())

gwh_cana   = tot_grupo[grupos_cana].sum()
gwh_outros = tot_grupo[grupos_outros].sum()
print(f'\n  cana   : {gwh_cana/1e3:5.2f} TWh ({gwh_cana/tot_grupo.sum()*100:.0f}%)')
print(f'  outros : {gwh_outros/1e3:5.2f} TWh ({gwh_outros/tot_grupo.sum()*100:.0f}%)')

# ajuste siderurgia
g['GWh_ajust'] = g['GWh']
for usina, frac in FRACAO_INJETADA.items():
    m = g['nom_usina'] == usina
    g.loc[m, 'GWh_ajust'] = g.loc[m, 'GWh'] * frac

# fatores
def fator(row):
    comb, usina, gwh = row['nom_tipocombustivel'], row['nom_usina'], row['GWh']
    if comb == 'Gás':
        return F_GAS_CC if gwh >= LIMITE_CC_GWH else F_GAS_MOTOR
    if comb == 'Carvão':
        return F_CARVAO
    if comb in ('Óleo Combustível', 'Óleo Diesel', 'Multi-Combustível Diesel/Óleo'):
        return F_OLEO
    if comb == 'Resíduos Industriais':
        return F_SIDERURGIA.get(usina, 0.0)
    if comb == 'Outras Multi-Combustível':
        return 0.0 if usina in grupos_cana else F_PQU_FOSSIL
    if comb in ('Biomassa', 'Hidráulica', 'Eólica', 'Fotovoltaica', 'Nuclear'):
        return 0.0
    return np.nan

g['fator'] = g.apply(fator, axis=1)
if g['fator'].isna().any():
    print('\nCombustiveis sem fator:')
    print(g[g['fator'].isna()].groupby('nom_tipocombustivel')['GWh'].sum().to_string())
    raise SystemExit(1)

g['tCO2e'] = g['GWh_ajust'] * g['fator']

# ------------------------------------------------------------- resultados
r = g.groupby('Subsistema').agg(
    TWh=('GWh_ajust', lambda s: s.sum()/1e3),
    MtCO2e=('tCO2e', lambda s: s.sum()/1e6)).reindex(ORDEM_SUB)
r['gCO2e_kWh'] = (r['MtCO2e']*1e6 / (r['TWh']*1e3)).round(1)

print('\n' + '=' * 74)
print('RESULTADO')
print('=' * 74)
print('\n' + r.round(2).to_string())

nacional = g['tCO2e'].sum() / g['GWh_ajust'].sum()
dif = (nacional - REF_MCTI) / REF_MCTI * 100
print(f'\nNACIONAL : {nacional:.1f} gCO2e/kWh')
print(f'MCTI 2025: {REF_MCTI:.1f} gCO2/kWh   ->   {dif:+.1f}%')

if abs(dif) > 15:
    print(f'\nDivergencia de {dif:+.1f}% acima da tolerancia. Causa nao')
    print('identificada — investigar antes de usar os resultados.')

# distancia entre os dois subsistemas de maior fator
top2 = r['gCO2e_kWh'].sort_values(ascending=False).head(2)
gap = (top2.iloc[0] - top2.iloc[1]) / top2.iloc[1] * 100
print(f'\nDistancia entre {top2.index[0]} e {top2.index[1]}: {gap:.1f}%')
if gap < 15:
    print('Diferenca pequena. Recomenda-se tratar os dois como um grupo de')
    print('alta intensidade, sem afirmar qual lidera.')

# ---------------------------------------------------------- sensibilidade
print('\n' + '=' * 74)
print('SENSIBILIDADE')
print('=' * 74)

testes = {
    'Base':                        None,
    'Todo PQU como cana':          ('pqu_cana', None),
    'Todo PQU como gas':           ('pqu_gas',  F_GAS_MOTOR),
    'Siderurgicas integrais':      ('sider',    None),
    'Todo gas como motor':         ('gas',      F_GAS_MOTOR),
}

print(f'\n{"Cenario":<28}{"Nacional":>10}{"vs MCTI":>10}   Ordenacao')
ordens = []
for nome, aj in testes.items():
    gc = g.copy()
    if aj:
        k, v = aj
        if k == 'pqu_cana':
            gc.loc[gc['nom_tipocombustivel'] == 'Outras Multi-Combustível', 'fator'] = 0.0
        elif k == 'pqu_gas':
            gc.loc[gc['nom_tipocombustivel'] == 'Outras Multi-Combustível', 'fator'] = v
        elif k == 'sider':
            gc['GWh_ajust'] = gc['GWh']
        elif k == 'gas':
            gc.loc[gc['nom_tipocombustivel'] == 'Gás', 'fator'] = v
    gc['tCO2e'] = gc['GWh_ajust'] * gc['fator']
    nac = gc['tCO2e'].sum() / gc['GWh_ajust'].sum()
    sub = gc.groupby('Subsistema').apply(
        lambda x: x['tCO2e'].sum()/x['GWh_ajust'].sum(),
        include_groups=False).reindex(ORDEM_SUB)
    ordem = tuple(sub.sort_values(ascending=False).index)
    ordens.append(ordem)
    print(f'{nome:<28}{nac:>10.1f}{(nac-REF_MCTI)/REF_MCTI*100:>9.1f}%   '
          f'{" > ".join(ordem)}')

grupo_alto = [set(o[:2]) for o in ordens]
if len(set(map(frozenset, grupo_alto))) == 1:
    print(f'\nOs dois subsistemas de maior fator sao sempre os mesmos: '
          f'{" e ".join(sorted(grupo_alto[0]))}.')
    if len(set(ordens)) > 1:
        print('A ordem entre eles varia conforme as premissas.')

# ----------------------------------------------------------------- origem
print('\n' + '=' * 74)
print('ORIGEM DAS EMISSOES (MtCO2e)')
print('=' * 74)
e = (g[g['tCO2e'] > 0].groupby(['Subsistema', 'nom_tipocombustivel'])['tCO2e']
     .sum().unstack(fill_value=0).reindex(ORDEM_SUB) / 1e6)
e['TOTAL'] = e.sum(axis=1)
print('\n' + e.round(2).to_string())

r.to_csv(f'{SAIDA}/fator_emissao_final_{ANO}.csv', encoding='utf-8-sig')
comp.to_csv(f'{SAIDA}/classificacao_grupos_pqu_{ANO}.csv', encoding='utf-8-sig')
print(f'\nSalvo em {SAIDA}/')
