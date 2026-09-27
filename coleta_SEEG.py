# =============================================================================
# TCC - MBA Data Science e Analytics (USP/ESALQ)
# Aluno: Lucas Ferraz Neri Ferreira
#
# Coleta e exploração dos dados do SEEG
# Arquivo: Dados-nacionais-13.0 (1).xlsx
# =============================================================================

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# -----------------------------------------------------------------------------
# PASSO 1 — Criar estrutura de pastas do projeto
# -----------------------------------------------------------------------------
pastas = [
    "tcc_ve/dados/brutos",
    "tcc_ve/dados/tratados",
    "tcc_ve/scripts",
    "tcc_ve/graficos",
    "tcc_ve/relatorio"
]
for pasta in pastas:
    os.makedirs(pasta, exist_ok=True)
print("Estrutura de pastas criada em 'tcc_ve/'")

# -----------------------------------------------------------------------------
# PASSO 2 — Carregar a aba "Consulta Série Histórica"
# ATENÇÃO: coloque o arquivo na mesma pasta deste script antes de rodar
# -----------------------------------------------------------------------------
ARQUIVO = "Dados-nacionais-13.0 (1).xlsx"
ABA     = "Consulta Série Histórica"

print(f"\nCarregando '{ARQUIVO}', aba '{ABA}'...")
df_raw = pd.read_excel(ARQUIVO, sheet_name=ABA, header=None)
print(f"Dimensões brutas: {df_raw.shape[0]} linhas x {df_raw.shape[1]} colunas")

# -----------------------------------------------------------------------------
# PASSO 3 — Identificar onde começa a tabela de dados
# A aba tem filtros no topo (Gás, Estado, Bioma) antes do cabeçalho real.
# -----------------------------------------------------------------------------
linha_cabecalho = None
for i, row in df_raw.iterrows():
    if row.astype(str).str.contains("Rótulos de Linha", na=False).any():
        linha_cabecalho = i
        break

if linha_cabecalho is None:
    print("ATENÇÃO: não encontrei 'Rótulos de Linha'. Verifique a aba selecionada.")
else:
    print(f"Cabeçalho encontrado na linha {linha_cabecalho}")

# Recarregar a partir da linha do cabeçalho
df = pd.read_excel(ARQUIVO, sheet_name=ABA, header=linha_cabecalho)
df.columns = df.columns.astype(str).str.strip()
print(f"\nColunas encontradas (primeiras 10): {df.columns.tolist()[:10]}")
print(f"Dimensões: {df.shape[0]} linhas x {df.shape[1]} colunas")

# -----------------------------------------------------------------------------
# PASSO 4 — Renomear coluna de setores e limpar dados
# -----------------------------------------------------------------------------
# A primeira coluna é "Rótulos de Linha" — renomear para "Setor"
primeira_col = df.columns[0]
df = df.rename(columns={primeira_col: "Setor"})
df["Setor"] = df["Setor"].astype(str).str.strip()

# Remover linhas vazias ou de total geral
df = df[~df["Setor"].isin(["nan", "Total Geral", "Grand Total", ""])]
df = df.dropna(subset=["Setor"])

print(f"\nSetores disponíveis:\n{df['Setor'].unique()}")

# -----------------------------------------------------------------------------
# PASSO 5 — Filtrar setores relevantes 
# Foco: Energia > Transportes e Energia > Geração de eletricidade
# -----------------------------------------------------------------------------
setores_interesse = [
    "Energia",
    "Transportes",
    "Geração de eletricidade (serviço público)"
]

df_filtrado = df[df["Setor"].isin(setores_interesse)].copy()
print(f"\nLinhas filtradas: {len(df_filtrado)}")
print(df_filtrado[["Setor"]].to_string())

# -----------------------------------------------------------------------------
# PASSO 6 — Identificar colunas de anos (formato "Soma de AAAA")
# -----------------------------------------------------------------------------
colunas_anos = [c for c in df.columns if "Soma de" in c or c.isdigit()]
print(f"\nColunas de anos encontradas: {len(colunas_anos)}")
print(f"Primeira: {colunas_anos[0]} | Última: {colunas_anos[-1]}")

# Renomear colunas de anos para só o número (ex: "Soma de 1990" -> "1990")
renomear = {c: c.replace("Soma de ", "").strip() for c in colunas_anos}
df_filtrado = df_filtrado.rename(columns=renomear)
anos = list(renomear.values())

# -----------------------------------------------------------------------------
# PASSO 7 — Transformar para formato longo (ideal para análise)
# De: uma coluna por ano
# Para: colunas Setor | Ano | Emissoes_tCO2e
# -----------------------------------------------------------------------------
df_longo = df_filtrado.melt(
    id_vars=["Setor"],
    value_vars=anos,
    var_name="Ano",
    value_name="Emissoes_tCO2e"
)
df_longo["Ano"] = pd.to_numeric(df_longo["Ano"], errors="coerce")
df_longo["Emissoes_tCO2e"] = pd.to_numeric(df_longo["Emissoes_tCO2e"], errors="coerce")
df_longo = df_longo.dropna()

print(f"\nDataset final — primeiras linhas:")
print(df_longo.head(10).to_string(index=False))
print(f"\nEstatísticas descritivas:")
print(df_longo.groupby("Setor")["Emissoes_tCO2e"].describe())

# -----------------------------------------------------------------------------
# PASSO 8 — Salvar dataset tratado
# -----------------------------------------------------------------------------
SAIDA = "tcc_ve/dados/tratados/seeg_energia_transportes.csv"
df_longo.to_csv(SAIDA, index=False, encoding="utf-8-sig")
print(f"\nArquivo salvo em: {SAIDA}")

# -----------------------------------------------------------------------------
# PASSO 9 — Visualização: emissões ao longo do tempo por setor
# -----------------------------------------------------------------------------
plt.figure(figsize=(12, 6))

for setor in df_longo["Setor"].unique():
    dados_setor = df_longo[df_longo["Setor"] == setor]
    plt.plot(
        dados_setor["Ano"],
        dados_setor["Emissoes_tCO2e"] / 1e6,  # converter para MtCO2e
        marker="o", markersize=4, linewidth=2,
        label=setor
    )

plt.title("Emissões de CO₂e — Energia e Transportes no Brasil (SEEG)", fontsize=14)
plt.xlabel("Ano")
plt.ylabel("Emissões (MtCO₂e)")
plt.legend(fontsize=9)
plt.grid(True, alpha=0.3)
plt.tight_layout()

GRAFICO = "tcc_ve/graficos/seeg_emissoes_serie_historica.png"
plt.savefig(GRAFICO, dpi=150)
plt.show()
print(f"Gráfico salvo em: {GRAFICO}")

# -------
# RESUMO  
# -------
print("\n" + "="*60)
print("CONCLUIDO!")
print("="*60)
print(f"Dataset tratado : {SAIDA}")
print(f"Gráfico         : {GRAFICO}")
print("="*60)