# AI report writing for home inspectors: a twelve-perspective rethink

Built by putting the idea in front of twelve personas independently, then sharpening each one against a critic. The personas: a 20-year veteran inspector, a 3-month rookie, a 12-inspector firm owner, a top-producing referring agent, a first-time buyer reading the report at 11pm, a head of product at the incumbent, an E&O underwriter paired with a defense attorney, a field-conditions UX designer, an ML engineer who ships vision and voice products, a bootstrapped vertical-SaaS founder, a contrarian investor, and a standards-and-privacy expert. Competitive and regulatory claims were then fact-checked against vendor pages and primary sources.

---

## 0. The verified landscape, as of September 2026

Checked against vendor pricing pages, press releases, the Texas rule text and public filings.

**Confirmed:**

- **Spectora acquired HomeGauge on April 1, 2025**, from American Family Mutual Insurance. Both platforms still run independently. No forced migration has been announced.
- **Carson Dunlop's Horizon sunsets on December 15, 2026.** Spectora is the named migration partner with a published one-click path, dedicated onboarding and special pricing. That is about twelve weeks from today. It is the only forced-switch event this industry has had in a decade.
- **Spectora shipped AI Report Assist on June 9, 2026.** Speak the observation, snap the photo, and it matches to comments already approved in the inspector's own template. Roughly 25% time savings claimed. TREC-compatible. It is in early access and free *during early access*, and the press release says it will be paid at launch. **AI Comment Assist is already live and free to all users.**
- **Spectora pricing**: $109/mo base, $99/mo per additional inspector, Advanced at $4 per published inspection.
- **Spectora has a documented template export.** Templates, then My Templates, then the overflow menu, then Export to spreadsheet, as plain text or HTML text. This matters enormously for your migration design.
- **Porch Group owns ISN, Home Inspector Pro, Palm-Tech, RWS and ISG**, and claims over 40% of US inspection companies and about 40% of all US home inspections. Self-reported at their December 2024 investor day, on 2023 data.
- **Texas 22 TAC 535.223**: REI 7-6 mandatory since February 1, 2022. The rule text requires the inspector to "reproduce the text of the standard form verbatim" and that "the spacing, borders and placement of text must be identical to the standard form." Permitted deviations are typeface at 10pt minimum, checkbox and typeface color, a cover page, expanded comment space, added pages and a logo. Amended again effective March 7, 2023 to require an explanation when multiple boxes are checked.
- **Competing AI-first entrants already selling**: InspectorData at $79/mo flat with a 30-day trial, importing from Spectora, HomeGauge and Home Inspector Pro; InspectForge at $39.99 to $99.99/mo; FieldScribe at $149 one-time.

**Corrected from the working assumptions:**

- **Market size is ~36,505 US home inspectors** as of April 2026 by directory count, 85.7% single-owner. The 30,000 to 35,000 figure was slightly low. There is no BLS occupation code for home inspectors, so no better number exists.
- **The "3,000 to 4,000 newly licensed inspectors per year" figure has no source.** Around 34 states license individually and there is no national register. Drop it or label it an unsourced guess. A strategy that leans on new-inspector acquisition is leaning on a number nobody has published.
- **InterNACHI dues** are $49/mo or $499/yr per their current FAQ, with $59/mo for members who joined after the 2023 increase. Their public directory shows 27,401 certified inspectors. ASHI is around 6,000 members.

---

## 1. Two premises in the original plan are wrong

**The "1-3 hours of report writing" is a rookie number, and the writing is not the work.**

The veteran: "I do not type notes and write narratives later; I tap my own pre-written comments on the tablet while I walk. My post-inspection 45-75 minutes is culling 250 photos to 120, drawing arrows on them, building the summary page, and re-reading every word for liability. AI that writes narratives attacks the 20 minutes I already solved."

The firm owner says the same: veterans finish about 80% on site and spend 30 to 45 minutes after. The ML engineer says the honest ceiling is 30 to 45 minutes saved, not two hours, because a 90%-correct draft still has to be read line by line by the person who signs it. Spectora's own published figure on the same architecture is 25%.

