# sistema_combine.py
# Contém a classe e a lógica para combinar familiares.

import random
from typing import Dict, List, Tuple

# Importa as configurações necessárias
from config import (REGRAS_COMBINE_AUTO, REGRAS_COMBINE_ESTRATEGICO, PITY_COMBINE_CONFIG,
                    FAMILIARES_ATIVOS_POR_CATEGORIA, NUM_CATEGORIAS_ATIVAS)

class SistemaCombine:
    """
    Gerencia as operações de combinação de familiares.
    """
    
    def _get_familiares_por_categoria(self, todos_familiares_ativos: List[str]) -> Dict[str, List[str]]:
        """
        Organiza a lista de familiares ATIVOS em um dicionário por categoria,
        baseado na ORDEM e não no nome.
        """
        categorias = {'A': [], 'B': [], 'C': []}
        letras_categoria = "ABC"
        for i, familiar in enumerate(todos_familiares_ativos):
            indice_categoria = i // FAMILIARES_ATIVOS_POR_CATEGORIA
            if indice_categoria < NUM_CATEGORIAS_ATIVAS:
                letra_categoria = letras_categoria[indice_categoria]
                categorias[letra_categoria].append(familiar)
        return categorias

    def combinar_automatico(self, inventario: Dict, todos_familiares: List[str]) -> List[str]:
        """
        Executa todas as combinações de 100% possíveis para raridades baixas,
        operando individualmente por familiar e em cascata.
        """
        log_combinacoes = []
        
        while True: # Loop para fazer combinações em cascata (0*->1*, depois 1*->2*, etc.)
            houve_combinacao_nesta_rodada = False
            
            # A lógica agora itera por CADA FAMILIAR, em vez de por categoria
            for familiar in todos_familiares:
                for raridade_alvo, qtd_necessaria in REGRAS_COMBINE_AUTO.items():
                    raridade_fonte = raridade_alvo - 1
                    
                    # Verifica se ESTE familiar tem material suficiente
                    if inventario[familiar][raridade_fonte] >= qtd_necessaria:
                        num_combines = inventario[familiar][raridade_fonte] // qtd_necessaria
                        
                        # Consome os materiais e adiciona o resultado AO MESMO familiar
                        inventario[familiar][raridade_fonte] -= num_combines * qtd_necessaria
                        inventario[familiar][raridade_alvo] += num_combines
                        
                        houve_combinacao_nesta_rodada = True
                        log_combinacoes.append(
                            f" -> {familiar}: {num_combines}x item(ns) {raridade_alvo}* criado(s)."
                        )

            # Se rodamos todos os familiares e ninguém conseguiu combinar mais nada, paramos.
            if not houve_combinacao_nesta_rodada:
                break
                
        return log_combinacoes

    def combinar_estrategico(self, inventario: Dict, creditos: Dict, raridade_alvo: int, familiar_alvo: str, metodo: str) -> Tuple[bool, int, str, Dict]:
        regras = REGRAS_COMBINE_ESTRATEGICO.get(raridade_alvo)
        if not regras: return False, 0, "Raridade alvo inválida.", creditos
        
        regras_metodo = regras.get(metodo)
        if not regras_metodo: return False, 0, f"Método '{metodo}' não disponível.", creditos

        raridade_fonte = regras['de']
        qtd_total_necessaria = regras_metodo['receita']
        
        chave_credito = (familiar_alvo, raridade_fonte)
        base_por_credito = creditos.get(chave_credito, 0)
        base_por_inventario = inventario[familiar_alvo][raridade_fonte]
        
        if base_por_credito == 0 and base_por_inventario == 0:
            return False, 0, f"Material base ({familiar_alvo} {raridade_fonte}*) insuficiente.", creditos

        qtd_sacrificio_necessaria = qtd_total_necessaria - 1

        familiares_por_categoria = self._get_familiares_por_categoria(list(inventario.keys()))
        categoria_alvo = next((cat for cat, fams in familiares_por_categoria.items() if familiar_alvo in fams), None)
        if not categoria_alvo: return False, 0, "Categoria não encontrada.", creditos

        familiares_da_categoria = familiares_por_categoria[categoria_alvo]
        total_sacrificio_disponivel = sum(inventario[f][raridade_fonte] for f in familiares_da_categoria)
        
        if base_por_credito == 0:
            total_sacrificio_disponivel -= 1

        if total_sacrificio_disponivel < qtd_sacrificio_necessaria:
            return False, 0, f"Sacrifícios ({raridade_fonte}*) insuficientes na Categoria '{categoria_alvo}'.", creditos
            
        if base_por_credito > 0:
            del creditos[chave_credito]
        else:
            inventario[familiar_alvo][raridade_fonte] -= 1

        itens_a_consumir = qtd_sacrificio_necessaria
        familiares_ordenados = sorted(familiares_da_categoria, key=lambda f: 1 if f == familiar_alvo else 0)
        for familiar in familiares_ordenados:
            if itens_a_consumir == 0: break
            qtd_a_remover = min(itens_a_consumir, inventario[familiar][raridade_fonte])
            inventario[familiar][raridade_fonte] -= qtd_a_remover
            itens_a_consumir -= qtd_a_remover

        pontos_pity = 0
        sucesso = False
        
        if metodo == "garantido":
            sucesso = True
            pontos_pity = PITY_COMBINE_CONFIG["PONTOS"][raridade_alvo]['sucesso_garantido']
        elif metodo == "probabilistico":
            if random.random() < 0.25:
                sucesso = True
                pontos_pity = PITY_COMBINE_CONFIG["PONTOS"][raridade_alvo]['sucesso_prob']
            else:
                sucesso = False
                pontos_pity = PITY_COMBINE_CONFIG["PONTOS"][raridade_alvo]['falha_prob']
                creditos[chave_credito] = 1

        if sucesso:
            inventario[familiar_alvo][raridade_alvo] += 1
            msg = f"SUCESSO! {familiar_alvo} foi combinado para {raridade_alvo}*. Ganhou {pontos_pity} pontos."
        else:
            msg = f"FALHA! O sacrifício foi perdido, mas a base {familiar_alvo} ({raridade_fonte}*) foi mantida. Ganhou {pontos_pity} pontos."
            
        return sucesso, pontos_pity, msg, creditos