# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# Decomposicao da geracao termica por combustivel (ONS, 2025)
#
# O QUE FAZ:
#   Processa os 12 arquivos mensais de "Geracao por Usina em Base Horaria",
#   um de cada vez para nao estourar a memoria e agrega por subsistema,
#   tipo de usina, combustivel e modalidade de operacao.
#
# VALIDACAO CRUZADA:
#   Compara o total obtido com o "Balanco de Energia nos Subsistemas".
#   Sao dois datasets independentes do ONS.
#   Se convergirem, ambos estao corretos.
#
# UNIDADE:
#   val_geracao esta em MWmed (potencia media na hora). Como cada registro
#   cobre 1 hora, somar MWmed resulta diretamente em MWh.
#
# Fonte: ONS — https://dados.ons.org.br/dataset/geracao-usina-2
# =============================================================================

import pandas as pd
import os
import sys

ANO     = 2025
PASTA   = 'tcc_ve/dados/brutos/geracao_usina'
SAIDA   = 'tcc_ve/dados/tratados'
os.makedirs(SAIDA, exist_ok=True)

NOME_SUB = {'N': 'Norte', 'NE': 'Nordeste', 'SE': 'Sudeste/C-Oeste', 'S': 'Sul'}
ORDEM_SUB = ['Norte', 'Nordeste', 'Sudeste/C-Oeste', 'Sul']

# =============================================================================
# ETAPA 1 — Conferir os arquivos antes de processar
# =============================================================================
print('=' * 74)
print(f'ETAPA 1 — CONFERENCIA DOS ARQUIVOS ({ANO})')
print('=' * 74)

arquivos = {}
for mes in range(1, 13):
    nome = f'GERACAO_USINA-2_{ANO}_{mes:02d}.csv'
    caminho = os.path.join(PASTA, nome)
    if os.path.exists(caminho):
        mb = os.path.getsize(caminho) / 1024**2
        arquivos[mes] = caminho
        print(f'  {mes:02d}  OK    {mb:7.1f} MB')
    else:
        print(f'  {mes:02d}  AUSENTE  -> {caminho}')

if len(arquivos) != 12:
    print(f'\nERRO: {len(arquivos)} de 12 arquivos encontrados. Interrompendo.')
    sys.exit(1)

# =============================================================================
# ETAPA 2 — Processar mes a mes
# =============================================================================
print('\n' + '=' * 74)
print('ETAPA 2 — PROCESSAMENTO')
print('=' * 74)

CHAVES = ['Subsistema', 'nom_tipousina', 'nom_tipocombustivel',
          'cod_modalidadeoperacao']

agregados = []
horas_por_mes = {}
usinas_vistas = set()

for mes, caminho in sorted(arquivos.items()):
    df = pd.read_csv(caminho, sep=';', encoding='utf-8')

    # Mapear subsistema
    df['Subsistema'] = df['id_subsistema'].map(NOME_SUB)
    nao_map = df[df['Subsistema'].isna()]['id_subsistema'].unique()
    if len(nao_map):
        print(f'\n  ERRO no mes {mes:02d}: id_subsistema nao mapeado: {nao_map}')
        sys.exit(1)

    horas = df['din_instante'].nunique()
    horas_por_mes[mes] = horas
    usinas_vistas.update(df['nom_usina'].unique())

    ag = df.groupby(CHAVES, dropna=False)['val_geracao'].sum().reset_index()
    ag['mes'] = mes
    agregados.append(ag)

    print(f'  {mes:02d}  {len(df):>8,} linhas | {horas:>4} horas | '
          f'{df["nom_usina"].nunique():>4} usinas | '
          f'{df["val_geracao"].sum()/1e6:8.2f} TWh')

    del df

dados = pd.concat(agregados, ignore_index=True)

