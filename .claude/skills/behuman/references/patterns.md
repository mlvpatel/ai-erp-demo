# Pattern reference: why each rule exists

Adapted from Wikipedia's "Signs of AI writing" (WikiProject AI Cleanup). That page is a detection guide for spotting undisclosed AI text on Wikipedia. This file inverts it into a generation guide and drops the MediaWiki-only mechanics (wikitext syntax, category and template hallucination, AfC submission templates, permissions gaming, canned user pages) that have no analogue outside a wiki. Everything else generalises.

`wordlists.md` holds the verbatim term lists. This file holds the reasoning, the examples, and the calibration.

## The root cause

Models infer the next token from a large corpus, so output regresses to the mean: the most statistically likely result across the widest variety of cases. Training data describes notable subjects in positive, important-sounding language, so the model drops the specific, unusual, statistically rare fact and substitutes the generic, positive, statistically common one.

The source's image for this is exact. "Inventor of the first train-coupling device" becomes "a revolutionary titan of industry". It is like shouting louder and louder that a portrait shows a uniquely important person while the portrait itself fades from a sharp photograph into a blurry sketch. The subject becomes simultaneously less specific and more exaggerated.

Every content rule in this skill is a corollary. Every surface rule is downstream of formatting habits inherited from Markdown-first system prompts and from readmes, listicles, and sales decks in training data.

## 1. Content padding

### Undue emphasis on significance, legacy, and broader trends

The model puffs up the subject by asserting that arbitrary aspects of it represent or contribute to something broader. There is a distinct, easily identifiable repertoire for this.

> The Statistical Institute of Catalonia was officially established in 1989, marking a pivotal moment in the evolution of regional statistics in Spain. [...] The founding of Idescat represented a significant shift toward regional statistical independence [...] This initiative was part of a broader movement across Spain to decentralize administrative functions and enhance regional governance.

Three sentences, one fact: it was established in 1989. Everything else asserts importance without supplying anything a reader could use to judge importance.

The same reflex invents debates. A subject "has generated debate about authenticity, consent, and the psychological effects of..." when no such debate is documented. It applies to the most mundane subjects, including etymologies and population counts, and it sometimes arrives with a hedging preamble that concedes the subject is minor before arguing for its significance anyway.

> During the Spanish colonial period, the name Bakunutan was hispanized to Bacnotan [...] This etymology highlights the enduring legacy of the community's resistance and the transformative power of unity in shaping its identity.

Fix: state the fact, delete the significance claim. If importance is real, the fact demonstrates it.

**Domain reflex, biology.** Writing about a species, models over-emphasise connections to the broader ecosystem even when tenuous or generic, and belabour conservation status and preservation efforts even when the status is unknown and no serious efforts exist.

> Currently, there is no specific conservation assessment for Lethrinops lethrinus by the IUCN. However, the general health of the Lake Malawi ecosystem is crucial for the survival of this and other endemic species. Factors such as overfishing, pollution, and habitat destruction could potentially impact their populations.

Every clause after the first is generic filler that would apply to any lake species anywhere. This is A11.

### Canned emphasis on notability, attribution, and media coverage

Models act as though the way to establish that something matters is to hit the reader over the head with claims that it matters, usually by listing what *kinds* of sources covered it rather than what those sources said. This is more common in output from 2025 onward, and models asked to write encyclopedically will echo the exact wording of Wikipedia's notability guidelines.

> The subject has been profiled in multiple high-quality, independent, and widely-read outlets [...] These sources provide significant, substantial, secondary coverage, not trivial mentions or press releases.

Note what is absent: any statement of what the coverage actually reported. Fix: summarise the content of the coverage, or cut it.

The social-media variant is idiosyncratic enough to be near-diagnostic, and was uncommon before roughly 2024:

> The mall maintains a strong digital presence, particularly on Instagram, where it actively shares the latest updates and events.

### Superficial analysis via participial tail

