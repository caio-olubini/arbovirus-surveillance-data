# Dense embeddings as text features

## From sparse counts to dense vectors

Feature extraction from text once meant sparse counts. A document became a vector
over its vocabulary, weighted by term frequency and inverse document frequency,
and similarity meant shared wording (Salton et al., 1975;
doi:10.1145/361219.361220). The space is wide and the coordinates are words, so
two texts that mean the same thing in different words are orthogonal.
Distributional word embeddings replaced the coordinates with learned dense
vectors, so that related words sit close (Mikolov et al., 2013;
arXiv:1301.3781; Pennington et al., 2014; doi:10.3115/v1/d14-1162), and a
document vector could be assembled from them (Le and Mikolov, 2014;
arXiv:1405.4053). Contextual encoders then removed the fixed meaning per word
(Peters et al., 2018; doi:10.18653/v1/N18-1202; Devlin et al., 2019;
doi:10.18653/v1/N19-1423). They return one vector per token, not per document,
so the text still has to be reduced to the single vector a downstream model
consumes, and the sentence-embedding literature is the body of work on that
reduction, where the choices below are argued (Reimers and Gurevych, 2019;
doi:10.18653/v1/d19-1410; Li et al., 2020; doi:10.18653/v1/2020.emnlp-main.733;
Gao et al., 2021; doi:10.18653/v1/2021.emnlp-main.552).

## The choices, against the alternatives

**The encoder.** BERTimbau is the base Portuguese encoder, pre-trained on the
brWaC web corpus and evaluated on similarity and entailment among other tasks
(Souza et al., 2020; doi:10.1007/978-3-030-61377-8_28). Its clinical sibling
BioBERTpt draws its vocabulary from clinical notes and SciELO abstracts, which
fits patient records rather than press copy (Schneider et al., 2020;
doi:10.18653/v1/2020.clinicalnlp-1.7). Multilingual encoders such as E5 and
BGE-M3, and dedicated Portuguese sentence encoders (Gomes et al., 2024;
arXiv:2407.19527), are the natural comparators. Public benchmarks rank encoders
on retrieval, clustering and classification, so the choice can rest on evidence
rather than reputation (Muennighoff et al., 2023;
doi:10.18653/v1/2023.eacl-main.148).

**The pooling.** The encoder's last hidden state is averaged over the article's
real tokens, masked by the attention mask, and scaled to unit length. The
alternatives are the `[CLS]` token, the pooler head, max pooling and learned
attention pooling. `[CLS]` carries the next-sentence-prediction signal and the
pooler head is a linear layer that the standard sentence-embedding recipes
discard, while masked mean is the pooling those recipes use (Reimers and
Gurevych, 2019; Li et al., 2020). Masking is the load-bearing part: averaging
over padding positions would make a vector depend on what it was batched with.
The choice is not held constant across encoders, because for some of them it is
not a choice: the dense embedding of BGE-M3 is defined as its `[CLS]` token, so
reading it with a mean would measure a configuration nobody uses. Each encoder is
read the way its authors published it.
Mean pooling has a documented weakness. A vanilla encoder is anisotropic, with
token vectors crowded into a narrow cone, so unrelated sentences look alike
(Ethayarajh, 2019; doi:10.18653/v1/d19-1006). The fixes are to map the pooled
vectors onto a smoother latent space (Li et al., 2020) or to fine-tune the
encoder contrastively (Gao et al., 2021). The first is applied as one
configuration of the comparison (Su et al., 2021; arXiv:2103.15316; Huang et al.,
2021; doi:10.18653/v1/2021.findings-emnlp.23); the second is not, because
fine-tuning would make the encoder a trained model of this corpus and the
comparison fixes it as frozen.

**The fine-tuning decision.** The encoder stays frozen and pinned to a revision,
so the same corpus yields the same vectors on any machine and at any later date.
Fine-tuning on this corpus would make the encoder a trained model of dengue
news, which is a different representation from the one the comparison fixes.

**The aggregation.** A week holds many articles, so the per-article vectors are
pooled a second time: the mean for the level of the week, together with the count
of articles that entered it. The alternatives at this level are concatenation, a
principal component, which is a modelling decision left open, or a topic model,
which assigns each document a mixture over latent themes (Blei et al., 2003) and
whose neural variants cluster document embeddings and label the clusters
(Grootendorst, 2022; arXiv:2203.05794). Topic models are more interpretable than
768 unnamed dimensions and coarser in time. Turning news into document embeddings
for reuse has a data-descriptor precedent (Kriesch and Lasser, 2025;
doi:10.1038/s41597-025-05422-w).

A second dispersion statistic within the week was published and has been
withdrawn. For L2-normalized article vectors the parallel-axis identity on the
unit sphere gives

    ‖std‖² = (1/n) Σᵢ ‖vᵢ − m‖² = 1 − ‖m‖²

so the norm of the per-dimension standard deviation is an exact deterministic
function of the mean the table already carries, and it was measured to agree with
it to 1.6e-06 over the rows that aggregate more than one article. No scalar
dispersion of unit vectors escapes the identity, since the mean pairwise cosine
distance is 1 − ‖m‖² as well. The dispersion of a week's coverage is therefore
read as being carried by the mean rather than as a feature of its own.

```
ENCODE(article)
    ids, mask ← tokenize(title + body)      # truncate to the encoder's window
    n_tokens  ← length before truncation    # kept per article, not discarded
    H ← encoder.last_hidden_state(ids)      # (n_tokens, dim)
    v ← Σᵢ maskᵢ · Hᵢ / Σᵢ maskᵢ             # masked mean over real tokens
    return v / ‖v‖                          # unit vector

POOL(week, location)
    V ← { ENCODE(a) : a published in week, scoped to location }
    if V is empty: emit nothing             # absence, not a zero vector
    return mean(V), |V|                     # mean, article count
```

## Where this instance sits

The combination is the conservative end of the design space: frozen encoders, the
pooling the standard recipes use, and no contrastive training. That placement is
measurable on this corpus. Mean pooling without fine-tuning is the baseline the
sentence-embedding literature improves on, and here it leaves 39.0% of the 4,369
articles truncated at the encoder's 512-token window. One configuration of the
comparison applies the anisotropy correction and needs no labels to do it; none of
them is fine-tuned, so the comparison can attribute a difference to the encoder
rather than to a training run.

A single configuration would leave a null result uninterpretable, since "this
representation loses" could not be separated from "this particular encoder was too
weak". The instance is therefore published as a bracket of six unsupervised
configurations — the Portuguese standard, its anisotropy-corrected form, a
multilingual model, a `[CLS]`-pooled model, a title-only floor, and an encoder
trained specifically for Portuguese with a shorter window — read as a range rather
than as a point. Two of them carry a declared risk: their pretraining cutoff is
undocumented, so protocol 00's temporal validation is what decides how far their
numbers can be trusted.

The content axis reads weak in the base configuration. The leading component of
the national weekly means explains 20.9% of its own variance and correlates 0.105
with weekly cases, against 0.297 for the number of articles in the week. The
coefficient is a magnitude rather than a signed value, because a principal
component's sign is unidentifiable — negating it leaves the component unchanged —
and so is not comparable across configurations. Those numbers describe one corpus,
one configuration and one target series, and they are not the protocol comparison —
which is the reason the bracket exists, and the reason the comparison carries a
shuffled-text control. They fix the question it has to answer: whether a dense
reading of the news earns its dimensions over counting the articles that carry it.
