# Aula 04 · Memória em agentes

Continuação independente da aplicação da Aula 03: mesmo atendimento P100/E100,
fan-out, políticas, TF-IDF, eventos e citações. A cópia não importa arquivos de outra aula.
O aluno modifica uma função, salva, verifica o código e repete a pergunta.

## Executar

Python 3.11/3.12. Na raiz do repositório:

```powershell
cd Aula_04
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Abra .env, informe OPENAI_API_KEY e confira OPENAI_MODEL.
python app.py
```

Abra http://127.0.0.1:5001. Sem ativação do venv, use
`.\.venv\Scripts\python.exe -m pip install -r requirements.txt` e
`.\.venv\Scripts\python.exe app.py`. Nenhuma chave é copiada de Aula 03.
Salvar `.py` recarrega o servidor; `.env` e dados exigem parar/iniciar.

## Três blocos, o mesmo caso

| Bloco | Experimento | Editar |
|---|---|---|
| 1 · Conversa e contexto | P100 → “E agora?”; sem memória, janela, estado | `context.py`, `memory.py`, `graph.py` |
| 2 · Preferência persistente | Confirmar, nova thread, corrigir, revogar, reiniciar | `memory.py` |
| 3 · Compartilhar por papel | Inspecionar projeções; campos próprios; conflito | `memory.py`, `graph.py` |

Comece em **RAG fixo**, mantendo a mesma arquitetura ao comparar memória.
Os caminhos baseline e RAG como ferramenta continuam disponíveis como referência.
**Usar pergunta** escolhe o bloco do exercício; o cartão mostra a alteração e a prova.

F5 conserva o identificador da thread em localStorage; os turnos ficam em SQLite.
O chat visual recomeça vazio após F5: **Inspecionar memória** mostra os turnos salvos.
**Nova conversa** cria outra thread. **Repetir pergunta** acrescenta um novo turno
à thread atual; para uma comparação controlada, abra uma nova conversa e repita a
mesma sequência de entrada. Os eventos anteriores continuam inspecionáveis na página.

O perfil usa controles explícitos: selecione o formato, confirme e guarde.
Use bloco 2 ou 3 para entregá-lo à síntese. Digitar uma preferência no chat não a
salva automaticamente. **Esquecer preferência** impede sua seleção futura.
O banco em `runtime/memory.sqlite3` não é versionado nem distribuído.

## Alternativa Colab e experimentos sem API

- `notebooks/401_conversa_e_contexto.ipynb`: bloco 1.
- `notebooks/402_memoria_persistente_e_compartilhada.ipynb`: blocos 2 e 3.

Ambos contêm todas as funções e dados em células; nenhum Flask, Drive mount,
download do repositório ou notebook anterior é necessário. Instalação exige rede;
experimentos locais de memória não chamam LLM. As células de conversa exigem API.
No Colab, reexecute a célula da função após editar. SQLite dura enquanto o arquivo
do runtime existir; não há promessa de persistência após descarte da VM.

## Conferir o ambiente

```powershell
python -m pip check
```

Os cartões de exercício já estão incluídos no aplicativo e nos notebooks.

## Limites do exemplo

Identidade fixa U100/loja_demo no Flask local; não é serviço autenticado multiusuário.
Memória persistida são turnos concluídos e estado do caso, não checkpoints por nó.
Uma interrupção não retoma ferramentas intermediárias. O merge do quadro ocorre
depois da junção; CAS de SQLite rejeita duas gravações da mesma versão de conversa.
O orçamento conta uma estimativa de mensagens e schemas com reserva; não é tokenizer
do provedor. Fatos operacionais e políticas são reconsultados. Não há ações reais,
resumo gerado por LLM, busca de episódios ou exclusão de backups/traces passados.
