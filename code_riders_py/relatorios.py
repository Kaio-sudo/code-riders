"""
relatorios.py - As 5 consultas do script SQL original, em Python.

Unica adaptacao relevante: na consulta 2 a divisao usa 100.0 porque,
no SQLite, inteiro / inteiro da inteiro (o percentual sairia zero).
Inscricoes canceladas nao contam como vaga ocupada.
"""


def participantes_confirmados(con):
    """Consulta 1 - Participantes pagantes/isentos."""
    return con.execute("""
        SELECT u.nome AS ciclista, e.titulo AS nome_evento, c.nome_categoria AS categoria,
               r.nome_rota AS rota, r.distancia_km, e.data_hora, i.status_pagamento
          FROM inscricao i
         INNER JOIN usuario u          ON i.cpf_usuario = u.cpf
         INNER JOIN evento e           ON i.id_evento = e.id_evento
         INNER JOIN categoria_evento c ON e.id_categoria = c.id_categoria
         INNER JOIN rota r             ON e.id_rota = r.id_rota
         WHERE i.status_pagamento IN ('Pago', 'Isento')
         ORDER BY e.data_hora ASC
    """).fetchall()


def ocupacao_eventos(con):
    """Consulta 2 - Ocupacao dos eventos."""
    return con.execute("""
        SELECT e.id_evento, e.titulo, e.limite_vagas,
               COUNT(i.id_inscricao) AS total_inscritos,
               e.limite_vagas - COUNT(i.id_inscricao) AS vagas_restantes,
               ROUND(COUNT(i.id_inscricao) * 100.0 / e.limite_vagas, 2) AS percentual_ocupacao
          FROM evento e
          LEFT JOIN inscricao i
                 ON e.id_evento = i.id_evento AND i.status_pagamento <> 'Cancelado'
         GROUP BY e.id_evento, e.titulo, e.limite_vagas
         ORDER BY percentual_ocupacao DESC
    """).fetchall()


def receita_por_evento(con):
    """Consulta 3 - Receita por evento."""
    return con.execute("""
        SELECT e.titulo AS evento, u.nome AS organizador, e.valor_inscricao,
               COUNT(i.id_inscricao) AS total_pagantes,
               SUM(e.valor_inscricao) AS receita_total
          FROM evento e
         INNER JOIN usuario u   ON e.cpf_organizador = u.cpf
         INNER JOIN inscricao i ON e.id_evento = i.id_evento
         WHERE i.status_pagamento = 'Pago'
         GROUP BY e.id_evento, e.titulo, u.nome, e.valor_inscricao
        HAVING receita_total > 0
         ORDER BY receita_total DESC
    """).fetchall()


def satisfacao_eventos(con):
    """Consulta 4 - Satisfacao dos eventos."""
    return con.execute("""
        SELECT e.id_evento, e.titulo AS evento, r.tipo_terreno,
               COUNT(a.id_avaliacao) AS total_avaliacoes,
               ROUND(AVG(a.nota), 2) AS media_satisfacao
          FROM evento e
         INNER JOIN inscricao i ON e.id_evento = i.id_evento
         INNER JOIN avaliacao a ON i.id_inscricao = a.id_inscricao
         INNER JOIN rota r      ON e.id_rota = r.id_rota
         GROUP BY e.id_evento, e.titulo, r.tipo_terreno
        HAVING COUNT(a.id_avaliacao) >= 1
         ORDER BY media_satisfacao DESC, total_avaliacoes DESC
    """).fetchall()


def ranking_ciclistas(con):
    """Consulta 5 - Ranking de ciclistas por km pedalado."""
    return con.execute("""
        SELECT u.cpf, u.nome AS ciclista, u.nivel_experiencia,
               COUNT(i.id_inscricao) AS eventos_concluidos,
               COALESCE(SUM(r.distancia_km), 0) AS km_total_pedalado
          FROM usuario u
         INNER JOIN inscricao i ON u.cpf = i.cpf_usuario
         INNER JOIN evento e    ON i.id_evento = e.id_evento
         INNER JOIN rota r      ON e.id_rota = r.id_rota
         WHERE i.presenca_confirmada = 1
         GROUP BY u.cpf, u.nome, u.nivel_experiencia
         ORDER BY km_total_pedalado DESC
    """).fetchall()


# (titulo exibido no menu, funcao)
RELATORIOS = [
    ("Participantes pagantes/isentos", participantes_confirmados),
    ("Ocupacao dos eventos", ocupacao_eventos),
    ("Receita por evento", receita_por_evento),
    ("Satisfacao dos eventos", satisfacao_eventos),
    ("Ranking de ciclistas (km pedalados)", ranking_ciclistas),
]
