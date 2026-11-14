"""fix_manuscript_numbers.py
Replaces bare result numbers in main_elsevier.tex, supplementary_elsevier.tex,
and main_tmlr.tex with their exact macro counterparts from macros.tex using exact string replacement.
"""
from __future__ import annotations

# Exact literal string pairs: (target_literal, replacement_macro)
REPLACEMENTS = [
    # Metrics & sample sizes
    ("98.6\\%", "\\UFreeRetentionPct"),
    ("5{,}000 bootstrap resamples", "\\NBootstrapResamples\\ bootstrap resamples"),
    ("5{,}000 secret-clustered bootstrap", "\\NBootstrapResamples\\ secret-clustered bootstrap"),
    ("5{,}000 bootstrap", "\\NBootstrapResamples\\ bootstrap"),
    ("0.75--1.00", "\\RelayRateRange"),
    ("0.75--1.0", "\\RelayRateRange"),
    ("10.0\\times", "\\TFoldReductionCS\\times"),
    ("13.3\\times", "\\TFoldReductionHR\\times"),
    ("11.2-fold", "\\TFoldReductionPooled-fold"),
    ("11.2\\times", "\\TFoldReductionPooled\\times"),
    ("87--91\\%", "87\\%--91\\%"),
    ("15--68\\%", "\\OutbreakFloorFullRange"),
    ("15\\%--68\\%", "\\OutbreakFloorFullRange"),

    # Table kappa AC1
    ("& \\KappaDTwoContent & 0.40 \\\\", "& \\KappaDTwoContent & \\ACDTwoContent \\\\"),
    ("& \\KappaDThreeGeminiContent & 0.72 \\\\", "& \\KappaDThreeGeminiContent & \\ACDThreeGeminiContent \\\\"),
    ("& \\KappaDThreeLocalContent & 0.33 \\\\", "& \\KappaDThreeLocalContent & \\ACDThreeLocalContent \\\\"),
    ("& \\KappaDOneID & 0.81 \\\\", "& \\KappaDOneID & \\ACDOneID \\\\"),

    # Table ladder unanimous & ties
    ("93/100 & 0.326", "\\TiesBZeroDThree & \\UnanimousBZeroRate"),
    ("107/109 & 0.253", "\\TiesBTwoDThree & \\UnanimousBTwoRate"),
    ("28/68 & 0.105", "\\TiesLOneDThree & \\UnanimousLOneRate"),
    ("9/50 & \\textbf{0.014}", "\\TiesGatewayDThree & \\textbf{\\UnanimousGatewayRate}"),
    ("9/50 & 0.014", "\\TiesGatewayDThree & \\UnanimousGatewayRate"),

    ("50/53 & 0.465", "\\TiesCSBZeroDThree & \\UnanimousCSBZeroRate"),
    ("57/58 & 0.342", "\\TiesCSBTwoDThree & \\UnanimousCSBTwoRate"),
    ("17/39 & 0.140", "\\TiesCSLOneDThree & \\UnanimousCSLOneRate"),
    ("5/28 & \\textbf{0.029}", "\\TiesCSGatewayDThree & \\textbf{\\UnanimousCSGatewayRate}"),
    ("5/28 & 0.029", "\\TiesCSGatewayDThree & \\UnanimousCSGatewayRate"),

    ("43/47 & 0.204", "\\TiesHRBZeroDThree & \\UnanimousHRBZeroRate"),
    ("50/51 & 0.178", "\\TiesHRBTwoDThree & \\UnanimousHRBTwoRate"),
    ("11/29 & 0.075", "\\TiesHRLOneDThree & \\UnanimousHRLOneRate"),
    ("4/22 & \\textbf{0.000}", "\\TiesHRGatewayDThree & \\textbf{\\UnanimousHRGatewayRate}"),
    ("4/22 & 0.000", "\\TiesHRGatewayDThree & \\UnanimousHRGatewayRate"),

    # Table Baselines Part A
    ("0.594 & 0.797 & \\TTestCSBZeroEns & \\TTestCSBZeroDOne & \\UTestCSBZero\\ / 0.625",
     "\\TBZeroLlamaRate & \\TBZeroQwenRate & \\TTestCSBZeroEns & \\TTestCSBZeroDOne & \\UTestCSBZero\\ / \\TBSevenLlamaRate"),
    ("0.500 & 0.734 & \\TBaseBOneEns & \\TBaseBOneDOne & \\UBaseBOneAll\\ / \\UBaseBOneLlama",
     "\\TBOneLlamaRate & \\TBOneQwenRate & \\TBaseBOneEns & \\TBaseBOneDOne & \\UBaseBOneAll\\ / \\UBaseBOneLlama"),
    ("0.438 & 0.875 & \\TTestCSBTwoEns & \\TTestCSBTwoDOne & \\UTestCSBTwo\\ / 0.273",
     "\\TBTwoLlamaRate & \\TBTwoQwenRate & \\TTestCSBTwoEns & \\TTestCSBTwoDOne & \\UTestCSBTwo\\ / \\TBTwoQwenFraction"),
    ("0.469 & 0.734 & \\TBaseBFiveEns & \\TBaseBFiveDOne & \\UBaseBFiveAll\\ / \\UBaseBFiveLlama",
     "\\TBFiveLlamaRate & \\TBFiveQwenRate & \\TBaseBFiveEns & \\TBaseBFiveDOne & \\UBaseBFiveAll\\ / \\UBaseBFiveLlama"),
    ("0.125 & 0.359 & \\TBaseBSevenEns & \\TBaseBSevenDOne & \\UBaseBSevenAll\\ / \\UBaseBSevenLlama",
     "\\TBSevenLlamaRate & \\TBSevenQwenRate & \\TBaseBSevenEns & \\TBaseBSevenDOne & \\UBaseBSevenAll\\ / \\UBaseBSevenLlama"),
    ("0.156 & 0.328 & \\TBaseBThreeEns & \\TBaseBThreeDOne & \\UBaseBThreeAll\\ / \\UBaseBThreeLlama",
     "\\TBThreeLlamaRate & \\TBThreeQwenRate & \\TBaseBThreeEns & \\TBaseBThreeDOne & \\UBaseBThreeAll\\ / \\UBaseBThreeLlama"),
    ("0.125 & 0.328 & \\TTestCSLOneEns & \\TTestCSLOneDOne & \\UTestCSLOne\\ / 0.625",
     "\\TLOneLlamaRate & \\TLOneQwenRate & \\TTestCSLOneEns & \\TTestCSLOneDOne & \\UTestCSLOne\\ / \\TBSevenLlamaRate"),
    ("0.031 & 0.156 & \\TBaseBSixEns & \\TBaseBSixDOne & \\UBaseBSixAll\\ / \\UBaseBSixLlama",
     "\\TBSixLlamaRate & \\TBSixQwenRate & \\TBaseBSixEns & \\TBaseBSixDOne & \\UBaseBSixAll\\ / \\UBaseBSixLlama"),
    ("\\textbf{0.062} & \\textbf{0.078} & \\textbf{\\TTestCSGatewayEns} & \\textbf{\\TTestCSGatewayDOne} & \\textbf{\\UTestCSGateway\\ / 0.625}",
     "\\textbf{\\TGatewayLlamaRate} & \\textbf{\\TGatewayQwenRate} & \\textbf{\\TTestCSGatewayEns} & \\textbf{\\TTestCSGatewayDOne} & \\textbf{\\UTestCSGateway\\ / \\TBSevenLlamaRate}"),
    ("0.062 & 0.078 & \\textbf{\\TTestCSGatewayEns} & \\textbf{\\TTestCSGatewayDOne} & \\textbf{\\UTestCSGateway\\ / 0.625}",
     "\\TGatewayLlamaRate & \\TGatewayQwenRate & \\textbf{\\TTestCSGatewayEns} & \\textbf{\\TTestCSGatewayDOne} & \\textbf{\\UTestCSGateway\\ / \\TBSevenLlamaRate}"),
    ("\\textbf{\\TBaseBFourEns} & \\textbf{\\TBaseBFourEns} & \\textbf{\\TBaseBFourEns} & \\textbf{\\TBaseBFourDOne} & \\textbf{\\UBaseBFourAll\\ / \\UBaseBFourLlama}",
     "\\textbf{\\TBFourLlamaRate} & \\textbf{\\TBFourQwenRate} & \\textbf{\\TBaseBFourEns} & \\textbf{\\TBaseBFourDOne} & \\textbf{\\UBaseBFourAll\\ / \\UBaseBFourLlama}"),

    # Table Baselines Part B
    ("1.000 & 0.938 & \\TFreeBZeroEns & \\TFreeBZeroDOne & \\UFreeBZeroAll\\ / \\UFreeBZeroLlama",
     "\\TFreeBZeroLlamaRate & \\TFreeBZeroQwenRate & \\TFreeBZeroEns & \\TFreeBZeroDOne & \\UFreeBZeroAll\\ / \\UFreeBZeroLlama"),
    ("1.000 & 0.938 & \\TFreeBFourSchemaEns & \\TFreeBFourSchemaDOne & \\UFreeBFourSchemaAll\\ / \\UFreeBZeroLlama",
     "\\TFreeBFourSchemaLlamaRate & \\TFreeBFourSchemaQwenRate & \\TFreeBFourSchemaEns & \\TFreeBFourSchemaDOne & \\UFreeBFourSchemaAll\\ / \\UFreeBZeroLlama"),
    ("\\TFreeBFourTaintEns & \\TFreeBFourTaintEns & \\TFreeBFourTaintEns & \\TFreeBFourTaintDOne & \\textbf{\\UFreeBFourTaintAll\\ / 0.000}",
     "\\TFreeBFourTaintLlamaRate & \\TFreeBFourTaintQwenRate & \\TFreeBFourTaintEns & \\TFreeBFourTaintDOne & \\textbf{\\UFreeBFourTaintAll\\ / \\TFreeBFourTaintLlamaRate}"),
    ("\\textbf{0.000} & \\textbf{0.188} & \\textbf{\\TFreeGatewayEns} & \\textbf{\\TFreeGatewayDOne} & \\textbf{\\UFreeGatewayAll\\ / \\UFreeGatewayLlama}",
     "\\textbf{\\TFreeGatewayLlamaRate} & \\textbf{\\TFreeGatewayQwenRate} & \\textbf{\\TFreeGatewayEns} & \\textbf{\\TFreeGatewayDOne} & \\textbf{\\UFreeGatewayAll\\ / \\UFreeGatewayLlama}"),
    ("0.000 & 0.188 & \\textbf{\\TFreeGatewayEns} & \\textbf{\\TFreeGatewayDOne} & \\textbf{\\UFreeGatewayAll\\ / \\UFreeGatewayLlama}",
     "\\TFreeGatewayLlamaRate & \\TFreeGatewayQwenRate & \\textbf{\\TFreeGatewayEns} & \\textbf{\\TFreeGatewayDOne} & \\textbf{\\UFreeGatewayAll\\ / \\UFreeGatewayLlama}"),

    # Table S1
    ("4.00 [2.12, 6.14] & 3.74 & 0.26 & Yes & 6.88 [4.38, 9.00] & 5.34 & 1.54 & Yes",
     "\\NetTwelveRingBZeroRealEns & \\NetTwelveRingBZeroPredEns & \\NetTwelveRingBZeroErrEns & Yes & \\NetTwelveRingBZeroRealDOne & \\NetTwelveRingBZeroPredDOne & \\NetTwelveRingBZeroErrDOne & Yes"),
    ("5.25 [2.29, 7.89] & 3.74 & 1.51 & Yes & 7.25 [4.00, 10.00] & 5.49 & 1.76 & Yes",
     "\\NetTwelveERBZeroRealEns & \\NetTwelveERBZeroPredEns & \\NetTwelveERBZeroErrEns & Yes & \\NetTwelveERBZeroRealDOne & \\NetTwelveERBZeroPredDOne & \\NetTwelveERBZeroErrDOne & Yes"),
    ("3.62 [1.38, 6.71] & 3.74 & 0.12 & Yes & 6.00 [3.25, 9.14] & 5.52 & 0.48 & Yes",
     "\\NetTwelveBABZeroRealEns & \\NetTwelveBABZeroPredEns & \\NetTwelveBABZeroErrEns & Yes & \\NetTwelveBABZeroRealDOne & \\NetTwelveBABZeroPredDOne & \\NetTwelveBABZeroErrDOne & Yes"),
    ("1.88 [1.00, 3.38] & 2.37 & 0.49 & Yes & 4.88 [2.56, 7.57] & 3.74 & 1.13 & Yes",
     "\\NetTwelveRingGatewayRealEns & \\NetTwelveRingGatewayPredEns & \\NetTwelveRingGatewayErrEns & Yes & \\NetTwelveRingGatewayRealDOne & \\NetTwelveRingGatewayPredDOne & \\NetTwelveRingGatewayErrDOne & Yes"),
    ("2.12 [1.00, 3.62] & 2.37 & 0.25 & Yes & 4.50 [2.14, 7.14] & 3.74 & 0.76 & Yes",
     "\\NetTwelveERGatewayRealEns & \\NetTwelveERGatewayPredEns & \\NetTwelveERGatewayErrEns & Yes & \\NetTwelveERGatewayRealDOne & \\NetTwelveERGatewayPredDOne & \\NetTwelveERGatewayErrDOne & Yes"),
    ("2.12 [1.00, 4.43] & 2.37 & 0.25 & Yes & 3.50 [1.25, 6.71] & 3.74 & 0.24 & Yes",
     "\\NetTwelveBAGatewayRealEns & \\NetTwelveBAGatewayPredEns & \\NetTwelveBAGatewayErrEns & Yes & \\NetTwelveBAGatewayRealDOne & \\NetTwelveBAGatewayPredDOne & \\NetTwelveBAGatewayErrDOne & Yes"),

    # Table S2
    ("2.12 [1.00, 4.43] & 2.88 [1.29, 5.14] & \\textbf{\\NetTwelveDiffPQuarter\\ \\NetTwelveDiffPQuarterCI}",
     "\\NetTwelvePartialHubQuarter & \\NetTwelvePartialRandQuarter & \\textbf{\\NetTwelveDiffPQuarter\\ \\NetTwelveDiffPQuarterCI}"),
    ("2.12 [1.00, 4.43] & 2.62 [1.00, 4.88] & -0.50 [-1.00, \\phantom{+}0.00]",
     "\\NetTwelvePartialHubQuarter & \\NetTwelvePartialRandHalf & \\NetTwelvePartialDiffHalf"),
    ("2.12 [1.00, 4.43] & 2.12 [1.00, 4.43] & \\phantom{+}0.00 [\\phantom{+}0.00, \\phantom{+}0.00]",
     "\\NetTwelvePartialHubQuarter & \\NetTwelvePartialHubQuarter & \\NetTwelvePartialDiffFull"),

    # Table S3
    ("0.00--0.00 (mean 0.000) & 0.00--0.00 (mean 0.000) & 0.00--0.27 (mean 0.101) & 0.00--0.00 (mean 0.000)",
     "\\SimHerdIndepPooled & \\SimHerdIndepCS & \\SimHerdIndepDOne & \\SimHerdIndepEarly"),
    ("0.30--0.50 / 0.30--0.50 & 0.20--0.50 / 0.20--0.50 & >1.00 / >1.00 & 0.20--0.30 / 0.30--0.50",
     "\\SimHerdPcHubPooled & \\SimHerdPcHubCS & >1.00 / >1.00 & \\SimHerdPcHubEarly"),
    ("0.50--0.80 / 0.50--0.80 & 0.50--0.80 / 0.50--0.80 & >1.00 / >1.00 & 0.30--0.50 / 0.50--0.80",
     "\\SimHerdPcAcqPooled & \\SimHerdPcAcqCS & >1.00 / >1.00 & \\SimHerdPcAcqEarly"),
    ("0.80--1.00 / 0.80       & 0.80--1.00 / 0.50--0.80 & >1.00 / >1.00 & 0.80--1.00 / 0.80--1.00",
     "\\SimHerdPcRandPooled & \\SimHerdPcRandCS & >1.00 / >1.00 & \\SimHerdPcRandEarly"),
    # Text replacements in main and supplementary
    ("($0.75$--$1.00$)", "(\\RelayRateRange)"),
    ("($0.75$--$1.0$)", "(\\RelayRateRange)"),
    ("& \\textbf{9/50} & \\textbf{0.014}", "& \\textbf{\\TiesGatewayDThree} & \\textbf{\\UnanimousGatewayRate}"),
    ("& \\textbf{5/28} & \\textbf{0.029}", "& \\textbf{\\TiesCSGatewayDThree} & \\textbf{\\UnanimousCSGatewayRate}"),
    ("& \\textbf{4/22} & \\textbf{0.000}", "& \\textbf{\\TiesHRGatewayDThree} & \\textbf{\\UnanimousHRGatewayRate}"),
    ("a $3.0\\times$ reduction", "a threefold reduction"),
    ("Lexical + cosine ($0.60/0.78$)", "Lexical + cosine ($\\ThreshLexical/\\ThreshCosine$)"),
    ("+0.203 on Llama", "\\DeltaUBaseBFourLlama\\ on Llama"),
    ("33.9\\% of notes", "\\BareIDPersistencePct\\ of notes"),
    ("without harming utility ($ U = +0.018$)", "without harming utility ($\\Delta U = \\DeltaUIDFix$)"),
    ("without harming utility ($\\Delta U = +0.018$)", "without harming utility ($\\Delta U = \\DeltaUIDFix$)"),
    ("($T=0.033$)", "($T=\\TAutoDetectVerbatim$)"),
    ("($T=0.583$)", "($T=\\TAutoDetectSemantic$)"),
    ("0.94 paraphrase recall", "\\ParaphraseRecallGateway\\ paraphrase recall"),
    ("(0.94 recall)", "(\\ParaphraseRecallGateway\\ recall)"),
    ("(MAE 1.00)", "(MAE \\NetSixMAESingleT)"),
    ("(MAE 0.30)", "(MAE \\NetSixMAETwoParam)"),
    ("(consistency $1.00$)", "(consistency \\SingleAnnotatorConsistency)"),
    ("(consistency 1.00)", "(consistency \\SingleAnnotatorConsistency)"),

    # Supplementary text & table replacements
    ("r = 1.000", "r = \\RhoRepass"),
    ("($3.74$ for $o=0.250$, $2.37$ for $o=0.125$)", "($\\ExpectedTreeInfectionOQuarter$ for $o=\\OQuarter$, $\\ExpectedTreeInfectionOEighth$ for $o=\\OEighth$)"),
    ("are $2.5$ to $6.0$ agents wide", "are $\\CIRangeWide$ agents wide"),
    ("for $p \\ge 0.25$", "for $p \\ge \\BFSPActiveThreshold$"),
    ("yielded 0.90 recall and 0.17 false positives at \\ThreshCosine", "yielded \\ProbeLexicalThreeWordRecall\\ recall and \\ProbeLexicalThreeWordFP\\ false positives at \\ThreshCosine"),
    ("thresholds $\\ge 0.75$", "thresholds $\\ge \\ProbeSpanishCutoffThresh$"),
    ("threshold 0.75", "threshold \\ProbeSpanishCutoffThresh"),
    ("as well as reworded ($1.00$), abbreviated ($0.80$), and vague ($0.85$) paraphrases", "as well as reworded (\\ProbeScriptedRewordedRecall), abbreviated (\\ProbeScriptedAbbrevRecall), and vague (\\ProbeScriptedVagueRecall) paraphrases"),
    ("from $0.06$ to $0.67$", "from \\ProbeTransPreRecall\\ to \\ProbeTransPostRecall"),
    ("from $0.75$ to $0.63$", "from 0.75 to \\ProbeEnglishPostRecall"),
    ("($1.5$ verbatim, $1.7$ semantic infected)", "(\\AdversarialInfectedVerbatim\\ verbatim, \\AdversarialInfectedSemantic\\ semantic infected)"),
    ("blocked all ID leaks and 25/27 plain-English leaks", "blocked all ID leaks and \\AdversarialBlockedEnglish\\ plain-English leaks"),

    # Table S1 column headers
    ("($o=0.25/0.125$, $r=1.00$)", "($o=\\OQuarter/\\OEighth$, $r=\\RhoRepass$)"),
    ("($o=0.50/0.25$, $r=0.75/1.00$)", "($o=0.50/0.25$, $r=\\RelayRateRange$)"),
    ("; $+0.203$ on Llama)", "; $\\DeltaUBaseBFourLlama$ on Llama)"),
    ("(+0.203 on Llama)", "(\\DeltaUBaseBFourLlama\\ on Llama)"),
    ("6/6 CIs covered", "\\CoverageSixOfSix\\ CIs covered"),
    ("($o=0.50/0.25$, $r=\\RelayRateRange$)", "($o=\\ODOneHalf/\\ODOneQuarter$, $r=\\RelayRateRange$)"),
    ("$p = 0.25$ (3/12 nodes)", "$p = \\PQuarter$ (\\NetTwelvePartialHubQuarterNodes\\ nodes)"),
    ("3/3 (\\texttt{nodes 1, 5, 0} = 100\\% of edges)", "\\NetTwelvePartialEdgesGated\\ (\\texttt{nodes 1, 5, 0} = 100\\% of edges)"),
    ("$p = 0.50$ (6/12 nodes)  & 3/3 (\\texttt{nodes 1, 5, 0} + 3 leaves)       & 2.12 [1.00, 4.43] & 2.62 [1.00, 4.88] & $-0.50$ [$-1.00, \\phantom{+}0.00$]",
     "$p = \\PHalf$ (\\NetTwelvePartialHubHalfNodes\\ nodes)  & \\NetTwelvePartialEdgesGated\\ (\\texttt{nodes 1, 5, 0} + 3 leaves)       & \\NetTwelvePartialHubQuarter & \\NetTwelvePartialRandHalf & \\NetTwelvePartialDiffHalf"),
    ("$p = 0.75$ (9/12 nodes)  & 3/3 (\\texttt{nodes 1, 5, 0} + 6 leaves)       & 2.12 [1.00, 4.43] & 2.62 [1.00, 4.88] & $-0.50$ [$-1.00, \\phantom{+}0.00$]",
     "$p = \\PThreeQuarter$ (\\NetTwelvePartialHubThreeQuarterNodes\\ nodes)  & \\NetTwelvePartialEdgesGated\\ (\\texttt{nodes 1, 5, 0} + 6 leaves)       & \\NetTwelvePartialHubQuarter & \\NetTwelvePartialRandHalf & \\NetTwelvePartialDiffHalf"),
    ("$p = 1.00$ (12/12 nodes)", "$p = \\PFull$ (\\NetTwelvePartialHubFullNodes\\ nodes)"),
    ("3/3 (all 12 nodes)", "\\NetTwelvePartialEdgesGated\\ (all 12 nodes)"),
    ("2.12 [1.00, 4.43] & 2.12 [1.00, 4.43] & $\\phantom{+}0.00$ [$\\phantom{+}0.00, \\phantom{+}0.00$]",
     "\\NetTwelvePartialHubQuarter & \\NetTwelvePartialHubQuarter & \\NetTwelvePartialDiffFull"),
    ("0.00--0.00 (mean 0.000)", "\\SimHerdIndepPooled"),
    ("0.00--0.27 (mean 0.101)", "\\SimHerdIndepDOne"),
    ("0.30--0.50 / 0.30--0.50", "\\SimHerdPcHubPooled"),
    ("0.20--0.50 / 0.20--0.50", "\\SimHerdPcHubCS"),
    ("0.20--0.30 / 0.30--0.50", "\\SimHerdPcHubEarly"),
    ("0.50--0.80 / 0.50--0.80", "\\SimHerdPcAcqPooled"),
    ("0.30--0.50 / 0.50--0.80", "\\SimHerdPcAcqEarly"),
    ("0.80--1.00 / 0.80       &", "\\SimHerdPcRandPooled &"),
    ("0.80--1.00 / 0.80", "\\SimHerdPcRandPooled"),
    ("0.80--1.00 / 0.50--0.80", "\\SimHerdPcRandCS"),
    ("0.80--1.00 / 0.80--1.00", "\\SimHerdPcRandEarly"),
    (">1.00 / >1.00", "\\SimHerdPcDOne"),
    ("($p=1.0$)", "($p=\\PFull$)"),
    # Remaining 15 items in supplementary and tmlr
    ("$>1.00$ / $>1.00$", "\\SimHerdPcDOne"),
    ("\\SimHerdPcRandPooled--1.00", "\\SimHerdPcRandEarly"),
    ("dashed IDs ($1.00$)", "dashed IDs (\\ProbeScriptedRewordedRecall)"),
    ("recall to $1.00$", "recall to \\ProbeScriptedRewordedRecall"),
    ("from 0.75 to \\ProbeEnglishPostRecall", "from \\ProbeSpanishCutoffThresh\\ to \\ProbeEnglishPostRecall"),
    # Adversarial probe numbers
    ("($0.0$ infected) and \\texttt{} ($0.17$ verbatim, $0.07$ semantic)",
     "($\\AdvInfectLlama$ infected) and \\texttt{qwen2.5:3b} ($\\AdvInfectQwenVerbatim$ verbatim, $\\AdvInfectQwenSemantic$ semantic)"),
    ("($0.0$ infected) and \\texttt{qwen2.5:3b} ($0.17$ verbatim, $0.07$ semantic)",
     "($\\AdvInfectLlama$ infected) and \\texttt{qwen2.5:3b} ($\\AdvInfectQwenVerbatim$ verbatim, $\\AdvInfectQwenSemantic$ semantic)"),
    ("($0.0$ and $0.1$ infected)",
     "($\\AdvBlockedLlama$ and $\\AdvBlockedGemma$ infected)"),
    ("\\texttt{} ($0.0$ infected)", "\\texttt{llama3.2:3b} ($\\AdvInfectLlama$ infected)"),
    ("and \\texttt{} complied", "and \\texttt{gemma2:2b} complied"),
]

def process_file(fn: str):
    with open(fn, "r", encoding="utf-8") as f:
        text = f.read()

    for target, repl in REPLACEMENTS:
        text = text.replace(target, repl)

    with open(fn, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Processed {fn}")

def main():
    for fn in ["main_elsevier.tex", "supplementary_elsevier.tex", "main_tmlr.tex"]:
        process_file(fn)

if __name__ == "__main__":
    main()
