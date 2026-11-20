# artigos — extração estruturada de eventos epidemiológicos por LLM

Familia `llm-extracao` do workflow de referencia. 10 artigos selecionados (passaram nos gates objetivos e com PDF verificado).

Gates: ano >= 2019; citacoes >= 10 (>= 2 anos) ou >= 3 (recentes); venue h-index >= 30 OU nome contendo ACL/EMNLP/NAACL/EACL/COLING/TACL/NeurIPS/ICLR/ICML/AAAI/JMLR; PDF obrigatorio. Ver `search.json` para contagens e a lista completa de reprovados/considerados.

| Arquivo | Citacao | O que faz aqui |
|---|---|---|
| `01_consoli_2025_epidemiological_kg_who_don.pdf` | Consoli et al., 2025 | Extrai um grafo de conhecimento epidemiologico do Disease Outbreak News da OMS — caso central de extracao estruturada de campos (doenca, local, data) a partir de relatorio oficial. |
| `02_algaradi_2025_mortality_extraction_llm.pdf` | Al-Garadi et al., 2025 | LLM para extrair contagens de mortalidade de texto; avaliacao contra anotacao humana — modelo de extracao numerica com validacao. |
| `03_neveditsin_2025_structured_output_robustness_json.pdf` | Neveditsin et al., 2025 | Robustez de saida estruturada (JSON-schema) em LLM — fundamenta a escolha de geracao restringida por schema. |
| `04_li_2024_aegpt_adverse_events_surveillance.pdf` | Li et al., 2024 | Extracao de eventos adversos por LLM em vigilancia; comparacao com baseline — mostra o padrao LLM vs. baseline neural. |
| `05_mortezaagha_2026_schema_constrained_biomedical_extraction.pdf` | Mortezaagha et al., 2026 | Extracao biomedica restringida por schema — evidencia recente de schema-constrained generation para campos. |
| `06_schmidt_2024_llm_data_extraction_systematic_reviews.pdf` | Schmidt et al., 2024 | Revisao sistematica de extracao de dados por LLM; panorama de metodos e avaliacao (precision/recall por campo). |
| `07_shamsabadi_2024_llm_scientific_information_extraction_virology.pdf` | Shamsabadi et al., 2024 | Extracao de informacao cientifica em virologia por LLM — dominio proximo (virologia) com avaliacao. |
| `09_abbood_2020_eventepi_nlp_event_based_surveillance.pdf` | Abbood et al., 2020 | Baseline NLP (nao-LLM) de vigilancia baseada em eventos — referencia de comparacao pre-LLM. |
| `10_dewandaru_2020_event_geoparser_numerical_argument_indonesian.pdf` | Dewandaru et al., 2020 | Event Geoparser: extracao de argumentos numericos e localizacao (indonesio) — baseline de extracao de numeros/local, multilingue. |
| `11_kim_2020_classification_online_sources_infectious_disease.pdf` | Kim et al., 2020 | Classificacao de fontes online de doencas infecciosas por aprendizado de maquina — baseline neural de triagem de noticia. |

Total: 10 PDFs. Contagens fecham: total_unique_hits=916, mechanical_gate_passers=291 (=10 selected + 281 considered_not_selected), sum(rejected_by_gate)=625.
