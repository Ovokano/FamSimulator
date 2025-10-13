import numpy as np
import random
import logging
from typing import Dict, Tuple, List
from sistema_gacha import SimuladorGacha
from sistema_combine import SistemaCombine
from config import (
    REGRAS_COMBINE_ESTRATEGICO,
    LOTE_DE_PULLS_SIMULACAO,
    PITY_COMBINE_CONFIG,
    LOTE_DE_PULLS_PRECISAO,
    PRECISAO_LIMIAR,
)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable


# ============================ CONFIGURAÇÕES GERAIS ============================

LOG_LEVEL = logging.WARNING  # Pode ser alterado entre WARNING, INFO ou DEBUG
RANDOM_SEED = None         # Defina um número fixo para resultados reprodutíveis

# ==============================================================================

logging.basicConfig(level=LOG_LEVEL, format="%(message)s")

# ============================ FUNÇÕES AUXILIARES ==============================

def obter_objetivos_do_usuario() -> Tuple[Dict[int, int], Dict[int, str]]:
    """
    Pede ao usuário os objetivos de quantidade e os métodos de combine por raridade.
    Retorna:
        objetivos_qtd: dict {raridade: quantidade}
        metodos_por_raridade: dict {raridade: 'probabilistico' | 'garantido'}
    """
    print("\n--- DEFINA SEUS OBJETIVOS ---")
    objetivos_qtd = {}
    metodos_por_raridade = {}
    
    for raridade in [8, 9, 10]:
        while True:
            try:
                qtd = int(input(f"Quantidade desejada de familiares {raridade}*: ") or 0)
                if qtd < 0:
                    raise ValueError
                objetivos_qtd[raridade] = qtd
                break
            except ValueError:
                print("Entrada inválida. Por favor, insira um número inteiro positivo.")

    maior_raridade_desejada = max((r for r, q in objetivos_qtd.items() if q > 0), default=0)

    if maior_raridade_desejada > 0:
        print("\n--- DEFINA OS MÉTODOS DE COMBINE ---")
        for raridade_etapa in range(8, maior_raridade_desejada + 1):
            if raridade_etapa == 10 and 'probabilistico' not in REGRAS_COMBINE_ESTRATEGICO.get(10, {}):
                print(" -> Para 10*, o único método é 100%.")
                metodos_por_raridade[raridade_etapa] = 'garantido'
                continue

            while True:
                metodo_input = input(f" -> Qual método usar para criar {raridade_etapa}* (25 ou 100)? ") or "100"
                if metodo_input == '25':
                    metodos_por_raridade[raridade_etapa] = 'probabilistico'
                    break
                elif metodo_input == '100':
                    metodos_por_raridade[raridade_etapa] = 'garantido'
                    break
                else:
                    print("Entrada inválida. Por favor, digite 25 ou 100.")
    
    return objetivos_qtd, metodos_por_raridade


def verificar_objetivos_atingidos(inventario: Dict, objetivos: Dict) -> bool:
    """Retorna True se todos os objetivos de raridade foram atingidos."""
    for raridade, qtd_desejada in objetivos.items():
        if qtd_desejada == 0:
            continue
        qtd_atual = sum(f.get(raridade, 0) for f in inventario.values())
        if qtd_atual < qtd_desejada:
            return False
    return True


def contar(inventario: Dict, raridade: int) -> int:
    """Conta quantos familiares existem de determinada raridade."""
    return sum(f.get(raridade, 0) for f in inventario.values())


# ============================ LÓGICA PRINCIPAL ================================

def escolher_melhor_candidato(simulador: SimuladorGacha, raridade_a_criar: int, raridade_fonte: int) -> str:
    """
    Escolhe o melhor candidato para combine baseado em:
      - Créditos disponíveis
      - Número de cópias
      - Prioridade a novos familiares
    """
    def pontuar(fam: str) -> int:
        tem_credito = (fam, raridade_fonte) in simulador.creditos_combine
        copias = simulador.inventario[fam][raridade_fonte]
        bonus_novo = 10 if simulador.inventario[fam][raridade_a_criar] == 0 else 0
        return copias + tem_credito + bonus_novo

    return max(simulador.familiares, key=pontuar, default=None)


def tentar_combine_estrategico(simulador: SimuladorGacha, combinador: SistemaCombine,
                               objetivos: Dict, metodos: Dict) -> bool:
    """Executa tentativas de combine estratégico."""
    for raridade_alvo in sorted(objetivos.keys(), reverse=True):
        qtd_atual = contar(simulador.inventario, raridade_alvo)
        if qtd_atual >= objetivos.get(raridade_alvo, 0):
            continue

        raridade_a_criar = raridade_alvo
        while raridade_a_criar >= 8:
            metodo = metodos.get(raridade_a_criar)
            if not metodo:
                break

            raridade_fonte = REGRAS_COMBINE_ESTRATEGICO[raridade_a_criar]['de']
            candidato = escolher_melhor_candidato(simulador, raridade_a_criar, raridade_fonte)

            if not candidato:
                raridade_a_criar -= 1
                continue

            sucesso, pontos, msg, creditos = combinador.combinar_estrategico(
                simulador.inventario, simulador.creditos_combine,
                raridade_a_criar, candidato, metodo
            )

            if "insuficiente" not in msg:
                simulador.creditos_combine = creditos
                simulador.pity_combine_contador += pontos
                logging.debug(f"Combine {raridade_a_criar}* com {candidato} ({metodo}) - {msg}")
                return True  # Houve progresso

            raridade_a_criar -= 1
    return False


