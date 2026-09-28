import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = name => fs.readFileSync(path.join(root, name), "utf8").replaceAll("\r\n", "\n");
const source = value => value.trim().split("\n").map(line => `${line}\n`);
const md = value => ({cell_type:"markdown", metadata:{}, source:source(value)});
const code = value => ({cell_type:"code", execution_count:null, metadata:{}, outputs:[], source:source(value)});
// Only imports between local modules and file/config loading change in Colab.
const canonical = name => read(name).replace(/^from (?:__future__|config|tools|agents|retrieval|events) import .*\n/gm, "");
const data = Object.fromEntries(["corpus_manifest", "chunks", "orders", "shipments"].map(name => [name, JSON.parse(read(`dados/${name}.json`))]));
const dataCell = code(`import json\nDATA = json.loads(r'''${JSON.stringify(data)}''')`);
dataCell.metadata = {jupyter:{source_hidden:true}, cellView:"form"};
let config = canonical("config.py").replace('Path(__file__).resolve().parent', 'Path.cwd()');
config = config.slice(0, config.indexOf("def _compute_build_id")) + 'def build_id() -> str:\n    return "notebook-local"\n';
const setup = code(config + `
load_environment()
if not key_configured():
    try:
        from google.colab import userdata
        os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY") or ""
    except (ImportError, Exception):
        pass
if not key_configured():
    from getpass import getpass
    os.environ["OPENAI_API_KEY"] = getpass("OPENAI_API_KEY: ")
`);
const operational = canonical("tools.py")
  .replace(/DATA_DIR = .*?SHIPMENTS = _read_json\("shipments.json"\)/s, 'ORDERS = DATA["orders"]\nSHIPMENTS = DATA["shipments"]');
const retrieval = canonical("retrieval.py")
  .replace(/DATA_DIR = .*?(?=def eligible_chunks)/s, '')
  .replace('_load_json("corpus_manifest.json")', 'DATA["corpus_manifest"]')
  .replace('_load_json("chunks.json")', 'DATA["chunks"]');
const agents = canonical("agents.py");
const splitFixed = agents.indexOf("def _fixed_prompt");
const splitAgentic = agents.indexOf("def synthesize_agentic");
const splitCitations = agents.indexOf("def resolve_citations");
const specialists = agents.slice(0, splitFixed);
const fixed = agents.slice(splitFixed, splitAgentic);
const agentic = agents.slice(splitAgentic, splitCitations);
const citations = agents.slice(splitCitations);
const graph = canonical("graph.py");
const install = code("%pip install -q " + fs.readFileSync(path.join(root, "..", "requirements.txt"), "utf8").split(/\r?\n/).filter(line => line && !line.startsWith("#")).join(" "));
const header = (number, title) => md(`# ${number} · ${title}
### AIE — Agents, Multi-Agents & Interoperability · Aula 03
#### Prof. Paulo Caixeta — profpaulo.oliveira@fiap.com.br

Assistente de Atendimento e Operações. Este notebook contém seu próprio ponto de partida; execute as células em ordem.
O código usa API real. O .env do PC não existe automaticamente no Colab: carregue-o no runtime, configure Secrets ou use getpass. Não salve a chave nas células.
Outputs estão limpos; serão produzidos ao executar. O build local é identificado como notebook-local.
`);
const ask = code(`history = []
def ask(message, history=None, stage="baseline"):
    events, emit = collect_events()
    output = run_case(message, stage=stage, history=history, emit=emit)
    print(output["answer"])
    print("Status:", output["status"], "Lacunas:", output["missing_information"])
    for event in events:
        print(event["seq"], event["type"], event["data"].get("node_id", event["data"].get("name", "")))
        if event["type"] == "retrieval_result":
            print(event["data"])
    if history is not None:
        history.extend([{"role":"user", "content":message}, {"role":"assistant", "content":output["answer"]}])
        history[:] = history[-8:]
    return output, events
`);
// The cards come from the app, so edits cannot silently diverge across surfaces.
const exercises = vm.runInNewContext(read("static/app.js").match(/const exercises = (\[[\s\S]*?\]);/)[1]);
const exercise = id => {
  const e = exercises.find(item => item.id === id);
  return md(`## ${e.id} — ${e.title}\n\nEtapa: ${e.stage}. Pergunta: ${e.question}\n\n**Sua alteração.** ${e.where} (célula correspondente acima). ${e.change}\n\nObserve: ${e.observe}\n\nDiscussão: ${e.discuss}\n\nApós editar, reexecute a célula da função e a chamada abaixo: run_case reconstrói o grafo e as ferramentas. Para comparar, mantenha history=None.`);
};
const run = (id, stage) => code(`# Experimento\noutput, events = ask(${JSON.stringify(exercises.find(e=>e.id===id).question)}, stage="${stage}")`);
const common = [install, setup, md("## Código fornecido — dados sintéticos\n\n12 documentos / 24 chunks; cópias do mesmo corpus do app."), dataCell, code(operational + "\n" + canonical("events.py")), code(specialists)];
const cells301 = [header("301", "Grafo e RAG fixo"), ...common,
  md("## Código fornecido — fan-out e junção\n\nA síntese baseline é Python. A lista de origens da aresta aguarda ambas as branches."),
  code(graph), ask, exercise("E1"), run("E1", "baseline"),
  code('print([(e.source, e.target) for e in build_graph("baseline", lambda *a, **k: None).get_graph().edges])'),
  md("## Código fornecido — retrieval\n\nFiltros antes do ranking; similaridade não é confiança nem precedência documental."), code(retrieval),
  exercise("E2"), code('query = build_query("P100 atrasou e não há previsão; o que podemos fazer?", ORDERS["P100"], SHIPMENTS["E100"], get_resolution_options("P100"))\nresult = search_policies(query)\nprint(result["query"])\nfor hit in result["hits"]: print(hit["chunk_id"], hit["score"], hit["text"])'),
  md("## Código fornecido — síntese fixa LLM\n\nA junção passa por retrieve_policies antes de synthesize; uma busca e uma chamada de síntese."), code(fixed),
  exercise("E3"), run("E3", "fixed_rag"),
  code('print(resolve_citations("Candidata [D99-C9]", {}))\nhistorical = next(c for c in CHUNKS if c["chunk_id"] == "D12-C2")\nprint(resolve_citations("P100 chegará em dois dias [D12-C2]", {"D12-C2": historical}))\nprint(historical["text"])'),
  md("O ID histórico existe, mas isso não fundamenta um prazo atual. Registre quatro linhas: pergunta; mudança; evento/trecho; limitação. Lab 1: 55 minutos.")];