So the actual bottlenecks, ranked: **photo triage and photo-to-defect binding**, then **retrieval of the right narrative from a 1,000 to 2,000 item library**, then **the summary page**, then **the liability re-read**. Prose generation is last and smallest.

**The migration bet and the time-savings bet point at different customers.**

The veteran with the 900-comment library worth migrating is exactly the person who already finishes on site and has no three-hour night. The rookie with the three-hour night has nothing to migrate. The rookie persona said it from the inside: "Your PDF-import pitch, the HomeGauge importer, the white-glove migration: none of it is for me."

You cannot lead with both. Pick.

---

## 2. Challenges, grouped by how hard they are to solve

### The ones that can kill the company

**The incumbent shipped your feature in June and priced it at zero for now.** AI Comment Assist is free permanently. Report Assist is free during early access and will be paid at launch. That last detail is the only crack in the free-forever argument, and it is thin: whatever they charge, it will be bundled against a subscription the inspector already pays.

**The TAM does not support a venture outcome.** 36,505 inspectors, 85.7% solo, at roughly $1,100/yr of software spend is about a $40M category. Twenty percent share, which is implausible, is $8M ARR. Executed well this is a $3-8M ARR bootstrapped business. Fund it that way or you are a zombie by month 30.

**You are the second subscription.** Scheduling, pre-inspection agreements, e-sign, payments, client history and the agent-facing link all stay with the incumbent. In several states the agreement must be signed before the inspection starts, so a report-only tool means running two systems on every single job, forever. The predicted churn interview: "I went back because I wanted scheduling, the agreement, payment and the report in one login."

**The agent is the real switching cost and your product never touches her.** Roughly 80% of jobs come from agent referrals. The one thing the agent actually *does* with inspection software is build the repair addendum: tick nine items, type "seller credit $4,500," export a PDF, attach it to the amendment. Every incumbent has that tool. If your report is a flat PDF, she is copy-pasting narratives into Word at 9pm and she remembers who made her do that. Four personas independently predicted the identical failure: the agent asks the inspector to "go back to the old format for my clients," he runs one job in the old tool, then the next, and the switch silently reverses.

### The ones that are solvable but expensive

**You are really building three products.** A field capture app, a report writer, and a migration tool. The field app is the moat and it is also where field-software startups die: offline sync, thermal shutdown in attics, gloves on capacitive glass, battery drain, phones dropped through scuttle holes, iOS killing background tasks, Android battery managers silently stopping your sync queue.

**Photo count is your cost of goods, and it scales by count not resolution.** 150 to 400 photos per job. The vision APIs downscale your images anyway, so sending lower resolution saves nothing; sending fewer photos saves everything. Estimated $0.50 to $3.00 per report in model and transcription fees against a $99 subscription at 20 to 40 jobs a month. On-device blur rejection, perceptual-hash dedupe and sending only photos with no bound note is the difference between 60% and 85% gross margin.

**PDF import recovers the wrong 30% of the library.** Ten reports exercise 150 to 400 of a 1,000 to 2,000 narrative library. The missing ones are Federal Pacific panels, aluminum branch wiring, polybutylene, Orangeburg sewer, knob-and-tube, EIFS: rare, and precisely the ones written after a lawyer called. A finished PDF is also the union of what *printed*, so conditional sections, suppressed narratives, unchecked items, per-item limitation text and do-not-print flags are invisible. You recover the skin and miss the skeleton.

**Given that Spectora has a documented template export, PDF reconstruction should not be your primary path for Spectora users at all.** Take the export for the full library and use the PDFs only to rank which narratives he actually uses. PDFs are the fallback for Horizon, HomeGauge desktop and old Palm-Tech installs.

**Texas is a fixed-layout compliance problem, not a template.** The rule requires verbatim form text with identical spacing, borders and placement. A neutral internal model that reflows layout is non-compliant by construction. The TREC path has to be a separate fixed renderer with a pixel diff against the official PDF in continuous integration, and the language model must never touch form structure.

### The quiet ones most founders miss