An "-ing" clause bolted onto a sentence end to editorialise. These are almost always unsupported synthesis.

> As of the April 2008 census, the population of Douera stood at approximately 56,998 inhabitants, creating a lively community within its borders. Situated in the central-north region of the country, Douera enjoys close proximity to the capital city, Algiers, further enhancing its significance as a dynamic hub of activity and culture.

The census figure is real. "Creating a lively community" and "further enhancing its significance" are inferences the source cannot support.

Retrieval-augmented models make this worse, not better. They attach the invented analysis to a named real source, producing "Roger Ebert highlighted the lasting influence" regardless of whether Ebert said anything close. That crosses from padding into fabricated attribution.

Fix: cut the tail, or replace it with a claim you can source.

### Promotional and advertisement-like language

Models struggle to hold a neutral tone even when explicitly prompted to. Output drifts toward travel-guide or press-release voice, and this happens when rewriting as well as when generating. An edit claiming to have "removed promotional tone" can introduce it.

> Nestled within the breathtaking region of Gonder in Ethiopia, Alamata Raya Kobo stands as a vibrant town with a rich cultural heritage [...] offers visitors a fascinating glimpse into the diverse tapestry of Ethiopia.

For companies and people the register shifts to corporate:

> CEO Allan Kilavuka emphasized the airline's commitment to sustainability, customer focus, and Africa's prosperity through responsible corporate practices.

Calibration: not all promotional writing is AI-generated, and humans have written press releases for a century. The tell is that models reuse the *same* promotional phrases regardless of topic. Older models such as GPT-4 are blatantly positive; newer ones are subtler and avoid overt superlatives, so keyword matching alone catches less than it used to.

### Vague attribution and overgeneralisation

Three distinct failures share this space. A claim attributed to no traceable source ("industry reports suggest", "experts argue"). One or two sources presented as a consensus ("reviewers noted", citing one reviewer). And a closed list implied to be open, with "such as" before an enumeration the sources give no indication is partial.

> Due to its unique characteristics, the Haolai River is of interest to researchers and conservationists. Efforts are ongoing to monitor its ecological health [...]

Which researchers, and which efforts. If you cannot name them, the sentence is not a fact.

### Outline-shaped challenges-and-future closers

A formulaic paragraph: concessive opener, vague challenges, vaguely positive or speculative resolution. Usually at the end of a piece with a rigid outline, often with a separate "Future Prospects" section.

> Despite its industrial and residential prosperity, Korattur faces challenges typical of urban areas, including[...] With its strategic location and ongoing initiatives, Korattur continues to thrive as an integral part of the Ambattur industrial zone, embodying the synergy between industry and residential living.

The target is the formula, not the topic. Naming a specific, sourced difficulty is good writing. The formula is what reads as machine output.

### Treating a generic title as a proper noun

Opening as though the subject were a defined entity rather than a concept.

> Catchment area (health) refers to the geographic area from which a health facility [...]
> The "List of songs about Mexico" is a curated compilation of musical works [...]

Fix: write about the thing the way someone who knows it would introduce it.

## 2. Syntax

### Avoidance of plain is and has

Models systematically swap copulas for fancier verbs. One study documented a drop of over 10% in the frequency of "is" and "are" in academic writing in 2023, with no comparable change beforehand, and the same effect appears when GPT-3.5 is asked merely to "revise the following sentence". The pattern is most visible in AI copyedits, which "improve" plain text into this register:

> **Before:** Gallery 825 on La Cienega Boulevard, which was purchased in 1958, is LAAA's exhibition arm for contemporary art. There are four individual gallery spaces
> **After:** Gallery 825 on La Cienega Boulevard serves as LAAA's exhibition space for contemporary art. The gallery features four separate spaces

Nothing was gained. Two plain verbs became two marketing verbs.

Newer output elaborates further: "ventured into politics as a candidate" for "was a candidate", "began his career as" for "was", "holds the distinction of being" for "is".

