"""
recomendacao.py - O diferencial inovador do PedalHub.

1) Indice de Dificuldade da Rota
   Combina distancia, subida acumulada e tipo de terreno num numero so:
       indice = (distancia_km + altimetria_m / 10) x fator_terreno
   Fator do terreno: Asfalto 1.0 | Misto 1.2 | Terra/Trilha 1.4
   Classificacao:    Leve < 35 | Moderada < 100 | Dificil >= 100

2) Recomendacao personalizada de eventos (pontuacao de 0 a 100)
   Para cada evento aberto em que o ciclista ainda nao esta inscrito:
     - ate 50 pts: dificuldade compativel com o nivel do ciclista
     - ate 20 pts: afinidade (categoria/terreno que ele ja pedalou)
     - ate 20 pts: reputacao (media das avaliacoes da categoria/organizador)
     - ate 10 pts: custo (evento gratuito ou barato pontua mais)
   O sistema explica o motivo de cada recomendacao e alerta quando a
   rota esta acima do nivel do ciclista (seguranca).

3) Evolucao do ciclista
   Analisa o historico (km pedalados, eventos concluidos, rota mais dificil)
   e sugere quando o ciclista esta pronto para subir de nivel.
"""

FATOR_TERRENO = {"Asfalto": 1.0, "Misto": 1.2, "Terra/Trilha": 1.4}
ORDEM_DIFICULDADE = ["Leve", "Moderada", "Dificil"]

# Dificuldade ideal e aceitavel para cada nivel de experiencia
PERFIL_NIVEL = {
    "Iniciante":     {"ideal": "Leve",     "aceitavel": []},
    "Intermediario": {"ideal": "Moderada", "aceitavel": ["Leve"]},
    "Avancado":      {"ideal": "Dificil",  "aceitavel": ["Moderada"]},
}

# Metas para sugerir a subida de nivel
METAS_EVOLUCAO = {
    "Iniciante":     {"proximo": "Intermediario", "eventos": 2, "km": 25},
    "Intermediario": {"proximo": "Avancado",      "eventos": 3, "km": 80},
}


def indice_dificuldade(distancia_km, altimetria_m, tipo_terreno):
    base = float(distancia_km) + (altimetria_m or 0) / 10
    return round(base * FATOR_TERRENO.get(tipo_terreno, 1.0), 1)


def classificar(indice):
    if indice < 35:
        return "Leve"
    if indice < 100:
        return "Moderada"
    return "Dificil"


def rotas_com_dificuldade(con):
    """Lista todas as rotas com o indice e a classificacao calculados."""
    resultado = []
    for r in con.execute("SELECT * FROM rota ORDER BY id_rota"):
        idx = indice_dificuldade(r["distancia_km"], r["altimetria_ganho_m"], r["tipo_terreno"])
        resultado.append({
            "id": r["id_rota"],
            "rota": r["nome_rota"],
            "km": r["distancia_km"],
            "subida_m": r["altimetria_ganho_m"],
            "terreno": r["tipo_terreno"],
            "indice": idx,
            "dificuldade": classificar(idx),
        })
    return sorted(resultado, key=lambda x: x["indice"])


def _historico(con, cpf):
    """Eventos em que o ciclista teve presenca confirmada."""
    return con.execute("""
        SELECT e.id_categoria, c.nome_categoria, r.tipo_terreno, r.distancia_km,
               r.altimetria_ganho_m, r.nome_rota
          FROM inscricao i
          JOIN evento e           ON e.id_evento = i.id_evento
          JOIN rota r             ON r.id_rota = e.id_rota
          JOIN categoria_evento c ON c.id_categoria = e.id_categoria
         WHERE i.cpf_usuario = ? AND i.presenca_confirmada = 1
    """, (cpf,)).fetchall()


def _media(con, coluna, valor):
    """Media das notas de eventos de uma categoria ou de um organizador."""
    linha = con.execute(f"""
        SELECT AVG(a.nota) AS media, COUNT(*) AS qtd
          FROM avaliacao a
          JOIN inscricao i ON i.id_inscricao = a.id_inscricao
          JOIN evento e    ON e.id_evento = i.id_evento
         WHERE e.{coluna} = ?
    """, (valor,)).fetchone()
    return linha["media"], linha["qtd"]


