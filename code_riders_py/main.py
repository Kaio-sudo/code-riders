"""
main.py - PedalHub / Code Riders
Sistema de eventos de ciclismo em linha de comando.

Como rodar:   python main.py
(nao precisa instalar nada: usa apenas a biblioteca padrao do Python)
"""

import banco
import recomendacao as rec
import servicos as srv
from relatorios import RELATORIOS
from servicos import RegraNegocioErro

con = banco.conectar()


# ---------------------------------------------------------------
# Utilitarios de tela
# ---------------------------------------------------------------

def titulo(texto):
    print("\n" + "=" * 70)
    print(f" {texto}")
    print("=" * 70)


def formatar(valor):
    if valor is None:
        return "-"
    if isinstance(valor, float):
        return f"{valor:.2f}"
    return str(valor)


def mostrar_tabela(linhas, colunas=None):
    """Imprime uma lista de linhas (sqlite3.Row ou dict) como tabela."""
    if not linhas:
        print("  (nenhum registro encontrado)")
        return
    colunas = colunas or list(linhas[0].keys())
    dados = [[formatar(l[c]) for c in colunas] for l in linhas]
    larguras = [max(len(c), *(len(d[i]) for d in dados)) for i, c in enumerate(colunas)]
    larguras = [min(w, 40) for w in larguras]

    def linha(valores):
        return " | ".join(v[:w].ljust(w) for v, w in zip(valores, larguras))

    print(linha(colunas))
    print("-+-".join("-" * w for w in larguras))
    for d in dados:
        print(linha(d))
    print(f"\n  {len(linhas)} registro(s)")


def perguntar(texto, obrigatorio=True, padrao=None):
    while True:
        sufixo = f" [{padrao}]" if padrao is not None else ""
        resp = input(f"{texto}{sufixo}: ").strip()
        if not resp and padrao is not None:
            return padrao
        if resp or not obrigatorio:
            return resp
        print("  Campo obrigatorio.")


def perguntar_numero(texto, tipo=int, padrao=None):
    while True:
        resp = perguntar(texto, padrao=None if padrao is None else str(padrao))
        try:
            return tipo(str(resp).replace(",", "."))
        except ValueError:
            print("  Digite um numero valido.")


def escolher_opcao(texto, opcoes):
    for i, op in enumerate(opcoes, 1):
        print(f"  {i}. {op}")
    while True:
        n = perguntar_numero(texto)
        if 1 <= n <= len(opcoes):
            return opcoes[n - 1]
        print("  Opcao invalida.")


def pausar():
    input("\nPressione ENTER para continuar...")


def submenu(nome, opcoes):
    """opcoes = lista de (descricao, funcao)."""
    while True:
        titulo(nome)
        for i, (desc, _) in enumerate(opcoes, 1):
            print(f"  {i}. {desc}")
        print("  0. Voltar")
        escolha = input("\nOpcao: ").strip()
        if escolha == "0":
            return
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            desc, funcao = opcoes[int(escolha) - 1]
            titulo(desc)
            try:
                funcao()
            except RegraNegocioErro as erro:
                print(f"\n  [!] {erro}")
            pausar()
        else:
            print("  Opcao invalida.")


# ---------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------

COLS_EVENTO = ["id_evento", "titulo", "data_hora", "categoria", "rota",
               "distancia_km", "valor_inscricao", "status_evento", "vagas_restantes"]


def listar_todos_eventos():
    mostrar_tabela(srv.listar_eventos(con), COLS_EVENTO)


def listar_eventos_abertos():
    mostrar_tabela(srv.listar_eventos(con, apenas_abertos=True), COLS_EVENTO)


def detalhes_evento():
    id_evento = perguntar_numero("ID do evento")
    ev = next((e for e in srv.listar_eventos(con) if e["id_evento"] == id_evento), None)
    if not ev:
        raise RegraNegocioErro("Evento nao encontrado.")
    r = con.execute("SELECT * FROM rota WHERE nome_rota = ?", (ev["rota"],)).fetchone()
    idx = rec.indice_dificuldade(r["distancia_km"], r["altimetria_ganho_m"], r["tipo_terreno"])
    print(f"\n  {ev['titulo']}  ({ev['status_evento']})")
    print(f"  Data:        {ev['data_hora']}")
    print(f"  Categoria:   {ev['categoria']}")
    print(f"  Organizador: {ev['organizador']}")
    print(f"  Rota:        {ev['rota']} - {r['distancia_km']} km, "
          f"{r['altimetria_ganho_m']} m de subida, {r['tipo_terreno']}")
    print(f"  Partida:     {r['ponto_partida']}")
    print(f"  Dificuldade: {rec.classificar(idx)} (indice {idx})")
    print(f"  Inscricao:   R$ {ev['valor_inscricao']:.2f}")
    print(f"  Vagas:       {ev['vagas_restantes']} de {ev['limite_vagas']}")
    avaliacoes = srv.avaliacoes_do_evento(con, id_evento)
    if avaliacoes:
        media = sum(a["nota"] for a in avaliacoes) / len(avaliacoes)
        print(f"\n  Avaliacoes (media {media:.1f}):")
        for a in avaliacoes:
            print(f"   {'*' * a['nota']:<5} {a['ciclista']}: {a['comentario']}")


