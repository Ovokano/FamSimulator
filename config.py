# config.py
# Este arquivo contém todas as regras e constantes do jogo.

# --- CONTROLES DA SIMULAÇÃO ---
# Use estas variáveis para definir as regras da simulação atual.
MAX_RARITY = 10 # Define o tamanho máximo do inventário de pulls. NÃO MUDE ESTE VALOR
LOTE_DE_PULLS_SIMULACAO = 1100 # Tamanho do lote de pulls que o simulador fará de uma vez quando precisar de materiais.
LOTE_DE_PULLS_PRECISAO = 110 # Lote menor a ser usado quando a simulação está perto do objetivo.
PRECISAO_LIMIAR = 0.5     # Percentual do objetivo para ativar modo de precisão

# --- BANCO DE DADOS DE FAMILIARES ---
# A lista completa com todos os 12 nomes possíveis.
NUM_CATEGORIAS_ATIVAS = 3 # Máximo 3
FAMILIARES_ATIVOS_POR_CATEGORIA = 4 # Máximo 4
NOMES_DOS_FAMILIARES = [
    # --- Categoria Attribute ---
    "HI", "TI", "JE", "A",
    # --- Categoria Battle ---
    "KU", "PE", "SHA", "PO",
    # --- Categoria Weapon ---
    "NA", "RU","RION", "MUS"
]
TOTAL_FAMILIARES_POR_CATEGORIA_NA_LISTA = 4 # Constante que define a estrutura da lista acima. NÃO MUDE ESTE VALOR.

# --- GACHA ---
CONFIG_GACHA = {
    "CUSTO_PULL_UNICO": 454, # 5000/11 (mantenho 500?)
    "CUSTO_PULL_MULTI": 5000,
    "QTD_PULL_MULTI": 11,
    "DROP_RATES": { 0: 0.5228, 1: 0.2612, 2: 0.1274, 3: 0.0520, 4: 0.0214, 5: 0.0121, 6: 0.0023, 7: 0.0007, 8: 0.0001 },
    "PITY_PULLS_THRESHOLD": 300,
    "PITY_PULLS_REWARD_RARITY": 6,
}

# --- COMBINAÇÃO ---
PROBABILIDADE_SUCESSO_COMBINE = 0.25
REGRAS_COMBINE_AUTO = {
    1: 2, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 3
}

REGRAS_COMBINE_ESTRATEGICO = {
    8: {
        'de': 7,
        'probabilistico': {'receita': 2, 'sacrificio': 1},
        'garantido':      {'receita': 5}
    },
    9: {
        'de': 8,
        'probabilistico': {'receita': 2, 'sacrificio': 1},
        'garantido':      {'receita': 5}
    },
    10: {
        'de': 9,
        'garantido':      {'receita': 2}
    }
}

PITY_COMBINE_CONFIG = {
    "THRESHOLD": 300,
    "REWARD_RARITY": 7,
    "PONTOS": {
        8:  {'sucesso_prob': 516, 'falha_prob': 48, 'sucesso_garantido': 516},
        9:  {'sucesso_prob': 900, 'falha_prob': 172, 'sucesso_garantido': 900},
        10: {'sucesso_garantido': 0}
    }
}