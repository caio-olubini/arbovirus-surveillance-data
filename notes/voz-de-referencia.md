# A voz de referência

Dois trechos escritos por Caio, guardados aqui por um motivo mecânico: eles são
a régua contra a qual o `scripts/checar_estilo_relatorio.py` calibra as medidas
de ritmo de frase. Sem uma referência em disco, essas medidas ficavam só sendo
reportadas, sem limite — e limite inventado a partir de intuição é chute com
cara de critério.

**Este arquivo é uma AMOSTRA, e é medido como tal.** Conta o que estiver FORA do
bloco de código no fim: os dois trechos abaixo. Todo o comentário está lá
dentro, porque comentário que ficasse fora passaria a fazer parte da amostra —
e um comentário explicando os vícios cita os vícios, que é o jeito mais rápido
de contaminar a própria medida. O teste
`test_amostra_de_voz_passa_no_proprio_linter` existe para pegar isso: se alguém
acrescentar prosa fora do bloco, ele quebra.

Não é texto do manuscrito e não entra em `texts/`, que é documentado como
*English manuscript drafts*. Este arquivo é português, é sobre COMO escrever, e
é insumo de ferramenta.

Os dois trechos foram escritos antes de existir qualquer regra de estilo neste
repositório, e por isso valem como amostra: não foram ajustados para agradar ao
contador.

## Trecho 1 — sobre o BERT e extração de características

Em vez de tratar palavras como blocos isolados num dicionário, o BERT lê frases
inteiras em ambas as direções, aprendendo como o sentido de cada termo muda de
acordo com o contexto ao redor. Quando usamos o modelo apenas para extração de
*features*, congelamos essa arquitetura pré-treinada e a aproveitamos como um
leitor altamente especializado: o texto bruto passa pela rede e sai convertido
em vetores numéricos densos, gerando uma espécie de impressão digital matemática
do significado da frase. Com essa bagagem semântica já destilada em coordenadas
precisas, conseguimos treinar classificadores muito mais leves e rápidos sem
precisar reensinar o modelo do zero, preservando as sutilezas da linguagem sem
carregar o custo computacional de um ajuste fino completo.

## Trecho 2 — sobre sensores urbanos e amortecimento térmico

Para entender como a vegetação urbana amortece os extremos climáticos locais,
instalamos sensores em vinte pontos da cidade para registrar a temperatura a
cada quinze minutos durante um ano inteiro. Em vez de olhar apenas para médias
mensais estáticas, tratamos essas medições como uma série temporal contínua —
uma espécie de eletrocardiograma do ambiente que acompanha oscilações hora a
hora. Ao decompor esses dados entre o ciclo diário do sol e as tendências
sazonais de fundo, conseguimos isolar o impacto direto da copa das árvores:
mesmo nas semanas mais quentes, as áreas verdes atrasam o pico de calor em quase
quatro horas em relação ao asfalto vizinho, revelando um mecanismo de
amortecimento térmico que resumos estáticos tradicionais simplesmente
esconderiam.

## Notas de calibração

```
MEDIDO NA AMOSTRA (579 palavras, 25 frases, 9 parágrafos)
    palavras por frase      mediana 19 · p90 39 · MÁXIMA 59 · desvio 12,6
    orações por frase       nenhuma frase acima de 4
    travessão               6,91 por mil palavras
    voz passiva             3,45 por mil palavras
    adjetivo inflado        0
    muleta                  0
    hedge                   0


O QUE ISSO DECIDE, E O QUE ISSO NÃO DECIDE

1. O TAMANHO DE FRASE NÃO PODE SER GATE, e a amostra prova isso sozinha: a
   frase mais longa da referência tem 59 palavras, e o limite antigo era 45. O
   linter reprovava a própria voz que se quer produzir. A troca por aninhamento
   não foi preferência de estilo; foi consertar um contador que apontava para o
   lado errado.

2. O ANINHAMENTO PODE SER GATE, e a amostra confirma: nenhuma frase da
   referência passa de quatro orações. O limite de 6 já estava calibrado nos
   relatórios; a referência mostra que ele não aperta demais.

3. TRAVESSÃO NÃO PODE SER GATE. A referência dá 6,91 por mil — DENTRO da faixa
   dos quatro relatórios (5,87 a 7,79). A hipótese de que o travessão era vício
   de escrita de máquina não sobreviveu à medição: quem escreve à mão usa tanto
   quanto.

4. VOZ PASSIVA NÃO PODE SER GATE, e pelo motivo oposto ao que se esperava: a
   referência usa MAIS passiva (3,45) que todos os quatro relatórios (1,04 a
   1,75). Se há desvio, é dos relatórios usarem de menos.

5. AS DENSIDADES NÃO PODEM SER CALIBRADAS AQUI. Zero ocorrências em 579
   palavras NÃO é evidência de que a referência evita essas coisas — é o que se
   espera ver mesmo que a taxa verdadeira dela seja igual à dos relatórios: a
   0,5 por mil, 579 palavras comportam 0,29 ocorrências, e ver zero é o
   resultado mais provável. Amostra pequena não calibra evento raro. Os limites
   de muleta, adjetivo e hedge continuam vindo dos quatro relatórios, e
   continuam sendo ALVO declarado, não medição da voz.


O QUE OS DOIS TRECHOS TÊM EM COMUM

- A metáfora faz trabalho, não enfeite. "Impressão digital matemática",
  "eletrocardiograma do ambiente" — cada uma substitui uma explicação de três
  linhas por uma imagem que quem lê já tem na cabeça.
- O número vem dentro de uma consequência. Não "o atraso foi de quatro horas",
  e sim "as áreas verdes atrasam o pico de calor em quase quatro horas em
  relação ao asfalto vizinho". O dado só aparece junto do que ele significa.
- Nenhuma frase pede licença: o texto afirma, não anuncia que vai afirmar.
- O adjetivo escolhe. "Leves e rápidos" contrasta com "ajuste fino completo";
  "médias mensais estáticas" contrasta com "série temporal contínua".


O QUE OS TRECHOS NÃO SÃO

Os dois estão em primeira pessoa do plural ("instalamos", "tratamos",
"conseguimos") e explicam um método próprio. Os relatórios de literatura do
repositório são impessoais e descrevem trabalho alheio. A referência calibra
RITMO e ANINHAMENTO — medidas sobre o corpo da frase, não sobre quem fala. Ela
não autoriza o relatório a virar primeira pessoa.
```
