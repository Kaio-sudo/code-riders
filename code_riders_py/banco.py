"""
banco.py - Conexao com o banco de dados do PedalHub (Code Riders).

O script original (trabalho corrigido 1.sql) foi escrito para MySQL.
Aqui ele foi adaptado para SQLite, que ja vem embutido no Python:
assim o programa roda em qualquer computador sem instalar servidor.

Adaptacoes feitas:
  - ENUM  -> TEXT com CHECK (... IN (...))
  - REGEXP do CPF -> CHECK com length() e GLOB
  - AUTO_INCREMENT -> INTEGER PRIMARY KEY AUTOINCREMENT
  - BOOLEAN -> INTEGER (0 = falso, 1 = verdadeiro)
Os dados de exemplo (usuarios, rotas, eventos, inscricoes e avaliacoes)
sao exatamente os mesmos do script original.
"""

import sqlite3
import sys
from pathlib import Path

# Quando roda como executavel (.exe), o banco fica ao lado do .exe;
# rodando pelo Python, fica ao lado deste arquivo.
if getattr(sys, "frozen", False):
    PASTA_APP = Path(sys.executable).parent
else:
    PASTA_APP = Path(__file__).parent
CAMINHO_BANCO = PASTA_APP / "pedalhub.db"

SCHEMA = """
CREATE TABLE usuario (
    cpf               TEXT NOT NULL PRIMARY KEY
                      CHECK (length(cpf) = 11 AND cpf NOT GLOB '*[^0-9]*'),
    nome              TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE,
    telefone          TEXT,
    nivel_experiencia TEXT DEFAULT 'Iniciante'
                      CHECK (nivel_experiencia IN ('Iniciante','Intermediario','Avancado')),
    data_cadastro     TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE categoria_evento (
    id_categoria   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_categoria TEXT NOT NULL UNIQUE,
    descricao      TEXT
);

CREATE TABLE rota (
    id_rota            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_rota          TEXT NOT NULL,
    distancia_km       REAL NOT NULL,
    altimetria_ganho_m INTEGER DEFAULT 0,
    tipo_terreno       TEXT NOT NULL
                       CHECK (tipo_terreno IN ('Asfalto','Terra/Trilha','Misto')),
    ponto_partida      TEXT NOT NULL
);

CREATE TABLE evento (
    id_evento       INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo          TEXT NOT NULL,
    data_hora       TEXT NOT NULL,
    limite_vagas    INTEGER NOT NULL,
    valor_inscricao REAL DEFAULT 0.00,
    status_evento   TEXT DEFAULT 'Agendado'
                    CHECK (status_evento IN ('Agendado','Em Andamento','Concluido','Cancelado')),
    cpf_organizador TEXT NOT NULL,
    id_categoria    INTEGER NOT NULL,
    id_rota         INTEGER NOT NULL,
    FOREIGN KEY (cpf_organizador) REFERENCES usuario(cpf)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_categoria) REFERENCES categoria_evento(id_categoria)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (id_rota) REFERENCES rota(id_rota)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE inscricao (
    id_inscricao        INTEGER PRIMARY KEY AUTOINCREMENT,
    cpf_usuario         TEXT NOT NULL,
    id_evento           INTEGER NOT NULL,
    data_inscricao      TEXT DEFAULT (datetime('now','localtime')),
    status_pagamento    TEXT DEFAULT 'Pendente'
                        CHECK (status_pagamento IN ('Pendente','Pago','Isento','Cancelado')),
    presenca_confirmada INTEGER DEFAULT 0 CHECK (presenca_confirmada IN (0,1)),
    UNIQUE (cpf_usuario, id_evento),
    FOREIGN KEY (cpf_usuario) REFERENCES usuario(cpf)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (id_evento) REFERENCES evento(id_evento)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE avaliacao (
    id_avaliacao   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_inscricao   INTEGER NOT NULL UNIQUE,
    nota           INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario     TEXT,
    data_avaliacao TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (id_inscricao) REFERENCES inscricao(id_inscricao)
        ON UPDATE CASCADE ON DELETE CASCADE
);
"""