def criar_evento():
    mostrar_tabela(srv.listar_categorias(con), ["id_categoria", "nome_categoria"])
    id_cat = perguntar_numero("\nID da categoria")
    rotas = rec.rotas_com_dificuldade(con)
    mostrar_tabela(rotas, ["id", "rota", "km", "terreno", "dificuldade"])
    id_rota = perguntar_numero("\nID da rota")
    novo = srv.criar_evento(
        con,
        titulo=perguntar("Titulo"),
        data_hora=perguntar("Data e hora (AAAA-MM-DD HH:MM)"),
        limite_vagas=perguntar_numero("Limite de vagas"),
        valor=perguntar_numero("Valor da inscricao (0 = gratuito)", float, 0),
        cpf_organizador=perguntar("CPF do organizador"),
        id_categoria=id_cat,
        id_rota=id_rota,
    )
    print(f"\n  Evento criado com ID {novo}.")


def alterar_status():
    id_evento = perguntar_numero("ID do evento")
    status = escolher_opcao("Novo status", list(srv.STATUS_EVENTO))
    srv.alterar_status_evento(con, id_evento, status)
    print("\n  Status atualizado.")


# ---------------------------------------------------------------
# Ciclistas
# ---------------------------------------------------------------

def listar_ciclistas():
    mostrar_tabela(srv.listar_usuarios(con))


def cadastrar_ciclista():
    cpf = perguntar("CPF (somente numeros ou com pontuacao)")
    if not srv.cpf_valido(cpf):
        raise RegraNegocioErro("CPF invalido (confira os digitos verificadores).")
    nome = perguntar("Nome")
    email = perguntar("E-mail")
    telefone = perguntar("Telefone", obrigatorio=False)
    print("Nivel de experiencia:")
    nivel = escolher_opcao("Escolha", list(srv.NIVEIS))
    srv.cadastrar_usuario(con, cpf, nome, email, telefone, nivel)
    print(f"\n  Bem-vindo(a) ao PedalHub, {nome}!")


def minhas_inscricoes():
    cpf = perguntar("CPF do ciclista")
    usuario = srv.buscar_usuario(con, cpf)
    if not usuario:
        raise RegraNegocioErro("Usuario nao encontrado.")
    print(f"\n  Inscricoes de {usuario['nome']}:\n")
    mostrar_tabela(srv.inscricoes_do_usuario(con, cpf))


def alterar_nivel():
    cpf = perguntar("CPF do ciclista")
    nivel = escolher_opcao("Novo nivel", list(srv.NIVEIS))
    srv.atualizar_nivel(con, cpf, nivel)
    print("\n  Nivel atualizado.")


# ---------------------------------------------------------------
# Inscricoes
# ---------------------------------------------------------------

def fazer_inscricao():
    listar_eventos_abertos()
    cpf = perguntar("\nCPF do ciclista")
    id_evento = perguntar_numero("ID do evento")
    id_insc = srv.inscrever(con, cpf, id_evento)
    insc = srv.buscar_inscricao(con, id_insc)
    print(f"\n  Inscricao #{id_insc} realizada! Situacao: {insc['status_pagamento']}")
    if insc["status_pagamento"] == "Pendente":
        print(f"  Valor a pagar: R$ {insc['valor_inscricao']:.2f}")


def pagar_inscricao():
    srv.registrar_pagamento(con, perguntar_numero("ID da inscricao"))
    print("\n  Pagamento registrado.")


def cancelar_inscricao():
    srv.cancelar_inscricao(con, perguntar_numero("ID da inscricao"))
    print("\n  Inscricao cancelada. A vaga foi liberada.")


def confirmar_presenca():
    srv.confirmar_presenca(con, perguntar_numero("ID da inscricao"))
    print("\n  Presenca confirmada.")


def avaliar_evento():
    id_insc = perguntar_numero("ID da inscricao")
    nota = perguntar_numero("Nota (1 a 5)")
    comentario = perguntar("Comentario", obrigatorio=False)
    srv.avaliar(con, id_insc, nota, comentario)
    print("\n  Obrigado pela avaliacao!")


# ---------------------------------------------------------------
# Relatorios
# ---------------------------------------------------------------

def menu_relatorios():
    opcoes = [(nome, (lambda f=f: mostrar_tabela(f(con)))) for nome, f in RELATORIOS]
    submenu("RELATORIOS", opcoes)


# ---------------------------------------------------------------
# Inovacao
# ---------------------------------------------------------------

