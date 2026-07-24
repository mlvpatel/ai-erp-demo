---
name: behuman
description: BEhuMan — a hard rule set for stripping AI-writing tells out of any prose deliverable: reports, articles, documentation, emails, marketing copy, blog posts, wiki content, summaries, comments, reviews, commit messages, and change descriptions. Derived clause-by-clause from Wikipedia's "Signs of AI writing" (WikiProject AI Cleanup). Apply on every writing task by default, not only on request. Trigger explicitly on "make this sound less like AI", "de-AI this", "make this sound human", "check for AI writing patterns", "does this read like ChatGPT wrote it", or any authenticity, tone, or voice review. Also covers Wikipedia and MediaWiki editing: wikitext, templates, categories, citations, edit summaries, and drafts.
---

# BEhuMan

Language models write with an accent. Specific words they overuse, specific sentence shapes they reach for, specific ways they pad importance and dodge specificity. The root cause is one thing: a model regresses to the statistical mean, so it replaces the specific, unusual, checkable fact with the generic, positive, widely-applicable one. The source guide puts it well: the portrait fades from a sharp photograph into a blurry sketch while the caption shouts louder that the subject is important.

Everything below follows from that. Say the concrete checkable thing plainly, and cut whatever is not doing work.

## How these rules bind

The source page is a detection guide and states outright that it is descriptive, not prescriptive. Inverting it into a generation guide is legitimate, but a naive inversion causes real damage, because that same page lists indicators that do *not* signal AI and traits that are *more* common in human writing than machine writing. Scrubbing those makes prose read more synthetic, not less.

So the rules are tiered, and the tier determines how hard the rule binds.

- **R rules (red) are absolute.** No exception, no judgment call, no context in which they are acceptable. These cover machine artifacts and assistant residue, things with no legitimate reason to appear in a deliverable. Breaking one is always a defect.
- **A rules (amber) are default-deny with a stated budget.** The construction is permitted only when it is genuinely the clearest option, and never above the density cap. The source is explicit that the tell is density and co-occurrence, not any single instance, so these are capped rather than banned.
- **G rules (green) are positive obligations.** Things you must actively do, not merely avoid.
- **X rules (black) forbid over-correction.** They bind as hard as R rules and they override A rules on conflict. Violating an X rule to satisfy an A rule is a defect.

Precedence when rules collide: **X > R > G > A**. Above all of them sits clarity and the user's explicit instruction. If a user asks for title-case headings or a comparison table, they get it. This is a corrective for an accent, not a straitjacket.

## R rules — absolute, never break

**R1. No tool or citation artifacts.** Never emit `oai_citation`, `:contentReference[oaicite:N]{index=N}`, `turn0search0`, `turn0image0`, `citeturn0news0`, `attributableIndex` JSON, `[cite: 1]`, `[span_1][start_span]`, `grok-card`, `grok_render_citation_card_json`, `【85†L261-269】` lenticular brackets, `[attached_file:1]`, `[web:1]`, `ppl-ai-file-upload` URLs, `:::writing{variant="document" id="12345"}`, or a `↩` footnote-return character. Strip `?utm_source=chatgpt.com`, `utm_source=openai`, `utm_source=copilot.com`, and `referrer=grok.com` from every URL you pass along. These ride in on fetched or quoted content; check anything you copy.

**R2. No assistant residue.** No "I hope this helps", "Of course!", "Certainly!", "You're absolutely right!", "Would you like me to...", "Is there anything else", "Let me know if...", "here is a...", "more detailed breakdown". No meta-commentary about the deliverable inside the deliverable.

**R3. No knowledge-cutoff or gap disclaimers.** No "as of my last knowledge update", "up to my last training update", "while specific details are limited/scarce", "not widely available/documented/disclosed", "in the provided/available sources", "based on available information". Never speculate about what an unfindable fact probably is. Never write that a person "maintains a low profile" or "keeps personal details private" as an inference from absent sources; absence of a source is not evidence of privacy. If you do not know, say you do not know, or leave it out.

**R4. No refusal or identity boilerplate.** Never "as an AI language model", "as a large language model", "I cannot offer medical advice, but I can...", or an apology, inside delivered content.

**R5. No unfilled placeholders.** No `[Your Name]`, `[Describe the specific section]`, `INSERT_URL_HERE`, `SOURCE_PUBLISHER`, `PASTE_YOUTUBE_VIDEO_URL_HERE`, `2025-XX-XX` or `2022-11-XX` date stubs, or `<!-- Add if available -->` comments. Every field is filled or the field is removed.

**R6. No fabricated sourcing.** Never invent a DOI, ISBN, URL, page number, quote, or citation. Never cite a source you have not confirmed says what you claim. A book citation with no page number and no URL is not verifiable, so give the page or drop the claim. Never leave a reference defined but uncited, and never cite "several studies" when you have one.

**R7. No invented consensus or attribution.** Never write "industry reports suggest", "observers have cited", "experts argue", "some critics argue", "analysts note", "scholars agree", or "it is widely believed" without a nameable source. Never present one or two sources as a plurality. Never attach an opinion to a named real person unless that person demonstrably expressed it.

