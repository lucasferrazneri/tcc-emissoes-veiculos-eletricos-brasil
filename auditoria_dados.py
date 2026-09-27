# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# SCRIPT 00 — AUDITORIA dos dados da ANEEL/SIGA
# Objetivo: verificar se o encoding e a classificação de fontes estão corretos
# Este script NÃO gera gráficos. Só imprime diagnósticos.
# =============================================================================
import pandas as pd

ARQUIVO = 'tcc_ve/dados/brutos/siga-empreendimentos-geracao.csv'

print("="*70)
print("TESTE 1 — QUAL ENCODING LÊ OS ACENTOS CORRETAMENTE?")
print("="*70)

for enc in ['latin1', 'utf-8', 'cp1252']:
    try:
        amostra = pd.read_csv(ARQUIVO, sep=';', encoding=enc, nrows=5000)
        col = 'DscFonteCombustivel'
        valores = amostra[col].dropna().astype(str).unique()
        # Procurar valores que deveriam ter acento
        com_acento = [v for v in valores if any(c in v for c in 'ÇÃÁÓÊÉÍÔÚ')]
        corrompidos = [v for v in valores if '\ufffd' in v or '?' in v]
        print(f"\n[{enc}]")
        print(f"  Valores com acento reconhecido : {len(com_acento)}")
        print(f"  Valores aparentemente corrompidos: {len(corrompidos)}")
        if com_acento:
            print(f"  Exemplos OK      : {com_acento[:4]}")
        if corrompidos:
            print(f"  Exemplos quebrados: {corrompidos[:4]}")
    except Exception as e:
        print(f"\n[{enc}] FALHOU: {e}")

print("\n" + "="*70)
print("TESTE 2 — TODAS AS FONTES DE COMBUSTIVEL E SUA POTENCIA")
print("="*70)
print("(usando o encoding que funcionou melhor no teste 1 — ajuste se preciso)")

ENCODING = 'latin1'   # <<< troque aqui se o teste 1 indicar outro

df = pd.read_csv(ARQUIVO, sep=';', encoding=ENCODING)
df_op = df[df['DscFaseUsina'].str.contains('Opera', case=False, na=False)].copy()
df_op['PotenciaMW'] = pd.to_numeric(
    df_op['MdaPotenciaFiscalizadaKw'], errors='coerce'
) / 1000

total_mw = df_op['PotenciaMW'].sum()

resumo = (df_op.groupby('DscFonteCombustivel')['PotenciaMW']
          .agg(['sum', 'count'])
          .sort_values('sum', ascending=False))
resumo['pct'] = (resumo['sum'] / total_mw * 100).round(2)
resumo.columns = ['MW', 'n_usinas', 'pct_matriz']

print(f"\nTotal em operacao: {total_mw:,.0f} MW\n")
print(resumo.head(40).to_string())

print("\n" + "="*70)
print("TESTE 3 — O QUE CAIU EM 'TERMELETRICA OUTRAS'?")
print("="*70)

def classificar_fonte(row):
    tipo  = str(row['SigTipoGeracao']).upper()
    fonte = str(row['DscFonteCombustivel']).upper()
    if 'UHE' in tipo or 'PCH' in tipo or 'CGH' in tipo or 'HIDRO' in fonte:
        return 'Hidreletrica'
    elif 'EOL' in tipo or 'EOLICA' in fonte:
        return 'Eolica'
    elif 'UFV' in tipo or 'SOLAR' in fonte:
        return 'Solar'
    elif 'UTE' in tipo:
        if any(x in fonte for x in ['GÁS','GAS','NATURAL']): return 'Gas Natural'
        elif any(x in fonte for x in ['CARVÃO','CARVAO']):   return 'Carvao'
        elif any(x in fonte for x in ['ÓLEO','OLEO','DIESEL','FUEL']): return 'Oleo/Diesel'
        elif any(x in fonte for x in ['BIOMASSA','BAGAÇO','BAGACO','MADEIRA','RESÍDUO','RESIDUO']):
            return 'Biomassa'
        else: return 'Termeletrica Outras'
    elif 'UNF' in tipo or 'NUCLEAR' in fonte: return 'Nuclear'
    elif 'UTD' in tipo or 'CGU' in tipo: return 'Biomassa'
    else: return 'Outras'

df_op['Classe'] = df_op.apply(classificar_fonte, axis=1)

for classe in ['Termeletrica Outras', 'Outras']:
    sub = df_op[df_op['Classe'] == classe]
    if len(sub) == 0:
        continue
    print(f"\n--- {classe}: {sub['PotenciaMW'].sum():,.0f} MW "
          f"({sub['PotenciaMW'].sum()/total_mw*100:.1f}% da matriz) ---")
    detalhe = (sub.groupby('DscFonteCombustivel')['PotenciaMW']
               .sum().sort_values(ascending=False))
    print(detalhe.head(20).to_string())

print("\n" + "="*70)
print("TESTE 4 — RENOVAVEIS: COMO ESTA vs COMO DEVERIA ESTAR")
print("="*70)

renov_atual = ['Hidreletrica', 'Eolica', 'Solar', 'Biomassa']
pct_atual = (df_op[df_op['Classe'].isin(renov_atual)]['PotenciaMW'].sum()
             / total_mw * 100)

print(f"\nRenovaveis pela classificacao ATUAL do script: {pct_atual:.1f}%")
print("\nOlhe o TESTE 3 acima: se houver bagaco, biomassa, licor negro,")
print("residuos florestais ou biogas dentro de 'Termeletrica Outras',")
print("entao esse percentual esta SUBESTIMADO.")
print("="*70)