The lead-sentence variant substitutes "refers to" for "is", framing the piece as being about the word rather than the thing.

Exception, stated explicitly in the source: this does not apply to "has" in the past perfect. "Has been featured" is ordinary English.

### Negative parallelism

Output that reads as though correcting a misconception the reader never held. "Not only X but also Y", "It's not just X, it's Y". Humans use this, especially in myth-busting writing, but models reach for it reflexively.

> This choice of language is not only dismissive but also unnecessarily harsh and confrontational.
> That's not just a sourcing issue—it's a systemic bias.
> Kusama's self-portrait is not a mirror but a portal: not a representation of self, but a mechanism for its constant reinvention.

A stronger form denies the first characteristic outright: "It's not..., it's...", "no..., no..., just...". The reversed form, "X rather than Y", is particularly common in Grok output.

Budget it at one per piece, and only where the contrast informs.

### Rule of three

Grouping in threes by default, from "adjective, adjective, adjective" to three parallel clauses to three bullets. Models use it to make superficial analysis look comprehensive.

> They blur boundaries between life and data, raising philosophical questions about identity, authenticity, and what it means to "live on" through algorithms.

A real list has as many items as it has. If the content has two, write two.

### Elegant variation

Generative models carry a repetition penalty, which pushes them to cycle synonyms for one referent rather than repeat a word. The effect is measurable when comparing pre-2023 and post-2023 text.

> In the challenging climate of Soviet artistic constraints, Yankilevsky, alongside other non-conformist artists, faced obstacles in expressing their creativity freely.

The same people become "non-conformist artists", then "these artists", then "the Russian émigré". Plain repetition is clearer.

Calibration: this is a weak signal about non-native English speakers. Italian schools, for instance, teach avoidance of word repetition as a matter of style.

## 3. Formatting

Most of these derive from system prompts that instruct models to format in Markdown, plus training data heavy in readmes, fan wikis, how-tos, sales pitches, slide decks, and listicles.

**Title case headings.** "Impact of Technology and Digitalization" instead of sentence case.

**Boldface overuse.** Scattered bolded phrases in a key-takeaways style, or bolding every instance of a chosen term. Some newer models now carry instructions against this.

**Inline-header vertical lists.** `**Bold Label:** description`, used to fake structure onto what should be prose. A genuine list of comparable items is fine; the tell is fragmenting paragraphs into labelled stubs. A variant omits the punctuation entirely, running the label straight into the text.

**Emoji as structure.** Emoji in front of headings or bullets as decoration. Now rarer than in 2025 but still seen.

**Unnecessary small tables.** A two-column table for something that is a sentence. "The market was valued at approximately USD 2.1 billion in 2024" does not need a table.

**Skipped heading levels and thematic breaks before every heading.** Both are artifacts of Markdown-to-other-format conversion rather than deliberate structure.

**Curly quotes.** ChatGPT and DeepSeek typically produce curly quotation marks and apostrophes, sometimes inconsistently mixed with straight ones. This is a weak signal on its own: Word, macOS, iOS, LanguageTool, and Chicago-style publishing all produce curly quotes legitimately. Gemini and Claude typically do not produce them. Worth managing only when house style calls for one or the other.

## 4. Punctuation

**Em dashes.** Models use them more than nonprofessional human writing of the same genre, and use them where a comma, colon, or parenthesis would be natural, often to fake a punchy rhetorical beat. The sharpest single detail: AI em dashes are usually *spaced* on both sides, contrary to the typographic conventions most human em-dash users know. That is why the spaced form is an absolute prohibition while the closed form is merely capped.

The signal is strongest in combination with other indicators, and is more common in discussion-style writing than in article prose. Because the pattern became notorious, some vendors now suppress em dashes deliberately, notably in GPT-5.1.

**Section symbol.** Never use `§`. Write "section". This is a hard preference rather than an AI-tell judgment.

## 5. Assistant residue

Text that leaks from helpful-assistant mode into the deliverable.