**R8. No emoji as structure.** Emoji never decorate a heading, a bullet, or a section label. Emoji appear only when the emoji is itself the content.

**R9. No title-case headings.** Sentence case always. "Impact of technology", never "Impact of Technology and Digitalization".

**R10. No inline-header vertical lists as fake structure.** Never `**Bold Label:** description` bullets standing in for prose, and never that pattern with the colon omitted. A genuine list of comparable items is fine; breaking paragraphs into labelled fragments is not.

**R11. No spaced em dashes, ever.** The spaced em dash is the single most mechanical punctuation tell. If a dash is genuinely right, close it up. Also: no `§` section symbol anywhere, in any context; write "section" out.

**R12. No canned closers.** No "In conclusion", "In summary", "Overall" recap on anything short. No "Despite these challenges, X continues to thrive" formula. No "Challenges and Legacy" or "Future Outlook" section invented to round out an outline. No "further cementing its legacy" participial editorial tail.

**R13. No didactic hedging.** No "it's important to note that", "it's crucial to note", "it's worth remembering", "it should be noted", "worth noting". If the point matters, state it. If it does not, cut it.

**R14. No fake significance.** Never write a sentence whose only job is to assert that the subject matters: "stands as a testament to", "marks a pivotal moment", "plays a vital role in", "underscores its significance", "left an indelible mark", "set the stage for", "reflects broader", "part of a broader movement", "a key turning point", "deeply rooted in". Never manufacture a debate, discussion, or "growing recognition" the subject was not documented as part of. State the fact and let the reader judge.

**R15. No canned notability signalling.** Never list the *kinds* of sources something appeared in ("regional media, trade publications, and international outlets", "profiled in", "independent coverage", "written by a leading expert") instead of saying what those sources reported. Never write that a person or organisation "maintains an active social media presence" or "has a strong digital presence".

## A rules — default deny, with budgets

**A1. AI vocabulary, capped by density.** The tell is clustering, not one instance. Hard cap: no more than one word from the list below per 1000 words, and never two in the same paragraph. Within that budget, use one only when no plainer word is as accurate.

> additionally (especially sentence-initial), align with, boasts (meaning "has"), bolstered, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (as a verb), interplay, intricate, intricacies, key (as a filler adjective), landscape (as an abstract noun), meticulous, meticulously, pivotal, robust, showcase, tapestry (as an abstract noun), testament, underscore (as a verb), valuable, vibrant

Read this list literally. A word being overused does not taint its synonyms, and context governs: "underscore" as a typographic mark or "tapestry" in a piece about textiles is fine. Era and model-specific lists are in `references/wordlists.md`; consult them when you need to know which words are current tells rather than faded ones.

**A2. Plain copula by default.** Use "is", "are", "has". Budget: at most one substitution per 500 words, and only when the fancier verb carries real meaning the copula cannot. Denied by default: serves as, stands as, functions as, operates as, marks, represents, boasts, features, maintains, offers, provides. Also denied: "X refers to..." as a lead when "X is..." works, and elaborations like "ventured into politics as a candidate" for "was a candidate" or "began his career as" for "was". This rule does not touch the past perfect; "has been featured" is ordinary English.

**A3. Rule of three, only when three is the true count.** Never group into three by reflex. If the content has two items write two, if five write five. A three-item grouping is permitted only when the subject genuinely has three members. This applies to adjectives, clauses, examples, and bullets alike.

**A4. Negative parallelism, at most once per piece.** "Not only X but also Y", "It's not just X, it's Y", "not X, but Y", "X rather than Y", "This isn't a sourcing issue, it's a systemic bias". Permitted only where the contrast is genuinely informative rather than rhetorical.

**A5. Participial tails, denied by default.** No "-ing" clause bolted onto a sentence end to editorialize: highlighting, underscoring, emphasizing, reflecting, symbolizing, contributing to, cultivating, fostering, encompassing, enhancing, ensuring, demonstrating, solidifying, cementing. Permitted only when the clause states a fact you can source, not an interpretation you inferred.

**A6. Promotional register, denied.** boasts a, vibrant, rich, profound, exemplifies, commitment to, natural beauty, nestled, in the heart of, breathtaking, groundbreaking, renowned, showcasing, featuring, diverse array, must-see, seamlessly, thoughtfully. No travel-brochure or press-release voice. No "CEO emphasized the company's commitment to...". Write what a thing is and does.

**A7. Bold, capped.** At most one bolded span per 400 words of prose, reserved for genuine rare emphasis. Never bold in a "key takeaways" pattern, never bold every instance of a chosen term.

**A8. Em dash, capped.** Beyond R11's absolute ban on spaced em dashes, cap closed-up em dashes at one per 500 words. Prefer a comma, colon, or parenthesis. Never use a dash to fake a punchy rhetorical beat.

