# Complete word and token lists

Every "words to watch" list from Wikipedia's "Signs of AI writing", reproduced in full, plus the era breakdown and the tool-artifact token inventory. The SKILL.md rules summarise these; this file is the authoritative lookup when you need to check a specific term.

## 1. Undue emphasis on significance, legacy, and broader trends

Maps to R14.

stands as, serves as, is a testament to, is a reminder of, a vital role, a significant role, a crucial role, a pivotal role, a key role, a vital moment, a significant moment, a crucial moment, a pivotal moment, a key moment, underscores its importance, underscores its significance, highlights its importance, highlights its significance, reflects broader, symbolizing its ongoing, symbolizing its enduring, symbolizing its lasting, contributing to the, setting the stage for, marking the, shaping the, represents a shift, marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted

Also: "has sparked debate about", "raised questions about", "has generated debate about", "prompted broader reflection on", "shaped emerging policy discussions about", "a growing recognition of", "part of a broader movement".

Note the hedged variant: an LLM will sometimes concede a subject is of low importance and then argue for its importance anyway. Cut both halves.

## 2. Canned emphasis on notability, attribution, and media coverage

Maps to R15. More common in output from 2025 onward.

independent coverage, local media outlets, regional media outlets, national media outlets, [country name] media outlets, music outlets, business outlets, tech outlets, trade publications, profiled in, written by a leading expert, active social media presence

Also: "maintains a strong digital presence", "significant, substantial, secondary coverage", "widely-read outlets", "high-quality, independent", "repeated national media coverage", naming a source and then attributing your own inference to it.

## 3. Superficial analyses

Maps to A5. Usually arrives as a trailing present participle clause.

highlighting..., underscoring..., emphasizing..., ensuring..., reflecting..., symbolizing..., contributing to..., cultivating..., fostering..., encompassing..., enhancing..., valuable insights, align with, resonate with

Also: demonstrating, illustrating, solidifying, cementing, embodying, capturing, driving, positioning. Retrieval-augmented models attach these to named sources regardless of whether the source supports them; that is fabricated attribution under R7, not merely padding.

## 4. Promotional and advertisement-like language

Maps to A6.

boasts a, vibrant, rich, profound, enhancing, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking, renowned, featuring, diverse array

Also: breathtaking, must-see, seamlessly, thoughtfully, captivates, charm, stunning, dynamic hub, gateway to, value-driven, cutting-edge, state-of-the-art, world-class.

Two documented sub-patterns. First, cultural-heritage reflex: when a subject could conceivably be called heritage, LLMs repeatedly remind the reader of its importance. Second, press-release voice for people and companies, typically "[Executive] emphasized the company's commitment to [values]".

Older models such as GPT-4 skew bluntly positive; newer models are subtler and avoid overt superlatives like "the best", which makes this harder to catch by keyword alone.

## 5. Vague attributions and overgeneralization

Maps to R7.

Industry reports, Observers have cited, Experts argue, Some critics argue, several sources, several publications, such as (placed before a list that implies non-exhaustiveness the sources do not support)

Also: analysts note, scholars agree, researchers treat, it is widely interpreted as, is described in scholarship as, modern researchers view, many have argued, is considered by many.

Three distinct failures live here: no traceable source at all; one source inflated into a plurality; and a closed list presented as an open one.

## 6. Outline-like conclusions about challenges and future prospects

Maps to R12.

Despite its [positive framing]... faces several challenges..., Despite these challenges..., Challenges and Legacy, Future Outlook, Future Directions, Future Prospects, Challenges and Future Directions

The formula: concessive opener, vague challenge list, vaguely positive or speculative resolution. The target is the rigid formula. Naming a specific, sourced difficulty is fine and often necessary.

## 7. AI vocabulary — the core list

Maps to A1. Reproduced exactly as the source gives it, including the parenthetical qualifiers, which matter.

Additionally (especially beginning a sentence), align with, boasts (meaning "has"), bolstered, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (as a verb), interplay, intricate/intricacies, key (as an adjective), landscape (as an abstract noun), meticulous/meticulously, pivotal, robust, showcase, tapestry (as an abstract noun), testament, underscore (as a verb), valuable, vibrant

The source instructs that this section be taken as literally as possible. A word being overused by AI does not imply its synonyms are. Context governs: a literal underscore character, or a tapestry in a piece about weaving, is unremarkable.