**Your marketing copy is a deposition exhibit.** "AI writes your report in 5 minutes" gets read aloud at your customer's deposition. So does your system prompt: if it says "write concise, client-friendly, reassuring narratives," plaintiff's counsel reads that to the jury as the instruction that softened the foundation finding. Write every prompt as Exhibit 14.

**You create a new category of loss.** Inspector claims are overwhelmingly *omissions*, defended by the agreement's scope clause. An AI that fills silence with reassurance produces *affirmative misstatements*, which plaintiffs plead as misrepresentation to escape the limitation-of-liability clause. You would be converting defensible claims into indefensible ones.

**Every log you build for defense is also the plaintiff's log.** GPS time-on-site of 58 minutes on a 2,900 sq ft house settles a case regardless of what the report said. So does a record of "suggestion dismissed." And deleting audio once litigation is reasonably anticipated is spoliation, while a routine pre-existing 30-day deletion policy is defensible. The difference is a document you write on day one.

**Much of "the inspector's library" is not his.** Libraries are stitched from InterNACHI's members-only library, vendor default templates and Facebook copy-paste. Importing verbatim imports vendor-copyrighted text, and your customer is caught in the middle of the cease-and-desist. Build a known-boilerplate fingerprint detector.

**You have three data subjects and a contract with none of them.** The buyer, the seller whose occupied home is photographed room by room, and the agent. The seller never consented to anything and is the one who files the deletion demand against the company whose logo is on the hosted report page. Photo intake should flag faces, mail, medicine, firearms and children's items for optional blur, and strip GPS from delivered copies while keeping the original EXIF in the inspector's vault, because that timestamp has won real claims.

**Always-on voice is a recording-consent problem.** The listing agent is usually in the house. Roughly a dozen states are all-party consent. Push-to-talk is a legal control disguised as a UX decision.

---

## 3. What is genuinely good about this

- **The pain is daily, time-stamped, and the buyer is reachable.** The whole market lives in a dozen Facebook groups, two associations and a handful of conferences. One respected inspector posting "it imported my library clean and I ran the export myself" is worth more than any ad budget.
- **The output space is small and structured**: section, item, severity from a fixed scale, narrative ID, photo list, limitation. This is retrieval and routing, not open-ended writing, so hallucination can be bounded architecturally and quality measured as item recall, false-item rate, severity agreement and photo-binding accuracy.
- **Every customer arrives with their own personalized training and eval set.** Few-shot retrieval over one inspector's 1,500 narratives beats a general model trained on a million other inspectors' reports. It is the one place a small team beats the incumbent's data advantage.
- **Vision is low-stakes** because the human already found and diagnosed the defect. The model sorts and phrases; it never has to detect.
- **Anti-lock-in is a real weapon.** No incumbent says "leave anytime with everything." The veteran said he would run the export on day two just to see that it works, and then tell the chapter meeting whether it did.
- **Consistency is a legal asset.** Plaintiff's experts pull 10 to 20 of the inspector's other reports to show he called the same crack "Major" last month and "Monitor" this month. One narrative per defect across every job gives them nothing. For a multi-inspector firm, "our firm always writes this defect this way" is a deposition defense.
- **Structured limitations change behavior.** "Attic access blocked by stored items, photo attached" is the exhibit that wins the missed-attic case, and tired inspectors skip it. Making it one tap is a genuine claims reducer.
- **Capture at the moment of observation** attacks the most common omission pattern in claims files: he saw it, photographed it, and forgot to write it at 9pm.

---

## 4. The contradictions you have to resolve

These are real disagreements between the personas. Straddling any of them is fatal.

**Texas first or Texas last?** The agent and the contrarian say start there: the mandatory form removes the template problem, the 7 to 10 day option period makes same-day delivery tangible, and it is a large single-state pool. The standards expert says ship Texas *last*: the verbatim-layout rule is unforgiving and one public complaint naming your software is unrecoverable. **Resolution:** the standards expert is right about sequencing risk and the others are right about the market. Build the TREC renderer as a fixed-layout path with a pixel diff in CI, validate it privately with real inspectors for a quarter, and only then market in Texas. Do not launch there on a reflowing template engine.