# Conferir cobertura horaria do ano
horas_totais = sum(horas_por_mes.values())
horas_esperadas = 8784 if ANO % 4 == 0 else 8760
print(f'\n  Horas somadas: {horas_totais:,} | esperado: {horas_esperadas:,}')
if horas_totais != horas_esperadas:
    print(f'  AVISO: diferenca de {horas_esperadas - horas_totais} horas.')
print(f'  Usinas distintas no ano: {len(usinas_vistas):,}')

# =============================================================================
# ETAPA 3 — VALIDACAO CRUZADA contra o Balanco por Subsistema
# =============================================================================
print('\n' + '=' * 74)
print('ETAPA 3 — VALIDACAO CRUZADA (geracao_usina vs balanco_subsistema)')
print('=' * 74)

# No balanco, NUCLEAR esta dentro de "termica". Aqui e categoria propria.
# Para comparar, foi agrupado nuclear junto da termica.
mapa_comparacao = {
    'HIDROELÉTRICA': 'Hidráulica',
    'EOLIELÉTRICA':  'Eólica',
    'FOTOVOLTAICA':  'Solar',
    'TÉRMICA':       'Térmica',
    'NUCLEAR':       'Térmica',      # <- agrupado so para a comparacao
}
dados['cat_balanco'] = dados['nom_tipousina'].map(mapa_comparacao)

nao_map = dados[dados['cat_balanco'].isna()]['nom_tipousina'].unique()
if len(nao_map):
    print(f'  ERRO: nom_tipousina nao mapeado: {nao_map}')
    sys.exit(1)

usina = (dados.groupby(['Subsistema', 'cat_balanco'])['val_geracao'].sum()
         .unstack(fill_value=0) / 1e6).reindex(ORDEM_SUB)

caminho_bal = f'{PASTA}/../BALANCO_ENERGIA_SUBSISTEMA_{ANO}.csv'
if os.path.exists(caminho_bal):
    bal = pd.read_csv(caminho_bal, sep=';', encoding='utf-8')
    bal = bal[bal['id_subsistema'] != 'SIN'].copy()
    bal['Subsistema'] = bal['id_subsistema'].map(NOME_SUB)
    balanco = (bal.groupby('Subsistema')[
        ['val_gerhidraulica', 'val_gertermica', 'val_gereolica', 'val_gersolar']
    ].sum() / 1e6).reindex(ORDEM_SUB)
    balanco.columns = ['Hidráulica', 'Térmica', 'Eólica', 'Solar']

    print(f'\n{"Subsistema":<18}{"Fonte":<13}{"por usina":>11}'
          f'{"balanco":>11}{"difer.":>9}')
    print('-' * 62)
    alerta = False
    for sub in ORDEM_SUB:
        for fonte in ['Hidráulica', 'Térmica', 'Eólica', 'Solar']:
            a = usina.loc[sub, fonte] if fonte in usina.columns else 0.0
            b = balanco.loc[sub, fonte]
            d = (a - b) / b * 100 if b else 0.0
            flag = '  <<' if abs(d) > 2 else ''
            if abs(d) > 2:
                alerta = True
            print(f'{sub:<18}{fonte:<13}{a:>10.2f}{b:>11.2f}{d:>8.1f}%{flag}')
    print('-' * 62)
    print(f'{"TOTAL":<31}{usina.sum().sum():>10.2f}{balanco.sum().sum():>11.2f}')
    if alerta:
        print('\n  ATENCAO: divergencias acima de 2% marcadas com <<.')
        print('  Interprete antes de usar os resultados.')
    else:
        print('\n  Convergencia dentro de 2% em todas as celulas: VALIDADO.')
else:
    print(f'  Balanco de {ANO} nao encontrado em {caminho_bal}')
    print('  Validacao cruzada nao realizada.')

# =============================================================================
# ETAPA 4 — DECOMPOSICAO DA GERACAO TERMICA
# =============================================================================
print('\n' + '=' * 74)
print('ETAPA 4 — DECOMPOSICAO DA GERACAO TERMICA POR COMBUSTIVEL')
print('=' * 74)