### Era breakdown

Which words are hot has shifted across model generations. These are not hard cutoffs, but they tell you whether text reads as earlier or later output, and which words are live tells today versus faded ones.

| Era | Model | Words clustering in that era |
|---|---|---|
| 2023 to mid-2024 | GPT-4 | Additionally, boasts, bolstered, crucial, delve, emphasizing, enduring, garner, intricate/intricacies, interplay, key, landscape, meticulous/meticulously, pivotal, underscore, tapestry, testament, valuable, vibrant |
| Mid-2024 to mid-2025 | GPT-4o | align with, bolstered, crucial, emphasizing, enhance, enduring, fostering, highlighting, pivotal, showcasing, underscore, vibrant |
| Mid-2025 onward | GPT-5 | emphasizing, enhance, highlighting, showcasing, plus the notability and media-coverage vocabulary in section 2 |

Practical consequence: *delve* was the famous 2023 tell and dropped off sharply in 2025, so policing it now is fighting the last war. The current live cluster is emphasizing, enhance, highlighting, showcasing, align with, and the canned-notability set.

### Model-specific

Grok overuses superficially scientific vocabulary: causal, empirical, correlate. It continues to overuse underscore as of 2026, and favours the reversed "X rather than Y" construction.

Gemini and Claude tend to be more concise than ChatGPT and Grok. Focusing on broader context is more characteristic of ChatGPT and Grok than of Gemini and Claude. Gemini and Claude typically do not produce curly quotes; ChatGPT and DeepSeek typically do.

## 8. Avoidance of basic copulatives

Maps to A2.

serves as [a], stands as [a], marks [a], functions as [a], operates as [a], represents [a], boasts [a], features [a], maintains [a], offers [a], refers to

Also: provides, delivers, holds the distinction of being, ventured into [field] as, began his career as, holds a pivotal place in.

One study found an over 10% drop in the words "is" and "are" in academic writing in 2023, with no comparable change before that, and the same decline appears when GPT-3.5 is asked merely to revise existing sentences. The pattern is strongest in AI copyedits, which "improve" plain text into this register.

Important exception, stated in the source: this does not apply to "has" in the past perfect. "Has been featured" is ordinary English and is not a tell.

## 9. Collaborative communication and assistant residue

Maps to R2.

I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., is there anything else, let me know, more detailed breakdown, here is a...

Also: "Here's a template for your...", "You can copy and paste this", "I can guide you step-by-step", "Delete this section before submission", any instruction addressed to the person who prompted you rather than the person who will read the deliverable.

## 10. Knowledge-cutoff disclaimers and speculation about gaps

Maps to R3.

as of [date], Up to my last training update, as of my last knowledge update, While specific details are limited..., While specific details are scarce..., not widely available, not widely documented, not widely disclosed, ...in the provided sources..., ...in the available sources..., ...in the search results..., based on available information

Also: "Below is a detailed overview based on available information", "the mountain likely supports...", "though the details aren't widely documented, they highlight...".

The critical failure is what follows the disclaimer. Models pair it with speculation about what the missing information probably is and why it matters. Both the speculation and the claim that something is undocumented are unfounded. For people specifically, this surfaces as "maintains a low profile" or "keeps personal details private", which are inferences from absent sources, not facts.

## 11. Phrasal templates and placeholder text

Maps to R5.