// Baseline needs citation resolution even before retrieval is introduced.
cells301[6].source = source(specialists + "\n" + citations);
const cells302 = [header("302", "RAG como ferramenta"), ...common,
  md("## Código fornecido — checkpoint de retrieval e síntese fixa"), code(retrieval + "\n" + fixed + "\n" + citations),
  md("## Código fornecido — busca decidida pelo agente\n\nA síntese escolhe quando buscar. O orçamento é compartilhado por todas as tool_calls, inclusive na mesma resposta."), code(agentic),
  md("## Código fornecido — grafo externo\n\nA busca é ferramenta dentro de synthesize; não há nó externo de retrieval nesta etapa."), code(graph), ask,
  exercise("E4"), code('for question in ["Qual o status do meu pedido P100?", "P100 atrasou; posso receber compensação automática?"]:\n    output, events = ask(question, stage="agentic_rag")'),
  exercise("E5"), run("E5", "agentic_rag"),
  md("Se o modelo acertar na primeira busca, registre isso. O teste test_agentic_budget_and_exhaustion, no app, usa um fake explícito para demonstrar o bloqueio sem depender do comportamento da API."),
  exercise("E6"), code('for k in (3, 5):\n    print("top_k", k)\n    for hit in search_policies("expresso_demo fila exceção", top_k=k)["hits"]:\n        print(hit["chunk_id"], hit["score"], hit["text"])'), run("E6", "agentic_rag"),
  md("## Registro final\n\nPreencha etapa | query | chunks | resultado | limite. Escolha uma arquitetura e justifique. Lab 2: 55 minutos; desafio: 30 minutos. Para conversa, passe history=history; comparações usam history=None."), code("# Limpar contexto da conversa\nhistory.clear()")];
for (const [name, cells] of [["301_grafo_e_rag_fixo", cells301], ["302_rag_como_ferramenta", cells302]]) {
  cells.forEach((cell, i) => {cell.id = `cell-${i}`;});
  const notebook = {cells, metadata:{kernelspec:{display_name:"Python 3", language:"python", name:"python3"}, language_info:{name:"python",version:"3.12"}}, nbformat:4, nbformat_minor:5};
  fs.writeFileSync(path.join(root, "notebooks", `${name}.ipynb`), JSON.stringify(notebook, null, 2) + "\n");
}
console.log("Notebooks gerados das funções e exercícios canônicos.");