def recomendar_eventos(con, cpf, limite=5):
    usuario = con.execute("SELECT * FROM usuario WHERE cpf = ?", (cpf,)).fetchone()
    if not usuario:
        return None, []

    nivel = usuario["nivel_experiencia"]
    perfil = PERFIL_NIVEL[nivel]
    historico = _historico(con, cpf)
    categorias_feitas = {h["id_categoria"] for h in historico}
    terrenos_feitos = {h["tipo_terreno"] for h in historico}

    candidatos = con.execute("""
        SELECT e.*, c.nome_categoria, r.nome_rota, r.distancia_km,
               r.altimetria_ganho_m, r.tipo_terreno, u.nome AS organizador,
               e.limite_vagas - (SELECT COUNT(*) FROM inscricao x
                                  WHERE x.id_evento = e.id_evento
                                    AND x.status_pagamento <> 'Cancelado') AS vagas
          FROM evento e
          JOIN categoria_evento c ON c.id_categoria = e.id_categoria
          JOIN rota r             ON r.id_rota = e.id_rota
          JOIN usuario u          ON u.cpf = e.cpf_organizador
         WHERE e.status_evento = 'Agendado'
           AND e.cpf_organizador <> :cpf
           AND NOT EXISTS (SELECT 1 FROM inscricao y
                            WHERE y.id_evento = e.id_evento
                              AND y.cpf_usuario = :cpf
                              AND y.status_pagamento <> 'Cancelado')
    """, {"cpf": cpf}).fetchall()

    recomendacoes = []
    for ev in candidatos:
        if ev["vagas"] <= 0:
            continue
        motivos, alerta, pontos = [], None, 0
        idx = indice_dificuldade(ev["distancia_km"], ev["altimetria_ganho_m"], ev["tipo_terreno"])
        dific = classificar(idx)

        # 1) Compatibilidade com o nivel (ate 50)
        if dific == perfil["ideal"]:
            pontos += 50
            motivos.append(f"rota {dific.lower()}, ideal para nivel {nivel}")
        elif dific in perfil["aceitavel"]:
            pontos += 30
            motivos.append(f"rota {dific.lower()}, tranquila para o seu nivel")
        elif ORDEM_DIFICULDADE.index(dific) > ORDEM_DIFICULDADE.index(perfil["ideal"]):
            alerta = f"Rota {dific.lower()} - acima do nivel {nivel}. Va acompanhado!"
        else:
            pontos += 10
            motivos.append("rota abaixo do seu nivel (bom para recuperacao)")

        # 2) Afinidade com o historico (ate 20)
        if ev["id_categoria"] in categorias_feitas:
            pontos += 12
            motivos.append(f"voce ja curtiu '{ev['nome_categoria']}'")
        if ev["tipo_terreno"] in terrenos_feitos:
            pontos += 8
            motivos.append(f"voce ja pedalou em {ev['tipo_terreno'].lower()}")
        if not historico:
            pontos += 10  # sem historico: nao penaliza quem esta comecando

        # 3) Reputacao (ate 20): usa categoria e organizador
        media_cat, qtd_cat = _media(con, "id_categoria", ev["id_categoria"])
        media_org, qtd_org = _media(con, "cpf_organizador", ev["cpf_organizador"])
        notas = [m for m in (media_cat, media_org) if m]
        if notas:
            media = sum(notas) / len(notas)
            pontos += round(media / 5 * 20)
            if media >= 4.5:
                motivos.append(f"muito bem avaliado (media {media:.1f})")
        else:
            pontos += 10  # sem avaliacoes ainda: pontuacao neutra

        # 4) Custo (ate 10)
        valor = ev["valor_inscricao"] or 0
        if valor == 0:
            pontos += 10
            motivos.append("gratuito")
        elif valor <= 20:
            pontos += 6
        elif valor <= 40:
            pontos += 3

        if alerta:
            pontos = min(pontos, 40)  # nunca fica no topo se for arriscado

        recomendacoes.append({
            "id_evento": ev["id_evento"],
            "titulo": ev["titulo"],
            "data_hora": ev["data_hora"],
            "rota": ev["nome_rota"],
            "dificuldade": f"{dific} ({idx})",
            "valor": valor,
            "vagas": ev["vagas"],
            "pontuacao": min(pontos, 100),
            "motivos": motivos,
            "alerta": alerta,
        })

    recomendacoes.sort(key=lambda r: r["pontuacao"], reverse=True)
    return usuario, recomendacoes[:limite]


def evolucao_ciclista(con, cpf):
    """Resumo do historico e sugestao de subida de nivel."""
    usuario = con.execute("SELECT * FROM usuario WHERE cpf = ?", (cpf,)).fetchone()
    if not usuario:
        return None
    historico = _historico(con, cpf)
    km_total = round(sum(h["distancia_km"] for h in historico), 2)
    subida_total = sum(h["altimetria_ganho_m"] or 0 for h in historico)

    mais_dificil = None
    for h in historico:
        idx = indice_dificuldade(h["distancia_km"], h["altimetria_ganho_m"], h["tipo_terreno"])
        if not mais_dificil or idx > mais_dificil[1]:
            mais_dificil = (h["nome_rota"], idx, classificar(idx))

    nivel = usuario["nivel_experiencia"]
    meta = METAS_EVOLUCAO.get(nivel)
    if meta is None:
        sugestao = "Nivel maximo atingido. Que tal organizar um evento?"
        progresso = None
    else:
        p_eventos = min(len(historico) / meta["eventos"], 1)
        p_km = min(km_total / meta["km"], 1)
        progresso = round((p_eventos + p_km) / 2 * 100)
        if progresso >= 100:
            sugestao = f"Pronto para subir para {meta['proximo']}!"
        else:
            faltam = []
            if len(historico) < meta["eventos"]:
                faltam.append(f"{meta['eventos'] - len(historico)} evento(s)")
            if km_total < meta["km"]:
                faltam.append(f"{meta['km'] - km_total:.1f} km")
            sugestao = f"Faltam {' e '.join(faltam)} para {meta['proximo']}."

    return {
        "nome": usuario["nome"],
        "nivel": nivel,
        "eventos": len(historico),
        "km_total": km_total,
        "subida_total": subida_total,
        "mais_dificil": mais_dificil,
        "progresso": progresso,
        "proximo_nivel": meta["proximo"] if meta else None,
        "sugestao": sugestao,
    }