def recomendar():
    cpf = srv.limpar_cpf(perguntar("CPF do ciclista"))
    usuario, lista = rec.recomendar_eventos(con, cpf)
    if not usuario:
        raise RegraNegocioErro("Usuario nao encontrado.")
    print(f"\n  Recomendacoes para {usuario['nome']} (nivel {usuario['nivel_experiencia']}):\n")
    if not lista:
        print("  Nenhum evento aberto disponivel para voce no momento.")
        return
    for pos, r in enumerate(lista, 1):
        barra = "#" * (r["pontuacao"] // 10) + "." * (10 - r["pontuacao"] // 10)
        print(f"  {pos}. [{barra}] {r['pontuacao']:>3}/100  {r['titulo']}  (ID {r['id_evento']})")
        print(f"     {r['data_hora']} | {r['rota']} | {r['dificuldade']} | "
              f"R$ {r['valor']:.2f} | {r['vagas']} vagas")
        if r["motivos"]:
            print(f"     Por que: {'; '.join(r['motivos'])}")
        if r["alerta"]:
            print(f"     ATENCAO: {r['alerta']}")
        print()


def evolucao():
    cpf = srv.limpar_cpf(perguntar("CPF do ciclista"))
    ev = rec.evolucao_ciclista(con, cpf)
    if not ev:
        raise RegraNegocioErro("Usuario nao encontrado.")
    print(f"\n  {ev['nome']} - nivel atual: {ev['nivel']}")
    print(f"  Eventos concluidos: {ev['eventos']}")
    print(f"  Km pedalados:       {ev['km_total']}")
    print(f"  Subida acumulada:   {ev['subida_total']} m")
    if ev["mais_dificil"]:
        nome, idx, classe = ev["mais_dificil"]
        print(f"  Rota mais dificil:  {nome} ({classe}, indice {idx})")
    if ev["progresso"] is not None:
        cheio = ev["progresso"] // 5
        print(f"\n  Progresso ate {ev['proximo_nivel']}: "
              f"[{'#' * cheio}{'.' * (20 - cheio)}] {ev['progresso']}%")
    print(f"  >> {ev['sugestao']}")


def dificuldade_rotas():
    print("  indice = (km + subida_m / 10) x fator do terreno")
    print("  fator: Asfalto 1.0 | Misto 1.2 | Terra/Trilha 1.4")
    print("  Leve < 35 | Moderada < 100 | Dificil >= 100\n")
    mostrar_tabela(rec.rotas_com_dificuldade(con))


# ---------------------------------------------------------------
# Menu principal
# ---------------------------------------------------------------

def resetar_banco():
    global con
    if perguntar("Isso apaga tudo e recarrega os dados originais. Confirma? (s/n)").lower() == "s":
        con.close()
        con = banco.resetar()
        print("\n  Banco recriado com os dados originais.")


MENU = [
    ("Eventos", lambda: submenu("EVENTOS", [
        ("Listar todos os eventos", listar_todos_eventos),
        ("Listar eventos com inscricoes abertas", listar_eventos_abertos),
        ("Detalhes e avaliacoes de um evento", detalhes_evento),
        ("Criar evento (organizador)", criar_evento),
        ("Alterar status de um evento", alterar_status),
    ])),
    ("Ciclistas", lambda: submenu("CICLISTAS", [
        ("Listar ciclistas", listar_ciclistas),
        ("Cadastrar ciclista", cadastrar_ciclista),
        ("Ver inscricoes de um ciclista", minhas_inscricoes),
        ("Alterar nivel de experiencia", alterar_nivel),
    ])),
    ("Inscricoes", lambda: submenu("INSCRICOES", [
        ("Inscrever ciclista em evento", fazer_inscricao),
        ("Registrar pagamento", pagar_inscricao),
        ("Cancelar inscricao", cancelar_inscricao),
        ("Confirmar presenca", confirmar_presenca),
        ("Avaliar evento", avaliar_evento),
    ])),
    ("Relatorios", menu_relatorios),
    ("PedalHub Inteligente (recomendacoes)", lambda: submenu("PEDALHUB INTELIGENTE", [
        ("Eventos recomendados para mim", recomendar),
        ("Minha evolucao como ciclista", evolucao),
        ("Indice de dificuldade das rotas", dificuldade_rotas),
    ])),
    ("Restaurar dados originais", resetar_banco),
]


def main():
    while True:
        titulo("PEDALHUB - Code Riders  |  Eventos de ciclismo no DF")
        for i, (desc, _) in enumerate(MENU, 1):
            print(f"  {i}. {desc}")
        print("  0. Sair")
        escolha = input("\nOpcao: ").strip()
        if escolha == "0":
            print("\nAte o proximo pedal!\n")
            break
        if escolha.isdigit() and 1 <= int(escolha) <= len(MENU):
            MENU[int(escolha) - 1][1]()
        else:
            print("  Opcao invalida.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nAte o proximo pedal!\n")
    finally:
        con.close()
