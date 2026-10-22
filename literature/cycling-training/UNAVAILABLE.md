# Remaining access gaps

Updated 22 October 2026 after importing the user's seven MinerU conversions and matching original PDFs. Five resolve previously missing core papers; two provide additional HRV evidence. One original selection remains abstract-only.

## Full paper still missing

**Javaloyes et al. (2019), Training Prescription Guided by Heart-Rate Variability in Cycling.** DOI `10.1123/ijspp.2018-0122`, PMID 29809080. [Publisher/manual download](https://journals.humankinetics.com/view/journals/ijspp/14/1/article-p23.xml) · [Current abstract-only assessment](papers/29809080/notes.md).

The supplied file is instead **Javaloyes et al. (2020), Training Prescription Guided by Heart Rate Variability Vs. Block Periodization in Well-Trained Cyclists**, DOI `10.1519/JSC.0000000000003337`, PMID 31490431. It is saved and assessed as a [separate supporting paper](papers/31490431/notes.md). It does not verify the 2019 paper's methods or replace its record. The further [Alfonso et al. 2025 paper](papers/41028151/notes.md) is now available as another relevant alternative for evaluating combined monitoring; it also does not supply the missing original.

The earlier ETH attempt for the 2019 paper returned `blocked_or_login_required`, HTTP 403. An ETH network was detected, but the response does not establish whether publisher blocking, authentication, or entitlement caused the failure. No successful new retrieval of that paper is claimed.

## Correction still unresolved

Neal's PubMed metadata links an **erratum: J Appl Physiol (1985), 2013 May 15;114(10):1490**. A separate correction was not included among the supplied files. Earlier PubMed citation lookup and journal/year/page searches did not resolve its contents; no DOI is asserted. The correction's impact remains unknown, and the downloaded main paper is not assumed to include it. [Publisher article page](https://journals.physiology.org/doi/10.1152/japplphysiol.00652.2012).

## Full text obtained, original PDF still missing

These are **not abstract-only**. Full text was obtained and read through PubMed/PMC; original-PDF checks remain unavailable.

| Paper | Manual download | Previous retrieval outcome |
|---|---|---|
| Little et al. (2010), *A practical model of low-volume high-intensity interval training induces mitochondrial biogenesis in human skeletal muscle* | [Publisher / DOI](https://onlinelibrary.wiley.com/doi/10.1113/jphysiol.2009.181743); [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC2849965/) | ETH candidate was not a PDF; this failure does not negate the successful PubMed HTML retrieval |
| Saw et al. (2016), *Monitoring the athlete training response: subjective self-reported measures trump commonly used objective measures* | [BMJ](https://bjsm.bmj.com/content/50/5/281); [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC4789708/) | PMC candidate was not a PDF; publisher follow-up returned HTTP 403 |

## Resolved by manual import

| Previously missing core paper | Now available |
|---|---|
| [Galán-Rioja, periodization](papers/36640771/notes.md) | Original PDF and preserved MinerU Markdown |
| [Seiler, interval duration/intensity](papers/21812820/notes.md) | Original PDF and preserved MinerU Markdown; conversion is needed because PDF body text is not machine-readable |
| [Rønnestad, short versus long intervals](papers/24382021/notes.md) | Original PDF and preserved MinerU Markdown |
| [Neal, polarized versus threshold](papers/23264537/notes.md) | Original PDF and preserved MinerU Markdown; linked erratum remains unresolved |
| [Wong, FTP](papers/36803419/notes.md) | Original PDF and preserved MinerU Markdown |

[Import provenance and filenames](manual-import.json) record all seven moves and hashes. Source Markdown was preserved byte-for-byte under descriptive names; original PDFs were copied, leaving their Downloads copies in place. Historical HTTP failures remain in the access manifest and raw local logs. Only the **current** access flags were upgraded after matching and assessment.

Future originals can be placed at `sources/<PMID>/original.pdf`. Source copies remain local and Git-ignored. Update assessment and verification status after reviewing each new source; do not silently promote a paper because a related title has become available.
