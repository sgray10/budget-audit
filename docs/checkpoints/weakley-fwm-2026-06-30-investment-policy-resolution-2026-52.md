# Checkpoint: Weakley FWM 2026-06-30 Resolution 2026-52 (Investment Policy)

## Scope

This is document/policy-text analysis, not fund-reconciliation work (issue #10). Covers the packet's Resolution No. 2026-52, "Resolution Amending the Weakley County Investment Policy," and its two attached policy exhibits.

Pages, all within the packet's front-matter range (never previously OCR'd for extraction, since this range is outside the budget-table page range 23-158 that fund extraction covers):

- Page 1: FWM committee agenda (lists Resolution 2026-52 as item `h`).
- Pages 3-5: minutes of the prior (2026-06-01) FWM meeting -- unrelated to this resolution, included here only because they share the front-matter page range that had to be rendered/OCR'd to reach page 6.
- Pages 6-7: Resolution 2026-52 itself (the enactment text and signature blocks).
- Pages 8-14: the **original** investment policy, stamped "ORIGINAL" in the page margin. 7 internal pages.
- Pages 15-22: the **amended** investment policy. 8 internal pages. This copy is itself a redline: text carried over unchanged from the original is printed in black, and every substantively new or replaced passage is printed in red ink in the source PDF. This is not an OCR artifact -- it is how the document distinguishes old from new.

## Reproducible command chain

Pages 3-22 were rendered and OCR'd for the first time as part of this work (they were previously untouched -- see the project's OCR scope note that pages 1-19/20-22 were "never in scope for fund extraction"):

    budget-audit render-pages data/raw/FWM-Meeting-Packet-6-30-26.pdf --pages 3-22 --out data/interim/rendered --dpi 300
    budget-audit ocr-pages data/interim/rendered --pages 3-22 --out data/interim/ocr

The OCR text was used only to locate content and as a first-pass cross-check; the transcription below was read and verified directly against the rendered page images (`data/interim/rendered/page-0XX.png`), the same discipline used for hand-verifying budget-table corrections elsewhere in this project. `data/interim/` is not committed (see `.gitignore`); re-run the two commands above to reproduce these working files.

## What the resolution does

Resolution 2026-52 (page 6) recites that the county adopted an investment policy attached to Resolution 2005-10 in September 2004, that the investment committee has since made amendments in accordance with Tennessee Code Annotated (TCA) Section 5-8-301, and resolves that "the attached Investment Policy be adopted." It repeals any conflicting prior resolutions and takes effect on passage (June 30, 2026).

## What changed between the original and amended policy (open question, `docs/weakley-county.md`)

Based on the source document's own redline (red text on pages 15-22), the amendment is concentrated in two sections. Everything else in the policy (Scope; General Objectives; Standards of Care items 1-2; Safekeeping and Custody; Collateralization/Repurchase Agreements headings; Investment Parameters; Reporting; Policy Considerations) is unchanged between the two copies.

**1. Section III.3, "Delegation of Authority" (original: page 10; amended: page 17).** The amended version keeps the original's TCA 5-21-105/5-21-107 citation and general delegation-to-"the investment officer" language, and adds:

- An explicit description of the investment committee's membership: "the County Trustee, County Mayor, County Director of Finance and 2 County Commissioners."
- A parenthetical naming the investment officer as "(trustee)."
- A new closing sentence: "The investment committee voted unanimously to allow the County Trustee and/or Finance Director to invest county funds without a formal vote from the committee to allow higher earning potential of county funds and give updates at financial management, finance ways and means when requested by any commissioner (November 18, 2024)."

**2. Section V, retitled "Suitable and Authorized Investments/Investment Types" (original: page 11-12; amended: page 18-20).** The original stated permitted investment types as a short bullet list. The amended version replaces that list with language that quotes TCA Section 5-8-301 through 5-8-303 directly, section by section. Within that rewrite, two changes affect what's actually permitted rather than just how it's cited:

- The nonconvertible-debt-security issuer list (item 6 in the amended numbering) drops "the student loan marketing association" (present in the original) and adds "the federal home loan mortgage corporation," plus a new catch-all for "any other obligations that are guaranteed as to principal and interest by the United States or any of its agencies."
- A new subsection (c) caps investments with 2-5 year maturities at 20% of idle funds, and separately permits counties with population between 20,000 and 150,000 to invest idle funds in prime commercial paper under specified conditions (highest-rated paper, 90-day maximum maturity, investment committee must adopt written policies first). Weakley County's 2020 census population is in that range, so this provision is applicable here, though the amendment doesn't state whether the county has exercised it.
- The Collateralization heading (item 4) gains an explicit citation, "Section § 9-4-105," alongside the pre-existing GFOA-practice reference.

No other content differs between the two copies; the redline in the source stops after this subsection (c), and the remainder of both documents (Maximum Maturities onward) reads the same.

## Other open questions from `docs/weakley-county.md`

- **Who has delegated authority to invest idle county funds?** The investment officer, whom the amended policy identifies as the County Trustee. An investment committee (County Trustee, County Mayor, County Director of Finance, 2 County Commissioners) delegated day-to-day investment authority to the County Trustee and/or Finance Director without requiring a formal committee vote per transaction, per the November 18, 2024 vote referenced in the amended text above.
- **What reports are required, how often, and are they public?** Section VII requires the investment officer to prepare a report at least bimonthly (securities held, realized/unrealized gains or losses, weighted average yield vs. benchmarks, listing by maturity date, percentage of portfolio by investment type), addressed to the county legislative body. This requirement is unchanged between the original and amended policy. **Needs review:** the policy text doesn't say whether these bimonthly reports are published or otherwise available on request; this packet doesn't include any actual investment report, only the policy that requires one. A public-records request for recent bimonthly investment reports would answer whether this requirement is being met in practice.
- **Are investment reports reconciled against policy requirements?** The policy states the bimonthly report should be prepared so the legislative body "can ascertain whether investment activities...have conformed to the investment policy" -- so oversight is built into the reporting requirement by design. **Needs review:** this packet contains only the policy itself, not any actual investment report, so whether that reconciliation happens in practice can't be confirmed from this source.

## Verification

Every page cited above (1, 3-22) was read directly from the rendered PNG images, not solely from OCR text, given the higher error rate of OCR on prose/legal formatting compared to the structured budget tables elsewhere in this project. The "ORIGINAL" stamp on page 8 and the red/black redline coloring on pages 15-22 are visual features of the source scan, confirmed by direct inspection, not inferred from OCR output.

This is a text/policy analysis, so there is no reconciliation number to verify against a packet total the way fund extraction is checked. The two things that could be independently re-verified: (1) that pages 8-14 and 15-22 are in fact near-duplicate policy documents (confirmed via a whitespace-normalized diff of the two OCR passes, `similarity ratio` ~0.71, consistent with mostly-shared text plus the substantive additions above), and (2) that the redline coloring lines up with those same substantive additions (confirmed by direct visual inspection page by page).
