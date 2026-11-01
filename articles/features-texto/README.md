# Features manuais de texto — dicionario, regras e contagens

Referencias para a extracao de features de texto por contagem/regra (o braco 01 do pipeline de noticias),
nao por embeddings densos. Cobre: vigilancia baseada em eventos (EBS) com dicionario/gazetteer/regras/
NER sobre noticia; extracao explicita de contagens (casos, mortes) e contagem cumulativa vs semanal;
estatisticas de superficie do texto (comprimento, densidade lexical, legibilidade); e o dominio de noticia
em portugues/multilingue com agregacao semanal e geografica.

O funil da busca fecha: 177 passaram nas regras objetivas = 35 selecionados com PDF verificado + 142 considerados e nao selecionados. Detalhe completo em `search.json`; a trilha por regra objetiva esta em `rejected_by_gate`.

## Dicionario, gazetteer e regras (EBS)

| File | Citation | What it does here |
|------|----------|-------------------|
| `03_collier_2008_biocaster_text_mining_rumors.pdf` | Collier et al., *Bioinformatics* (2008) [doi:10.1093/bioinformatics/btn534](https://doi.org/10.1093/bioinformatics/btn534) | BioCaster: mineracao de texto de rumores de noticia com ontologia e dicionario de termos de doenca. |
| `04_meng_2022_biocaster_2021_news_outbreaks.pdf` | Meng et al., *Bioinformatics* (2022) [doi:10.1093/bioinformatics/btac497](https://doi.org/10.1093/bioinformatics/btac497) | BioCaster 2021: cobertura e classificacao de noticias de surtos apos uma decada. |
| `07_keller_2009_unstructured_event_reports_ebs.pdf` | Keller et al., *Emerg. Infect. Dis.* (2009) [doi:10.3201/eid1505.081114](https://doi.org/10.3201/eid1505.081114) | Extracao de eventos de relatos nao estruturados com features lexicais. |
| `08_collier_2011_cross_lingual_alerting_epidemic.pdf` | Collier et al., *J. Biomed. Semantics* (2011) [doi:10.1186/2041-1480-2-s5-s10](https://doi.org/10.1186/2041-1480-2-s5-s10) | Alerta cross-lingual para noticias epidemicas. |
| `09_collier_2010_unusual_online_outbreak_news.pdf` | Collier et al., *J. Biomed. Semantics* (2010) [doi:10.1186/2041-1480-1-2](https://doi.org/10.1186/2041-1480-1-2) | Deteccao de noticias incomuns de surto online. |
| `15_arsevska_2018_web_monitoring_animal_diseases.pdf` | Arsevska et al., *PLoS ONE* (2018) [doi:10.1371/journal.pone.0199960](https://doi.org/10.1371/journal.pone.0199960) | Monitoramento web de doencas animais (dicionarios de termos veterinarios). |
| `16_you_2021_text_mining_promed_mail.pdf` | You et al., *J. R. Stat. Soc. A* (2021) [doi:10.1111/rssa.12721](https://doi.org/10.1111/rssa.12721) | Mineracao de texto dos e-mails do ProMED. |
| `30_conway_2010_disease_outbreak_event_corpus.pdf` | Conway et al., *J. Med. Internet Res.* (2010) [doi:10.2196/jmir.1323](https://doi.org/10.2196/jmir.1323) | Corpus de eventos de surto de doenca anotado. |
| `32_keller_2009_vocabulary_discovery_geoparsing.pdf` | Keller et al., *BMC Bioinformatics* (2009) [doi:10.1186/1471-2105-10-385](https://doi.org/10.1186/1471-2105-10-385) | Descoberta de vocabulario e geoparsing de noticias. |

## Contagens explicitas (casos/mortes) extraidas de texto

| File | Citation | What it does here |
|------|----------|-------------------|
| `10_ng_2020_nlp_extract_news_event_based.pdf` | Ng et al., *Can. Commun. Dis. Rep.* (2020) [doi:10.14745/ccdr.v46i06a06](https://doi.org/10.14745/ccdr.v46i06a06) | NLP para extrair informacao de noticia em EBS (campos: contagens, local). |
| `11_ganser_2022_global_variations_event_based.pdf` | Ganser et al., *JMIR Public Health Surveill.* (2022) [doi:10.2196/36211](https://doi.org/10.2196/36211) | Variacoes globais em EBS: comparacao de cobertura e contagens. |
| `12_barboza_2013_evaluation_epidemic_intelligence_systems.pdf` | Barboza et al., *PLoS ONE* (2013) [doi:10.1371/journal.pone.0057252](https://doi.org/10.1371/journal.pone.0057252) | Avaliacao de sistemas de inteligencia epidemica (eventos e contagens). |
| `13_barboza_2014_performance_internet_biosurveillance.pdf` | Barboza et al., *PLoS ONE* (2014) [doi:10.1371/journal.pone.0090536](https://doi.org/10.1371/journal.pone.0090536) | Desempenho de biosurveillance baseada na internet. |
| `18_carlson_2023_who_disease_outbreak_news_database.pdf` | Carlson et al., *PLOS Glob. Public Health* (2023) [doi:10.1371/journal.pgph.0001083](https://doi.org/10.1371/journal.pgph.0001083) | Banco de noticias de surtos da OMS (contagens de casos). |
| `19_consoli_2025_knowledge_graph_who_don.pdf` | Consoli et al., *Sci. Data* (2025) [doi:10.1038/s41597-025-05276-2](https://doi.org/10.1038/s41597-025-05276-2) | Grafo de conhecimento a partir de noticias de surtos (WHO DON). |
| `20_madoff_2011_monitoring_dengue_activity.pdf` | Madoff et al., *PLoS Negl. Trop. Dis.* (2011) [doi:10.1371/journal.pntd.0001215](https://doi.org/10.1371/journal.pntd.0001215) | Monitoramento de atividade de dengue a partir de noticias. |

## Superficie do texto (legibilidade / features rasas)

| File | Citation | What it does here |
|------|----------|-------------------|
| `21_pitler_2008_revisiting_readability_text_quality.pdf` | Pitler et al., *EMNLP 2008* (2008) [doi:10.3115/1613715.1613742](https://doi.org/10.3115/1613715.1613742) | Legibilidade como qualidade de texto: features de superficie (Pitler & Nenkova). |
| `22_lee_2021_text_readability_handcrafted_features.pdf` | Lee et al., *EMNLP 2021* (2021) [doi:10.18653/v1/2021.emnlp-main.834](https://doi.org/10.18653/v1/2021.emnlp-main.834) | Legibilidade com features manufaturadas em classificacao de texto. |
| `23_chae_2009_fluency_shallow_structural_features.pdf` | Chae et al., *EACL 2009* (2009) [doi:10.3115/1609067.1609082](https://doi.org/10.3115/1609067.1609082) | Fluencia com features estruturais rasas. |
| `24_crossley_2011_readability_formulas_simplification.pdf` | Crossley et al., *Read. Foreign Lang.* (2011) [doi:10.64152/10125/66657](https://doi.org/10.64152/10125/66657) | Formulas de legibilidade na simplificacao de texto. |

## Dominio: noticia, PT/multilingue, agregacao semanal e geografica

| File | Citation | What it does here |
|------|----------|-------------------|
| `01_freifeld_2007_healthmap_global_media_monitoring.pdf` | Freifeld et al., *JAMIA* (2007) [doi:10.1197/jamia.m2544](https://doi.org/10.1197/jamia.m2544) | Sistema seminal de EBS: classifica e geolocaliza noticias da web para alerta de surtos (regras/dicionario antes de embeddings). |
| `02_brownstein_2008_surveillance_sans_frontieres_healthmap.pdf` | Brownstein et al., *PLoS Med* (2008) [doi:10.1371/journal.pmed.0050151](https://doi.org/10.1371/journal.pmed.0050151) | HealthMap: arquitetura de inteligencia de noticia da internet, multilíngue; referencia de desenho de EBS. |
| `05_valentin_2020_padi_web_multilingual_ebs.pdf` | Valentin et al., *Comput. Electron. Agric.* (2020) [doi:10.1016/j.compag.2019.105163](https://doi.org/10.1016/j.compag.2019.105163) | PADI-web: EBS multilíngue que processa noticias com dicionarios e regras. |
| `06_valentin_2021_padi_web_3_fine_grained_news.pdf` | Valentin et al., *One Health* (2021) [doi:10.1016/j.onehlt.2021.100357](https://doi.org/10.1016/j.onehlt.2021.100357) | PADI-web 3.0: extracao fina (granularidade) de eventos de noticia. |
| `17_milinovich_2013_internet_based_surveillance_review.pdf` | Milinovich et al., *Lancet Infect. Dis.* (2013) [doi:10.1016/s1473-3099(13)70244-5](https://doi.org/10.1016/s1473-3099(13)70244-5) | Revisao de vigilancia baseada na internet. |
| `26_neto_2016_digital_disease_detection_brazil.pdf` | Neto et al., *Rev. Saude Publica* (2016) [doi:10.1590/s1518-8787.2016050006201](https://doi.org/10.1590/s1518-8787.2016050006201) | Deteccao digital de doencas no Brasil a partir de midia. |
| `27_melo_2021_news_tweets_covid_brazil.pdf` | Melo et al., *JMIR Public Health Surveill.* (2021) [doi:10.2196/24585](https://doi.org/10.2196/24585) | Noticias e tweets da COVID no Brasil. |
| `28_schwind_2014_local_media_surveillance_hotspots.pdf` | Schwind et al., *PLoS ONE* (2014) [doi:10.1371/journal.pone.0110236](https://doi.org/10.1371/journal.pone.0110236) | Vigilancia de midia local e deteccao de hotspots. |
| `29_kriesch_2025_geolocated_german_news_dataset.pdf` | Kriesch et al., *Sci. Data* (2025) [doi:10.1038/s41597-025-05422-w](https://doi.org/10.1038/s41597-025-05422-w) | Dataset de noticias alemas geolocalizadas. |

## Validacao e avaliacao (timeliness, granularidade, geoparsing)

| File | Citation | What it does here |
|------|----------|-------------------|
| `14_bahk_2015_timeliness_formal_informal_reporting.pdf` | Bahk et al., *BMC Infect. Dis.* (2015) [doi:10.1186/s12879-015-0885-0](https://doi.org/10.1186/s12879-015-0885-0) | Timeliness de notificacao formal vs informal (validacao temporal). |
| `31_chanlekha_2010_spatial_temporal_granularity_reports.pdf` | Chanlekha et al., *BMC Med. Inform. Decis. Mak.* (2010) [doi:10.1186/1472-6947-10-1](https://doi.org/10.1186/1472-6947-10-1) | Granularidade espaco-temporal de relatos de noticia. |
| `33_hu_2023_location_reference_recognition.pdf` | Hu et al., *ACM Comput. Surv.* (2023) [doi:10.1145/3625819](https://doi.org/10.1145/3625819) | Reconhecimento de referencia de localizacao em texto. |
| `34_syed_2023_geospatre_spatial_relation_geocoding.pdf` | Syed et al., *Cartogr. Geogr. Inf. Sci.* (2023) [doi:10.1080/15230406.2023.2264753](https://doi.org/10.1080/15230406.2023.2264753) | Geocodificacao por relacao espacial (GeoSPaTRe). |
| `35_mutuvi_2020_multilingual_epidemiological_classification.pdf` | Mutuvi et al., *COLING 2020* (2020) [doi:10.18653/v1/2020.coling-main.543](https://doi.org/10.18653/v1/2020.coling-main.543) | Classificacao epidemiologica multilíngue de noticias. |
| `36_gritta_2020_pragmatic_guide_geoparsing_evaluation.pdf` | Gritta et al., *Lang. Resour. Eval.* (2020) [doi:10.1007/s10579-019-09475-3](https://doi.org/10.1007/s10579-019-09475-3) | Guia pragmatico de avaliacao de geoparsing. |
