# Modelagem por tópicos como feature de notícia

Referências para a família `topicos`: modelos de tópicos (LDA, NMF, STM, BERTopic, topicos dinâmicos/neurais) cuja **saída** (proporção por tópico, tópico dominante, termos por tópico) é usada como feature de previsão, regressão ou vigilância; a escolha do **número de tópicos** (coerência, estabilidade, perplexidade); modelos com o **tempo dentro** (tópicos dinâmicos, deriva de vocabulário); a **estabilidade/reprodutibilidade** dos tópicos; e o **domínio** mais próximo do nosso — notícia de doença, texto curto e português.

O funil da busca fecha: **3935** candidatos únicos → **1440** passaram nas regras objetivas + relevância → **48** selecionados com PDF verificado (os outros 1392 passantes estão listados um a um em `search.json`). Detalhe completo em [`search.json`](./search.json); a trilha por regra objetiva em `rejected_by_gate`.

> **Nota de escopo:** os arquivos 45 e 46 (Zika discourse; Influenza/Twitter) usam **mídia social** como corpus, não notícia; foram mantidos por serem o precedente de doença + tópico + multilíngue mais próximo do nosso recorte de texto curto.

## A saída do modelo de tópicos como variável de previsão

| File | Citation | What it does here |
|------|----------|-------------------|
| `01_rodrigues_2017_learning_supervised_topic_models.pdf` | Rodrigues et al., *IEEE Transactions on Pattern Analysis and Machine Intelligence* (2017) [doi:10.1109/tpami.2017.2648786](https://doi.org/10.1109/tpami.2017.2648786) | Modelo de topico supervisionado que aprende topicos e, ao mesmo tempo, o alvo (classificacao/regressao) a partir de rotulos ruidosos — a saida do topico entra direto no modelo preditivo (eixo feature). |
| `02_chuluunsaikhan_2020_incorporating_deep_learning_news.pdf` | Chuluunsaikhan et al., *Agriculture* (2020) [doi:10.3390/agriculture10110513](https://doi.org/10.3390/agriculture10110513) | Noticias sobre preco de suino: topicos de noticia viram features de uma rede profunda que preve o preco — topic model de noticia como covariavel de previsao (eixo feature). |
| `03_chiu_2024_predicting_icu_readmission_electronic.pdf` | Chiu et al., *Journal of Clinical Medicine* (2024) [doi:10.3390/jcm13185503](https://doi.org/10.3390/jcm13185503) | BERTopic sobre prontuarios gera features de topico alimentando um LSTM para prever readmissao em UTI (eixo feature). |
| `04_ghosh_2017_temporal_topic_modeling_assess.pdf` | Ghosh et al., *Scientific Reports* (2017) [doi:10.1038/srep40841](https://doi.org/10.1038/srep40841) | Topicos temporais que associam tendencias de noticia a surtos de doenca infecciosa — o precedente mais direto de noticia x doenca ao longo do tempo (eixos feature, tempo, dominio). |
| `05_mcgough_2017_forecasting_zika_incidence_latin.pdf` | McGough et al., *PLoS neglected tropical diseases* (2017) [doi:10.1371/journal.pntd.0005295](https://doi.org/10.1371/journal.pntd.0005295) | Combina noticia, busca e redes sociais para prever incidencia de Zika na America Latina em 2016 (eixo dominio). |
| `06_peinelt_2020_tbert_topic_models_bert.pdf` | Peinelt et al., *Proceedings of the conference - Association for Computational Linguistics. Meeting* (2020) [doi:10.18653/v1/2020.acl-main.630](https://doi.org/10.18653/v1/2020.acl-main.630) | Junta modelo de topicos e BERT como features para similaridade semantica — hibrido topico+contextual (eixo feature/metodos). |
| `08_hughes_2020_assessment_prediction_model_antidepressant.pdf` | Hughes et al., *JAMA Network Open* (2020) [doi:10.1001/jamanetworkopen.2020.5308](https://doi.org/10.1001/jamanetworkopen.2020.5308) | Topicos supervisionados para prever estabilidade de tratamento antidepressivo — saida do topico como preditor clinico (eixo feature). |
| `44_roberts_2019_stm_r_package_structural.pdf` | Roberts et al., *Journal of Statistical Software* (2019) [doi:10.18637/jss.v091.i02](https://doi.org/10.18637/jss.v091.i02) | stm: o pacote R do Structural Topic Model — a prevalencia de cada topico e condicionada a metadados (covariaveis), exatamente o mecanismo 'topico como funcao de metadado' (eixos feature, k). |

## Quantos tópicos: coerência, estabilidade e critérios que discordam

| File | Citation | What it does here |
|------|----------|-------------------|
| `09_gan_2021_selection_optimal_number_topics.pdf` | Gan et al., *Entropy* (2021) [doi:10.3390/e23101301](https://doi.org/10.3390/e23101301) | Como escolher o numero de topicos para LDA (Entropy 2021) — metodos de selecao de k (eixo k). |
| `10_zhao_2015_heuristic_approach_determine_appropriate.pdf` | Zhao et al., *BMC Bioinformatics* (2015) [doi:10.1186/1471-2105-16-s13-s8](https://doi.org/10.1186/1471-2105-16-s13-s8) | Heuristica para determinar o numero apropriado de topicos (BMC Bioinformatics) — selecao de k (eixo k). |
| `11_krasnov_2019_number_topics_optimization_clustering.pdf` | Krasnov et al., *Machine Learning and Knowledge Extraction* (2019) [doi:10.3390/make1010025](https://doi.org/10.3390/make1010025) | Otimizacao do numero de topicos por abordagem de clustering (eixo k). |
| `12_vangara_2021_finding_number_latent_topics.pdf` | Vangara et al., *IEEE Access* (2021) [doi:10.1109/access.2021.3106879](https://doi.org/10.1109/access.2021.3106879) | Escolha do numero de topicos latentes via NMF semantica (eixo k). |
| `13_meaney_2023_quality_indices_topic_model.pdf` | Meaney et al., *BMC Medical Informatics and Decision Making* (2023) [doi:10.1186/s12911-023-02216-1](https://doi.org/10.1186/s12911-023-02216-1) | Indices de qualidade para selecao e avaliacao de modelos de topico: revisao + estudo de caso (eixo k). |
| `14_zheng_2023_adaptive_lda_optimal_topic.pdf` | Zheng et al., *IEEE Access* (2023) [doi:10.1109/access.2023.3308520](https://doi.org/10.1109/access.2023.3308520) | Selecao adaptativa do numero otimo de topicos para identificacao de topico de noticia (eixos k, dominio). |
| `15_terragni_2021_octis_comparing_optimizing_topic.pdf` | Terragni et al., *Conference of the European Chapter of the Association for Computational Linguistics* (2021) [doi:10.18653/v1/2021.eacl-demos.31](https://doi.org/10.18653/v1/2021.eacl-demos.31) | OCTIS: biblioteca para comparar e otimizar modelos de topico (coerencia, k) (eixo k). |
| `16_hoyle_2021_automated_topic_model_evaluation.pdf` | Hoyle et al., *arXiv (Cornell University)* (2021) [doi:10.48550/arxiv.2107.02173](https://doi.org/10.48550/arxiv.2107.02173) | Mostra que as metricas automaticas de coerencia de topico nao acompanham o julgamento humano (NeurIPS) — coerencia x verossimilhanca (eixo k). |
| `17_hoyle_2022_neural_topic_models_broken.pdf` | Hoyle et al., *Findings of the Association for Computational Linguistics: EMNLP (Findings of EMNLP)* (2022) [doi:10.18653/v1/2022.findings-emnlp.390](https://doi.org/10.18653/v1/2022.findings-emnlp.390) | Seguimento de Hoyle 2021: onde a avaliacao de modelos de topico neural falha (eixo k). |
| `18_morstatter_2016_novel_measure_coherence_statistical.pdf` | Morstatter et al., *Proceedings of the conference - Association for Computational Linguistics. Meeting* (2016) [doi:10.18653/v1/p16-2088](https://doi.org/10.18653/v1/p16-2088) | Nova medida de coerencia para modelos de topico estatisticos (ACL 2016) (eixo k). |
| `35_egger_2022_topic_modeling_comparison_lda.pdf` | Egger et al., *Frontiers in Sociology* (2022) [doi:10.3389/fsoc.2022.886498](https://doi.org/10.3389/fsoc.2022.886498) | Comparacao LDA x NMF x Top2Vec x BERTopic (eixo k/metodos). |

## Tópicos que mudam com o tempo

| File | Citation | What it does here |
|------|----------|-------------------|
| `19_greene_2017_exploring_political_agenda_european.pdf` | Greene et al., *Political Analysis* (2017) [doi:10.1017/pan.2016.7](https://doi.org/10.1017/pan.2016.7) | Modelo de topico dinamico aplicado a decadas de agenda parlamentar — assuntos que mudam no tempo (eixo tempo). |
| `20_dieng_2019_dynamic_embedded_topic_model.pdf` | Dieng et al., *arXiv (Cornell University)* (2019) [doi:10.48550/arxiv.1907.05545](https://doi.org/10.48550/arxiv.1907.05545) | DETM: topico dinamico com embeddings, com deriva temporal de topico e vocabulario (eixo tempo). |
| `21_montariol_2021_scalable_interpretable_semantic_change.pdf` | Montariol et al., *Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT)* (2021) [doi:10.18653/v1/2021.naacl-main.369](https://doi.org/10.18653/v1/2021.naacl-main.369) | Deteccao escalavel e interpretavel de mudanca semantica (NAACL) — deriva de vocabulario ao longo do tempo (eixo tempo). |
| `22_meier_2024_topic_modeling_three_decades.pdf` | Meier et al., *Frontiers in Communication* (2024) [doi:10.3389/fcomm.2023.1322498](https://doi.org/10.3389/fcomm.2023.1322498) | Topic model sobre tres decadas de noticia de clima na Dinamarca — noticia x tempo (eixos tempo, dominio). |
| `37_krawczyk_2021_quantifying_online_news_media.pdf` | Krawczyk et al., *Journal of Medical Internet Research* (2021) [doi:10.2196/28253](https://doi.org/10.2196/28253) | Quantifica a cobertura de noticia online sobre COVID-19 e publica o recurso — noticia x tempo (eixos dominio, tempo). |

## Estabilidade e reprodutibilidade dos tópicos

| File | Citation | What it does here |
|------|----------|-------------------|
| `23_rieger_2024_ldaprototype_model_selection_algorithm.pdf` | Rieger et al., *PeerJ Computer Science* (2024) [doi:10.7717/peerj-cs.2279](https://doi.org/10.7717/peerj-cs.2279) | LDAPrototype: algoritmo de selecao de modelo para melhorar a confiabilidade (estabilidade) do LDA (eixo estabilidade). |
| `24_schofield_2016_comparing_apples_apple_effects.pdf` | Schofield et al., *Transactions of the Association for Computational Linguistics* (2016) [doi:10.1162/tacl_a_00099](https://doi.org/10.1162/tacl_a_00099) | Efeito do stemmer nos topicos (TACL): a escolha de pre-processamento muda os topicos — estabilidade/reprodutibilidade (eixo estabilidade). |
| `25_schofield_2017_pulling_out_stops_rethinking.pdf` | Schofield et al., *Conference of the European Chapter of the Association for Computational Linguistics* (2017) [doi:10.18653/v1/e17-2069](https://doi.org/10.18653/v1/e17-2069) | Reavalia a remocao de stopwords em topicos (EACL) — pre-processamento e estabilidade (eixo estabilidade). |
| `26_janssens_2025_comparative_analysis_topic_reduction.pdf` | Janssens et al., *IEEE Access* (2025) [doi:10.1109/access.2025.3638956](https://doi.org/10.1109/access.2025.3638956) | Compara tecnicas de reducao de topicos no BERTopic (eixo estabilidade/k). |
| `27_hecking_2018_topic_modelling_empirical_text.pdf` | Hecking et al., *arXiv (Cornell University)* (2018) [doi:10.48550/arxiv.1806.01045](https://doi.org/10.48550/arxiv.1806.01045) | Validade, confiabilidade e reprodutibilidade de topicos em corpora empiricos (eixo estabilidade). |

## Notícia de doença, texto curto e português

| File | Citation | What it does here |
|------|----------|-------------------|
| `28_melo_2021_comparing_news_articles_tweets.pdf` | Melo et al., *JMIR Public Health and Surveillance* (2021) [doi:10.2196/24585](https://doi.org/10.2196/24585) | Compara noticias e tweets sobre COVID-19 no Brasil com analise de sentimento e modelo de topico — recorte PT/Brasil (eixo dominio). |
| `29_doogan_2023_systematic_review_use_topic.pdf` | Doogan et al., *Artificial Intelligence Review* (2023) [doi:10.1007/s10462-023-10471-x](https://doi.org/10.1007/s10462-023-10471-x) | Revisao sistematica do uso de topicos em texto curto de midia social (eixo dominio, texto curto). |
| `30_zuo_2015_word_network_topic_model.pdf` | Zuo et al., *Knowledge and Information Systems* (2015) [doi:10.1007/s10115-015-0882-z](https://doi.org/10.1007/s10115-015-0882-z) | Word network topic model: solucao geral para texto curto e desequilibrado (eixo dominio). |
| `31_weisser_2022_pseudo_document_simulation_comparing.pdf` | Weisser et al., *Computational Statistics* (2022) [doi:10.1007/s00180-022-01246-z](https://doi.org/10.1007/s00180-022-01246-z) | Simulacao de pseudo-documento comparando LDA, GSDMM e GPM em texto curto e esparso (eixo dominio, k). |
| `32_wu_2020_short_text_topic_modeling.pdf` | Wu et al., *Conference on Empirical Methods in Natural Language Processing (EMNLP)* (2020) [doi:10.18653/v1/2020.emnlp-main.138](https://doi.org/10.18653/v1/2020.emnlp-main.138) | Topicos para texto curto com quantizacao da distribuicao de topico (EMNLP) (eixo dominio). |
| `33_muthusami_2024_investigating_topic_modeling_techniques.pdf` | Muthusami et al., *Scientific Reports* (2024) [doi:10.1038/s41598-024-61738-4](https://doi.org/10.1038/s41598-024-61738-4) | Investiga tecnicas de topico em texto curto de dominios diversos (Sci Rep) (eixo dominio). |
| `34_grootendorst_2022_bertopic_neural_topic_modeling.pdf` | Grootendorst, *arXiv (Cornell University)* (2022) [doi:10.48550/arxiv.2203.05794](https://doi.org/10.48550/arxiv.2203.05794) | BERTopic: o modelo de topico neural com c-TF-IDF que domina o uso atual (eixo dominio/metodos). |
| `36_albalawi_2020_topic_modeling_methods_short.pdf` | Albalawi et al., *Frontiers in Artificial Intelligence* (2020) [doi:10.3389/frai.2020.00042](https://doi.org/10.3389/frai.2020.00042) | Topicos para texto curto: analise comparativa de metodos (eixo dominio). |
| `39_bianchi_2021_cross_lingual_contextualized_topic.pdf` | Bianchi et al., *Conference of the European Chapter of the Association for Computational Linguistics* (2021) [doi:10.18653/v1/2021.eacl-main.143](https://doi.org/10.18653/v1/2021.eacl-main.143) | Topicos contextualizados cross-lingual com zero-shot (EACL) — topicos multilingues (eixo dominio/multilingue). |
| `45_kagashe_2017_enhancing_seasonal_influenza_surveillance.pdf` | Kagashe et al., *Journal of Medical Internet Research* (2017) [doi:10.2196/jmir.7393](https://doi.org/10.2196/jmir.7393) | Analise de topico de tweets sobre medicamentos para melhorar a vigilancia de influenza (eixo dominio, texto curto). |
| `46_pruss_2019_zika_discourse_americas_multilingual.pdf` | Pruss et al., *PLoS ONE* (2019) [doi:10.1371/journal.pone.0216922](https://doi.org/10.1371/journal.pone.0216922) | Analise de topico multilingue do discurso de Zika nas Americas (PLoS ONE) — doenca + multilingue (eixo dominio). |
| `47_tizzoni_2020_impact_news_exposure_collective.pdf` | Tizzoni et al., *PLoS Computational Biology* (2020) [doi:10.1371/journal.pcbi.1007633](https://doi.org/10.1371/journal.pcbi.1007633) | Impacto da exposicao a noticia na atencao coletiva durante a epidemia de Zika de 2016 (eixo dominio). |
| `48_feng_2020_topic_modeling_short_texts.pdf` | Feng et al., *IEEE Access* (2020) [doi:10.1109/access.2020.2973207](https://doi.org/10.1109/access.2020.2973207) | Topicos para texto curto via embedding de palavra e correlacao de documentos (IEEE Access) (eixo dominio). |

## Modelos e métodos de tópico (base metodológica)

| File | Citation | What it does here |
|------|----------|-------------------|
| `07_zhang_2022_neural_topic_modelling_better.pdf` | Zhang et al., *Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT)* (2022) [doi:10.18653/v1/2022.naacl-main.285](https://doi.org/10.18653/v1/2022.naacl-main.285) | Estudo empirico: topico neural e melhor que clustering contextual? Compara metodos em varios corpora (eixo k). |
| `38_dieng_2020_topic_modeling_embedding_spaces.pdf` | Dieng et al., *Transactions of the Association for Computational Linguistics* (2020) [doi:10.1162/tacl_a_00325](https://doi.org/10.1162/tacl_a_00325) | ETM: topicos em espaco de embeddings (TACL) (eixo metodos). |
| `40_zhao_2021_topic_modelling_meets_deep.pdf` | Zhao et al., *International Joint Conference on Artificial Intelligence* (2021) [doi:10.24963/ijcai.2021/638](https://doi.org/10.24963/ijcai.2021/638) | Revisao de modelos de topico neurais (IJCAI) (eixo metodos). |
| `41_wu_2024_survey_neural_topic_models.pdf` | Wu et al., *Artificial Intelligence Review* (2024) [doi:10.1007/s10462-023-10661-7](https://doi.org/10.1007/s10462-023-10661-7) | Revisao de modelos de topico neurais: metodos, aplicacoes e desafios (eixo metodos). |
| `42_srivastava_2017_autoencoding_variational_inference_topic.pdf` | Srivastava et al., *arXiv (Cornell University)* (2017) [doi:10.48550/arxiv.1703.01488](https://doi.org/10.48550/arxiv.1703.01488) | NVI: inferencia variacional por autoencoder para modelos de topico (ICLR) (eixo metodos). |
| `43_nguyen_2015_improving_topic_models_latent.pdf` | Nguyen et al., *Transactions of the Association for Computational Linguistics* (2015) [doi:10.1162/tacl_a_00140](https://doi.org/10.1162/tacl_a_00140) | Melhora modelos de topico com representacoes de palavras latentes (TACL) (eixo metodos). |

## Download notes (this checkout)

- Todos os 48 PDFs foram verificados com `file` = `PDF document`.
- 13 artigos relevantes ficaram de fora por falta de PDF OA obtível (ScienceDirect/ACM/IEEE e repositórios com bot-wall): ver `rejected_by_gate.pdf` em `search.json`.
- Contagens de citação em `references.csv` são do OpenAlex (coluna `Extra` traz a do Semantic Scholar quando disponível).
- A coleta usou `curl --cacert logs/macos-ca-bundle.pem` (o proxy corporativo quebra o TLS do Python).