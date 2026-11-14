"""
app_gui.py - PedalHub / Code Riders com interface grafica (Tkinter).

Como rodar:   python app_gui.py
Usa os mesmos modulos da versao de terminal (banco, servicos,
relatorios e recomendacao); so a "casca" visual e diferente.
"""

import csv
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import banco
import recomendacao as rec
import servicos as srv
from relatorios import RELATORIOS
from servicos import RegraNegocioErro

# Paleta inspirada em natureza / ciclismo
VERDE_ESCURO = "#1f3d2b"
VERDE = "#2e7d4f"
VERDE_CLARO = "#e8f3ec"
LARANJA = "#f28c28"
VERMELHO = "#c0392b"
CINZA_TEXTO = "#4a4a4a"
FUNDO = "#f6f7f5"
BRANCO = "#ffffff"

FONTE = ("Segoe UI", 10)
FONTE_NEGRITO = ("Segoe UI", 10, "bold")
FONTE_TITULO = ("Segoe UI", 18, "bold")
FONTE_SUBTITULO = ("Segoe UI", 12, "bold")


def rotulo_coluna(nome):
    """'valor_inscricao' -> 'Valor inscricao'."""
    return nome.replace("_", " ").capitalize()


def formatar(valor):
    if valor is None:
        return "-"
    if isinstance(valor, float):
        return f"{valor:.2f}"
    return str(valor)


# ---------------------------------------------------------------
# Componentes reutilizaveis
# ---------------------------------------------------------------

class Tabela(ttk.Frame):
    """Treeview com barras de rolagem e preenchimento a partir de linhas do banco."""

    def __init__(self, master, altura=12):
        super().__init__(master)
        self.tree = ttk.Treeview(self, show="headings", height=altura, selectmode="browse")
        sy = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        sx = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tree.tag_configure("par", background=VERDE_CLARO)
        self.colunas, self.linhas = [], []

    def preencher(self, linhas, colunas=None):
        self.linhas = list(linhas)
        self.colunas = colunas or (list(self.linhas[0].keys()) if self.linhas else self.colunas)
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = self.colunas
        for c in self.colunas:
            maior = max([len(rotulo_coluna(c))] + [len(formatar(l[c])) for l in self.linhas])
            self.tree.heading(c, text=rotulo_coluna(c))
            self.tree.column(c, width=min(max(maior * 8 + 16, 70), 320), anchor="w")
        for i, l in enumerate(self.linhas):
            self.tree.insert("", "end", iid=str(i), values=[formatar(l[c]) for c in self.colunas],
                             tags=("par",) if i % 2 else ())

    def selecionada(self):
        sel = self.tree.selection()
        return self.linhas[int(sel[0])] if sel else None


