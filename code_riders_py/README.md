# PedalHub (Code Riders) em Python

Programa em linha de comando que usa o banco `pedalhub_db` do trabalho
(usuários, categorias, rotas, eventos, inscrições e avaliações).

## Como rodar

Há duas versões, com as mesmas funções:

| Versão | Comando |
|--------|---------|
| Com telas (janela) | `python app_gui.py` |
| No terminal | `python main.py` |

Não precisa instalar nada além do Python 3.8 ou mais novo. Na primeira execução o programa cria o
arquivo `pedalhub.db` (SQLite) com as mesmas tabelas e os mesmos dados do
script `trabalho corrigido 1.sql`. O botão **Restaurar dados originais**
volta o banco ao estado inicial.

## Gerar o executável (.exe)

1. Num computador Windows com Python instalado, dê dois cliques em `gerar_executavel.bat`.
2. Em 1 ou 2 minutos aparece `dist\PedalHub.exe`.
3. Esse único arquivo roda em **qualquer Windows, sem Python**. O banco
   `pedalhub.db` é criado ao lado do `.exe` na primeira vez que ele abre.

O Windows pode mostrar um aviso "O Windows protegeu o computador", porque o
executável não é assinado digitalmente. Clique em **Mais informações → Executar assim mesmo**.

## Arquivos

| Arquivo           | O que faz |
|-------------------|-----------|
| `app_gui.py`      | Versão com telas (Tkinter) |
| `main.py`         | Versão de terminal |
| `gerar_executavel.bat` | Gera o `PedalHub.exe` com PyInstaller |
| `pedalhub.ico`    | Ícone do programa |
| `banco.py`        | Criação das tabelas (adaptadas do MySQL para SQLite) e carga dos dados |
| `servicos.py`     | Regras de negócio: cadastro, inscrição, pagamento, presença, avaliação |
| `relatorios.py`   | As 5 consultas do script SQL |
| `recomendacao.py` | Módulo de inovação (recomendações e evolução do ciclista) |

## Funcionalidades

- **Eventos**: listar, ver detalhes com avaliações, criar evento, mudar status.
- **Ciclistas**: listar, cadastrar (valida os dígitos verificadores do CPF e o e-mail),
  ver as inscrições, mudar o nível.
- **Inscrições**: inscrever, pagar, cancelar (libera a vaga), confirmar presença, avaliar.
- **Relatórios**: as 5 consultas do SQL (participantes, ocupação, receita,
  satisfação, ranking de km). Na versão com telas dá para exportar em CSV (abre no Excel).
- **Início** (versão com telas): painel com totais e próximos eventos.

### Regras de negócio aplicadas
- Só aceita inscrição em evento `Agendado` e com vaga disponível.
- Evento gratuito gera inscrição `Isento`; evento pago começa como `Pendente`.
- Presença só pode ser confirmada com pagamento em dia (`Pago`/`Isento`) e evento já iniciado.
- Só avalia quem teve presença confirmada e com o evento `Concluido` (uma avaliação por inscrição, nota de 1 a 5).
- Não cancela inscrição de evento em andamento ou concluído.

## Inovação: PedalHub Inteligente

1. **Índice de Dificuldade da Rota**: um número único que junta distância,
   subida e terreno:
   `índice = (km + subida_m / 10) × fator` (Asfalto 1.0, Misto 1.2, Terra/Trilha 1.4).
   Leve < 35, Moderada < 100, Difícil a partir de 100.
2. **Recomendação personalizada** (nota de 0 a 100) para cada evento aberto:
   compatibilidade com o nível (50), afinidade com o histórico (20),
   reputação pelas avaliações da categoria e do organizador (20) e custo (10).
   O sistema explica o motivo de cada sugestão e **avisa quando a rota está acima
   do nível** do ciclista, por segurança.
3. **Evolução do ciclista**: km pedalados, subida acumulada, rota mais difícil
   já feita e barra de progresso até o próximo nível.

## Adaptações em relação ao script MySQL
- `ENUM` virou `TEXT` com `CHECK`, `AUTO_INCREMENT` virou `AUTOINCREMENT` e `BOOLEAN` virou 0/1.
- Consulta 2: a divisão usa `100.0`, porque no SQLite inteiro dividido por inteiro dá inteiro.
- Inscrições canceladas não contam como vaga ocupada.