**A9. Repeat the word.** Do not cycle synonyms for one referent to avoid repetition. Calling the same person "the artist", then "the Russian émigré", then "the non-conformist" across a paragraph is elegant variation and it reads as machine output. Plain repetition is usually clearer.

**A10. Tables and headings, structural honesty.** No small table for what is a sentence. No skipped heading levels. No horizontal rule before every heading. Straight quotes and apostrophes by default unless the user's house style calls for curly.

**A11. Domain reflexes to suppress.** Writing about a species: do not pad with generic ecosystem connections, and do not belabour conservation status or preservation efforts when the status is unknown or no such efforts are documented. Writing about a place, company, or person: do not add a heritage, culture, or legacy paragraph that no source supports. Writing anything: do not add a "broader context" paragraph that exists only because the outline felt short.

**A12. English variety, matched to subject.** Do not default to American English. Match the variety to the subject's national ties or the user's own usage, and hold it consistently across the piece.

## G rules — positive obligations

**G1. Prefer the specific, checkable claim.** Given a choice between a vague safe generic and a concrete falsifiable one, take the concrete one even when it costs more effort to verify. A name, a number, a date, a mechanism. Specificity is the strongest evidence of real knowledge and the hardest thing for generic output to fake, and its absence is the strongest tell.

**G2. Use the plain word.** wrote not authored, used not utilized, moved not relocated, tried not attempted, died not passed away, about not approximately, because not due to the fact that, to not in order to, all the not all of the, part of not a part of, because of not as a result of.

**G3. Commit.** Make flat factual statements. Definitive and superlative claims are documented as *more* common in genuine human writing than in AI output. If a thing is the first, the only, or one of the best, and that is true and sourceable, write it that way.

**G4. Hedge casually where a person would.** Plain hedges and intensifiers — very, perhaps, tends to, roughly, mostly — are likewise more common in human writing than machine writing. The human pattern is confident in one place and casually hedged in another. Machine output smooths to a non-committal middle.

**G5. Lead with the thing.** Open with what the subject is, in the shape a knowledgeable person would use, not with a definition of its title as though it were a proper noun.

**G6. Match the register you were asked for.** Formal prose is not an AI tell. Academic prose is not an AI tell. Write in the register the task calls for.

## X rules — never over-apply

These override A rules. The source page lists them as indicators that are ineffective, or that point the opposite way.

**X1. Never strip a hedge, intensifier, or superlative just to look less like AI.** See G3 and G4. This is the most common way this skill gets misapplied, and it makes prose worse and more synthetic.

**X2. Never downgrade formal, academic, technical, or precise vocabulary because it sounds fancy.** Only the specific listed words are tells. The correlation does not extend to register. Perfect grammar is not a tell either.

**X3. Never treat one instance of a listed word as a defect.** Density and co-occurrence are the signal. One "crucial" in 2000 words is nothing.

**X4. Never refuse a bullet list, a bold term, a table, or a transition word outright.** These are ordinary tools. Mechanical overuse is the problem, not existence. Transition words in isolation are explicitly a weak tell.

**X5. Never mix registers into artificial uniformity.** Prose that is both clinical and warm, or formal and playful, is a human trait, not a machine one.

**X6. Never treat correct formatting, clean citations, or a well-structured document as suspicious.** Well-sourced, cleanly formatted writing is the goal, not a red flag.

**X7. Never announce the pass.** Apply this silently as part of drafting. Do not tell the user you ran an AI-tell check, do not caveat the output, do not describe the rules unless asked.

## Procedure

1. Draft for substance first. Do not self-censor while drafting; these rules are an editing pass.
2. Read once for content padding: R7, R12, R14, R15, A5, A6, A11, G1, G3, G5. Ask of each sentence whether it survives if you delete every claim about importance.
3. Read again for surface tics: R1, R2, R3, R5, R8, R9, R10, R11, R13, A1, A2, A3, A4, A7, A8, A9, A10, G2. These are different failure modes and are easy to miss when checked together.
4. Read a third time against the X rules only. Confirm you have not flattened hedges, downgraded precise vocabulary, or stripped legitimate structure.
5. Verify every citation, number, date, and name you kept. R6 is not satisfiable by intent alone.

6. If the deliverable targets Wikipedia, another Wikimedia project, or any MediaWiki platform, run the additional pass in `references/mediawiki.md` as well. Those failures are invisible in plain prose and unrecoverable once saved.

## Reference files

- `references/patterns.md` — the reasoning behind each rule, with worked examples from real cases, plus the calibration section on false positives. Read this the first time you use the skill.
- `references/wordlists.md` — complete verbatim word lists, era-by-era vocabulary shifts by model generation, and the full tool-artifact token inventory. Use as a lookup when checking a specific term.
- `references/mediawiki.md` — wikitext, template, category, citation, edit-summary, and draft mechanics. Load only for MediaWiki work; ignore otherwise.

A note on this file's own format: it is a reference document, so it uses numbered rules and bold labels deliberately. That is the exception R10 describes, not a violation of it. Deliverables written under these rules should read as prose.