def tentar_combine_automatico(simulador: SimuladorGacha, combinador: SistemaCombine) -> bool:
    """Executa combinações automáticas padrão."""
    if combinador.combinar_automatico(simulador.inventario, simulador.familiares):
        logging.debug("Combine automático executado.")
        return True
    return False


def tentar_puxar_material(simulador: SimuladorGacha, objetivos: Dict, modo_precisao: bool) -> None:
    """Executa pulls para obter novos materiais."""
    if modo_precisao:
        simulador.puxar_em_lote_otimizado(LOTE_DE_PULLS_PRECISAO)
        logging.debug("Puxando materiais em modo precisão.")
    else:
        simulador.puxar_em_lote_otimizado(LOTE_DE_PULLS_SIMULACAO)
        logging.debug("Puxando materiais em modo rápido.")


def processar_pity(simulador: SimuladorGacha) -> None:
    """Gerencia o sistema de pity para recompensas garantidas."""
    if simulador.pity_combine_contador >= PITY_COMBINE_CONFIG["THRESHOLD"]:
        num_pities = simulador.pity_combine_contador // PITY_COMBINE_CONFIG["THRESHOLD"]
        simulador.pity_combine_contador %= PITY_COMBINE_CONFIG["THRESHOLD"]
        for _ in range(num_pities):
            recompensa = random.choice(simulador.familiares)
            simulador.inventario[recompensa][PITY_COMBINE_CONFIG["REWARD_RARITY"]] += 1
        logging.debug(f"{num_pities} pity(s) processados.")


def executar_simulacao(objetivos: Dict, metodos: Dict) -> int:
    """
    Executa uma simulação completa até atingir os objetivos.
    Retorna o total de diamantes gastos.
    """
    simulador = SimuladorGacha()
    combinador = SistemaCombine()

    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)
        np.random.seed(RANDOM_SEED)

    maior_raridade_objetivo = max((r for r, q in objetivos.items() if q > 0), default=0)

    while not verificar_objetivos_atingidos(simulador.inventario, objetivos):
        progresso = (
            tentar_combine_estrategico(simulador, combinador, objetivos, metodos)
            or tentar_combine_automatico(simulador, combinador)
        )

        if progresso:
            processar_pity(simulador)
            continue

        qtd_atual = contar(simulador.inventario, maior_raridade_objetivo)
        qtd_objetivo = objetivos.get(maior_raridade_objetivo, 0)
        modo_precisao = qtd_objetivo > 0 and (qtd_atual / qtd_objetivo) >= PRECISAO_LIMIAR

        tentar_puxar_material(simulador, objetivos, modo_precisao)

    return simulador.diamantes_gastos


# ============================ EXECUÇÃO PRINCIPAL ==============================

if __name__ == "__main__":
    objetivos_qtd, metodos_por_raridade = obter_objetivos_do_usuario()

    if not any(objetivos_qtd.values()):
        print("\nNenhum objetivo definido. Encerrando.")
        exit(0)

    while True:
        try:
            num_simulacoes = int(input("Quantas vezes deseja rodar a simulação? ") or 1)
            if num_simulacoes <= 0:
                raise ValueError
            break
        except ValueError:
            print("Entrada inválida. Insira um número inteiro maior que zero.")

    custos = []
    print("\nIniciando simulações... Isso pode levar algum tempo.\n")

    for _ in tqdm(range(num_simulacoes), desc="Simulando"):
        custos.append(executar_simulacao(objetivos_qtd, metodos_por_raridade))

    custos = np.array(custos)

    print("\n" + "=" * 60)
    print("--- RESULTADOS FINAIS DA SIMULAÇÃO ---")
    print("=" * 60)

    for raridade, qtd in objetivos_qtd.items():
        if qtd > 0:
            metodo = metodos_por_raridade[raridade].replace("probabilistico", "25%").replace("garantido", "100%")
            print(f"  - {qtd}x Familiar {raridade}* (método {metodo})")

    print(f"\nBaseado em {num_simulacoes} simulações:")
    print(f"  - Custo médio: {np.mean(custos):,.0f} diamantes".replace(",", "."))
    print(f"  - Custo mínimo: {np.min(custos):,.0f} diamantes".replace(",", "."))
    print(f"  - Custo máximo: {np.max(custos):,.0f} diamantes".replace(",", "."))
    print(f"  - Mediana: {np.median(custos):,.0f} diamantes".replace(",", "."))
    print(f"  - Desvio padrão: {np.std(custos):,.0f} diamantes".replace(",", "."))
    print("=" * 60)