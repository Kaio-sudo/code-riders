"""
servicos.py - Regras de negocio do PedalHub.

Cada funcao recebe a conexao com o banco, valida as regras e grava.
Quando alguma regra e violada, lanca RegraNegocioErro com uma mensagem
amigavel, que o menu (main.py) mostra para o usuario.
"""

import re
import sqlite3

NIVEIS = ("Iniciante", "Intermediario", "Avancado")
STATUS_EVENTO = ("Agendado", "Em Andamento", "Concluido", "Cancelado")


class RegraNegocioErro(Exception):
    """Erro de regra de negocio (ex.: evento lotado, CPF invalido)."""


# ---------------------------------------------------------------
# Validacoes
# ---------------------------------------------------------------

def limpar_cpf(cpf):
    """Remove pontos, traco e espacos: '123.456.789-09' -> '12345678909'."""
    return re.sub(r"\D", "", cpf or "")


def cpf_valido(cpf):
    """Confere o formato e os dois digitos verificadores do CPF."""
    cpf = limpar_cpf(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(cpf[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(cpf[tamanho]):
            return False
    return True


def email_valido(email):
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or "") is not None


# ---------------------------------------------------------------
# Consultas de apoio
# ---------------------------------------------------------------

def buscar_usuario(con, cpf):
    return con.execute("SELECT * FROM usuario WHERE cpf = ?", (limpar_cpf(cpf),)).fetchone()


def buscar_evento(con, id_evento):
    return con.execute("SELECT * FROM evento WHERE id_evento = ?", (id_evento,)).fetchone()


def buscar_inscricao(con, id_inscricao):
    return con.execute(
        """SELECT i.*, e.titulo, e.status_evento, e.valor_inscricao
             FROM inscricao i JOIN evento e ON e.id_evento = i.id_evento
            WHERE i.id_inscricao = ?""",
        (id_inscricao,),
    ).fetchone()


def inscritos_ativos(con, id_evento):
    """Quantidade de inscricoes que ocupam vaga (todas, menos as canceladas)."""
    return con.execute(
        """SELECT COUNT(*) FROM inscricao
            WHERE id_evento = ? AND status_pagamento <> 'Cancelado'""",
        (id_evento,),
    ).fetchone()[0]


def listar_usuarios(con):
    return con.execute(
        "SELECT cpf, nome, email, telefone, nivel_experiencia FROM usuario ORDER BY nome"
    ).fetchall()


def listar_categorias(con):
    return con.execute("SELECT * FROM categoria_evento ORDER BY id_categoria").fetchall()


def listar_rotas(con):
    return con.execute("SELECT * FROM rota ORDER BY id_rota").fetchall()


def listar_eventos(con, apenas_abertos=False):
    """Eventos com categoria, rota, organizador e vagas restantes."""
    filtro = "WHERE e.status_evento = 'Agendado'" if apenas_abertos else ""
    return con.execute(
        f"""
        SELECT e.id_evento, e.titulo, e.data_hora, c.nome_categoria AS categoria,
               r.nome_rota AS rota, r.distancia_km, r.tipo_terreno,
               e.valor_inscricao, e.status_evento, u.nome AS organizador,
               e.limite_vagas,
               e.limite_vagas - COUNT(CASE WHEN i.status_pagamento <> 'Cancelado'
                                           THEN i.id_inscricao END) AS vagas_restantes
          FROM evento e
          JOIN categoria_evento c ON c.id_categoria = e.id_categoria
          JOIN rota r             ON r.id_rota = e.id_rota
          JOIN usuario u          ON u.cpf = e.cpf_organizador
          LEFT JOIN inscricao i   ON i.id_evento = e.id_evento
          {filtro}
         GROUP BY e.id_evento
         ORDER BY e.data_hora
        """
    ).fetchall()


def inscricoes_do_usuario(con, cpf):
    return con.execute(
        """
        SELECT i.id_inscricao, e.titulo, e.data_hora, e.status_evento,
               i.status_pagamento,
               CASE i.presenca_confirmada WHEN 1 THEN 'Sim' ELSE 'Nao' END AS presenca,
               COALESCE(a.nota, '-') AS nota
          FROM inscricao i
          JOIN evento e ON e.id_evento = i.id_evento
          LEFT JOIN avaliacao a ON a.id_inscricao = i.id_inscricao
         WHERE i.cpf_usuario = ?
         ORDER BY e.data_hora
        """,
        (limpar_cpf(cpf),),
    ).fetchall()


def avaliacoes_do_evento(con, id_evento):
    return con.execute(
        """
        SELECT u.nome AS ciclista, a.nota, a.comentario, a.data_avaliacao
          FROM avaliacao a
          JOIN inscricao i ON i.id_inscricao = a.id_inscricao
          JOIN usuario u   ON u.cpf = i.cpf_usuario
         WHERE i.id_evento = ?
         ORDER BY a.data_avaliacao
        """,
        (id_evento,),
    ).fetchall()


# ---------------------------------------------------------------
# Operacoes (gravam no banco)
# ---------------------------------------------------------------

def cadastrar_usuario(con, cpf, nome, email, telefone="", nivel="Iniciante"):
    cpf = limpar_cpf(cpf)
    if not cpf_valido(cpf):
        raise RegraNegocioErro("CPF invalido (confira os digitos verificadores).")
    if not nome.strip():
        raise RegraNegocioErro("O nome e obrigatorio.")
    if not email_valido(email):
        raise RegraNegocioErro("E-mail invalido.")
    if nivel not in NIVEIS:
        raise RegraNegocioErro(f"Nivel deve ser um destes: {', '.join(NIVEIS)}.")
    if buscar_usuario(con, cpf):
        raise RegraNegocioErro("Ja existe um usuario com esse CPF.")
    try:
        con.execute(
            """INSERT INTO usuario (cpf, nome, email, telefone, nivel_experiencia)
               VALUES (?, ?, ?, ?, ?)""",
            (cpf, nome.strip(), email.strip().lower(), telefone.strip(), nivel),
        )
        con.commit()
    except sqlite3.IntegrityError:
        raise RegraNegocioErro("Ja existe um usuario com esse e-mail.")


def atualizar_nivel(con, cpf, nivel):
    if nivel not in NIVEIS:
        raise RegraNegocioErro(f"Nivel deve ser um destes: {', '.join(NIVEIS)}.")
    if not buscar_usuario(con, cpf):
        raise RegraNegocioErro("Usuario nao encontrado.")
    con.execute("UPDATE usuario SET nivel_experiencia = ? WHERE cpf = ?",
                (nivel, limpar_cpf(cpf)))
    con.commit()


def criar_evento(con, titulo, data_hora, limite_vagas, valor, cpf_organizador,
                 id_categoria, id_rota):
    if not titulo.strip():
        raise RegraNegocioErro("O titulo e obrigatorio.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", data_hora.strip()):
        raise RegraNegocioErro("Data/hora deve estar no formato AAAA-MM-DD HH:MM.")
    if limite_vagas <= 0:
        raise RegraNegocioErro("O limite de vagas deve ser maior que zero.")
    if valor < 0:
        raise RegraNegocioErro("O valor da inscricao nao pode ser negativo.")
    if not buscar_usuario(con, cpf_organizador):
        raise RegraNegocioErro("Organizador nao encontrado (cadastre o usuario antes).")
    try:
        cur = con.execute(
            """INSERT INTO evento (titulo, data_hora, limite_vagas, valor_inscricao,
                                   cpf_organizador, id_categoria, id_rota)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (titulo.strip(), data_hora.strip() + ":00", limite_vagas, valor,
             limpar_cpf(cpf_organizador), id_categoria, id_rota),
        )
        con.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise RegraNegocioErro("Categoria ou rota inexistente.")


def alterar_status_evento(con, id_evento, novo_status):
    if novo_status not in STATUS_EVENTO:
        raise RegraNegocioErro(f"Status deve ser um destes: {', '.join(STATUS_EVENTO)}.")
    if not buscar_evento(con, id_evento):
        raise RegraNegocioErro("Evento nao encontrado.")
    con.execute("UPDATE evento SET status_evento = ? WHERE id_evento = ?",
                (novo_status, id_evento))
    con.commit()


def inscrever(con, cpf, id_evento):
    """Inscreve o ciclista no evento. Retorna o id da inscricao."""
    cpf = limpar_cpf(cpf)
    if not buscar_usuario(con, cpf):
        raise RegraNegocioErro("Usuario nao encontrado.")
    evento = buscar_evento(con, id_evento)
    if not evento:
        raise RegraNegocioErro("Evento nao encontrado.")
    if evento["status_evento"] != "Agendado":
        raise RegraNegocioErro(
            f"Inscricoes fechadas: o evento esta '{evento['status_evento']}'.")
    if inscritos_ativos(con, id_evento) >= evento["limite_vagas"]:
        raise RegraNegocioErro("Evento lotado, nao ha vagas disponiveis.")

    # Evento gratuito ja nasce como 'Isento'; pago comeca 'Pendente'
    status = "Isento" if evento["valor_inscricao"] == 0 else "Pendente"

    existente = con.execute(
        "SELECT * FROM inscricao WHERE cpf_usuario = ? AND id_evento = ?",
        (cpf, id_evento),
    ).fetchone()
    if existente:
        if existente["status_pagamento"] != "Cancelado":
            raise RegraNegocioErro("Esse ciclista ja esta inscrito nesse evento.")
        # Reativa uma inscricao que havia sido cancelada
        con.execute(
            """UPDATE inscricao SET status_pagamento = ?, presenca_confirmada = 0,
                      data_inscricao = datetime('now','localtime')
                WHERE id_inscricao = ?""",
            (status, existente["id_inscricao"]),
        )
        con.commit()
        return existente["id_inscricao"]

    cur = con.execute(
        "INSERT INTO inscricao (cpf_usuario, id_evento, status_pagamento) VALUES (?, ?, ?)",
        (cpf, id_evento, status),
    )
    con.commit()
    return cur.lastrowid


def registrar_pagamento(con, id_inscricao):
    insc = buscar_inscricao(con, id_inscricao)
    if not insc:
        raise RegraNegocioErro("Inscricao nao encontrada.")
    if insc["status_pagamento"] != "Pendente":
        raise RegraNegocioErro(
            f"So e possivel pagar inscricoes pendentes (atual: {insc['status_pagamento']}).")
    con.execute("UPDATE inscricao SET status_pagamento = 'Pago' WHERE id_inscricao = ?",
                (id_inscricao,))
    con.commit()


def cancelar_inscricao(con, id_inscricao):
    insc = buscar_inscricao(con, id_inscricao)
    if not insc:
        raise RegraNegocioErro("Inscricao nao encontrada.")
    if insc["status_evento"] in ("Concluido", "Em Andamento"):
        raise RegraNegocioErro("Nao e possivel cancelar: o evento ja comecou ou terminou.")
    if insc["status_pagamento"] == "Cancelado":
        raise RegraNegocioErro("Essa inscricao ja esta cancelada.")
    con.execute("UPDATE inscricao SET status_pagamento = 'Cancelado' WHERE id_inscricao = ?",
                (id_inscricao,))
    con.commit()


def confirmar_presenca(con, id_inscricao):
    insc = buscar_inscricao(con, id_inscricao)
    if not insc:
        raise RegraNegocioErro("Inscricao nao encontrada.")
    if insc["status_pagamento"] not in ("Pago", "Isento"):
        raise RegraNegocioErro("A presenca so pode ser confirmada com pagamento em dia.")
    if insc["status_evento"] not in ("Em Andamento", "Concluido"):
        raise RegraNegocioErro("O evento ainda nao aconteceu.")
    con.execute("UPDATE inscricao SET presenca_confirmada = 1 WHERE id_inscricao = ?",
                (id_inscricao,))
    con.commit()


def avaliar(con, id_inscricao, nota, comentario=""):
    insc = buscar_inscricao(con, id_inscricao)
    if not insc:
        raise RegraNegocioErro("Inscricao nao encontrada.")
    if insc["status_evento"] != "Concluido":
        raise RegraNegocioErro("So e possivel avaliar eventos concluidos.")
    if not insc["presenca_confirmada"]:
        raise RegraNegocioErro("So quem participou (presenca confirmada) pode avaliar.")
    if not 1 <= nota <= 5:
        raise RegraNegocioErro("A nota deve ser de 1 a 5.")
    try:
        con.execute(
            "INSERT INTO avaliacao (id_inscricao, nota, comentario) VALUES (?, ?, ?)",
            (id_inscricao, nota, comentario.strip()),
        )
        con.commit()
    except sqlite3.IntegrityError:
        raise RegraNegocioErro("Essa inscricao ja foi avaliada.")