term = dados[dados['nom_tipousina'] == 'TÉRMICA'].copy()

tab = (term.groupby(['Subsistema', 'nom_tipocombustivel'])['val_geracao']
       .sum().unstack(fill_value=0) / 1e6).reindex(ORDEM_SUB)
tab['TOTAL'] = tab.sum(axis=1)

print('\nGeracao termica por combustivel (TWh/ano):')
print(tab.round(2).to_string())

tab_pct = (tab.drop(columns='TOTAL')
           .div(tab['TOTAL'], axis=0) * 100).round(1)
print('\nParticipacao de cada combustivel dentro da termica (%):')
print(tab_pct.to_string())

# Nuclear separado
nuc = (dados[dados['nom_tipousina'] == 'NUCLEAR']
       .groupby('Subsistema')['val_geracao'].sum() / 1e6)
print('\nGeracao nuclear (TWh/ano) — categoria propria, fora da termica:')
print(nuc.round(2).to_string())

# =============================================================================
# ETAPA 5 —  "Outras Multi-Combustivel"
# =============================================================================
print('\n' + '=' * 74)
print('ETAPA 5 — CATEGORIA SEM COMBUSTIVEL IDENTIFICADO')
print('=' * 74)

mc = term[term['nom_tipocombustivel'] == 'Outras Multi-Combustível']
if len(mc):
    total_term = term['val_geracao'].sum()
    print(f'\n  Volume: {mc["val_geracao"].sum()/1e6:.2f} TWh '
          f'({mc["val_geracao"].sum()/total_term*100:.1f}% da geracao termica)')
    print('\n  Por subsistema (TWh):')
    print((mc.groupby('Subsistema')['val_geracao'].sum() / 1e6)
          .round(2).to_string())
    print('\n  Por modalidade de operacao (TWh):')
    print((mc.groupby('cod_modalidadeoperacao')['val_geracao'].sum() / 1e6)
          .round(2).to_string())
else:
    print('\n  Categoria nao encontrada nos dados de 2025.')

# =============================================================================
# ETAPA 6 — Separar geracao distribuida (MMGD)
# =============================================================================
print('\n' + '=' * 74)
print('ETAPA 6 — GERACAO DISTRIBUIDA (MMGD)')
print('=' * 74)

mmgd = dados[dados['cod_modalidadeoperacao'].str.contains('MMGD', na=False)]
if len(mmgd):
    print(f'\n  Total MMGD: {mmgd["val_geracao"].sum()/1e6:.2f} TWh '
          f'({mmgd["val_geracao"].sum()/dados["val_geracao"].sum()*100:.1f}% '
          f'da geracao total)')
    print('\n  Por subsistema e tipo (TWh):')
    print((mmgd.groupby(['Subsistema', 'nom_tipousina'])['val_geracao'].sum()
           / 1e6).round(2).to_string())
else:
    print('\n  Nenhum registro de MMGD encontrado.')

# =============================================================================
# ETAPA 7 — Salvar
# =============================================================================
dados.to_csv(f'{SAIDA}/ons_geracao_usina_{ANO}_agregado.csv',
             index=False, encoding='utf-8-sig')
tab.round(4).to_csv(f'{SAIDA}/ons_termica_por_combustivel_{ANO}.csv',
                    encoding='utf-8-sig')
tab_pct.to_csv(f'{SAIDA}/ons_termica_pct_{ANO}.csv', encoding='utf-8-sig')

print('\n' + '=' * 74)
print('ARQUIVOS GERADOS')
print('=' * 74)
print(f'  {SAIDA}/ons_geracao_usina_{ANO}_agregado.csv')
print(f'  {SAIDA}/ons_termica_por_combustivel_{ANO}.csv')
print(f'  {SAIDA}/ons_termica_pct_{ANO}.csv')
print('=' * 74)
