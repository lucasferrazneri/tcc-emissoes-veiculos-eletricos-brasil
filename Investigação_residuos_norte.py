# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# Investigação de Resíduos Industriais e Anomalias no Norte
# =============================================================================
# OBJETIVOS:
#   1. Mapear usinas da categoria "Resíduos Industriais". O objetivo é permitir 
#      a segregação posterior entre Biomassa (celulose) e Fóssil (siderurgia), 
#      evitando inflacionar o fator de emissão do subsistema Norte em ~9%.
#   2. Avaliar a divergência mensal da geração térmica no Norte, testando a 
#      hipótese de que Roraima foi interligada ao SIN ao longo de 2025.
#
# TIPO: Script de diagnóstico (não altera as bases consolidadas).
# =============================================================================

import os
import pandas as pd

PASTA = 'tcc_ve/dados/brutos/geracao_usina'
ANO = 2025

# =============================================================================
# PARTE 1 — TODAS AS USINAS DE "RESÍDUOS INDUSTRIAIS"
# =============================================================================
print('=' * 78)
print('PARTE 1 — USINAS CLASSIFICADAS COMO "RESÍDUOS INDUSTRIAIS"')
print('=' * 78)

blocos = []
for mes in range(1, 13):
    c = f'{PASTA}/GERACAO_USINA-2_{ANO}_{mes:02d}.csv'
    if not os.path.exists(c):
        continue
    d = pd.read_csv(c, sep=';', encoding='utf-8')
    ri = d[d['nom_tipocombustivel'] == 'Resíduos Industriais']
    if len(ri):
        blocos.append(ri.groupby(
            ['id_subsistema', 'id_estado', 'nom_usina', 'ceg',
             'cod_modalidadeoperacao'], dropna=False
        )['val_geracao'].sum().reset_index())
    del d

if not blocos:
    print('\n  Categoria não encontrada nos arquivos.')
else:
    ri_ano = (pd.concat(blocos)
              .groupby(['id_subsistema', 'id_estado', 'nom_usina', 'ceg',
                        'cod_modalidadeoperacao'], dropna=False)
              ['val_geracao'].sum().reset_index())
    ri_ano['GWh_ano'] = (ri_ano['val_geracao'] / 1e3).round(1)
    ri_ano = ri_ano.sort_values('GWh_ano', ascending=False)

    total_ri = ri_ano['GWh_ano'].sum()
    print(f'\n  Total da categoria em {ANO}: {total_ri/1e3:.2f} TWh'
          f'  ({len(ri_ano)} usinas)\n')

    print(ri_ano[['id_subsistema', 'id_estado', 'nom_usina',
                  'cod_modalidadeoperacao', 'GWh_ano']]
          .to_string(index=False))

    print('\n[RESULTADO] Geração por subsistema (TWh):')
    print((ri_ano.groupby('id_subsistema')['GWh_ano'].sum() / 1e3)
          .round(2).to_string())
    print('\n[AÇÃO] Consultar nomes/CEG para classificar manualmente como Fóssil ou Biomassa.')

# =============================================================================
# PARTE 2 — DIVERGÊNCIA MENSAL DA TÉRMICA DO NORTE
# =============================================================================
print('\n' + '=' * 78)
print('PARTE 2 — EVOLUÇÃO MENSAL DA DIVERGÊNCIA (TÉRMICA DO NORTE)')
print('=' * 78)

cam_bal = f'tcc_ve/dados/brutos/BALANCO_ENERGIA_SUBSISTEMA_{ANO}.csv'
if not os.path.exists(cam_bal):
    print(f'\n  Balanço por subsistema não encontrado em {cam_bal}')
else:
    bal = pd.read_csv(cam_bal, sep=';', encoding='utf-8')
    bal = bal[bal['id_subsistema'] == 'N'].copy()
    bal['mes'] = pd.to_datetime(bal['din_instante']).dt.month
    bal_mes = bal.groupby('mes')['val_gertermica'].sum() / 1e3   # GWh

    linhas = []
    for mes in range(1, 13):
        c = f'{PASTA}/GERACAO_USINA-2_{ANO}_{mes:02d}.csv'
        if not os.path.exists(c):
            continue
        d = pd.read_csv(c, sep=';', encoding='utf-8')
        dn = d[(d['id_subsistema'] == 'N') & (d['nom_tipousina'] == 'TÉRMICA')]
        com_rr = dn['val_geracao'].sum() / 1e3
        so_rr  = dn[dn['id_estado'] == 'RR']['val_geracao'].sum() / 1e3
        ref    = bal_mes.get(mes, float('nan'))
        linhas.append({
            'mes': mes,
            'usina_com_RR': round(com_rr, 1),
            'usina_sem_RR': round(com_rr - so_rr, 1),
            'RR': round(so_rr, 1),
            'balanco': round(ref, 1),
            'dif_com_RR_%': round((com_rr - ref) / ref * 100, 1) if ref else None,
            'dif_sem_RR_%': round((com_rr - so_rr - ref) / ref * 100, 1) if ref else None,
        })
        del d

    m = pd.DataFrame(linhas)
    print('\n[RESULTADO] Evolução mensal (Valores em GWh | Divergência em % sobre o balanço):')
    print(m.to_string(index=False))

print('\n' + '=' * 78)
print('FIM DO DIAGNÓSTICO')
print('=' * 78)