[Describe the specific section], [Your Name], [Entertainer's Name], [link to the revised article], INSERT_URL_HERE, INSERT_SOURCE_URL_30, SOURCE_PUBLISHER, PASTE_SPOTIFY_TRACK_URL_HERE, PASTE_YOUTUBE_VIDEO_URL_HERE

Date stubs: `2025-XX-XX`, `2025-xx-xx`, `2022-11-XX`, typically in an access-date or date field.

Comment stubs: `<!-- Add if available with citation -->`, `<!-- EDIT BELOW THIS LINE -->`, and any "Add ____" boilerplate.

## 12. Tool and citation artifact tokens

Maps to R1. Strip all of these from anything you quote, paraphrase, or summarise out of fetched content, and never generate them.

| Source | Tokens |
|---|---|
| ChatGPT | `:contentReference[oaicite:0]{index=0}`, `oai_citation`, `oaicite`, `Example+1`, `citeturn0search0`, `turn0search0`–`turn0search7`, `turn0image0`–`turn0image7`, `citeturn0news0`, `citeturn1file0`, `citegenerated-reference-identifier`, `<ref name="0search12">`, `({"attribution":{"attributableIndex":"X-Y"}})` |
| Gemini | `[cite: 1]`, `[cite: 3, 12, 13]`, `[span_1][start_span]`, `[span_1][end_span]` |
| Grok | `<grok-card data-id="..." data-type="citation_card">`, `grok_render_citation_card_json={"cardIds":[...]}` |
| DeepSeek | Lenticular brackets with dagger, e.g. `【85†L261-269】`, `【854140639155648†L119-L123】` |
| Perplexity | `[attached_file:1]`, `[web:1]`, S3 URLs containing `ppl-ai-file-upload` |
| Unclassified | `:::writing{variant="document" id="68427"}`, and its non-English variants such as `:::écriture{variante="document" id="28471"}` |
| Footnotes | The `↩` return character around footnote text |

Tracking parameters to strip from URLs: `utm_source=chatgpt.com`, `utm_source=openai`, `utm_source=copilot.com`, `referrer=grok.com`. Gemini and Claude use UTM parameters less often. Note that a UTM parameter proves a tool touched the URL, not that a tool wrote the surrounding text; some people use AI only to find citations for prose they wrote themselves.

## 13. Historical indicators

Common in older models, much rarer now. Still worth catching, and still worth never generating.

**Didactic disclaimers, roughly November 2022 to 2024.** Maps to R13. it's important to note, it's critical to note, it's crucial to note, it's important to remember, it's important to consider, worth noting, may vary. Often framed as safety advice to an imagined reader, or as a disclaimer that rules differ by jurisdiction.

**Section summaries.** Maps to R12. In summary, In conclusion, Overall, and standalone "Conclusion" headings on short pieces.

**Prompt refusal.** Maps to R4. as an AI language model, as a large language model, I cannot offer medical advice but I can..., I'm sorry.

**Abrupt cut-offs.** Output stopping mid-sentence because a token limit was hit.

**Outdated access-dates.** Citation access dates noticeably older than the writing date, for example a December 2025 piece citing `access-date=12 December 2024`. Legitimate causes exist, including copied citations and offline work.

## 14. Signs of genuine human writing

Maps to G2, G3, G4. These are documented as *more* common in human writing than in AI output, across 25 years of Wikipedia text. Reach for them deliberately.

- Simple is/has phrases: "there is a", "it has a".
- Plain words over stiff or euphemistic synonyms: wrote over authored, moved over relocated, used over utilized, tried over attempted, died over passed away.
- Superlative or definitive statements: "one of the best", "is the only", "was the first".
- Hedging qualifiers and intensifiers: very, perhaps, tends to.
- Isolated wordy constructions, left alone rather than optimised out: "as a result of", "in order to", "all of the", "a part of", "the fact that".

The last two are counterintuitive and are the reason X1 exists. AI output smooths toward a non-committal middle; casual hedging in one place and flat confidence in another is a human signature.

## 15. Ineffective indicators

Maps to the X rules. The source lists these as unreliable or backwards. Do not optimise against them.

- **Perfect grammar.** Many people write well, professionally.
- **Mixed casual and formal register**, or prose that is both clinical and emotional. Indicates a technical writer, youth, playfulness, neurodivergence, or simply multiple authors.
- **Bland or robotic prose.** AI output actually skews positive and verbose, not flat.
- **Fancy, academic, or formal prose.** The correlation holds for specific listed words only, never for register.
- **Transition words in isolation.** Only a few are overused, the pattern predates LLMs in essay writing, and many style guides endorse them.
- **Unsourced content.** Over 570,000 articles are tagged as needing citations and most predate LLMs. Modern models cite heavily, if not always accurately.
- **Bizarre markup.** Random-seeming errors point to browser extensions, translation tools, or visual editors, not to models.
- **Correct markup.** Getting formatting right is normal.

Two further cautions from the source. Non-native English speakers avoid word repetition for reasons of their own schooling, so elegant variation is a weak signal about them. And human speech and writing are themselves being reshaped by LLM exposure, measurably since 2024, so the two distributions are converging.