**Flat price or per-report?** The contrarian says per-report so you share the cyclicality and do not get cancelled in January. Everyone who has actually sold to this trade says flat, because the most resented thing in the market right now is Spectora Advanced's $4 per published inspection. **Resolution:** flat, with a cheap winter pause plan and an annual prepay push in February. Per-report pricing looks identical to the fee they already resent and caps you at the incumbent's add-on price.

**Log everything or keep almost nothing?** The defense side wants a one-button defense file: agreement, final PDF, photo originals with EXIF, delivery and open logs, revision history. The same lens warns that time-on-site metadata and dismissed-suggestion records lose cases, and that some attorneys tell inspectors to destroy unused photos because 300 unreported photos are discovery ammunition. **Resolution:** retention is a per-inspector *policy*, not a default. Write it before the transcription code. Raw audio auto-deletes N days after publish, rejected suggestions are never persisted, edit history is kept, and there is a legal-hold switch per job.

**Who is the customer: veteran, rookie, or firm?** They want opposite products. The veteran wants portability, offline reliability, archive permanence and zero paraphrase. The rookie wants a vet-quality library, structure, calibration and a low price. The firm owner wants master-template control, an approval gate, a QA queue and per-inspector drift reporting, and he is the only one with real budget. **Resolution:** the firm has the best economics and the hardest build. The rookie is the cheapest acquisition and the worst retention, and note that the annual-new-inspector number everyone quotes has no source. The veteran is the one agents listen to and whose endorsement moves the market. Sell rookies for volume, court two or three veterans for credibility, build for firms.

**Shorter reports or more complete ones?** The agent and the buyer want fewer, calmer, better-ranked items. The liability lens wants every limitation documented. **Resolution:** these are not opposed if you separate them structurally. Cap the summary at 8 to 10 items the inspector ranks at review time, make limitations a first-class object printed consistently in one place, and let the body be as complete as it needs to be. The failure mode is hedging *inside* every narrative, which trains the reader to skim past the one warning that mattered.

**Replacement or supplement?** Decide by month six. Supplement means your output lands inside the incumbent with zero friction and you accept being a feature they can absorb. Replacement means building scheduling, agreements, payments and the agent portal. The straddle is where the money goes and the product stalls.

---

## 5. The mindset to hold

- **The report is a legal document first, the agent's marketing second, and the inspector's time sink third.** Rank every feature in that order, because that is the order the inspector is judged in.
- **Precision over recall, always.** Inspectors are used to catching what they missed. They are not used to deleting what a machine invented. Tune toward omission and make omissions *visible*, as in "3 notes unmatched," rather than filling gaps with plausible text.
- **You are building a labeling and review interface with a model behind it**, not a model with a UI in front of it. The review screen is 80% of the engineering. If review takes 40 minutes on a 90%-correct draft, you have saved nothing.
- **Provenance is the product.** Every line traces to note N, photo M and library narrative K. If you cannot show where a sentence came from, it does not belong in a document someone signs under a license number.
- **Own the schema, rent the models.** Your durable asset is the internal structure of sections, items, conditions, severity mapping, photo bindings and limitations, plus the importers into it, the correction logs and the eval set. Model vendors will change under you every six months.
- **The library is not content, it is case law.** Every hedge has a story and an attorney's phone call behind it. Never edit without a visible diff and an explicit approval.
- **Consistency beats eloquence.** A boring sentence used 4,000 times is worth more than a beautiful new one.
- **Think in seasons.** Build and migrate November to February, sell January to March, ship nothing risky April to August when a broken sync costs a customer his day's income.
- **Measure at 8pm on a Tuesday** after two inspections and a 90-minute drive, on a phone at 12% battery. Not in a demo with a clean template.
- **Assume a non-party subpoena in year two.**

---

## 6. Style and positioning

**Never lead with AI.** Every persona that touches liability or referrals said this independently. The inspector hears "AI" as the thing that gets him sued. The agent hears a reason for the listing agent to dismiss every finding. The buyer hears "did he actually look?" Say **"Your words. Your template. Done in the driveway."**

