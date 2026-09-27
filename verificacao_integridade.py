# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# VERIFICACAO DE INTEGRIDADE dos arquivos baixados do ONS
#
# Confere, para cada arquivo mensal:
#   1. existencia e tamanho plausivel
#   2. cabecalho com as 12 colunas esperadas
#   3. ultima linha completa (detecta download truncado)
#   4. numero de horas distintas = numero de horas do mes
#   5. datas dentro do mes correto
#   6. ausencia de nulos nas colunas criticas
# =============================================================================

import pandas as pd
import calendar
import os

ANO   = 2025
PASTA = 'tcc_ve/dados/brutos/geracao_usina'

COLUNAS_ESPERADAS = [
    'din_instante', 'id_subsistema', 'nom_subsistema', 'id_estado',
    'nom_estado', 'cod_modalidadeoperacao', 'nom_tipousina',
    'nom_tipocombustivel', 'nom_usina', 'id_ons', 'ceg', 'val_geracao'
]

print('=' * 78)
print(f'VERIFICACAO DE INTEGRIDADE — Geracao por Usina {ANO}')
print('=' * 78)
print(f'{"Mes":<5}{"MB":>8}{"Linhas":>10}{"Horas":>8}{"Esper.":>8}'
      f'{"TWh":>9}  Situacao')
print('-' * 78)

problemas = []
resumo = []

for mes in range(1, 13):
    nome    = f'GERACAO_USINA-2_{ANO}_{mes:02d}.csv'
    caminho = os.path.join(PASTA, nome)
    dias    = calendar.monthrange(ANO, mes)[1]
    horas_esperadas = dias * 24

    # --- 1. existencia ---
    if not os.path.exists(caminho):
        print(f'{mes:02d}   {"—":>8}{"—":>10}{"—":>8}{horas_esperadas:>8}'
              f'{"—":>9}  AUSENTE')
        problemas.append(f'{nome}: arquivo nao encontrado')
        continue

    mb = os.path.getsize(caminho) / 1024**2
    if mb < 1:
        print(f'{mes:02d}   {mb:>8.1f}{"—":>10}{"—":>8}{horas_esperadas:>8}'
              f'{"—":>9}  ARQUIVO VAZIO')
        problemas.append(f'{nome}: tamanho de {mb:.2f} MB — provavelmente vazio')
        continue

    erros_mes = []

    # --- 2. cabecalho ---
    with open(caminho, 'r', encoding='utf-8', errors='replace') as f:
        cabecalho = f.readline().strip().split(';')
    if cabecalho != COLUNAS_ESPERADAS:
        faltando = set(COLUNAS_ESPERADAS) - set(cabecalho)
        erros_mes.append(f'cabecalho divergente (faltam: {faltando})')

    # --- 3. ultima linha completa ---
    with open(caminho, 'rb') as f:
        f.seek(max(0, os.path.getsize(caminho) - 4096))
        ultimo_bloco = f.read().decode('utf-8', errors='replace')
    linhas = [l for l in ultimo_bloco.split('\n') if l.strip()]
    if linhas and linhas[-1].count(';') != len(COLUNAS_ESPERADAS) - 1:
        erros_mes.append('ultima linha incompleta — download truncado')

    # --- 4, 5, 6. conteudo ---
    try:
        df = pd.read_csv(caminho, sep=';', encoding='utf-8')
    except Exception as e:
        print(f'{mes:02d}   {mb:>8.1f}{"—":>10}{"—":>8}{horas_esperadas:>8}'
              f'{"—":>9}  ERRO DE LEITURA')
        problemas.append(f'{nome}: {type(e).__name__}: {e}')
        continue

    horas = df['din_instante'].nunique()
    twh   = df['val_geracao'].sum() / 1e6

    if horas != horas_esperadas:
        erros_mes.append(f'{horas} horas, esperado {horas_esperadas}')

    datas = pd.to_datetime(df['din_instante'])
    if datas.dt.month.nunique() != 1 or datas.dt.month.iloc[0] != mes:
        meses_achados = sorted(datas.dt.month.unique())
        erros_mes.append(f'contem meses {meses_achados}, esperado [{mes}]')
    if datas.dt.year.nunique() != 1 or datas.dt.year.iloc[0] != ANO:
        erros_mes.append(f'ano divergente: {sorted(datas.dt.year.unique())}')

    criticas = ['din_instante', 'id_subsistema', 'nom_tipousina',
                'nom_tipocombustivel', 'val_geracao']
    for c in criticas:
        n = df[c].isna().sum()
        if n:
            erros_mes.append(f'{n} nulos em {c}')

    if (df['val_geracao'] < 0).any():
        n = (df['val_geracao'] < 0).sum()
        erros_mes.append(f'{n} valores negativos em val_geracao')

    situacao = 'OK' if not erros_mes else 'PROBLEMA'
    print(f'{mes:02d}   {mb:>8.1f}{len(df):>10,}{horas:>8}{horas_esperadas:>8}'
          f'{twh:>9.2f}  {situacao}')

    if erros_mes:
        for e in erros_mes:
            problemas.append(f'{nome}: {e}')

    resumo.append({'mes': mes, 'linhas': len(df), 'twh': twh,
                   'usinas': df['nom_usina'].nunique()})
    del df

# =============================================================================
print('-' * 78)

if resumo:
    r = pd.DataFrame(resumo)
    print(f'\n  Meses verificados : {len(r)} de 12')
    print(f'  Linhas no total   : {r["linhas"].sum():,}')
    print(f'  Geracao no ano    : {r["twh"].sum():.2f} TWh')
    print(f'  Usinas (min-max)  : {r["usinas"].min()} a {r["usinas"].max()}')

    # Sanity check contra o balanco por subsistema (LOG 05): 700,43 TWh em 2025
    ref = 700.43
    dif = (r['twh'].sum() - ref) / ref * 100
    print(f'\n  Referencia do balanco por subsistema ({ANO}): {ref:.2f} TWh')
    print(f'  Diferenca: {dif:+.1f}%')
    if abs(dif) <= 3:
        print('  -> Compativel. (Pequena diferenca e esperada: os datasets')
        print('     tem criterios de agregacao distintos.)')
    else:
        print('  -> ATENCAO: diferenca alem do esperado. Investigar no 06b.')

print('\n' + '=' * 78)
if problemas:
    print(f'PROBLEMAS ENCONTRADOS ({len(problemas)})')
    print('=' * 78)
    for p in problemas:
        print(f'  - {p}')
    print('\n  Apague os arquivos com problema e rode o download novamente:')
    print('  ele so baixa o que estiver faltando.')
else:
    print('NENHUM PROBLEMA ENCONTRADO.')
print('=' * 78)
