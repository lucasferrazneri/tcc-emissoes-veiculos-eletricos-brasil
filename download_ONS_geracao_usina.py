# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# DOWNLOAD automatico dos arquivos mensais do ONS
#              "Geracao por Usina em Base Horaria"
#
# Baixa os 12 arquivos de 2025 direto do S3 do ONS.
# Nao sobrescreve arquivos ja baixados
#
# Fonte: https://dados.ons.org.br/dataset/geracao-usina-2
# =============================================================================

import os
import time
import urllib.request
import urllib.error

ANO     = 2025
MESES   = range(1, 13)          # 1 a 12
DESTINO = 'tcc_ve/dados/brutos/geracao_usina'

BASE_URL = ('https://ons-aws-prod-opendata.s3.amazonaws.com'
            '/dataset/geracao_usina_2_ho')

os.makedirs(DESTINO, exist_ok=True)

# -----------------------------------------------------------------------------
# Funcao de download com barra de progresso
# -----------------------------------------------------------------------------
def progresso(bloco, tam_bloco, tam_total):
    if tam_total <= 0:
        return
    baixado = bloco * tam_bloco
    pct = min(baixado / tam_total * 100, 100)
    mb_atual = baixado / 1024**2
    mb_total = tam_total / 1024**2
    barra = '#' * int(pct // 4) + '.' * (25 - int(pct // 4))
    print(f'\r      [{barra}] {pct:5.1f}%  {mb_atual:6.1f} / {mb_total:.1f} MB',
          end='', flush=True)

# -----------------------------------------------------------------------------
# Loop de download
# -----------------------------------------------------------------------------
print('=' * 70)
print(f'DOWNLOAD — Geracao por Usina em Base Horaria ({ANO})')
print('=' * 70)
print(f'Destino: {DESTINO}\n')

baixados, pulados, falhas = [], [], []

for mes in MESES:
    nome    = f'GERACAO_USINA-2_{ANO}_{mes:02d}.csv'
    url     = f'{BASE_URL}/{nome}'
    caminho = os.path.join(DESTINO, nome)

    # Ja existe? pula.
    if os.path.exists(caminho) and os.path.getsize(caminho) > 1024:
        tam = os.path.getsize(caminho) / 1024**2
        print(f'  {mes:02d}/{ANO}  ja existe ({tam:.1f} MB) — pulando')
        pulados.append(nome)
        continue

    print(f'  {mes:02d}/{ANO}  baixando {nome}')
    try:
        urllib.request.urlretrieve(url, caminho, reporthook=progresso)
        tam = os.path.getsize(caminho) / 1024**2
        print(f'\n         concluido ({tam:.1f} MB)')
        baixados.append(nome)
        time.sleep(1)          # pausa breve entre requisicoes
    except urllib.error.HTTPError as e:
        print(f'\n         FALHOU — HTTP {e.code}')
        print(f'         URL tentada: {url}')
        falhas.append((nome, f'HTTP {e.code}'))
        if os.path.exists(caminho):
            os.remove(caminho)
    except Exception as e:
        print(f'\n         FALHOU — {type(e).__name__}: {e}')
        falhas.append((nome, str(e)))
        if os.path.exists(caminho):
            os.remove(caminho)

# -----------------------------------------------------------------------------
# Resumo
# -----------------------------------------------------------------------------
print('\n' + '=' * 70)
print('RESUMO')
print('=' * 70)
print(f'  Baixados agora : {len(baixados)}')
print(f'  Ja existentes  : {len(pulados)}')
print(f'  Falhas         : {len(falhas)}')

if falhas:
    print('\n  Arquivos que falharam:')
    for nome, motivo in falhas:
        print(f'    {nome}  ->  {motivo}')
    print('\n  Erro 403 ou 404 costuma significar que o padrao do nome mudou.')
    print('  Confira na pagina do ONS o nome exato do arquivo e ajuste a')
    print('  variavel "nome" no script.')

# Listagem final
print('\n  Conteudo da pasta:')
total_mb = 0
for arq in sorted(os.listdir(DESTINO)):
    if arq.endswith('.csv'):
        mb = os.path.getsize(os.path.join(DESTINO, arq)) / 1024**2
        total_mb += mb
        print(f'    {arq:<35} {mb:8.1f} MB')
print(f'    {"TOTAL":<35} {total_mb:8.1f} MB')

if len(pulados) + len(baixados) == len(list(MESES)):
    print('\n  Os 12 meses estao disponiveis. Pode seguir para o processamento.')
print('=' * 70)
