# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# SCRIPT: Diagnóstico de Divergência na Geração Térmica (Subsistema Norte)
# =============================================================================
# CONTEXTO: Investigação do desvio de +4,5% (0,82 TWh) na geração térmica do 
#           Subsistema Norte identificado na validação cruzada.
# HIPÓTESE: O dataset "Geração por Usina" engloba Roraima (Sistema Isolado), 
#           enquanto o "Balanço por Subsistema" reflete apenas o SIN.
# OBJETIVO: Quantificar a geração de RR e validar a sua exclusão para 
#           garantir o alinhamento metodológico dos dados.
# =============================================================================

import pandas as pd
import os

PASTA = 'tcc_ve/dados/brutos/geracao_usina'
ANO   = 2025
MES_AMOSTRA = 5          # mes usado no diagnostico detalhado

# =============================================================================
# PARTE 1 — Diagnostico detalhado em um mes
# =============================================================================
caminho = f'{PASTA}/GERACAO_USINA-2_{ANO}_{MES_AMOSTRA:02d}.csv'
df = pd.read_csv(caminho, sep=';', encoding='utf-8')

print('=' * 72)
print(f'PARTE 1 — SUBSISTEMA NORTE EM {MES_AMOSTRA:02d}/{ANO}')
print('=' * 72)

n = df[df['id_subsistema'] == 'N']

print('\nGeracao total do subsistema N, por estado (GWh no mes):')
print((n.groupby('id_estado')['val_geracao'].sum() / 1e3)
      .round(1).sort_values(ascending=False).to_string())

print('\nApenas TERMICA, por estado (GWh no mes):')
t = n[n['nom_tipousina'] == 'TÉRMICA']
print((t.groupby('id_estado')['val_geracao'].sum() / 1e3)
      .round(1).sort_values(ascending=False).to_string())

print('\nApenas TERMICA, por estado e usina (15 maiores, GWh no mes):')
print((t.groupby(['id_estado', 'nom_usina'])['val_geracao'].sum() / 1e3)
      .round(1).sort_values(ascending=False).head(15).to_string())

print('\nApenas TERMICA, por estado e combustivel (GWh no mes):')
print((t.groupby(['id_estado', 'nom_tipocombustivel'])['val_geracao'].sum() / 1e3)
      .round(1).sort_values(ascending=False).to_string())

# =============================================================================
# PARTE 2 — Roraima aparece em quais subsistemas?
# =============================================================================
print('\n' + '=' * 72)
print('PARTE 2 — RORAIMA NO CONJUNTO POR USINA')
print('=' * 72)

rr = df[df['id_estado'] == 'RR']
if len(rr) == 0:
    print('\n[RESULTADO] Roraima não apresenta registos neste ficheiro.')
    print('[DIAGNÓSTICO] Hipótese refutada: O estado não justifica a divergência.')
else:
    print(f'\n  Roraima aparece com {rr["nom_usina"].nunique()} usinas.')
    print(f'  Rotulada sob id_subsistema: {sorted(rr["id_subsistema"].unique())}')
    print(f'  Geracao no mes: {rr["val_geracao"].sum()/1e3:.2f} GWh')
    print('\n  Por tipo de usina (GWh):')
    print((rr.groupby('nom_tipousina')['val_geracao'].sum() / 1e3)
          .round(2).to_string())
    print('\n  Usinas de Roraima (GWh):')
    print((rr.groupby(['nom_usina', 'nom_tipousina', 'nom_tipocombustivel'])
           ['val_geracao'].sum() / 1e3).round(2)
          .sort_values(ascending=False).to_string())

# =============================================================================
# PARTE 3 — Quantificar no ano inteiro
# =============================================================================
print('\n' + '=' * 72)
print(f'PARTE 3 — QUANTIFICACAO NO ANO DE {ANO}')
print('=' * 72)

linhas = []
for mes in range(1, 13):
    c = f'{PASTA}/GERACAO_USINA-2_{ANO}_{mes:02d}.csv'
    if not os.path.exists(c):
        print(f'  Aviso: arquivo do mes {mes:02d} nao encontrado.')
        continue
    d = pd.read_csv(c, sep=';', encoding='utf-8')
    dn = d[d['id_subsistema'] == 'N']
    dt = dn[dn['nom_tipousina'] == 'TÉRMICA']
    linhas.append({
        'mes': mes,
        'term_N_total': dt['val_geracao'].sum(),
        'term_N_sem_RR': dt[dt['id_estado'] != 'RR']['val_geracao'].sum(),
        'term_RR': dt[dt['id_estado'] == 'RR']['val_geracao'].sum(),
        'ger_RR_total': dn[dn['id_estado'] == 'RR']['val_geracao'].sum(),
    })
    del d

r = pd.DataFrame(linhas)
tot_term_n     = r['term_N_total'].sum() / 1e6
tot_term_sem   = r['term_N_sem_RR'].sum() / 1e6
tot_term_rr    = r['term_RR'].sum() / 1e6
tot_ger_rr     = r['ger_RR_total'].sum() / 1e6

REF_BALANCO = 18.46      # TWh — termica do Norte no balanco por subsistema

print(f'\n  Termica do subsistema N (todos os estados) : {tot_term_n:6.2f} TWh')
print(f'  Termica de Roraima                          : {tot_term_rr:6.2f} TWh')
print(f'  Termica do subsistema N excluindo Roraima   : {tot_term_sem:6.2f} TWh')
print(f'  Referencia do balanco por subsistema        : {REF_BALANCO:6.2f} TWh')

dif_com = (tot_term_n - REF_BALANCO) / REF_BALANCO * 100
dif_sem = (tot_term_sem - REF_BALANCO) / REF_BALANCO * 100

print(f'\n  Divergencia COM Roraima      : {dif_com:+.1f}%')
print(f'  Divergencia SEM Roraima      : {dif_sem:+.1f}%')

print('\n[CONCLUSÃO DO DIAGNÓSTICO]:')
if abs(dif_sem) < 1.0 and abs(dif_com) > 2.0:
    print('  [ESTADO] Hipótese Confirmada. A exclusão de Roraima (Sistema Isolado) elimina a divergência.')
    print('  [AÇÃO REQUERIDA] Aplicar filtro `id_estado != "RR"` no script "decomposicao_termica".')
elif abs(dif_sem) < abs(dif_com):
    print('  [ESTADO] Hipótese Parcialmente Confirmada. RR reduz o desvio, mas persiste um resíduo.')
    print('  [AÇÃO REQUERIDA] Ampliar a investigação na base de dados.')
else:
    print('  [ESTADO] Hipótese Refutada. Roraima não explica o desvio térmico.')
    print('  [AÇÃO REQUERIDA] Investigar critérios de agregação ou classificação de autoprodutores.')

print(f'\n  (Geracao total de Roraima no ano, todas as fontes: {tot_ger_rr:.2f} TWh)')
print('=' * 72)