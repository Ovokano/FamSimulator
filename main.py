import random
from sistema_gacha import SimuladorGacha
from sistema_combine import SistemaCombine
from config import PITY_COMBINE_CONFIG, CONFIG_GACHA, REGRAS_COMBINE_ESTRATEGICO

def exibir_estado_completo(simulador: SimuladorGacha):
    """Função auxiliar para mostrar o estado completo da simulação."""
    print("\n" + "="*40)
    print("ESTADO ATUAL DA SIMULAÇÃO")
    print(f" -> Diamantes Gastos: {simulador.diamantes_gastos:,}".replace(",", "."))
    print(f" -> Pity de Pulls: {simulador.pity_pulls_contador} / {CONFIG_GACHA['PITY_PULLS_THRESHOLD']}")
    print(f" -> Pity de Combine: {simulador.pity_combine_contador} / {PITY_COMBINE_CONFIG['THRESHOLD']}")
    
    if simulador.creditos_combine:
        print(" -> Créditos de Combine (Base Mantida):")
        for (familiar, raridade), qtd in simulador.creditos_combine.items():
            print(f"    - {qtd}x {familiar} ({raridade}*)")

    print("="*40)

def exibir_inventario(simulador: SimuladorGacha):
    """Mostra o inventário de forma organizada e compacta."""
    print("\n--- SEU INVENTÁRIO ---")
    encontrou_algo = False
    # Extrai a letra da categoria para agrupar
    familiares_por_categoria = {}
    for f_nome in simulador.familiares:
        # Acha a categoria pela ordem na lista, não pelo nome
        indice = simulador.familiares.index(f_nome)
        indice_categoria = indice // simulador.config.get("FAMILIARES_POR_CATEGORIA", 4) # Usa 4 como padrão
        letra_categoria = "ABC"[indice_categoria]
        if letra_categoria not in familiares_por_categoria:
            familiares_por_categoria[letra_categoria] = []
        familiares_por_categoria[letra_categoria].append(f_nome)

    for cat, fams in sorted(familiares_por_categoria.items()):
        for familiar in sorted(fams):
            itens_deste_familiar = []
            for raridade, quantidade in simulador.inventario[familiar].items():
                if quantidade > 0:
                    itens_deste_familiar.append(f"{quantidade}x ({raridade}*)")
            
            if itens_deste_familiar:
                encontrou_algo = True
                # Mostra o nome do familiar e a categoria
                print(f"{familiar}: {', '.join(itens_deste_familiar)}")
    
    if not encontrou_algo:
        print("O inventário está vazio.")
    print("-" * 22)