**No badge on the report.** No "Powered by," no "AI-assisted" footer. The only names on that PDF are the inspector's, his license number and his client's. The one honest exception the buyer asked for is a single quiet line: "Narratives drafted from the inspector's notes with software, reviewed and signed by the inspector." That line beats them finding out on Reddit.

**The founder has to have been in a crawlspace.** If you cannot explain a double-tapped breaker, an S-trap and a TPR discharge line without notes, no veteran hands you his library. Hire a licensed inspector part-time as the voice and the forum presence if you are not one.

**Show up in person and in the forums, not on LinkedIn.** State association chapter meetings, doing a live migration of a volunteer's real library in front of the room and then running the export. The InterNACHI forum and the big inspector Facebook groups under your own name. Never argue with a critic there: fix it and post the fix.

**Testimonials with name, city, years and license number.** "John S., inspector" is worth nothing, and a two-year inspector endorsing your speed is worth nothing to a veteran.

**Look like a tool, not a SaaS product.** Dense, high contrast, dark mode, large type. A Fluke meter or a DeWalt app, not a fintech dashboard. No purple gradients, no sparkle icons anywhere near report text.

**Publish what your import does and does not carry.** Spectora's own importer documentation says clean-up will be necessary. An honest limitations list beats a perfect demo with a veteran, and you can be more honest than they are.

**Put a real sample report on the homepage.** Inspectors judge software by the finished report and agents judge the inspector by the same document. "Send me a sample report" is how this entire market evaluates everything.

**One price, on the page, no per-inspection fee, in the headline.** That is your sharpest available contrast against $109 plus $4 per published inspection plus $99 per additional inspector. Do not claim "no payment fees" unless it is true; inspectors know what card processing costs.

**Do not attack Spectora by name.** Half your leads like them. The positioning they cannot answer is "independent, not owned by Porch or a private equity fund."

---

## 7. UI and UX, concretely

### Field capture

- **Bind photo to note at capture with a gesture.** Take the photo, hold to talk, release. They are one record from birth. This deletes the single hardest modeling problem in the product instead of solving it later with timestamp clustering.
- **Push-to-talk, never always-on.** Minimum 72pt bottom-center button, distinct haptics for start, stop and saved. Ship a Bluetooth push-to-talk button clipped to the headlamp strap to beta users. Always-on is a consent problem and a privacy-awkward moment when the buyer's family is following him room to room.
- **Show the transcript for three seconds with one-tap re-record.** Catching "no GFCI" versus "GFCI" while standing at the receptacle is free. Catching it at the kitchen table is a corrected report.
- **Offline-first, write-through.** Every note and photo hits disk before the UI acknowledges. Append-only log. A visible chip: "Saved on device 2s ago, 3 notes waiting for signal."
- **Curb sync and an exit guard.** Push whenever any bars appear. When the phone leaves the property geofence with unsynced items, full-screen warning: "17 items exist only on this phone."
- **Degrade gracefully when the phone overheats.** "Camera paused, phone too hot, notes still work." Do not crash when the operating system yanks the capture session.
- **56pt minimum targets, no swipe-only or long-press-only actions, everything critical in the bottom 40% of the screen.** Gloves on, one thumb, headlamp, reading glasses off.
- **Camera roll import as a first-class path.** A meaningful share of inspectors shoot with a real camera and a thermal attachment and import later. No incumbent handles this well.
- **Tap-to-mark in the field, annotate in the truck.** Nobody draws arrows on a ladder, but a report without them reads as amateur to the agent who sends him most of his work.

### Review