- Collaborative filler: "I hope this helps", "Of course!", "Certainly!", "You're absolutely right!", "Would you like me to...", "Let me know if you'd like a more detailed breakdown".
- Instructions addressed to the prompter rather than the reader: "Here's a template you can copy and paste", "Delete this section before submission".
- Knowledge-cutoff and gap disclaimers, covered below.
- Unfilled placeholders and date stubs.
- Section-summary reflexes on short pieces.
- Didactic hedging: "it's important to note that".
- Refusal boilerplate, which should never reach delivered content at all.

### The gap-speculation failure

Worth separating out, because it is the most damaging item in this group. When a retrieval-capable model cannot find sources, it does not stop. It announces the gap and then speculates into it:

> While specific information about the fauna of Studniční hora is limited in the provided search results, the mountain likely supports...

Both halves are unfounded. The model does not know that the information is undocumented, only that it did not find it, and everything after "likely" is invention. For people this surfaces as "maintains a low profile" or "keeps personal details private", presented as biography when it is inference from absence.

The honest moves are: say you could not find it, or leave it out. Never both announce a gap and fill it.

## 6. Sourcing

- Every citation must point to something that actually says what the text claims. A citation's presence is not evidence of its accuracy.
- Never claim "several sources" or "multiple studies" for one or two.
- Book citations need a page number, or a real quote, or a URL. A general-topic book cited without a page is unverifiable, and the source flags exactly this pattern: plausible book, no page, no link, claim not actually in it.
- Never fabricate DOIs, ISBNs, or URLs. Hallucinated DOIs often resolve, but to unrelated articles, which makes them worse than broken ones. The source's worked example cites two IEEE papers that do not exist, one attributed to an author who had been dead for thirty years.
- Never define a reference and leave it uncited.
- Broken links clustered in new work, especially links absent from web archives, indicate fabrication rather than ordinary link rot.

## 7. Tool artifact hygiene

When quoting, paraphrasing, or summarising fetched content, check for citation and tracking debris that other AI tools leave in their own output. If a source page was itself AI-generated, this rides along in copied text. The complete token inventory is in `wordlists.md` section 12.

Note the limit of this signal: a `utm_source=chatgpt.com` parameter proves a tool touched the URL, not that a tool wrote the surrounding prose. People use AI to find citations for text they wrote themselves.

## 8. Calibration: what this skill must not do

The source page is unusually careful about false positives, and that care is load-bearing. Three findings constrain how hard these rules can be applied.

**Detection is genuinely hard.** A 2025 study found human ability to distinguish LLM text from human text no better than chance. Another found recognition rates of 57% for AI texts and 64% for human texts. Heavy LLM users reach about 90%, meaning roughly one false positive in ten. Automated detectors beat chance but carry non-trivial error rates and are defeated by paraphrasing, markup changes, and unseen models.

**The distributions are converging.** Human speech and writing are measurably influenced by LLM exposure, evident in spoken content by 2024 and confirmed for semantics and word choice since. Every year, "sounds like AI" means less.

**Some tells point backwards.** Hedges, intensifiers, superlatives, definitive statements, and isolated wordy constructions are all *more* common in genuine human writing than in AI output. Model text smooths toward a non-committal middle. A writer who hedges casually in one paragraph and states something flatly in the next is displaying a human signature, and a rule set that scrubs both directions destroys it.

This is why the X rules override the A rules. The failure mode of over-applying this skill is real, produces worse prose, and is harder to notice than the failure mode it corrects, because it feels like compliance.

Specifically, none of the following is a defect: perfect grammar; formal, academic, or technical register; mixed casual and formal voice; prose that is both clinical and warm; a bullet list; a bolded term; a table; a transition word; a correctly formatted citation; a clean document structure. Several of these are listed in the source as indicators that are ineffective or that point the opposite way from what people assume.

One occurrence of one listed word is not a tell. Density and co-occurrence are the tell. Where there is one, there are usually others, and it is the cluster you are removing, not the word.