def menu_principal():
    """Função que gerencia o menu interativo."""
    simulador = SimuladorGacha()
    combinador = SistemaCombine()
    print("Bem-vindo ao Simulador de Gacha e Combine!")

    while True:
        exibir_estado_completo(simulador)

        print("\nO que você deseja fazer?")
        print("  --- Gacha ---")
        print("  1. Puxar 1x")
        print("  2. Puxar 11x")
        print("  --- Combinação ---")
        print("  3. Combinar Automático (Raridades Baixas)")
        print("  4. Combinar em Cadeia (Estratégico)")
        print("  --- Outros ---")
        print("  5. Ver Inventário")
        print("  6. Sair")
        print("  --- Testes ---")
        print("  7. Puxar em Massa (Avançar Tempo)")
        
        escolha = input("Escolha uma opção: ")

        if escolha == '1':
            resultado = simulador.puxar_um()
            print(f"\nVocê obteve: {resultado[0]} ({resultado[1]}*)")
        
        elif escolha == '2':
            resultados = simulador.puxar_onze()
            print("\nVocê obteve os seguintes familiares:")
            for familiar, raridade in resultados:
                print(f"  - {familiar} ({raridade}*)")

        elif escolha == '3':
            print("\nExecutando combinações automáticas...")
            logs = combinador.combinar_automatico(simulador.inventario, simulador.familiares)
            if not logs:
                print("Nenhuma combinação automática foi possível.")
            else:
                for log in logs:
                    print(log)
        
        elif escolha == '4':
            try:
                print("\n--- Combinar em Cadeia ---")
                familiar_alvo = input(f"Qual o nome do familiar alvo (ex: {simulador.familiares[0]})? ")
                raridade_alvo = int(input("Qual a raridade alvo final (8, 9 ou 10)? "))

                # Valida o nome do familiar (ignorando maiúsculas/minúsculas)
                familiar_real = next((f for f in simulador.familiares if f.lower() == familiar_alvo.lower()), None)
                if not familiar_real:
                    print("Erro: Nome de familiar inválido.")
                    continue
                
                # Pede os métodos para cada etapa da cadeia
                metodos = {}
                for r in range(8, raridade_alvo + 1):
                    if r == 10 and 'probabilistico' not in REGRAS_COMBINE_ESTRATEGICO.get(10, {}):
                        print(" -> Para 10*, o único método é 100%.")
                        metodos[r] = 'garantido'
                        continue
                    while True:
                        m_input = input(f" -> Qual método usar para a etapa de {r}* (25 ou 100)? ")
                        if m_input == '25':
                            metodos[r] = 'probabilistico'
                            break
                        elif m_input == '100':
                            metodos[r] = 'garantido'
                            break
                        else:
                            print("Entrada inválida.")

                # Inicia o "bot" de crafting
                print(f"\nIniciando combine em cadeia para {familiar_real} -> {raridade_alvo}*...")
                tentativas_gerais = 0
                while tentativas_gerais < 100: # Um limite de segurança contra loops infinitos
                    houve_progresso = False
                    
                    # O bot trabalha de baixo para cima: tenta criar 8*, depois 9*, etc.
                    for r_alvo_etapa in range(8, raridade_alvo + 1):
                        metodo_etapa = metodos[r_alvo_etapa]
                        
                        sucesso, pontos, msg, creditos_att = combinador.combinar_estrategico(
                            simulador.inventario, simulador.creditos_combine, r_alvo_etapa, familiar_real, metodo_etapa
                        )
                        
                        # Se a tentativa foi possível (não deu erro de material insuficiente)
                        if "insuficiente" not in msg:
                            print(msg) # Mostra o resultado do passo
                            simulador.creditos_combine = creditos_att
                            simulador.pity_combine_contador += pontos
                            houve_progresso = True
                            
                            # Verifica pity de combine
                            if simulador.pity_combine_contador >= PITY_COMBINE_CONFIG["THRESHOLD"]:
                                num_pities = simulador.pity_combine_contador // PITY_COMBINE_CONFIG["THRESHOLD"]
                                simulador.pity_combine_contador %= PITY_COMBINE_CONFIG["THRESHOLD"]
                                for _ in range(num_pities):
                                    recompensa = random.choice(simulador.familiares)
                                    simulador.inventario[recompensa][PITY_COMBINE_CONFIG["REWARD_RARITY"]] += 1
                                    print(f"--- PITY DE COMBINE ATINGIDO! Recompensa: 1x {recompensa} 7*! ---")
                            
                            break # Se houve uma ação, para e reinicia a análise do zero
                    
                    if houve_progresso:
                        tentativas_gerais += 1
                        continue # Volta ao início do loop para tentar o próximo passo
                    else:
                        # Se o loop inteiro rodou e não houve progresso, não há mais materiais
                        print("\nProcesso finalizado: Não há mais materiais para continuar a combinação.")
                        break
                
            except ValueError:
                print("Entrada inválida. Por favor, insira um número para a raridade.")
            except Exception as e:
                print(f"Ocorreu um erro inesperado: {e}")

        elif escolha == '5':
            exibir_inventario(simulador)

        elif escolha == '6':
            print("Obrigado por usar o simulador!")
            break

        elif escolha == '7':
            print("\n--- Puxar em Massa ---")
            print("  1. Por número de pulls")
            print("  2. Por quantidade de diamantes")
            sub_escolha = input("Escolha o método: ")
            
            try:
                if sub_escolha == '1':
                    qtd = int(input("Quantos pulls você quer fazer? "))
                    pulls_feitos, custo = simulador.puxar_em_massa(num_pulls=qtd)
                    print(f"\n{pulls_feitos:,} pulls executados! Custo: {custo:,} diamantes.".replace(",", "."))

                elif sub_escolha == '2':
                    qtd = int(input("Quantos diamantes você quer gastar? "))
                    pulls_feitos, custo = simulador.puxar_em_massa(num_diamantes=qtd)
                    print(f"\n{pulls_feitos:,} pulls executados! Custo: {custo:,} diamantes.".replace(",", "."))
                else:
                    print("Opção inválida.")
            except ValueError:
                print("Entrada inválida. Por favor, insira um número.")
            except Exception as e:
                print(f"Ocorreu um erro: {e}")

        else:
            print("Opção inválida. Por favor, tente novamente.")


if __name__ == "__main__":
    menu_principal()