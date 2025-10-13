# sistema_gacha.py
# Contém a classe e toda a lógica para simular o sistema de pulls e o estado do jogo.

import numpy as np
import random
from typing import Dict, List, Tuple

# Módulos
from config import (
    CONFIG_GACHA,
    MAX_RARITY,
    NOMES_DOS_FAMILIARES,
    NUM_CATEGORIAS_ATIVAS,
    FAMILIARES_ATIVOS_POR_CATEGORIA,
    TOTAL_FAMILIARES_POR_CATEGORIA_NA_LISTA
)


class SimuladorGacha:
    """
    Gerencia o estado e as ações do sistema de gacha (pulls).
    """
    
    def __init__(self):
        self.config = CONFIG_GACHA
        self.diamantes_gastos: int = 0
        self.pity_pulls_contador: int = 0
        self.pity_combine_contador: int = 0
        self.creditos_combine: Dict[Tuple[str, int], int] = {}
        self.familiares: List[str] = self._gerar_lista_familiares()
        self.inventario: Dict[str, Dict[int, int]] = {
            familiar: {raridade: 0 for raridade in range(MAX_RARITY + 1)}
            for familiar in self.familiares
        }
        self.raridades_lista: List[int] = list(self.config["DROP_RATES"].keys())
        self.raridades_pesos: List[float] = list(self.config["DROP_RATES"].values())

    def _gerar_lista_familiares(self) -> List[str]:
        lista_completa = NOMES_DOS_FAMILIARES
        familiares_ativos = []
        for i in range(NUM_CATEGORIAS_ATIVAS):
            inicio_bloco = i * TOTAL_FAMILIARES_POR_CATEGORIA_NA_LISTA
            fim_bloco = inicio_bloco + FAMILIARES_ATIVOS_POR_CATEGORIA
            familiares_ativos.extend(lista_completa[inicio_bloco:fim_bloco])
        if not familiares_ativos:
            raise ValueError("Nenhum familiar foi selecionado. Verifique as configurações em config.py")
        return familiares_ativos

    def _puxar_um_unico_familiar(self, silencioso: bool = False) -> Tuple[str, int]:
        self.pity_pulls_contador += 1
        familiar_sorteado = random.choice(self.familiares)
        raridade_sorteada = random.choices(self.raridades_lista, weights=self.raridades_pesos, k=1)[0]
        
        if self.pity_pulls_contador >= self.config["PITY_PULLS_THRESHOLD"]:
            if not silencioso:
                print(f"--- PITY DE PULLS ATINGIDO EM {self.pity_pulls_contador} PULLS! ---")
            raridade_sorteada = self.config["PITY_PULLS_REWARD_RARITY"]
            self.pity_pulls_contador = 0
            
        return familiar_sorteado, raridade_sorteada

    def puxar_um(self, silencioso: bool = False) -> Tuple[str, int]:
        self.diamantes_gastos += self.config["CUSTO_PULL_UNICO"]
        familiar, raridade = self._puxar_um_unico_familiar(silencioso=silencioso)
        self.inventario[familiar][raridade] += 1
        return familiar, raridade

    def puxar_onze(self, silencioso: bool = False) -> List[Tuple[str, int]]:
        self.diamantes_gastos += self.config["CUSTO_PULL_MULTI"]
        resultados = []
        for _ in range(self.config["QTD_PULL_MULTI"]):
            familiar, raridade = self._puxar_um_unico_familiar(silencioso=silencioso)
            self.inventario[familiar][raridade] += 1
            resultados.append((familiar, raridade))
        return resultados

    def puxar_em_massa(self, *, num_pulls: int = 0, num_diamantes: int = 0) -> Tuple[int, int]:
        if num_pulls == 0 and num_diamantes == 0:
            return 0, 0
        pulls_a_fazer = 0
        custo_total = 0
        if num_pulls > 0:
            pulls_a_fazer = num_pulls
            custo_total = pulls_a_fazer * self.config["CUSTO_PULL_UNICO"]
        elif num_diamantes > 0:
            pulls_a_fazer = num_diamantes // self.config["CUSTO_PULL_UNICO"]
            custo_total = pulls_a_fazer * self.config["CUSTO_PULL_UNICO"]
        if pulls_a_fazer == 0:
            return 0, 0
        self.diamantes_gastos += custo_total
        try:
            from tqdm import tqdm
            # Usando leave=False para limpar a barra após a conclusão
            iterator = tqdm(range(pulls_a_fazer), desc="Puxando familiares", leave=False)
        except ImportError:
            iterator = range(pulls_a_fazer)
        for _ in iterator:
            # Puxar em massa é sempre silencioso para não poluir o terminal
            familiar, raridade = self._puxar_um_unico_familiar(silencioso=True)
            self.inventario[familiar][raridade] += 1
        return pulls_a_fazer, custo_total
    
    def puxar_em_lote_otimizado(self, num_pulls: int):
        """
        Executa um lote de pulls de forma massivamente otimizada usando NumPy.
        """
        if num_pulls <= 0:
            return

        # 1. Custo
        # Calcula quantos "pacotes de 11" são necessários e usa o preço do pacote.
        num_pacotes = np.ceil(num_pulls / self.config["QTD_PULL_MULTI"])
        custo_lote = num_pacotes * self.config["CUSTO_PULL_MULTI"]
        self.diamantes_gastos += custo_lote

        # 2. Cálculo matemático do Pity (instantâneo)
        pulls_contados = self.pity_pulls_contador + num_pulls
        pities_ativados = pulls_contados // self.config["PITY_PULLS_THRESHOLD"]
        if pities_ativados > 0:
            # ASSUMINDO: A recompensa do pity é um familiar aleatório da raridade certa
            for _ in range(pities_ativados):
                familiar_recompensa = random.choice(self.familiares)
                self.inventario[familiar_recompensa][self.config["PITY_PULLS_REWARD_RARITY"]] += 1
        self.pity_pulls_contador = pulls_contados % self.config["PITY_PULLS_THRESHOLD"]

        # 3. Vetorização dos Sorteios (extremamente rápido)
        # Sorteia TODOS os familiares de uma vez
        indices_familiares = np.random.randint(0, len(self.familiares), size=num_pulls)
        # Sorteia TODAS as raridades de uma vez
        raridades_sorteadas = np.random.choice(self.raridades_lista, size=num_pulls, p=self.raridades_pesos)

        # 4. Atualiza o inventário
        # Este loop ainda é em Python, mas as operações LENTAS (sorteio) já foram feitas.
        for i in range(num_pulls):
            familiar_sorteado = self.familiares[indices_familiares[i]]
            raridade_sorteada = raridades_sorteadas[i]
            self.inventario[familiar_sorteado][raridade_sorteada] += 1