"""Gera dois notebooks com código em células, dados embutidos e mesmos exercícios."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ["config", "events", "tools", "retrieval", "memory", "context", "agents", "graph"]
EXERCISES = json.loads((ROOT / "exercises.json").read_text(encoding="utf-8"))


def cell(kind, text, tag=None):
    item = {"cell_type": kind, "metadata": {}, "source": text.strip().splitlines(keepends=True)}
    # splitlines leaves the last line un-terminated: nbformat permits it.
    if kind == "code":
        item.update(execution_count=None, outputs=[])
    if tag:
        item["metadata"]["tags"] = [tag]
    return item


def canonical(module):
    source = (ROOT / f"{module}.py").read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    for node in reversed(ast.parse(source).body):
        if isinstance(node, ast.ImportFrom) and node.module in MODULES + ["__future__"]:
            del lines[node.lineno - 1:node.end_lineno]
    source = "".join(lines).replace("Path(__file__).resolve().parent", "Path.cwd()")
    if module == "config":
        source = source[:source.index("def _compute_build_id")] + '\ndef build_id():\n    return "notebook-local"\n'
    if module in ("tools", "retrieval"):
        fn = "_read_json" if module == "tools" else "_load_json"
        tree = ast.parse(source)
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn)
        lines = source.splitlines(keepends=True)
        lines[node.lineno-1:node.end_lineno] = [f'def {fn}(name):\n    return json.loads(json.dumps(DATA[name]))\n']
        source = "".join(lines)
    return source


def build():
    js_path = ROOT / "static" / "app.js"
    js = js_path.read_text(encoding="utf-8")
    js = re.sub(r"const exercises = \[[\s\S]*?\];", lambda _: "const exercises = " + json.dumps(EXERCISES, ensure_ascii=False, indent=2) + ";", js, count=1)
    js_path.write_text(js, encoding="utf-8")
    data = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "dados").glob("*.json")}
    pins = " ".join(l.strip() for l in (ROOT.parent / "requirements.txt").read_text().splitlines() if l.strip() and not l.startswith("#"))
    mapping = {}
    for number, title, blocks in [("401", "Conversa e contexto", ["1"]), ("402", "Memória persistente e compartilhada", ["2", "3"])]:
        cells = [cell("markdown", f"# AIE - Agents, Multi-Agents & Interoperability - Aula 04\n## {number} · {title}\nPaulo Caixeta · profpaulo.oliveira@fiap.com.br\n\nAssistente de Atendimento e Operações. Código completo nas células; nenhum arquivo de Aula 03 ou Flask é necessário. Dados sintéticos. Salvar estado não treina o modelo. Execute em ordem; depois altere uma função, reexecute sua célula e repita a pergunta. O runtime do Colab é temporário; SQLite só sobrevive enquanto o arquivo existir."),
                 cell("code", "%pip install -q " + pins, "setup"),
                 cell("code", "import json\nDATA = json.loads(" + repr(json.dumps(data, ensure_ascii=False)) + ")")]
        indices = {}
        for module in MODULES:
            cells.append(cell("markdown", f"## Código · {module}.py\nMesmas funções do aplicativo local. Reexecute esta célula após editar."))
            indices[module] = len(cells) + 1
            cells.append(cell("code", canonical(module)))
        cells += [cell("markdown", "## API (somente para conversar com a LLM)\nNão execute esta célula se quiser apenas os experimentos locais abaixo. O modelo é configurável; erros não viram demonstração silenciosamente."),
                  cell("code", 'import getpass\nimport os\nif not os.getenv("OPENAI_API_KEY"):\n    os.environ["OPENAI_API_KEY"] = getpass.getpass("Chave de API: ")\nprint("Modelo:", configured_model())', "live"),
                  cell("code", 'thread_id = new_thread()\n\ndef ask(question, mode="short", strategy="structured", stage="fixed_rag"):\n    events, emit = collect_events()\n    output = run_case(question, stage=stage, thread_id=thread_id, memory_mode=mode, strategy=strategy, emit=emit)\n    print(output["answer"])\n    for event in events:\n        if event["type"].startswith("memory_") or event["type"] == "context_budget":\n            print(event["type"], event["data"])\n    return output, events'),
                  cell("markdown", "## Experimento local · estado, janela e persistência\nSem API; banco temporário isolado. Não é avaliação de resposta de LLM."),
                  cell("code", 'import tempfile\nfrom pathlib import Path\nwith tempfile.TemporaryDirectory() as directory:\n    db = Path(directory) / "demo.sqlite3"\n    t = new_thread(db_path=db)\n    s = update_case_state({}, "P100. Não abrir chamado ainda", "P100")\n    save_turn(t, 0, s, {"request": "P100. Não abrir chamado ainda"}, db_path=db)\n    save_turn(t, 1, s, {"request": "Obrigado"}, db_path=db)\n    save_turn(t, 2, s, {"request": "E agora?"}, db_path=db)\n    reopened = load_thread(t, db_path=db)\n    for strategy in ("none", "recent", "structured"):\n        print(strategy, select_context(reopened, strategy))')]
        for exercise in EXERCISES:
            if exercise["id"][0] not in blocks:
                continue
            cells.append(cell("markdown", f'## {exercise["id"]} · {exercise["title"]}\n**Funções:** {exercise["where"]}.\n\n**Alteração:** {exercise["change"]}\n\n**Observe:** {exercise["observe"]}\n\n**Discuta:** {exercise["discuss"]}\n\nRegistre pergunta, mudança, evidência antes/depois e uma limitação. No Colab, use as funções abaixo; os botões são a alternativa no app.'))
            cells.append(cell("code", f'output, events = ask({exercise["question"]!r}, mode={exercise["mode"]!r})', "live"))
        if number == "402":
            cells += [cell("markdown", "## Experimento local · confirmação, correção, isolamento e expiração\nO perfil exige confirmação. Nenhum modelo é chamado. Cada função reabre o SQLite."),
                      cell("code", 'from datetime import timedelta\nwith tempfile.TemporaryDirectory() as directory:\n    db = Path(directory) / "profile.sqlite3"\n    now = utc_now()\n    p = save_profile("concise", True, 0, db_path=db, now=now)\n    print("salvo", p)\n    print("outro usuário", read_profile(user_id="U200", db_path=db, now=now))\n    p = save_profile("detailed", True, p["version"], db_path=db, now=now)\n    print("corrigido", p)\n    print("expirado", read_profile(db_path=db, now=now + timedelta(days=31)))\n    print("revogado", revoke_profile(p["version"], db_path=db))'),
                      cell("markdown", "## Experimento local · conflito e propriedade\nA segunda proposta usa deliberadamente uma versão obsoleta. No grafo, as branches escrevem campos distintos e o coordenador faz o merge após a junção."),
                      cell("code", 'board = {"version": 0}\nboard = merge_shared(board, "logistics", {"logistics": {"status": "consultado"}}, 0)\nfor role, proposal, version in [("resolution", {"resolution": {}}, 0), ("logistics", {"permissions": "all"}, 1)]:\n    try:\n        merge_shared(board, role, proposal, version)\n    except ValueError as error:\n        print("rejeitado:", error)\nboard = merge_shared(board, "resolution", {"resolution": {"status": "consultado"}}, board["version"])\nprint(board)'),
                      cell("markdown", "## Controles equivalentes aos botões do app\nExecute uma linha por vez e inspecione os eventos da próxima pergunta."),
                      cell("code", '# Perfil de U100 neste runtime; execute só a ação desejada.\n# p = read_profile()\n# save_profile("concise", True, p["version"])\n# thread_id = new_thread()\n# output, events = ask("Qual o status de P100?", mode="long")\n# revoke_profile(read_profile()["version"])\n# output, events = ask("Qual o status de P100?", mode="shared")')]
        cells.append(cell("markdown", "## Limites e conclusão\nSQLite salva turnos concluídos, não a execução de cada nó. O perfil não concede autorização, e thread_id não autentica usuários. Identidade fixa de demonstração; não hospedar como aplicação multiusuário. A estimativa inclui schemas e reserva, mas não é tokenizer do provedor. Os fatos atuais vêm das ferramentas; regras vêm do RAG. Memória não cria ferramenta de ação.\n\nDefenda em 3–5 linhas o que lembrar, reconsultar, compartilhar e esquecer."))
        for i, c in enumerate(cells):
            c["id"] = f"a04-{number}-{i+1:02}"
        notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}}, "nbformat": 4, "nbformat_minor": 5}
        name = f"{number}_" + ("conversa_e_contexto" if number == "401" else "memoria_persistente_e_compartilhada") + ".ipynb"
        (ROOT / "notebooks").mkdir(exist_ok=True)
        (ROOT / "notebooks" / name).write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        mapping[name] = indices
    (ROOT / "notebooks" / "cell_map.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    print(json.dumps(mapping, indent=2))


if __name__ == "__main__":
    build()
