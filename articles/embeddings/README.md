# Embeddings - dense text embeddings as news features

Reference library for the `embeddings` family: dense sentence/document encoders used as fixed
feature vectors (for time-series / regression / downstream models), the pooling and normalization
choices that make those vectors usable (mean/CLS, whitening, SIF, first-component removal), and the
news/journalism & multilingual/Portuguese application domain.

Gates (frozen before the search): year >= 2015; citations >= 10 if age >= 2y else >= 3;
venue h-index >= 30 OR venue name matches the ACL/EMNLP/... allow-list; a **verified** PDF
(`file` = "PDF document"). Full audit trail in [`search.json`](./search.json); Zotero-importable
index in [`references.csv`](./references.csv).

Funnel: **1057** unique candidates -> **429** passed the objective rules -> **23** selected with a
verified PDF (the other 406 passers are listed individually in `search.json`, each with a reason).

## Sentence / document encoders as features

| File | Citation | What it does here |
|------|----------|-------------------|
| `01_reimers_2019_sentence_bert.pdf` | Reimers et al., *Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing and the 9th International Joint Conference on Natural Language Processing (EMNLP-IJCNLP)* (2019) [doi:10.18653/v1/d19-1410](https://doi.org/10.18653/v1/d19-1410) | Canonical sentence encoder (SBERT); bi-encoder producing fixed sentence vectors - the default encoder-as-feature backbone. |
| `02_gao_2021_simcse.pdf` | Gao et al., *Conference on Empirical Methods in Natural Language Processing (EMNLP)* (2021) [doi:10.18653/v1/2021.emnlp-main.552](https://doi.org/10.18653/v1/2021.emnlp-main.552) | Contrastive sentence embeddings (SimCSE); dropout-as-positive-pair training yields isotropic sentence vectors. |
| `03_conneau_2017_infersent.pdf` | Conneau et al., *Conference on Empirical Methods in Natural Language Processing (EMNLP)* (2017) [doi:10.18653/v1/d17-1070](https://doi.org/10.18653/v1/d17-1070) | InferSent; the classic study of pooling (max/mean/last) for fixed sentence representations used as downstream features. |
| `04_cer_2018_universal_sentence_encoder.pdf` | Cer et al., *Conference on Empirical Methods in Natural Language Processing: System Demonstrations (EMNLP)* (2018) [doi:10.18653/v1/d18-2029](https://doi.org/10.18653/v1/d18-2029) | Universal Sentence Encoder; ready-made document/sentence feature vector. |
| `05_feng_2022_labse.pdf` | Feng et al., *Annual Meeting of the Association for Computational Linguistics (ACL)* (2022) [doi:10.18653/v1/2022.acl-long.62](https://doi.org/10.18653/v1/2022.acl-long.62) | LaBSE; language-agnostic sentence embedding over 109 languages - multilingual/short-text baseline. |
| `06_reimers_2020_multilingual_distillation.pdf` | Reimers et al., *Conference on Empirical Methods in Natural Language Processing (EMNLP)* (2020) [doi:10.18653/v1/2020.emnlp-main.365](https://doi.org/10.18653/v1/2020.emnlp-main.365) | Makes a monolingual sentence encoder multilingual via knowledge distillation - recipe for a PT-capable encoder. |
| `07_ni_2022_sentence_t5.pdf` | Ni et al., *Findings of the Association for Computational Linguistics: ACL 2022* (2022) [doi:10.18653/v1/2022.findings-acl.146](https://doi.org/10.18653/v1/2022.findings-acl.146) | Sentence-T5; studies encoder size and pooling for embedding quality. |
| `19_shen_2018_baseline_needs_more_love_pooling.pdf` | Shen et al., *Annual Meeting of the Association for Computational Linguistics (ACL)* (2018) [doi:10.18653/v1/p18-1041](https://doi.org/10.18653/v1/p18-1041) | Baseline Needs More Love; isolates the effect of pooling mechanisms on simple word-embedding models - pooling evidence. |
| `20_pagliardini_2018_sent2vec_compositional_ngram.pdf` | Pagliardini et al., *Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (NAACL-HLT)* (2018) [doi:10.18653/v1/n18-1049](https://doi.org/10.18653/v1/n18-1049) | Sent2Vec; unsupervised sentence embeddings from compositional n-gram features - cheap encoder-as-feature. |
| `21_wieting_2015_universal_paraphrastic_sentence.pdf` | Wieting et al., *arXiv (Cornell University)* (2015) [doi:10.48550/arxiv.1511.08198](https://doi.org/10.48550/arxiv.1511.08198) | Towards Universal Paraphrastic Sentence Embeddings; early universal encoder via paraphrase supervision. |

## Pooling & normalization (mean/CLS, whitening, SIF, first-component removal)

| File | Citation | What it does here |
|------|----------|-------------------|
| `08_yin_2018_dimensionality_word_embedding.pdf` | Yin et al., *arXiv (Cornell University)* (2018) [doi:10.48550/arxiv.1812.04224](https://doi.org/10.48550/arxiv.1812.04224) | On the Dimensionality of Word Embedding; shows the top principal component is a mean/anisotropy direction - motivates removing it. |
| `09_mu_2017_all_but_the_top.pdf` | Mu et al., *arXiv (Cornell University)* (2017) [doi:10.48550/arxiv.1702.01417](https://doi.org/10.48550/arxiv.1702.01417) | All-but-the-Top; subtracts mean and top principal components to isotropize embeddings - the remove-first-component recipe. |
| `10_su_2021_whitening_sentence_representations.pdf` | Su et al., *arXiv (Cornell University)* (2021) [doi:10.48550/arxiv.2103.15316](https://doi.org/10.48550/arxiv.2103.15316) | Whitening sentence representations; linear whitening that decorrelates embedding dimensions. |
| `11_arora_2017_sif_sentence_embeddings.pdf` | Arora et al., *International Conference on Learning Representations* (2017) [link](https://openreview.net/pdf?id=SyK00v5xx) | SIF (Arora et al.); frequency-weighted average + first-singular-direction removal - the tough-to-beat unsupervised baseline. |
| `12_li_2020_bert_flow_sentence_embeddings.pdf` | Li et al., *Conference on Empirical Methods in Natural Language Processing (EMNLP)* (2020) [doi:10.18653/v1/2020.emnlp-main.733](https://doi.org/10.18653/v1/2020.emnlp-main.733) | BERT-flow; diagnoses anisotropy of BERT embeddings and fixes it with a normalizing flow. |

## Multilingual & Portuguese grounding

| File | Citation | What it does here |
|------|----------|-------------------|
| `13_pires_2019_how_multilingual_mbert.pdf` | Pires et al., *Annual Meeting of the Association for Computational Linguistics (ACL)* (2019) [doi:10.18653/v1/p19-1493](https://doi.org/10.18653/v1/p19-1493) | How Multilingual is Multilingual BERT?; cross-lingual transfer analysis - grounding for multilingual feature reuse. |
| `14_yang_2020_multilingual_use.pdf` | Yang et al., *Annual Meeting of the Association for Computational Linguistics: System Demonstrations (ACL Demo)* (2020) [doi:10.18653/v1/2020.acl-demos.12](https://doi.org/10.18653/v1/2020.acl-demos.12) | Multilingual Universal Sentence Encoder; 16-language encoder (incl. Portuguese) for cross-lingual retrieval. |

## Domain: news / journalism text as a surveillance signal

| File | Citation | What it does here |
|------|----------|-------------------|
| `15_kim_2019_weekly_ili_news.pdf` | Kim et al., *BMC Bioinformatics* (2019) [doi:10.1186/s12859-019-2894-2](https://doi.org/10.1186/s12859-019-2894-2) | Weekly ILI prediction from news with SVM - news text turned into features predicts week-to-week ILI change. |
| `16_kim_2021_outbreak_media_ml.pdf` | Kim et al., *Scientific Reports* (2021) [doi:10.1038/s41598-021-83926-2](https://doi.org/10.1038/s41598-021-83926-2) | Outbreak prediction from media articles with ML - country-scale news-text-to-signal pipeline. |
| `17_gautam_2025_attention_news_outbreak.pdf` | Gautam et al., *Big Data and Cognitive Computing* (2025) [doi:10.3390/bdcc9110291](https://doi.org/10.3390/bdcc9110291) | Attention-driven deep learning over news text for disease-outbreak prediction (recent, 2025). |
| `18_jang_2019_word2vec_cnn_news.pdf` | Jang et al., *PLoS ONE* (2019) [doi:10.1371/journal.pone.0220976](https://doi.org/10.1371/journal.pone.0220976) | Word2vec + CNN over news articles - the classic dense word-vector feature pipeline. |
| `22_ghosh_2017_temporal_topic_news_disease.pdf` | Ghosh et al., *Scientific Reports* (2017) [doi:10.1038/srep40841](https://doi.org/10.1038/srep40841) | Temporal topic modeling linking news trends to infectious disease - domain evidence for news as a surveillance signal. |
| `23_huang_2018_public_opinions_diseases_news_media.pdf` | Huang et al., *Journal of Medical Internet Research* (2018) [doi:10.2196/10047](https://doi.org/10.2196/10047) | Public opinions toward diseases from news media (infodemiology) - domain grounding on news-media surveillance. |

## Download notes (this checkout)

- All 23 PDFs verified with `file` = `PDF document`.
- **SBERT** (`01_...`): OpenAlex `primary_location.source` is null for the ACL record; venue
  confirmed from the ACL Anthology (EMNLP-IJCNLP 2019), matching the `EMNLP` allow-list.
- **Jang 2019** and **Arora 2017 (SIF)**: no OA PDF link in OpenAlex; PDFs obtained from PLoS ONE and
  the OpenReview PDF respectively (verified with `file`).
- **Yin 2018 / Mu 2017 / Su 2021 / Wieting 2015**: OpenAlex indexes the arXiv records (source h-index
  760), so they pass the venue gate on h-index; the peer-reviewed venues are NeurIPS 2018, ICLR 2018,
  and ICLR 2016 respectively.
- Citation counts are OpenAlex `cited_by_count`; Semantic Scholar counts are systematically higher and
  are recorded in the `Extra` column of `references.csv`.

## Query provenance

4 seed queries (from the family definition) + 21 follow-up OpenAlex queries + a DOI-resolution lookup
and a title lookup for the selected set. Semantic Scholar's search endpoint returned HTTP 429
throughout (no key); per-DOI lookups were used for the citation cross-check. See `search.json` for every
query, its URL, and its hit count.