class Formulario(tk.Toplevel):
    """
    Janela de formulario generica.
    campos = lista de tuplas (rotulo, chave, tipo, opcoes)
      tipo: 'texto' | 'lista' (combobox) | 'nota' (1 a 5) | 'multilinha'
    Depois de fechar, self.resultado tem um dict com os valores (ou None).
    """

    def __init__(self, master, titulo, campos, botao="Salvar"):
        super().__init__(master)
        self.title(titulo)
        self.configure(bg=FUNDO, padx=20, pady=16)
        self.resizable(False, False)
        self.transient(master)
        self.resultado = None
        self.widgets = {}

        tk.Label(self, text=titulo, font=FONTE_SUBTITULO, bg=FUNDO, fg=VERDE_ESCURO) \
            .grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        for i, (rotulo, chave, tipo, opcoes) in enumerate(campos, start=1):
            tk.Label(self, text=rotulo, font=FONTE, bg=FUNDO, fg=CINZA_TEXTO) \
                .grid(row=i, column=0, sticky="nw", pady=4, padx=(0, 10))
            if tipo == "lista":
                w = ttk.Combobox(self, values=opcoes, state="readonly", width=42)
                if opcoes:
                    w.current(0)
            elif tipo == "nota":
                w = ttk.Spinbox(self, from_=1, to=5, width=5, state="readonly")
                w.set(5)
            elif tipo == "multilinha":
                w = tk.Text(self, width=44, height=4, font=FONTE)
            else:
                w = ttk.Entry(self, width=44)
                if opcoes:
                    w.insert(0, opcoes)
            w.grid(row=i, column=1, sticky="w", pady=4)
            self.widgets[chave] = (w, tipo)

        botoes = tk.Frame(self, bg=FUNDO)
        botoes.grid(row=len(campos) + 1, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(botoes, text="Cancelar", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(botoes, text=botao, style="Acao.TButton", command=self._ok).pack(side="right")
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

        # centraliza a janela sobre a principal
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        primeiro = next(iter(self.widgets.values()))[0]
        primeiro.focus_set()
        self.grab_set()
        self.wait_window()

    def _ok(self):
        dados = {}
        for chave, (w, tipo) in self.widgets.items():
            dados[chave] = w.get("1.0", "end").strip() if tipo == "multilinha" else w.get().strip()
        self.resultado = dados
        self.destroy()


# ---------------------------------------------------------------
# Aplicacao
# ---------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.con = banco.conectar()
        self.title("PedalHub - Code Riders")
        self.geometry("1180x700")
        self.minsize(980, 600)
        self.configure(bg=FUNDO)
        self._icone()
        self._estilos()
        self._montar_layout()
        self.protocol("WM_DELETE_WINDOW", self._sair)
        self.mostrar("inicio")

    # ---------- aparencia ----------
    def _icone(self):
        """Usa o pedalhub.ico (dentro do .exe ou ao lado do arquivo)."""
        pasta = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        try:
            self.iconbitmap(pasta / "pedalhub.ico")
        except tk.TclError:
            pass  # em Linux/Mac o .ico pode nao ser suportado

    def _estilos(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", font=FONTE, background=FUNDO)
        s.configure("Treeview", rowheight=26, background=BRANCO, fieldbackground=BRANCO)
        s.configure("Treeview.Heading", font=FONTE_NEGRITO, background=VERDE, foreground=BRANCO)
        s.map("Treeview.Heading", background=[("active", VERDE_ESCURO)])
        s.map("Treeview", background=[("selected", LARANJA)], foreground=[("selected", BRANCO)])
        s.configure("TButton", padding=(12, 6))
        s.configure("Acao.TButton", background=VERDE, foreground=BRANCO, font=FONTE_NEGRITO)
        s.map("Acao.TButton", background=[("active", VERDE_ESCURO)])
        s.configure("Perigo.TButton", background=VERMELHO, foreground=BRANCO)
        s.map("Perigo.TButton", background=[("active", "#962d22")])
        s.configure("TNotebook", background=FUNDO)
        s.configure("TNotebook.Tab", padding=(14, 6), font=FONTE_NEGRITO)
        s.configure("Verde.Horizontal.TProgressbar", background=VERDE, troughcolor="#dfe6e1")
        s.configure("Laranja.Horizontal.TProgressbar", background=LARANJA, troughcolor="#dfe6e1")
        s.configure("TCheckbutton", background=FUNDO)

    def _montar_layout(self):
        self.menu_lateral = tk.Frame(self, bg=VERDE_ESCURO, width=220)
        self.menu_lateral.pack(side="left", fill="y")
        self.menu_lateral.pack_propagate(False)

        tk.Label(self.menu_lateral, text="PedalHub", font=("Segoe UI", 20, "bold"),
                 bg=VERDE_ESCURO, fg=BRANCO).pack(pady=(24, 0))
        tk.Label(self.menu_lateral, text="Code Riders", font=FONTE,
                 bg=VERDE_ESCURO, fg="#a9c9b5").pack(pady=(0, 24))

        self.botoes_menu = {}
        itens = [
            ("inicio", "Inicio"),
            ("eventos", "Eventos"),
            ("ciclistas", "Ciclistas"),
            ("inscricoes", "Inscricoes"),
            ("relatorios", "Relatorios"),
            ("inteligente", "PedalHub Inteligente"),
        ]
        for chave, texto in itens:
            b = tk.Button(self.menu_lateral, text=f"   {texto}", anchor="w", font=FONTE_NEGRITO,
                          bg=VERDE_ESCURO, fg=BRANCO, activebackground=VERDE,
                          activeforeground=BRANCO, bd=0, relief="flat", cursor="hand2",
                          padx=10, pady=10, command=lambda c=chave: self.mostrar(c))
            b.pack(fill="x")
            self.botoes_menu[chave] = b

        tk.Button(self.menu_lateral, text="Restaurar dados originais", font=("Segoe UI", 9),
                  bg=VERDE_ESCURO, fg="#a9c9b5", bd=0, activebackground=VERDE,
                  activeforeground=BRANCO, cursor="hand2", command=self._resetar) \
            .pack(side="bottom", pady=16)

        self.conteudo = tk.Frame(self, bg=FUNDO, padx=24, pady=18)
        self.conteudo.pack(side="left", fill="both", expand=True)

    def mostrar(self, tela):
        for chave, b in self.botoes_menu.items():
            b.configure(bg=VERDE if chave == tela else VERDE_ESCURO)
        for w in self.conteudo.winfo_children():
            w.destroy()
        self.tela_atual = tela
        getattr(self, f"tela_{tela}")()

    def recarregar(self):
        self.mostrar(self.tela_atual)

    # ---------- utilitarios ----------
    def cabecalho(self, titulo, subtitulo=""):
        tk.Label(self.conteudo, text=titulo, font=FONTE_TITULO, bg=FUNDO,
                 fg=VERDE_ESCURO).pack(anchor="w")
        if subtitulo:
            tk.Label(self.conteudo, text=subtitulo, font=FONTE, bg=FUNDO,
                     fg=CINZA_TEXTO).pack(anchor="w", pady=(0, 12))

    def barra_botoes(self, botoes):
        barra = tk.Frame(self.conteudo, bg=FUNDO)
        barra.pack(fill="x", pady=(0, 10))
        for texto, comando, estilo in botoes:
            ttk.Button(barra, text=texto, command=comando, style=estilo).pack(side="left", padx=(0, 6))
        return barra

    def executar(self, acao, sucesso=None):
        """Roda uma acao tratando erros de regra de negocio."""
        try:
            retorno = acao()
        except RegraNegocioErro as erro:
            messagebox.showwarning("Atencao", str(erro), parent=self)
            return None
        except ValueError:
            messagebox.showwarning("Atencao", "Verifique os numeros digitados.", parent=self)
            return None
        if sucesso:
            messagebox.showinfo("PedalHub", sucesso, parent=self)
        self.recarregar()
        return retorno

    def exigir_selecao(self, tabela, o_que="um registro"):
        linha = tabela.selecionada()
        if linha is None:
            messagebox.showinfo("PedalHub", f"Selecione {o_que} na tabela.", parent=self)
        return linha

    def opcoes_ciclistas(self):
        return [f"{u['nome']} - {u['cpf']}" for u in srv.listar_usuarios(self.con)]

    @staticmethod
    def cpf_da_opcao(texto):
        return texto.rsplit(" - ", 1)[-1]

    @staticmethod
    def id_da_opcao(texto):
        return int(texto.split(" - ", 1)[0].replace("#", ""))

    # ---------------------------------------------------------------
    # TELA: Inicio
    # ---------------------------------------------------------------
    def tela_inicio(self):
        self.cabecalho("Bem-vindo ao PedalHub",
                       "Eventos, rotas e encontros de ciclismo no Distrito Federal")
        c = self.con
        indicadores = [
            ("Ciclistas", c.execute("SELECT COUNT(*) FROM usuario").fetchone()[0], VERDE),
            ("Eventos abertos",
             c.execute("SELECT COUNT(*) FROM evento WHERE status_evento='Agendado'").fetchone()[0],
             LARANJA),
            ("Inscricoes ativas",
             c.execute("SELECT COUNT(*) FROM inscricao WHERE status_pagamento<>'Cancelado'")
              .fetchone()[0], VERDE_ESCURO),
            ("Km pedalados",
             f"{sum(r['km_total_pedalado'] for r in RELATORIOS[4][1](c)):.0f}", "#3b6ea5"),
        ]
        cards = tk.Frame(self.conteudo, bg=FUNDO)
        cards.pack(fill="x", pady=(0, 18))
        for i, (rotulo, valor, cor) in enumerate(indicadores):
            card = tk.Frame(cards, bg=cor, padx=18, pady=14)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            cards.columnconfigure(i, weight=1)
            tk.Label(card, text=str(valor), font=("Segoe UI", 26, "bold"), bg=cor, fg=BRANCO) \
                .pack(anchor="w")
            tk.Label(card, text=rotulo, font=FONTE_NEGRITO, bg=cor, fg=BRANCO).pack(anchor="w")

        tk.Label(self.conteudo, text="Proximos eventos com inscricoes abertas",
                 font=FONTE_SUBTITULO, bg=FUNDO, fg=VERDE_ESCURO).pack(anchor="w", pady=(0, 6))
        t = Tabela(self.conteudo, altura=6)
        t.pack(fill="both", expand=True)
        t.preencher(srv.listar_eventos(c, apenas_abertos=True),
                    ["titulo", "data_hora", "categoria", "rota", "valor_inscricao",
                     "vagas_restantes"])

        dica = tk.Frame(self.conteudo, bg=VERDE_CLARO, padx=14, pady=10)
        dica.pack(fill="x", pady=(14, 0))
        tk.Label(dica, text="Dica: va em 'PedalHub Inteligente' para receber eventos "
                            "recomendados para o seu nivel.",
                 font=FONTE, bg=VERDE_CLARO, fg=VERDE_ESCURO).pack(anchor="w")

    # ---------------------------------------------------------------
    # TELA: Eventos
    # ---------------------------------------------------------------
    def tela_eventos(self):
        self.cabecalho("Eventos", "Todos os pedais cadastrados")
        self.so_abertos = getattr(self, "so_abertos", tk.BooleanVar(value=False))
        barra = self.barra_botoes([
            ("Ver detalhes", self.evento_detalhes, "TButton"),
            ("Novo evento", self.evento_novo, "Acao.TButton"),
            ("Alterar status", self.evento_status, "TButton"),
        ])
        ttk.Checkbutton(barra, text="Somente com inscricoes abertas", variable=self.so_abertos,
                        command=self.recarregar).pack(side="right")
        self.tab_eventos = Tabela(self.conteudo)
        self.tab_eventos.pack(fill="both", expand=True)
        self.tab_eventos.preencher(
            srv.listar_eventos(self.con, apenas_abertos=self.so_abertos.get()),
            ["id_evento", "titulo", "data_hora", "categoria", "rota", "distancia_km",
             "valor_inscricao", "status_evento", "organizador", "vagas_restantes"])
        self.tab_eventos.tree.bind("<Double-1>", lambda e: self.evento_detalhes())

    def evento_detalhes(self):
        ev = self.exigir_selecao(self.tab_eventos, "um evento")
        if not ev:
            return
        r = self.con.execute(
            "SELECT r.* FROM rota r JOIN evento e ON e.id_rota = r.id_rota WHERE e.id_evento = ?",
            (ev["id_evento"],)).fetchone()
        idx = rec.indice_dificuldade(r["distancia_km"], r["altimetria_ganho_m"], r["tipo_terreno"])

        janela = tk.Toplevel(self)
        janela.title(ev["titulo"])
        janela.configure(bg=FUNDO, padx=22, pady=18)
        janela.transient(self)
        tk.Label(janela, text=ev["titulo"], font=FONTE_SUBTITULO, bg=FUNDO,
                 fg=VERDE_ESCURO).pack(anchor="w")
        tk.Label(janela, text=ev["status_evento"], font=FONTE_NEGRITO, bg=LARANJA, fg=BRANCO,
                 padx=8).pack(anchor="w", pady=(2, 10))
        info = [
            ("Data", ev["data_hora"]),
            ("Categoria", ev["categoria"]),
            ("Organizador", ev["organizador"]),
            ("Rota", f"{r['nome_rota']} - {r['distancia_km']} km, "
                     f"{r['altimetria_ganho_m']} m de subida, {r['tipo_terreno']}"),
            ("Partida", r["ponto_partida"]),
            ("Dificuldade", f"{rec.classificar(idx)} (indice {idx})"),
            ("Inscricao", f"R$ {ev['valor_inscricao']:.2f}"),
            ("Vagas", f"{ev['vagas_restantes']} de {ev['limite_vagas']}"),
        ]
        grade = tk.Frame(janela, bg=FUNDO)
        grade.pack(anchor="w")
        for i, (k, v) in enumerate(info):
            tk.Label(grade, text=k + ":", font=FONTE_NEGRITO, bg=FUNDO).grid(row=i, column=0, sticky="w")
            tk.Label(grade, text=v, font=FONTE, bg=FUNDO).grid(row=i, column=1, sticky="w", padx=8)

        avals = srv.avaliacoes_do_evento(self.con, ev["id_evento"])
        if avals:
            media = sum(a["nota"] for a in avals) / len(avals)
            tk.Label(janela, text=f"Avaliacoes  (media {media:.1f} de 5)", font=FONTE_SUBTITULO,
                     bg=FUNDO, fg=VERDE_ESCURO).pack(anchor="w", pady=(14, 4))
            for a in avals:
                tk.Label(janela, text=f"{'★' * a['nota']}{'☆' * (5 - a['nota'])}  {a['ciclista']}",
                         font=FONTE_NEGRITO, bg=FUNDO, fg=LARANJA).pack(anchor="w")
                tk.Label(janela, text=a["comentario"], font=FONTE, bg=FUNDO, fg=CINZA_TEXTO,
                         wraplength=480, justify="left").pack(anchor="w", pady=(0, 6))
        ttk.Button(janela, text="Fechar", command=janela.destroy).pack(anchor="e", pady=(10, 0))

    def evento_novo(self):
        categorias = [f"{c['id_categoria']} - {c['nome_categoria']}"
                      for c in srv.listar_categorias(self.con)]
        rotas = [f"{r['id']} - {r['rota']} ({r['dificuldade']}, {r['km']} km)"
                 for r in rec.rotas_com_dificuldade(self.con)]
        f = Formulario(self, "Novo evento", [
            ("Titulo", "titulo", "texto", None),
            ("Data e hora", "data_hora", "texto", "2026-12-05 07:00"),
            ("Limite de vagas", "vagas", "texto", "20"),
            ("Valor (R$)", "valor", "texto", "0"),
            ("Organizador", "org", "lista", self.opcoes_ciclistas()),
            ("Categoria", "cat", "lista", categorias),
            ("Rota", "rota", "lista", rotas),
        ], botao="Criar evento")
        d = f.resultado
        if d:
            self.executar(lambda: srv.criar_evento(
                self.con, d["titulo"], d["data_hora"], int(d["vagas"]),
                float(d["valor"].replace(",", ".")), self.cpf_da_opcao(d["org"]),
                self.id_da_opcao(d["cat"]), self.id_da_opcao(d["rota"])),
                "Evento criado com sucesso!")

    def evento_status(self):
        ev = self.exigir_selecao(self.tab_eventos, "um evento")
        if not ev:
            return
        opcoes = list(srv.STATUS_EVENTO)
        f = Formulario(self, f"Status: {ev['titulo']}", [("Novo status", "s", "lista", opcoes)])
        if f.resultado:
            self.executar(lambda: srv.alterar_status_evento(self.con, ev["id_evento"],
                                                            f.resultado["s"]),
                          "Status atualizado.")

    # ---------------------------------------------------------------
    # TELA: Ciclistas
    # ---------------------------------------------------------------
    def tela_ciclistas(self):
        self.cabecalho("Ciclistas", "Comunidade cadastrada no PedalHub")
        self.barra_botoes([
            ("Novo ciclista", self.ciclista_novo, "Acao.TButton"),
            ("Alterar nivel", self.ciclista_nivel, "TButton"),
            ("Ver inscricoes", self.ciclista_inscricoes, "TButton"),
        ])
        self.tab_ciclistas = Tabela(self.conteudo)
        self.tab_ciclistas.pack(fill="both", expand=True)
        self.tab_ciclistas.preencher(srv.listar_usuarios(self.con))

    def ciclista_novo(self):
        f = Formulario(self, "Novo ciclista", [
            ("CPF", "cpf", "texto", None),
            ("Nome", "nome", "texto", None),
            ("E-mail", "email", "texto", None),
            ("Telefone", "tel", "texto", None),
            ("Nivel", "nivel", "lista", list(srv.NIVEIS)),
        ], botao="Cadastrar")
        d = f.resultado
        if d:
            self.executar(lambda: srv.cadastrar_usuario(self.con, d["cpf"], d["nome"],
                                                        d["email"], d["tel"], d["nivel"]),
                          f"Bem-vindo(a) ao PedalHub, {d['nome']}!")

    def ciclista_nivel(self):
        u = self.exigir_selecao(self.tab_ciclistas, "um ciclista")
        if not u:
            return
        f = Formulario(self, f"Nivel de {u['nome']}",
                       [("Novo nivel", "n", "lista", list(srv.NIVEIS))])
        if f.resultado:
            self.executar(lambda: srv.atualizar_nivel(self.con, u["cpf"], f.resultado["n"]),
                          "Nivel atualizado.")

    def ciclista_inscricoes(self):
        u = self.exigir_selecao(self.tab_ciclistas, "um ciclista")
        if u:
            self.filtro_ciclista = f"{u['nome']} - {u['cpf']}"
            self.mostrar("inscricoes")

    # ---------------------------------------------------------------
    # TELA: Inscricoes
    # ---------------------------------------------------------------
    TODOS = "Todos os ciclistas"

    def tela_inscricoes(self):
        self.cabecalho("Inscricoes", "Inscreva, registre pagamento, confirme presenca e avalie")
        filtro = tk.Frame(self.conteudo, bg=FUNDO)
        filtro.pack(fill="x", pady=(0, 10))
        tk.Label(filtro, text="Ciclista:", font=FONTE_NEGRITO, bg=FUNDO).pack(side="left")
        opcoes = [self.TODOS] + self.opcoes_ciclistas()
        self.combo_ciclista = ttk.Combobox(filtro, values=opcoes, state="readonly", width=40)
        self.combo_ciclista.set(getattr(self, "filtro_ciclista", self.TODOS))
        self.combo_ciclista.pack(side="left", padx=8)
        self.combo_ciclista.bind("<<ComboboxSelected>>", self._mudou_ciclista)

        self.barra_botoes([
            ("Nova inscricao", self.insc_nova, "Acao.TButton"),
            ("Registrar pagamento", lambda: self.insc_acao(srv.registrar_pagamento,
                                                           "Pagamento registrado."), "TButton"),
            ("Confirmar presenca", lambda: self.insc_acao(srv.confirmar_presenca,
                                                          "Presenca confirmada."), "TButton"),
            ("Avaliar evento", self.insc_avaliar, "TButton"),
            ("Cancelar inscricao", self.insc_cancelar, "Perigo.TButton"),
        ])
        self.tab_insc = Tabela(self.conteudo)
        self.tab_insc.pack(fill="both", expand=True)

        escolha = self.combo_ciclista.get()
        if escolha == self.TODOS:
            linhas = self.con.execute("""
                SELECT i.id_inscricao, u.nome AS ciclista, e.titulo AS evento, e.data_hora,
                       e.status_evento, i.status_pagamento,
                       CASE i.presenca_confirmada WHEN 1 THEN 'Sim' ELSE 'Nao' END AS presenca,
                       COALESCE(a.nota, '-') AS nota
                  FROM inscricao i
                  JOIN usuario u ON u.cpf = i.cpf_usuario
                  JOIN evento e  ON e.id_evento = i.id_evento
                  LEFT JOIN avaliacao a ON a.id_inscricao = i.id_inscricao
                 ORDER BY e.data_hora, u.nome""").fetchall()
        else:
            linhas = srv.inscricoes_do_usuario(self.con, self.cpf_da_opcao(escolha))
        self.tab_insc.preencher(linhas, list(linhas[0].keys()) if linhas else
                                ["id_inscricao", "titulo", "data_hora", "status_pagamento"])

    def _mudou_ciclista(self, _evento=None):
        self.filtro_ciclista = self.combo_ciclista.get()
        self.recarregar()

    def insc_nova(self, id_evento=None, cpf=None):
        abertos = [f"{e['id_evento']} - {e['titulo']} ({e['data_hora'][:10]}, "
                   f"R$ {e['valor_inscricao']:.2f}, {e['vagas_restantes']} vagas)"
                   for e in srv.listar_eventos(self.con, apenas_abertos=True)]
        if not abertos:
            messagebox.showinfo("PedalHub", "Nao ha eventos com inscricoes abertas.", parent=self)
            return
        ciclistas = self.opcoes_ciclistas()
        atual = self.combo_ciclista.get() if hasattr(self, "combo_ciclista") else self.TODOS
        if atual in ciclistas:  # ja deixa o ciclista filtrado em primeiro
            ciclistas.remove(atual)
            ciclistas.insert(0, atual)
        f = Formulario(self, "Nova inscricao", [
            ("Ciclista", "c", "lista", ciclistas),
            ("Evento", "e", "lista", abertos),
        ], botao="Inscrever")
        d = f.resultado
        if d:
            self._inscrever(self.cpf_da_opcao(d["c"]), self.id_da_opcao(d["e"]))

    def _inscrever(self, cpf, id_evento):
        try:
            id_insc = srv.inscrever(self.con, cpf, id_evento)
        except RegraNegocioErro as erro:
            messagebox.showwarning("Atencao", str(erro), parent=self)
            return
        insc = srv.buscar_inscricao(self.con, id_insc)
        msg = f"Inscricao #{id_insc} realizada!\nSituacao: {insc['status_pagamento']}"
        if insc["status_pagamento"] == "Pendente":
            msg += f"\nValor a pagar: R$ {insc['valor_inscricao']:.2f}"
        messagebox.showinfo("PedalHub", msg, parent=self)
        self.recarregar()

    def insc_acao(self, funcao, mensagem):
        linha = self.exigir_selecao(self.tab_insc, "uma inscricao")
        if linha:
            self.executar(lambda: funcao(self.con, linha["id_inscricao"]), mensagem)

    def insc_cancelar(self):
        linha = self.exigir_selecao(self.tab_insc, "uma inscricao")
        if linha and messagebox.askyesno("Cancelar inscricao",
                                         "Confirma o cancelamento? A vaga sera liberada.",
                                         parent=self):
            self.executar(lambda: srv.cancelar_inscricao(self.con, linha["id_inscricao"]),
                          "Inscricao cancelada.")

    def insc_avaliar(self):
        linha = self.exigir_selecao(self.tab_insc, "uma inscricao")
        if not linha:
            return
        f = Formulario(self, "Avaliar evento", [
            ("Nota (1 a 5)", "nota", "nota", None),
            ("Comentario", "coment", "multilinha", None),
        ], botao="Enviar avaliacao")
        d = f.resultado
        if d:
            self.executar(lambda: srv.avaliar(self.con, linha["id_inscricao"], int(d["nota"]),
                                              d["coment"]),
                          "Obrigado pela avaliacao!")

    # ---------------------------------------------------------------
    # TELA: Relatorios
    # ---------------------------------------------------------------
    def tela_relatorios(self):
        self.cabecalho("Relatorios", "As consultas do banco de dados do projeto")
        barra = tk.Frame(self.conteudo, bg=FUNDO)
        barra.pack(fill="x", pady=(0, 10))
        tk.Label(barra, text="Relatorio:", font=FONTE_NEGRITO, bg=FUNDO).pack(side="left")
        nomes = [n for n, _ in RELATORIOS]
        self.combo_rel = ttk.Combobox(barra, values=nomes, state="readonly", width=40)
        self.combo_rel.current(getattr(self, "rel_atual", 0))
        self.combo_rel.pack(side="left", padx=8)
        self.combo_rel.bind("<<ComboboxSelected>>", self._mudou_relatorio)
        ttk.Button(barra, text="Exportar CSV", command=self._exportar_csv).pack(side="right")

        self.tab_rel = Tabela(self.conteudo)
        self.tab_rel.pack(fill="both", expand=True)
        self.tab_rel.preencher(RELATORIOS[self.combo_rel.current()][1](self.con))

    def _mudou_relatorio(self, _evento=None):
        self.rel_atual = self.combo_rel.current()
        self.recarregar()

    def _exportar_csv(self):
        if not self.tab_rel.linhas:
            return
        nome = RELATORIOS[self.combo_rel.current()][0].lower().replace(" ", "_").replace("/", "_")
        caminho = filedialog.asksaveasfilename(parent=self, defaultextension=".csv",
                                               initialfile=f"{nome}.csv",
                                               filetypes=[("CSV", "*.csv")])
        if caminho:
            with open(caminho, "w", newline="", encoding="utf-8-sig") as arq:
                w = csv.writer(arq, delimiter=";")
                w.writerow(self.tab_rel.colunas)
                for l in self.tab_rel.linhas:
                    w.writerow([l[c] for c in self.tab_rel.colunas])
            messagebox.showinfo("PedalHub", "Relatorio exportado!", parent=self)

    # ---------------------------------------------------------------
    # TELA: PedalHub Inteligente (inovacao)
    # ---------------------------------------------------------------
    def tela_inteligente(self):
        self.cabecalho("PedalHub Inteligente",
                       "Recomendacoes personalizadas, evolucao e dificuldade das rotas")
        topo = tk.Frame(self.conteudo, bg=FUNDO)
        topo.pack(fill="x", pady=(0, 10))
        tk.Label(topo, text="Ciclista:", font=FONTE_NEGRITO, bg=FUNDO).pack(side="left")
        opcoes = self.opcoes_ciclistas()
        self.combo_ia = ttk.Combobox(topo, values=opcoes, state="readonly", width=40)
        atual = getattr(self, "ciclista_ia", None)
        self.combo_ia.set(atual if atual in opcoes else opcoes[0])
        self.combo_ia.pack(side="left", padx=8)
        self.combo_ia.bind("<<ComboboxSelected>>", self._mudou_ciclista_ia)

        abas = ttk.Notebook(self.conteudo)
        abas.pack(fill="both", expand=True)
        aba_rec = tk.Frame(abas, bg=FUNDO, padx=10, pady=10)
        aba_evo = tk.Frame(abas, bg=FUNDO, padx=16, pady=16)
        aba_rotas = tk.Frame(abas, bg=FUNDO, padx=10, pady=10)
        abas.add(aba_rec, text="Eventos recomendados")
        abas.add(aba_evo, text="Minha evolucao")
        abas.add(aba_rotas, text="Dificuldade das rotas")
        abas.select(getattr(self, "aba_ia", 0))
        abas.bind("<<NotebookTabChanged>>",
                  lambda e: setattr(self, "aba_ia", abas.index(abas.select())))

        cpf = self.cpf_da_opcao(self.combo_ia.get())
        self._aba_recomendacoes(aba_rec, cpf)
        self._aba_evolucao(aba_evo, cpf)
        self._aba_rotas(aba_rotas)

    def _mudou_ciclista_ia(self, _evento=None):
        self.ciclista_ia = self.combo_ia.get()
        self.recarregar()

    def _aba_recomendacoes(self, pai, cpf):
        usuario, lista = rec.recomendar_eventos(self.con, cpf)
        tk.Label(pai, text=f"Para {usuario['nome']}  -  nivel {usuario['nivel_experiencia']}",
                 font=FONTE_SUBTITULO, bg=FUNDO, fg=VERDE_ESCURO).pack(anchor="w", pady=(0, 8))
        if not lista:
            tk.Label(pai, text="Nenhum evento aberto disponivel para este ciclista no momento.",
                     font=FONTE, bg=FUNDO, fg=CINZA_TEXTO).pack(anchor="w")
            return

        # area rolavel com os cartoes
        canvas = tk.Canvas(pai, bg=FUNDO, highlightthickness=0)
        rolagem = ttk.Scrollbar(pai, orient="vertical", command=canvas.yview)
        lista_frame = tk.Frame(canvas, bg=FUNDO)
        lista_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        janela = canvas.create_window((0, 0), window=lista_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(janela, width=e.width))
        canvas.configure(yscrollcommand=rolagem.set)
        canvas.pack(side="left", fill="both", expand=True)
        rolagem.pack(side="right", fill="y")

        for pos, r in enumerate(lista, 1):
            cor_borda = VERMELHO if r["alerta"] else VERDE
            cartao = tk.Frame(lista_frame, bg=BRANCO, highlightbackground=cor_borda,
                              highlightthickness=2, padx=14, pady=10)
            cartao.pack(fill="x", pady=(0, 10))

            linha1 = tk.Frame(cartao, bg=BRANCO)
            linha1.pack(fill="x")
            tk.Label(linha1, text=f"{pos}. {r['titulo']}", font=FONTE_SUBTITULO, bg=BRANCO,
                     fg=VERDE_ESCURO).pack(side="left")
            tk.Label(linha1, text=f"{r['pontuacao']}/100", font=("Segoe UI", 14, "bold"),
                     bg=BRANCO, fg=cor_borda).pack(side="right")
            barra = ttk.Progressbar(cartao, maximum=100, value=r["pontuacao"],
                                    style="Laranja.Horizontal.TProgressbar" if r["alerta"]
                                    else "Verde.Horizontal.TProgressbar")
            barra.pack(fill="x", pady=4)
            tk.Label(cartao, text=f"{r['data_hora'][:16]}   |   {r['rota']}   |   "
                                  f"{r['dificuldade']}   |   R$ {r['valor']:.2f}   |   "
                                  f"{r['vagas']} vagas",
                     font=FONTE, bg=BRANCO, fg=CINZA_TEXTO).pack(anchor="w")
            if r["motivos"]:
                tk.Label(cartao, text="Por que: " + "; ".join(r["motivos"]), font=FONTE,
                         bg=BRANCO, fg=VERDE, wraplength=760, justify="left").pack(anchor="w",
                                                                                   pady=(4, 0))
            if r["alerta"]:
                tk.Label(cartao, text="ATENCAO: " + r["alerta"], font=FONTE_NEGRITO, bg=BRANCO,
                         fg=VERMELHO).pack(anchor="w", pady=(4, 0))
            ttk.Button(cartao, text="Inscrever-me", style="Acao.TButton",
                       command=lambda i=r["id_evento"]: self._inscrever(cpf, i)) \
                .pack(anchor="e", pady=(6, 0))

    def _aba_evolucao(self, pai, cpf):
        ev = rec.evolucao_ciclista(self.con, cpf)
        tk.Label(pai, text=ev["nome"], font=FONTE_TITULO, bg=FUNDO, fg=VERDE_ESCURO).pack(anchor="w")
        tk.Label(pai, text=f"Nivel atual: {ev['nivel']}", font=FONTE_SUBTITULO, bg=FUNDO,
                 fg=LARANJA).pack(anchor="w", pady=(0, 14))

        numeros = tk.Frame(pai, bg=FUNDO)
        numeros.pack(fill="x")
        dados = [("Eventos concluidos", ev["eventos"]),
                 ("Km pedalados", f"{ev['km_total']:.1f}"),
                 ("Subida acumulada", f"{ev['subida_total']} m")]
        for i, (rotulo, valor) in enumerate(dados):
            caixa = tk.Frame(numeros, bg=BRANCO, highlightbackground="#d5ddd8",
                             highlightthickness=1, padx=16, pady=12)
            caixa.grid(row=0, column=i, sticky="nsew", padx=(0, 10))
            numeros.columnconfigure(i, weight=1)
            tk.Label(caixa, text=str(valor), font=("Segoe UI", 22, "bold"), bg=BRANCO,
                     fg=VERDE).pack(anchor="w")
            tk.Label(caixa, text=rotulo, font=FONTE, bg=BRANCO, fg=CINZA_TEXTO).pack(anchor="w")

        if ev["mais_dificil"]:
            nome, idx, classe = ev["mais_dificil"]
            tk.Label(pai, text=f"Rota mais dificil ja concluida: {nome}  ({classe}, indice {idx})",
                     font=FONTE, bg=FUNDO, fg=CINZA_TEXTO).pack(anchor="w", pady=(16, 0))

        if ev["progresso"] is not None:
            tk.Label(pai, text=f"Progresso ate {ev['proximo_nivel']}: {ev['progresso']}%",
                     font=FONTE_SUBTITULO, bg=FUNDO, fg=VERDE_ESCURO).pack(anchor="w", pady=(18, 4))
            ttk.Progressbar(pai, maximum=100, value=ev["progresso"], length=500,
                            style="Verde.Horizontal.TProgressbar").pack(anchor="w")
        destaque = tk.Frame(pai, bg=VERDE_CLARO, padx=14, pady=10)
        destaque.pack(fill="x", pady=(16, 0))
        tk.Label(destaque, text=ev["sugestao"], font=FONTE_NEGRITO, bg=VERDE_CLARO,
                 fg=VERDE_ESCURO).pack(anchor="w")

    def _aba_rotas(self, pai):
        tk.Label(pai, text="indice = (km + subida em metros / 10) x fator do terreno     "
                           "(Asfalto 1.0  |  Misto 1.2  |  Terra/Trilha 1.4)",
                 font=FONTE, bg=FUNDO, fg=CINZA_TEXTO).pack(anchor="w")
        tk.Label(pai, text="Leve < 35   |   Moderada < 100   |   Dificil >= 100",
                 font=FONTE_NEGRITO, bg=FUNDO, fg=VERDE_ESCURO).pack(anchor="w", pady=(0, 8))
        t = Tabela(pai)
        t.pack(fill="both", expand=True)
        t.preencher(rec.rotas_com_dificuldade(self.con))
        t.tree.tag_configure("Leve", foreground=VERDE)
        t.tree.tag_configure("Moderada", foreground="#b8860b")
        t.tree.tag_configure("Dificil", foreground=VERMELHO)
        for i, r in enumerate(t.linhas):
            t.tree.item(str(i), tags=(r["dificuldade"],))

    # ---------------------------------------------------------------
    def _resetar(self):
        if messagebox.askyesno("Restaurar dados",
                               "Isso apaga tudo que foi alterado e volta aos dados originais. "
                               "Continuar?", parent=self):
            self.con.close()
            self.con = banco.resetar()
            self.recarregar()

    def _sair(self):
        self.con.close()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