- **Three panes per item**: raw input with note, audio scrubber and photos; matched narrative with alternatives; final text. Sort "needs attention" above the confident items.
- **Unmatched is a hard stop.** Anything the model could not map to a library narrative must be resolved before export. Free text never flows into a signed report without a visible decision.
- **Negation confirmation.** Any transcribed finding containing no, not, without, absent or none is highlighted with its three-second audio clip and cannot be accepted without a tap. In 200 claims files the operative sentence is one line long, and this is that line.
- **Severity comes from the narrative, never from the model.** Each library narrative carries the inspector's default severity from import. An override is logged as a correction.
- **A linter** that flags "good condition," "up to code," "no problems," "safe," remaining-life and cost estimates, and causation language such as "due to," "caused by" and "likely," unless the text came from his own library.
- **Publish is blocked at a non-zero unreviewed count**, and the button shows the number.
- **Orphan-photo check** at publish: any photo not attached to a finding or limitation gets flagged.
- **Publish is a lock**: hash, timestamp, immutable PDF. Post-delivery edits create a visibly labeled revision with a changelog, never a silent overwrite.
- **Review is phone-first, in the truck.** Desktop is the fallback, though veterans want a real keyboard-driven desktop pass for the evening.

### The agent's report

- **Summary page first**, grouped by severity with counts, one line per item plus location plus a thumbnail. This is 90% of what the agent and the buyer read.
- **A repair request builder from day one.** Tick items, add "credit $X" or "repair by licensed electrician," see a running total, export a PDF for the amendment, with a log of who added or removed what. This is the only part of the software the agent *uses* rather than reads, and it is the retention mechanism the incumbent owns without having designed it.
- **Re-inspection mode**: pull the original items, mark each Repaired, Not Repaired or Not Verified with a new photo, publish a short addendum that lines up item by item with the amendment.
- **Addenda attach to the same link**: radon lab results 48 to 96 hours later, the wood-destroying-insect form, the sewer scope video, with version history and notification. Agents need one link that updates, not a second PDF in the inbox.
- **Publish sequencing the inspector controls.** No push notification to the buyer leading with a safety count while the inspector is still in the attic. The verbal walkthrough comes first.
- **Keep his exact severity labels and colors.** Agents learned them over years and will notice a change before the inspector does.

### The buyer's report

- **Cap the summary at 8 to 10 items the inspector ranks at review time.** The cap forces ranking, which no incumbent makes him do.
- **Design the finding card as a single phone screenshot**: photo, plain-English location such as "Basement, NE corner behind water heater," what it is, why it matters, what to do next. That is the unit of consumption, because they text it to their father.
- **A severity legend at the top in terms of what to do tonight**, not a glossary on page 58.
- **Rewrite limitations for the reader**: "We could not see X because Y. If that worries you, here is who to call and roughly what it costs." This is also where the inspector's radon, sewer scope and termite add-on revenue lives.
- **A property facts card**: roof material and age, panel brand and amperage, pipe materials, water heater and HVAC age. The buyer's insurer asks for exactly these before binding coverage and the buyer is currently the courier flipping through 60 pages.
- **Text-first with real headings, and a JSON representation.** Buyers paste reports into chatbots the night before the deadline. Image-heavy PDFs fail silently at exactly that moment.
- **Thumbnails first, full resolution on tap, dark mode, PDF under 15MB.** They are reading in bed at 11pm and standing in a driveway with no signal the next morning.
- **Permanent links that survive the inspector's lapsed subscription**, for a decade. Median homeowner tenure is around ten years and buyers come back for insurance claims and resale disclosure.

### For firms

- **Master template with roles.** Owner edits, inspectors propose, proposals queue with a diff, one version pushes to everyone with a changelog. No silent personal forks.
- **Per-section generation mode**: approved-library-only or freeform, where freeform output is "proposed narrative, needs owner approval" and cannot publish.
- **A QA queue** showing AI-proposed versus inspector-edited versus final, time on report, acceptance ratio, defects without photos, missing limitations, unsigned agreement, unpaid invoice. Eight reports cleared in 40 minutes is the bar.
- **A drift report.** Fourteen versions of the GFCI narrative across twelve inspectors is invisible in every incumbent, and surfacing it is a product owners will pay for on its own.
- **Two inspectors on one report** with section-level merge, and owner reassignment when a device dies at 3pm.
- **The rubber-stamp signal.** An inspector who accepts 100% of suggestions in four minutes is the owner's biggest liability. Time-on-report and edit ratio are the QA metrics, not prose quality.