DADOS_INICIAIS = """
INSERT INTO usuario (cpf, nome, email, telefone, nivel_experiencia, data_cadastro) VALUES
('12345678909', 'Lucas Silveira',   'lucas.silveira@email.com',   '(61) 98111-1001', 'Avancado',      '2026-01-10 08:30:00'),
('23456789173', 'Mariana Rocha',    'mariana.rocha@email.com',    '(61) 98222-2002', 'Intermediario', '2026-01-15 14:20:00'),
('34567891228', 'Carlos Eduardo',   'cadu.pedal@email.com',       '(61) 98333-3003', 'Avancado',      '2026-02-01 09:15:00'),
('45678912364', 'Beatriz Mendes',   'beatriz.mendes@email.com',   '(61) 98444-4004', 'Iniciante',     '2026-02-10 18:00:00'),
('56789123482', 'Thiago Fernandes', 'thiago.fernandes@email.com', '(61) 98555-5005', 'Intermediario', '2026-02-18 11:45:00'),
('67891234582', 'Juliana Paiva',    'juliana.paiva@email.com',    '(61) 98666-6006', 'Iniciante',     '2026-03-01 10:10:00'),
('78912345664', 'Rodrigo Alencar',  'rodrigo.alencar@email.com',  '(61) 98777-7007', 'Avancado',      '2026-03-05 16:30:00'),
('89123456728', 'Fernanda Lima',    'fernanda.lima@email.com',    '(61) 98888-8008', 'Iniciante',     '2026-03-12 19:00:00');

INSERT INTO categoria_evento (nome_categoria, descricao) VALUES
('Pedal Noturno Urbano',       'Passeio em grupo por vias iluminadas com foco em integracao e seguranca'),
('Treino de Alta Performance', 'Treino focado em ritmo medio elevado e ganho de resistencia aerobica'),
('Mountain Bike / Trilha',     'Percursos fora de estrada, terra batida, cascalho e trilhas tecnicas'),
('Passeio Cicloturismo',       'Viagem de medio curso explorando paisagens turisticas e pontos historicos'),
('Iniciacao ao Ciclismo',      'Pedais curtos e planos para quem esta comecando no esporte');

INSERT INTO rota (nome_rota, distancia_km, altimetria_ganho_m, tipo_terreno, ponto_partida) VALUES
('Circuito dos Ministerios',            18.50,  95, 'Asfalto',      'Museu Nacional'),
('Trilha da Floresta Nacional (Flona)', 32.00, 480, 'Terra/Trilha', 'Entrada Principal Flona'),
('Volta do Lago Sul',                   42.80, 310, 'Asfalto',      'Pontao do Lago Sul'),
('Eixo Monumental Noturno',             14.00,  70, 'Asfalto',      'Torre de TV'),
('Circuito Serrinha do Paranoa',        55.40, 720, 'Misto',        'Barragem do Paranoa'),
('Parque da Cidade Suave',              10.00,  40, 'Asfalto',      'Estacionamento 10');

INSERT INTO evento (titulo, data_hora, limite_vagas, valor_inscricao, status_evento,
                    cpf_organizador, id_categoria, id_rota) VALUES
('Pedal da Lua Cheia',            '2026-04-10 19:30:00', 30,  0.00, 'Concluido', '12345678909', 1, 4),
('Desafio Subida da Serrinha',    '2026-04-18 06:30:00', 20, 45.00, 'Concluido', '34567891228', 2, 5),
('Giro Flona Radical',            '2026-04-25 07:00:00', 25, 30.00, 'Concluido', '78912345664', 3, 2),
('Ciclotur Lago Sul',             '2026-05-02 06:00:00', 40, 25.00, 'Agendado',  '12345678909', 4, 3),
('Primeiras Pedaladas no Parque', '2026-05-09 08:00:00', 15,  0.00, 'Agendado',  '23456789173', 5, 6),
('Expresso Noturno DF',           '2026-05-15 20:00:00', 35, 10.00, 'Agendado',  '34567891228', 1, 1);

INSERT INTO inscricao (cpf_usuario, id_evento, data_inscricao, status_pagamento, presenca_confirmada) VALUES
('23456789173', 1, '2026-04-01 10:00:00', 'Isento',   1),
('45678912364', 1, '2026-04-02 11:30:00', 'Isento',   1),
('67891234582', 1, '2026-04-03 15:40:00', 'Isento',   1),
('89123456728', 1, '2026-04-04 09:20:00', 'Isento',   0),
('12345678909', 2, '2026-04-10 08:00:00', 'Pago',     1),
('23456789173', 2, '2026-04-11 12:10:00', 'Pago',     1),
('78912345664', 2, '2026-04-12 17:00:00', 'Pago',     1),
('34567891228', 3, '2026-04-15 14:00:00', 'Pago',     1),
('56789123482', 3, '2026-04-16 16:30:00', 'Pago',     1),
('78912345664', 3, '2026-04-17 19:15:00', 'Pago',     0),
('23456789173', 4, '2026-04-20 09:00:00', 'Pago',     0),
('45678912364', 4, '2026-04-21 10:45:00', 'Pendente', 0),
('56789123482', 4, '2026-04-22 13:20:00', 'Pago',     0),
('67891234582', 5, '2026-04-23 18:00:00', 'Isento',   0),
('89123456728', 5, '2026-04-24 11:10:00', 'Isento',   0),
('12345678909', 6, '2026-04-25 15:00:00', 'Pendente', 0);

INSERT INTO avaliacao (id_inscricao, nota, comentario, data_avaliacao) VALUES
(1, 5, 'Pedal fantastico! Muito seguro e bem guiado pela equipe.', '2026-04-11 08:00:00'),
(2, 4, 'Gostei muito, mas o ritmo apertou um pouco no retorno.',   '2026-04-11 09:30:00'),
(3, 5, 'Excelente para iniciantes, organizacao impecavel.',        '2026-04-11 12:15:00'),
(5, 5, 'Treino muito puxado, ganho de altimetria insano. Nota 10.', '2026-04-19 10:00:00'),
(6, 4, 'Subidas duras, mas o apoio mecanico fez diferenca.',       '2026-04-19 11:20:00'),
(7, 5, 'Melhor percurso da regiao. Ritmo constante.',              '2026-04-19 14:00:00'),
(8, 5, 'Trilha tecnica com cascalho e lama, sensacional!',         '2026-04-26 18:30:00');
"""


def conectar(caminho=CAMINHO_BANCO):
    """Abre o banco. Se o arquivo ainda nao existir, cria as tabelas e os dados."""
    caminho = Path(caminho)
    banco_novo = not caminho.exists()
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row          # permite acessar colunas pelo nome
    con.execute("PRAGMA foreign_keys = ON")  # SQLite exige ativar as FKs
    if banco_novo:
        con.executescript(SCHEMA)
        con.executescript(DADOS_INICIAIS)
        con.commit()
    return con


def resetar(caminho=CAMINHO_BANCO):
    """Apaga o arquivo do banco e recria tudo com os dados originais."""
    caminho = Path(caminho)
    if caminho.exists():
        caminho.unlink()
    return conectar(caminho)
