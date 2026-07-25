# Wikipedia and MediaWiki mechanics

The signs in `patterns.md` and `wordlists.md` generalise to any prose. The ones here do not: they depend on wikitext, on MediaWiki's template and category system, or on Wikipedia's own review processes. Load this file when writing or editing for Wikipedia, another Wikimedia project, or any MediaWiki platform such as Miraheze. Ignore it otherwise.

Two framings apply throughout. When **writing**, these are defects to avoid. When **reviewing**, they are evidence, and the same false-positive cautions in `patterns.md` section 8 apply with full force.

## Policy context

The speedy deletion criterion **G15** covers LLM-generated pages without human review. It lists some signs of AI writing but is deliberately limited to the most objective ones. Everything else on this list, including everything in the other reference files, is **not sufficient on its own** for speedy deletion.

A high percentage reported by an AI detection tool is explicitly **not** a valid G15 criterion. Detectors beat chance but carry non-trivial error rates and are defeated by paraphrasing, markup changes, and models they were not trained on.

Comments suspected of being pasted from an LLM may be collapsed with `{{collapse AI}}` per WP:AITALK. The `{{Looks AI-generated}}` template exists for tagging.

Critical framing from the source, worth repeating: these signs are potential indicators of a problem, not the problem itself. Excessive boldface and broken markup are easy to fix, and fixing only those makes the real problems harder to detect. The deeper concerns are unverifiable claims, fabricated sources, and synthesis. Address those, or flag them.

## 1. Markdown leaking into wikitext

Models are not proficient in wikitext. It is a niche markup language found mostly on Wikipedia and other MediaWiki wikis, so wikitext-formatted content is thin in training data. The millions of Wikipedia articles that were ingested were not processed as files containing wikitext syntax. Meanwhile, system prompts typically instruct models to format answers in Markdown, and chatbot apps render that Markdown on screen.

The two languages differ at every point:

| Element | Markdown | Wikitext |
|---|---|---|
| Bold and italic | `*` or `_` | `'` single quotes |
| Headings | `#` | `=` |
| URLs | `(parentheses)` | `[square brackets]` |
| Thematic break | `---`, `***`, `___` | `----` four hyphens |

Consequences to watch for:

- `**Bold**` and `*italic*` surviving into article text.
- `##` used for a heading. MediaWiki reads it as a nested numbered list, so "## Geography" followed by "## History" renders as `1. 1. History`.
- Three backticks appearing in the text, especially ` ```wikitext `. This happens when a model wraps its attempted wikitext in a Markdown fenced code block, its equivalent of WP:PRE. Faulty wikitext mixed with Markdown syntax, particularly inside a fenced block, is a strong indicator.
- A model offering "Would you like me to turn this into actual Wikipedia markup format (`wikitext`)?" and, if told to proceed, producing syntax that is rudimentary, incorrect, or both.

Calibration: **Markdown alone is a weak indicator.** Developers, researchers, technical writers, and experienced internet users write Markdown routinely in Obsidian, GitHub, Reddit, Discord, and Slack. iOS Notes, Google Docs, and Windows Notepad support it. Its ubiquity also leads new editors to assume Wikipedia supports it.

## 2. Broken wikitext and templates

Since models are weak at wikitext, they produce faulty syntax. A known cluster involves `Template:AfC submission`, because new editors ask chatbots how to submit an Articles for Creation draft. The failure produces garbage like a category name containing an entire mangled timestamp expression.

**Non-existent templates.** Models hallucinate plausible-sounding templates, especially infoboxes, and hallucinate parameters for real templates. Both render as red links, and invented parameters silently do nothing. Models also use templates deleted after their knowledge cutoff, such as the `lang-??` series. A worked example from the source invents `{{Infobox ancient population}}` where `{{Infobox archaeological culture}}` is the real template, with every parameter name correspondingly wrong: `regions` for `region`, `descendants` for `followedby`, `archaeological_sites` for `majorsites`.

Wikipedia:Database reports/Transclusions of non-existent templates is the standing list. Many entries are ordinary mistakes, but the infobox and lang sections concentrate LLM hallucinations.

**Non-existent or out-of-place categories.** Models invent categories that sound like plausible titles or SEO keywords, and reproduce obsolete or renamed ones from training data. These show as red links. Watch also for category redirects, including the long-time spam favourite `Category:Entrepreneurs`. The hyphenation trap is typical: `[[Category:American hip hop musicians]]` where the real category is `[[Category:American hip-hop musicians]]`.

Because reviewers sometimes delete broken categories, check earlier revisions if you suspect a page.

Calibration, stated explicitly in the source: none of this is a hard-and-fast rule. New editors do not know the style guidelines for these sections, and returning editors may remember categories that have since been deleted.

## 3. Heading levels and thematic breaks

Models tend to skip level-2 headings (`==`) and start sections at level 3 (`===`). This violates Wikipedia's accessibility and style conventions, so a manually formatted page is very unlikely to have the quirk.

They also insert a thematic break (`----`) before each heading, which is a habit carried over from Markdown output.

## 4. Citation mechanics

`patterns.md` section 6 covers sourcing honesty. These are the MediaWiki-specific failures.

**Broken external links.** A new article or draft with several dead links, especially links absent from the Internet Archive, is a strong sign. Most links rot over time, but absence from archives makes it unlikely the link was ever real.

Do not misread: links that fail for you but work for others (university library proxies), links mangled by bots and scripts, and links missing their start or end from a human copy-paste are all ordinary.

**Invalid DOIs and ISBNs.** ISBNs carry a checksum, and citation templates warn on failure. DOIs resist link rot better than plain URLs. An unresolvable DOI or a failed ISBN checksum points to hallucination.

**DOIs that resolve to unrelated articles.** Worse than broken, because they look verified. The source's example generates two *Proceedings of the IEEE* citations for Ohm's law that are entirely fabricated. Both DOIs resolve, but to different papers, and one is attributed to C. L. Fortescue, who had been dead for more than thirty years at the purported date.

**Book citations without page numbers or URLs.** A plausible book on a general topic, cited with no page and no link. The example cites Goldwater's *The Conscience of a Conservative* p. 12 for a claim about Edmund Burke; searching the book for "Burke" returns nothing. Legitimate book citations often include a link to an online copy, so its absence alongside a general-topic book is a signal.

**Incorrect reference re-use syntax.** Models attempt Wikipedia's named-reference mechanism and get it wrong, sometimes inserting the malformed re-use markup after every single full stop.

**Named references declared but never used.** Sources placed inside a `<references>` tag with no inline invocation, producing `Cite error: A list-defined reference named "X" is not used in the content`. This can also result from copy-pasting between articles.

**Stale access-dates.** Citations defaulting to an access-date noticeably older than the edit, such as a December 2025 article with `|access-date=12 December 2024`. Newer chatbots seldom do this, and legitimate causes exist: copied citations, offline work, batch moves and merges.

**Placeholder dates.** `|access-date=2025-XX-XX` and variants. Search with `insource:/20[0-9][0-9]-(XX|xx)-(XX|xx)/`.

**Not an AI sign.** From 2018 to 2023 a VisualEditor UX bug (T198456) caused editors to insert references to PubMed articles with very low PMIDs, producing absurdly irrelevant citations such as a paper about rat livers (PMID 9) cited in a list of Disney television films. These resemble hallucinations and should be fixed, but they are not AI.

## 5. Comment-specific indicators

Beyond anything else on this list, editors using LLMs for talk page comments are likely to:

- Misquote policies and guidelines, and cite made-up shortcuts that lead nowhere. The source's example cites `WP:BIOSIG`, which is not a real shortcut.
- Transclude maintenance banners whenever they mention them.
- Post lengthy comments divided into titled sections, in Markdown, plain text, or level-2 and level-3 subheadings.
- Assure other editors that their content adheres to Wikipedia's policies and guidelines, or that they are trying to ensure it does.
- Request input from others to determine exactly what they need to improve.
- Accuse those who call out AI use of acting on speculation about writing style and failing to present stronger evidence.

Note the last one carefully when reviewing. It is a described pattern, not proof, and treating a denial as confirmation is exactly the confirmation bias the source warns against.

## 6. Edit summaries

AI-generated edit summaries are formal first-person paragraphs, written without abbreviations, that conspicuously echo the exact text of Wikipedia's policies or of maintenance tags on the article. They itemise adherence to WP:NPOV or "encyclopedic tone", mention things they "ensured" or "avoided", and justify minor edits at length. This is especially visible when AI is used to "fix" text after AI use was suspected.

An AI edit summary strongly suggests the edit itself is AI-generated. Nobody uses a model for the summary but not for the far more time-consuming writing.

**Canned assurance of adherence.** Words to watch: ensured that... adheres to, improved, in compliance with, complies with, revised, verifiability, neutrality, neutral tone, encyclopedic tone.

Human editors do cite guidelines, but briefly and specifically, with a link: "removed excessive links per MOS:OVERLINK". The AI equivalent is more verbose and less specific, because the person prompting does not know the guidelines well enough to ask for anything sharper than "make this more neutral". The more assurances stacked into one summary, especially covering a wide spread of improvements unlikely in a single human edit, the stronger the sign.

**Mentions of preserved or retained material.** Words to watch: preserved, preserving, retained, retaining. It is unusual for a human summary to mention material that was *not* edited, and exactly what you would expect from a model told to change X and Y while leaving Z alone. Typical shape: "Revised [section] to improve [neutrality] while preserving [whatever]".

**Overemphasis on the presence of citations.** Words to watch: added sourced [information/content/infobox/section], added [coverage/citations/references], improved attribution. This is the edit-summary form of the general tendency to allude to coverage without summarising it. A human is far more likely to describe the content added ("Added info about the artist's debut") than the fact that it was sourced.

## 7. Draft and user page artifacts

**AfC submission statements.** At least one model inserts a "submission statement" addressed to reviewers, explaining why the subject is notable and why the draft meets guidelines. It typically opens "Reviewer note (for AfC):" and enumerates qualifications against WP:RS, WP:BLP, and WP:NBIO. All it achieves is telling the reviewer the draft is LLM-generated.

**Pre-placed maintenance templates.** A new editor's draft arrives with an AfC review template already set to declined, content-free and with no reviewer reasoning. The model offers to add a submission template and supplies `{{AfC submission|d}}`, where `d` pre-declines by substituting `{{AfC submission/declined}}`. The creator then asks at the Help desk why their draft was declined with no feedback. A content-free "submission declined" header is a strong indicator.

Models also create pages carrying maintenance tags and incorrect protection templates that could not plausibly belong there yet.

**Canned user pages.** A recognisable format with inline-header vertical lists and headings such as "Welcome To My User Page!", "About Me", "My Interests", and "Let's Connect!", usually with emoji and bold text. Attempted bold via Markdown is the strongest giveaway. See Wikipedia:Canned user pages.

## 8. Permissions gaming

Permissions gaming is disruptive editing where someone makes many benign-looking but unconstructive edits, often across unrelated topics in quick succession, until their edit count raises their access level and lets them pursue spam, vandalism, or contentious content.

Because models generate plausible-looking content quickly, post-2023 permissions gaming often uses throwaway AI rewrites across dozens of unrelated articles. Uncleaned, the result is a large body of unreviewed AI content.

**This sign runs in one direction only.** Someone rapidly adding AI-generated text is not thereby a permissions gamer and must not be accused of it without other evidence. The inference only runs the other way: if someone is found or reasonably suspected to be gaming permissions by rapidly changing a lot of text, those edits may be AI.

## 9. Dating and attribution

**Before 30 November 2022, AI use can be safely ruled out.** That is ChatGPT's public launch. OpenAI had comparably powerful models earlier, but they were paid services, not easily accessible or known to lay people. Older writing sometimes displays these signs convincingly; Wikipedia is vast enough for the coincidence.

**Ability to explain editorial choices.** Editors should be able to explain why they made an edit or a mistake. If someone inserts an apparently fabricated URL, ask how the mix-up happened rather than concluding. Supplying the correct link, or the relevant passage from the real source, points to ordinary human error such as a typo.

**Style drift over time.** If an editor has used AI for years, their style tracks contemporaneous tools: 2023 edits resemble 2023 output, 2025 edits resemble 2025 output. Conversely, a style consistent from before November 2022 through today suggests the newer edits are not AI.

**Sudden style shifts.** Unexpectedly flawless grammar relative to an editor's other communication may indicate AI, particularly when the other writing predates November 2022.

**English variety mismatch.** A mismatch between the editor's location, the topic's national ties, and the variety of English used may indicate AI, since several models default to American English unless prompted otherwise. A writer from India covering an Indian university would probably not use American English.

Calibration on the last two: non-native speakers mix varieties, and many writers code-switch into more formal prose in particular venues. Only a dramatic and not easily explainable shift should raise suspicion.

## 10. Markup that is not an AI sign

From the source's "Ineffective indicators". These get misread as AI constantly.

**Bizarre wikitext.** Models hallucinate templates and produce invalid syntax for the reasons in section 1, but they do not produce random, inexplicable errors. Strangely placed HTML tags such as `<span>` point to badly written browser extensions or to a known bug in Wikipedia's content translation tool (T113137). Misplaced syntax like `''Catch-22 i''s a satirical novel.`, which renders correctly as "*Catch-22* is a satirical novel", indicates a VisualEditor mistake, where such errors are much harder to notice than in source editing.

**Correct wikitext.** Getting formatting right, even for complex templates, is normal, especially for someone using the visual editor or the Preview button.

**Unsourced content.** More than 570,000 articles are tagged as needing citations and most predate LLMs. Modern chatbots search the web and read supplied sources, so citations are now common in AI text. Common, not accurate, but present.

## 11. Search queries for review work

Useful `insource:` and text searches from the source, for finding existing artifacts rather than for writing:

- `insource:/20[0-9][0-9]-(XX|xx)-(XX|xx)/` for placeholder access-dates
- `"contentReference" OR "oaicite" OR "oai_citation"` for ChatGPT reference bugs
- `insource:/turn0(search|image|news|file)[0-9]+/` for ChatGPT turn markers
- `insource:/【[0-9]+†/` for DeepSeek lenticular brackets, drafts only
- `"span 1 start span" OR "span 1 end span"` and variants for Gemini span bugs
- `"grok-card data-id"` for Grok citation cards
- `insource:"utm_source=chatgpt.com"`, `insource:"utm_source=openai"`, `insource:"utm_source=copilot.com"`, `insource:"referrer=grok.com"` for tracking parameters
- `"About Me" "Let's Connect"` and `"About Me" "Let's Collaborate"` in user space, for canned user pages
- `"you declined your"`, `"you declined it yourself"`, `"put a decline"` in the AfC Help desk archives, for pre-declined drafts
- Variations on `"to ensure the article adheres to Wikipedia's"` across adheres / aligns with / complies with / follows / meets, for canned assurances