---

## 8. Approach

**Sequence by where the hours are, not where the moat is.** Phase one is truck review over camera-roll photos plus dictation, where LTE exists and you can prove the saving without solving crawlspace connectivity. Phase two is the on-site capture app, built local-first, treated as the moat. Phase three is marketing migration, only after a beta cohort has run 200 real inspections without losing a single item.

**Retrieval first, generation last.** Embed the inspector's library, match each note to top-k narratives with a cross-encoder rerank, fall back to generation only below a similarity threshold, and flag that fallback visibly. Ship phase one as "voice shorthand to your own narratives" with zero paraphrase.

**Build the eval harness before the feature.** A per-inspector gold set from your first white-glove customers: their first 20 inspections with every correction captured. Metrics: item recall, false-item rate, severity agreement, photo-binding accuracy, unmatched rate. Block release on regressions. Pin model versions, shadow-evaluate the next one, never let a vendor auto-upgrade you in production.

**Get the library from the source, not from PDFs, wherever a source exists.** Spectora has a documented spreadsheet export of a template. HomeGauge desktop keeps templates as plain files on the inspector's own machine and bundles templates, comments, cover page, agreement, logo and signature in its settings backup, though the reports folder is excluded from that backup and needs a separate pass. Use PDFs to rank which narratives he *actually uses* and to reconstruct where no export exists. Never scrape a logged-in competitor account on the customer's behalf: it gives them a terms-of-service reason to block you and a story to tell.

**Show honest import coverage.** "312 narratives recovered from 10 reports. Your source library likely holds more; export your template to get the rest." A fake 100% is a churn bomb that detonates on the first 1972 house with aluminum wiring.

**Import the template chrome too.** The scope statement, standards reference, system-level "not inspected" boilerplate and the agreement text are not "narratives" and get dropped by naive importers. They are what defense counsel reaches for first.

**Run a boilerplate detector on import.** When text matches a known vendor default or an association library, ask: keep, replace, or rewrite. Do not silently import it as his.

**Migrate the report archive, not just the template.** This is the deepest switching cost and almost nobody addresses it. Agents have bookmarked links. Buyers come back in year three for an insurance claim. States require multi-year retention. Reinspections and 11-month warranty walks reopen the original report, so without the archive he keeps the old subscription and never truly switches. "Your reports stay online after you cancel, forever" in the contract removes that.

**Do the first 100 migrations yourself, on Zoom, recorded, with a hard stop at 100.** It is your parser training set, your onboarding video library, your best sales calls, and a services business you must exit on schedule. Charge firms for it, roughly $2,000 to $5,000, to filter serious buyers.

**Put a quality gate on every import** that counts narratives in versus out, flags every severity or category change, and lists dropped limitations, with a sign-off before the account goes live. A silent severity mis-map is the failure that produces the forum post that costs you fifty signups.

**Build the agent-facing layer before the AI gets fancy.** Report link, summary page, repair request builder, a PDF that matches the old one, agreement e-sign and payment in the same flow. Referral protection is the buying criterion. AI is the tiebreaker.

**Sell the liability QA layer, not speed.** Missing required items, defects without photos, contradictory statements, dropped limitations, unaddressed standards items blocking finalization. Incumbents sell speed. Nobody sells the audit. Then take it to the two or three carriers that dominate inspector errors-and-omissions coverage and ask them to review it. A premium credit moves inspectors faster than any feature.

**Get density in three metros rather than breadth.** When five inspectors in one market use the same report format, agents there learn it and the layout stops being friction.

**Time everything to the season.** Migrate November through February, let them run parallel through February, decide March 1. Nobody switches report software in June.

**Never tie the published report link to billing state.** That link is a document in a real estate transaction with a deadline attached. A failed card can block new reports; it can never dark an agent's access to a published one.

**Twenty ride-alongs with a stopwatch and a tap counter, before more code.** Count how many inspectors actually spend over an hour post-inspection. If fewer than half do, the core pain is smaller than the plan assumes.

---

## 9. The non-obvious things worth keeping

- **Solve photo-to-note association at capture with a gesture, not afterward with machine learning.** No timestamp clustering comes close to hold-to-talk-over-the-photo.
- **General language models are helpfully wrong on inspector shorthand.** They fix grammar, expand abbreviations and "clarify" negatives. "GFCI no trip" comes back as "GFCI tripped as expected." Suppress helpfulness explicitly; the note is ground truth to be matched, not text to be improved.
- **Speech models hallucinate whole sentences in silence and background noise.** A furnace room is exactly that input. Voice activity detection before transcription is not optional.
- **The comments that protect him appear least often**, so ten reports teach you his small talk, not his armor.
- **Data plate OCR plus serial-number date decoding** is the cheapest place to look brilliant. Inspectors do it by hand with lookup tables today.
- **Buyers compare across inspectors; inspectors think they are only compared to the house.** Severity scales are per-inspector, so a buyer on their second report cannot tell whether this house is worse or this inspector is stricter.
- **Repair credits are capped by the buyer's loan, not the seller's generosity.** On a conventional loan under 10% down, seller contributions cap at 3% of price and cannot exceed closing costs. That math decides which items become credits, which become repairs and which the buyer eats. Nobody in inspection software knows it exists.
- **"Recommend further evaluation by a licensed contractor" repeated 23 times** trains the buyer to skim past it, including the one time it was attached to "structural engineer." Boilerplate hedging does not reduce liability; it hides the warning and moves the liability to the lawsuit.
- **Because inspectors are paid per job, the inspector captures the time savings and the firm owner captures nothing.** Sell owners the three things they do capture: ramp time for new hires, review hours, and peak-season capacity.
- **The second user is the spouse at the kitchen table**, who does scheduling, invoicing and follow-up and touches the software more hours a week than the inspector does. She vetoes any switch that breaks her routine.
- **The verbal walkthrough and the written report are two products with opposite tones**, and the buyer trusts the verbal one. Whoever closes that gap in writing wins.
- **Upload time is noticed more than generation time.** Ninety seconds of drafting is forgiven; ten minutes of photo upload on a hotspot in the driveway is not.
- **The top 100 comments cover roughly 80% of report content**, but inspectors believe they use their whole library. Showing an inspector his own usage statistics dissolves most of the switching fear, and no incumbent has any reason to tell him.
- **An agent who reads 100 reports a year has never chosen an inspector for his software, but has dropped inspectors whose reports got worse or slower.** From her chair a software switch has zero upside and real downside, so the only good switch is one she never notices.

---

## 10. First 90 days

1. **Decide this week whether to chase the Horizon shutdown.** It closes December 15, 2026, Spectora is the named migration partner with one-click migration and special pricing, and it is the only forced-switch event in a decade. Chasing it means a Horizon importer, a permanent archive for their old reports and a presence in the association forum thread by late October. Skipping it means the next comparable window is the January-to-February slow season.
2. **Twenty ride-alongs with a stopwatch and a tap counter.** Record where he stalls, when the phone goes in his pocket, how many photos are taken without a note, how many defects he says aloud versus only photographs, and how long the post-inspection work actually takes. Those five numbers are the roadmap and they will correct the premise.
3. **Decide replacement or supplement, and write it down.** Straddling is the most common way this company dies.
4. **Build the capture-and-review loop with zero paraphrase first.** Voice and photo to *his own* narratives, offline, with negation confirmation, an unreviewed counter that blocks publish, and severity inherited from the library. No composition until that works.
5. **Write the retention and data policy before the transcription code**, get a defense attorney and an errors-and-omissions underwriter to review the revision-history design and the wording you use around AI assistance, and publish a one-page plain-English data promise.
6. **Build the agent-facing report and repair request builder in parallel with the field app.** Not after. It is the referral protection that makes an inspector willing to publish from your tool rather than only draft in it.
7. **Recruit ten design partners: five veterans doing 300-plus a year and two or three multi-inspector firms.** Pay them for their time. Interview each one's top three referring agents. Get one agent to say "I like this report better," because that sentence converts an inspector faster than any side-by-side migration demo.
