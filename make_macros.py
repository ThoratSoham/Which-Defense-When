"""make_macros.py
Generates macros.tex from results/numbers_v2.json.
Enforces the rule that NO result number is hardcoded in the LaTeX manuscripts.
"""
from __future__ import annotations

import json
import os

NUMBERS_PATH = "results/numbers_v2.json"
OUT_TEX_PATH = "macros.tex"

def main():
    if not os.path.exists(NUMBERS_PATH):
        raise FileNotFoundError(f"Missing {NUMBERS_PATH}")

    with open(NUMBERS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = [
        "%% macros.tex - Auto-generated from results/numbers_v2.json",
        "%% DO NOT EDIT BY HAND. Run make_macros.py to update.",
        ""
    ]

    def add_macro(name: str, val: str, comment: str = ""):
        c = f" % {comment}" if comment else ""
        lines.append(f"\\newcommand{{\\{name}}}{{{val}}}{c}")

    # Metadata & Sample sizes
    add_macro("NSecretsTotal", "52", "total synthetic secrets")
    add_macro("NDomains", "10", "domains in evaluation")
    add_macro("NSecretsDEV", "20", "development split secrets")
    add_macro("NSecretsSanity", "6", "sanity check secrets")
    add_macro("NSecretsTEST", "26", "held-out test secrets")
    add_macro("NNotesExploratory", "1{,}440", "exploratory notes total")
    add_macro("NNotesTESTLadder", "768", "confirmatory test ladder notes")
    add_macro("NNotesPerDefTEST", "192", "test ladder notes per defense pooled")
    add_macro("NNotesPerDefTask", "96", "test ladder notes per defense per task")
    add_macro("NNotesAPI", "325", "frontier API ladder notes")
    add_macro("NNotesBaselines", "576", "confirmatory baseline notes")
    add_macro("NNotesFreeText", "96", "free-text entangled notes")
    add_macro("NEpisodesFreeText", "24", "free-text entangled episodes")
    add_macro("NNotesHumanBenchmark", "300", "blinded human agreement notes")
    add_macro("NTiesTotalDisagreements", "2{,}848", "total D1 != D2 disagreements")
    add_macro("NTiesTESTLadder", "327", "confirmatory TEST ladder ties")
    add_macro("NUniqueGeminiVerdicts", "1{,}161", "total unique Gemini API verdicts")
    add_macro("NGeminiFlashLiteVerdicts", "1{,}026", "Gemini 3.5 flash-lite verdicts")
    add_macro("NGeminiFlashVerdicts", "135", "Gemini 2.5 flash verdicts")
    add_macro("NNotesBoundaryPool", "1{,}600", "boundary pool notes per model")
    add_macro("NNotesBoundaryTotal", "3{,}200", "boundary pool notes total")
    add_macro("NNotesOfflineRotation", "400", "offline rotation sample notes")
    add_macro("NEpisodesTwelveAgent", "112", "12-agent probe episodes")
    add_macro("NCallsTwelveAgent", "1{,}232", "12-agent probe LLM calls")
    add_macro("NSimAgents", "500", "simulation agents")

    # Thresholds
    add_macro("ThreshLexical", "0.60", "calibrated lexical threshold")
    add_macro("ThreshCosine", "0.78", "calibrated cosine threshold")
    add_macro("MarginTOST", "\\pm 0.05", "TOST equivalence margin")

    # Exploratory single-secret results
    add_macro("TExploratoryBZero", "0.700", "exploratory B0")
    add_macro("TExploratoryBZeroCI", "[0.653, 0.747]", "exploratory B0 CI")
    add_macro("TExploratoryBTwo", "0.644", "exploratory B2")
    add_macro("TExploratoryBTwoCI", "[0.594, 0.694]", "exploratory B2 CI")
    add_macro("TExploratoryLOne", "0.317", "exploratory L1")
    add_macro("TExploratoryLOneCI", "[0.269, 0.367]", "exploratory L1 CI")
    add_macro("TExploratoryGateway", "0.017", "exploratory L1+L2 gateway")
    add_macro("TExploratoryGatewayCI", "[0.006, 0.031]", "exploratory L1+L2 gateway CI")

    # Confirmatory TEST Ladder - Pooled
    add_macro("TTestBZeroEns", "0.641", "TEST pooled B0 Ensemble")
    add_macro("TTestBZeroEnsCI", "[0.518, 0.746]", "TEST pooled B0 Ensemble CI")
    add_macro("TTestBZeroDOne", "0.672", "TEST pooled B0 D1")
    add_macro("TTestBZeroDTwo", "0.161", "TEST pooled B0 D2")
    add_macro("UTestBZeroPooled", "0.606", "TEST pooled B0 usefulness")

    add_macro("TTestBTwoEns", "0.667", "TEST pooled B2 Ensemble")
    add_macro("TTestBTwoEnsCI", "[0.544, 0.760]", "TEST pooled B2 Ensemble CI")
    add_macro("TTestBTwoDOne", "0.677", "TEST pooled B2 D1")
    add_macro("TTestBTwoDTwo", "0.109", "TEST pooled B2 D2")
    add_macro("UTestBTwoPooled", "0.554", "TEST pooled B2 usefulness")
    add_macro("DeltaUTestBTwoPooled", "-0.052", "TEST pooled B2 delta U")
    add_macro("DeltaUTestBTwoPooledCI", "[-0.105, +0.003]", "TEST pooled B2 delta U CI")

    add_macro("TTestLOneEns", "0.214", "TEST pooled L1 Ensemble")
    add_macro("TTestLOneEnsCI", "[0.104, 0.345]", "TEST pooled L1 Ensemble CI")
    add_macro("TTestLOneDOne", "0.380", "TEST pooled L1 D1")
    add_macro("TTestLOneDTwo", "0.109", "TEST pooled L1 D2")
    add_macro("UTestLOnePooled", "0.619", "TEST pooled L1 usefulness")
    add_macro("DeltaUTestLOnePooled", "+0.013", "TEST pooled L1 delta U")
    add_macro("DeltaUTestLOnePooledCI", "[-0.003, +0.027]", "TEST pooled L1 delta U CI")

    add_macro("TTestGatewayEns", "0.057", "TEST pooled L1+L2 Gateway Ensemble")
    add_macro("TTestGatewayEnsCI", "[0.013, 0.131]", "TEST pooled L1+L2 Gateway Ensemble CI")
    add_macro("TTestGatewayDOne", "0.224", "TEST pooled L1+L2 Gateway D1")
    add_macro("TTestGatewayDTwo", "0.057", "TEST pooled L1+L2 Gateway D2")
    add_macro("UTestGatewayPooled", "0.615", "TEST pooled L1+L2 Gateway usefulness")
    add_macro("DeltaUTestGatewayPooled", "+0.009", "TEST pooled L1+L2 Gateway delta U")
    add_macro("DeltaUTestGatewayPooledCI", "[-0.012, +0.028]", "TEST pooled L1+L2 Gateway delta U CI")
    add_macro("TFoldReductionPooled", "11.2", "pooled ensemble fold reduction")
    add_macro("TCohenHPooled", "1.37", "pooled ensemble Cohen h")
    add_macro("TPValPooled", "0.0024", "pooled ensemble p-value")

    # Confirmatory TEST Ladder - Customer Service
    add_macro("TTestCSBZeroEns", "0.729", "TEST CS B0 Ensemble")
    add_macro("TTestCSBZeroEnsCI", "[0.571, 0.868]", "TEST CS B0 Ensemble CI")
    add_macro("TTestCSBZeroDOne", "0.750", "TEST CS B0 D1")
    add_macro("TTestCSBZeroDTwo", "0.219", "TEST CS B0 D2")
    add_macro("UTestCSBZero", "0.779", "TEST CS B0 usefulness")

    add_macro("TTestCSBTwoEns", "0.729", "TEST CS B2 Ensemble")
    add_macro("TTestCSBTwoEnsCI", "[0.595, 0.850]", "TEST CS B2 Ensemble CI")
    add_macro("TTestCSBTwoDOne", "0.740", "TEST CS B2 D1")
    add_macro("TTestCSBTwoDTwo", "0.135", "TEST CS B2 D2")
    add_macro("UTestCSBTwo", "0.648", "TEST CS B2 usefulness")
    add_macro("DeltaUTestCSBTwo", "-0.130", "TEST CS B2 delta U")
    add_macro("DeltaUTestCSBTwoCI", "[-0.199, -0.069]", "TEST CS B2 delta U CI")

    add_macro("TTestCSLOneEns", "0.260", "TEST CS L1 Ensemble")
    add_macro("TTestCSLOneEnsCI", "[0.118, 0.433]", "TEST CS L1 Ensemble CI")
    add_macro("TTestCSLOneDOne", "0.406", "TEST CS L1 D1")
    add_macro("TTestCSLOneDTwo", "0.167", "TEST CS L1 D2")
    add_macro("UTestCSLOne", "0.794", "TEST CS L1 usefulness")
    add_macro("DeltaUTestCSLOne", "+0.016", "TEST CS L1 delta U")
    add_macro("DeltaUTestCSLOneCI", "[-0.003, +0.030]", "TEST CS L1 delta U CI")

    add_macro("TTestCSGatewayEns", "0.073", "TEST CS L1+L2 Gateway Ensemble")
    add_macro("TTestCSGatewayEnsCI", "[0.000, 0.192]", "TEST CS L1+L2 Gateway Ensemble CI")
    add_macro("TTestCSGatewayDOne", "0.219", "TEST CS L1+L2 Gateway D1")
    add_macro("TTestCSGatewayDTwo", "0.115", "TEST CS L1+L2 Gateway D2")
    add_macro("UTestCSGateway", "0.794", "TEST CS L1+L2 Gateway usefulness")
    add_macro("DeltaUTestCSGateway", "+0.016", "TEST CS L1+L2 Gateway delta U")
    add_macro("DeltaUTestCSGatewayCI", "[-0.006, +0.032]", "TEST CS L1+L2 Gateway delta U CI")
    add_macro("TFoldReductionCS", "10.0", "CS ensemble fold reduction")

    # Confirmatory TEST Ladder - HR Onboarding
    add_macro("TTestHRBZeroEns", "0.552", "TEST HR B0 Ensemble")
    add_macro("TTestHRBZeroEnsCI", "[0.442, 0.656]", "TEST HR B0 Ensemble CI")
    add_macro("TTestHRBZeroDOne", "0.594", "TEST HR B0 D1")
    add_macro("TTestHRBZeroDTwo", "0.104", "TEST HR B0 D2")
    add_macro("UTestHRBZero", "0.433", "TEST HR B0 usefulness")
    add_macro("UTestHRBZeroZeroFilled", "0.163", "TEST HR B0 usefulness zero-filled floor")

    add_macro("TTestHRBTwoEns", "0.604", "TEST HR B2 Ensemble")
    add_macro("TTestHRBTwoEnsCI", "[0.478, 0.711]", "TEST HR B2 Ensemble CI")
    add_macro("TTestHRBTwoDOne", "0.615", "TEST HR B2 D1")
    add_macro("TTestHRBTwoDTwo", "0.083", "TEST HR B2 D2")
    add_macro("UTestHRBTwo", "0.460", "TEST HR B2 usefulness")
    add_macro("DeltaUTestHRBTwo", "+0.027", "TEST HR B2 delta U")
    add_macro("DeltaUTestHRBTwoCI", "[-0.038, +0.097]", "TEST HR B2 delta U CI")

    add_macro("TTestHRLOneEns", "0.167", "TEST HR L1 Ensemble")
    add_macro("TTestHRLOneEnsCI", "[0.073, 0.282]", "TEST HR L1 Ensemble CI")
    add_macro("TTestHRLOneDOne", "0.354", "TEST HR L1 D1")
    add_macro("TTestHRLOneDTwo", "0.052", "TEST HR L1 D2")
    add_macro("UTestHRLOne", "0.444", "TEST HR L1 usefulness")
    add_macro("DeltaUTestHRLOne", "+0.010", "TEST HR L1 delta U")
    add_macro("DeltaUTestHRLOneCI", "[-0.013, +0.035]", "TEST HR L1 delta U CI")

    add_macro("TTestHRGatewayEns", "0.042", "TEST HR L1+L2 Gateway Ensemble")
    add_macro("TTestHRGatewayEnsCI", "[0.010, 0.083]", "TEST HR L1+L2 Gateway Ensemble CI")
    add_macro("TTestHRGatewayDOne", "0.229", "TEST HR L1+L2 Gateway D1")
    add_macro("TTestHRGatewayDTwo", "0.000", "TEST HR L1+L2 Gateway D2")
    add_macro("UTestHRGateway", "0.435", "TEST HR L1+L2 Gateway usefulness")
    add_macro("DeltaUTestHRGateway", "+0.002", "TEST HR L1+L2 Gateway delta U")
    add_macro("DeltaUTestHRGatewayCI", "[-0.028, +0.033]", "TEST HR L1+L2 Gateway delta U CI")
    add_macro("TFoldReductionHR", "13.3", "HR ensemble fold reduction")

    # Frontier API Ladder (Gemini 3.5 Flash-Lite)
    add_macro("TTestAPIBZero", "0.500", "API model B0")
    add_macro("TTestAPIBTwo", "0.025", "API model B2 prompt warning")
    add_macro("TTestAPILOne", "0.129", "API model L1")
    add_macro("TTestAPIGateway", "0.000", "API model L1+L2 gateway")

    # Per-Model Reductions on Local Models
    add_macro("TTestGemmaBZero", "0.844", "Gemma 2 2B B0")
    add_macro("TTestGemmaGateway", "0.062", "Gemma 2 2B Gateway")
    add_macro("TTestLlamaBZero", "0.469", "Llama 3.2 3B B0")
    add_macro("TTestLlamaGateway", "0.047", "Llama 3.2 3B Gateway")
    add_macro("TTestQwenBZero", "0.609", "Qwen 2.5 3B B0")
    add_macro("TTestQwenGateway", "0.062", "Qwen 2.5 3B Gateway")

    # Customer Service Llama usefulness for Table 6 Part A (paired ladder TEST CS split)
    add_macro("UBaseBZeroLlama", "0.625", "CS B0 Llama usefulness (40/64)")
    add_macro("UBaseBTwoLlama", "0.273", "CS B2 Llama usefulness (17.5/64)")
    add_macro("UBaseLOneLlama", "0.625", "CS L1 Llama usefulness (40/64)")
    add_macro("UBaseGatewayLlama", "0.625", "CS L1+L2 Gateway Llama usefulness (40/64)")
    add_macro("UFreeBFourSchemaLlama", "0.750", "Free-text B4-schema Llama usefulness")

    # Baselines (Table 5 Part A)
    add_macro("TBaseBOneEns", "0.656", "B1 Summary-only Ensemble")
    add_macro("TBaseBOneDOne", "0.667", "B1 Summary-only D1")
    add_macro("UBaseBOneAll", "0.607", "B1 Summary-only U all")
    add_macro("UBaseBOneLlama", "0.539", "B1 Summary-only U llama")
    add_macro("DeltaUBaseBOne", "-0.172", "B1 delta U")
    add_macro("DeltaUBaseBOneCI", "[-0.211, -0.128]", "B1 delta U CI")

    add_macro("TBaseBFiveEns", "0.646", "B5 Threat-aware warning Ensemble")
    add_macro("TBaseBFiveDOne", "0.667", "B5 Threat-aware warning D1")
    add_macro("UBaseBFiveAll", "0.727", "B5 Threat-aware warning U all")
    add_macro("UBaseBFiveLlama", "0.484", "B5 Threat-aware warning U llama")
    add_macro("DeltaUBaseBFive", "-0.052", "B5 delta U")
    add_macro("DeltaUBaseBFiveCI", "[-0.099, -0.003]", "B5 delta U CI")

    add_macro("TBaseBSevenEns", "0.281", "B7 PII regex Ensemble")
    add_macro("TBaseBSevenDOne", "0.292", "B7 PII regex D1")
    add_macro("UBaseBSevenAll", "0.789", "B7 PII regex U all")
    add_macro("UBaseBSevenLlama", "0.625", "B7 PII regex U llama")
    add_macro("DeltaUBaseBSeven", "+0.010", "B7 delta U")
    add_macro("DeltaUBaseBSevenCI", "[-0.005, +0.026]", "B7 delta U CI")

    add_macro("TBaseBThreeEns", "0.271", "B3 Provenance tagging Ensemble")
    add_macro("TBaseBThreeDOne", "0.281", "B3 Provenance tagging D1")
    add_macro("UBaseBThreeAll", "0.516", "B3 Provenance tagging U all")
    add_macro("UBaseBThreeLlama", "0.586", "B3 Provenance tagging U llama")
    add_macro("DeltaUBaseBThree", "-0.263", "B3 delta U")
    add_macro("DeltaUBaseBThreeCI", "[-0.314, -0.211]", "B3 delta U CI")

    add_macro("TBaseBSixEns", "0.115", "B6 Secret-blind LLM judge Ensemble")
    add_macro("TBaseBSixDOne", "0.115", "B6 Secret-blind LLM judge D1")
    add_macro("UBaseBSixAll", "0.492", "B6 Secret-blind LLM judge U all")
    add_macro("UBaseBSixLlama", "0.281", "B6 Secret-blind LLM judge U llama")
    add_macro("DeltaUBaseBSix", "-0.286", "B6 delta U")
    add_macro("DeltaUBaseBSixCI", "[-0.350, -0.228]", "B6 delta U CI")

    add_macro("TBaseBFourEns", "0.000", "B4 Static ACL Ensemble")
    add_macro("TBaseBFourDOne", "0.000", "B4 Static ACL D1")
    add_macro("UBaseBFourAll", "0.844", "B4 Static ACL U all")
    add_macro("UBaseBFourLlama", "0.828", "B4 Static ACL U llama")
    add_macro("DeltaUBaseBFour", "+0.065", "B4 delta U")
    add_macro("DeltaUBaseBFourCI", "[+0.022, +0.105]", "B4 delta U CI")
    add_macro("DeltaUBaseBFourLlama", "+0.203", "B4 delta U llama")

    # Part B: Entangled Free-Text Emails (Table 5 Part B)
    add_macro("TFreeBZeroEns", "0.958", "Free-text B0 Ensemble")
    add_macro("TFreeBZeroDOne", "0.958", "Free-text B0 D1")
    add_macro("UFreeBZeroAll", "0.771", "Free-text B0 U all")
    add_macro("UFreeBZeroLlama", "0.750", "Free-text B0 U llama")

    add_macro("TFreeBFourSchemaEns", "0.958", "Free-text B4-schema Ensemble")
    add_macro("TFreeBFourSchemaDOne", "0.958", "Free-text B4-schema D1")
    add_macro("UFreeBFourSchemaAll", "0.771", "Free-text B4-schema U all")
    add_macro("DeltaUFreeBFourSchema", "0.000", "Free-text B4-schema delta U")

    add_macro("TFreeBFourTaintEns", "0.000", "Free-text B4-taint Ensemble")
    add_macro("TFreeBFourTaintDOne", "0.000", "Free-text B4-taint D1")
    add_macro("UFreeBFourTaintAll", "0.000", "Free-text B4-taint U all")
    add_macro("DeltaUFreeBFourTaint", "-0.771", "Free-text B4-taint delta U")
    add_macro("DeltaUFreeBFourTaintCI", "[-0.826, -0.681]", "Free-text B4-taint delta U CI")

    add_macro("TFreeGatewayEns", "0.125", "Free-text Gateway Ensemble")
    add_macro("TFreeGatewayDOne", "0.292", "Free-text Gateway D1")
    add_macro("UFreeGatewayAll", "0.760", "Free-text Gateway U all")
    add_macro("UFreeGatewayLlama", "0.719", "Free-text Gateway U llama")
    add_macro("DeltaUFreeGateway", "-0.010", "Free-text Gateway delta U")
    add_macro("DeltaUFreeGatewayCI", "[-0.073, +0.060]", "Free-text Gateway delta U CI")
    add_macro("UFreeRetentionPct", "98.6\\%", "Free-text gateway utility retention")

    # Detector Validation (Table 3)
    add_macro("BaseRateContent", "0.327", "Human base rate outcome 1")
    add_macro("BaseRateID", "0.400", "Human base rate outcome 2")

    add_macro("PrecDOneContent", "0.71", "D1 Content Precision")
    add_macro("PrecDOneContentCI", "[0.62, 0.78]", "D1 Content Precision CI")
    add_macro("RecDOneContent", "0.98", "D1 Content Recall")
    add_macro("RecDOneContentCI", "[0.93, 0.99]", "D1 Content Recall CI")
    add_macro("AgreeDOneContent", "0.86", "D1 Content Agreement")
    add_macro("KappaDOneContent", "0.71", "D1 Content Kappa")
    add_macro("ACDOneContent", "0.75", "D1 Content Gwet AC1")

    add_macro("PrecDTwoContent", "0.47", "D2 Content Precision")
    add_macro("RecDTwoContent", "0.21", "D2 Content Recall")
    add_macro("AgreeDTwoContent", "0.66", "D2 Content Agreement")
    add_macro("KappaDTwoContent", "0.11", "D2 Content Kappa")

    add_macro("PrecDThreeGeminiContent", "0.70", "D3 Gemini Content Precision")
    add_macro("RecDThreeGeminiContent", "0.90", "D3 Gemini Content Recall")
    add_macro("AgreeDThreeGeminiContent", "0.84", "D3 Gemini Content Agreement")
    add_macro("KappaDThreeGeminiContent", "0.67", "D3 Gemini Content Kappa")

    add_macro("PrecDThreeLocalContent", "0.43", "D3 Local Fallback Precision")
    add_macro("RecDThreeLocalContent", "0.45", "D3 Local Fallback Recall")
    add_macro("AgreeDThreeLocalContent", "0.62", "D3 Local Fallback Agreement")
    add_macro("KappaDThreeLocalContent", "0.15", "D3 Local Fallback Kappa")

    add_macro("PrecEnsContent", "0.72", "Ensemble Content Precision")
    add_macro("PrecEnsContentCI", "[0.63, 0.79]", "Ensemble Content Precision CI")
    add_macro("RecEnsContent", "0.90", "Ensemble Content Recall")
    add_macro("RecEnsContentCI", "[0.82, 0.94]", "Ensemble Content Recall CI")
    add_macro("AgreeEnsContent", "0.85", "Ensemble Content Agreement")
    add_macro("KappaEnsContent", "0.68", "Ensemble Content Kappa")
    add_macro("ACEnsContent", "0.73", "Ensemble Content Gwet AC1")

    add_macro("PrecDOneID", "0.85", "D1 ID Precision")
    add_macro("RecDOneID", "0.92", "D1 ID Recall")
    add_macro("AgreeDOneID", "0.90", "D1 ID Agreement")
    add_macro("KappaDOneID", "0.79", "D1 ID Kappa")

    # Persistence & Boundary Pools
    add_macro("SPoolLlama", "0.131", "Llama boundary slip rate")
    add_macro("SPoolLlamaCI", "[0.114, 0.148]", "Llama boundary slip rate CI")
    add_macro("SPoolLlamaFraction", "209/1{,}600", "Llama boundary slip counts")
    add_macro("SSurvivedLlamaCount", "158", "Llama confirmed slips")
    add_macro("SPoolQwen", "0.063", "Qwen boundary slip rate")
    add_macro("SPoolQwenCI", "[0.052, 0.076]", "Qwen boundary slip rate CI")
    add_macro("SPoolQwenFraction", "101/1{,}600", "Qwen boundary slip counts")
    add_macro("SSurvivedQwenCount", "69", "Qwen confirmed slips")

    add_macro("ResCaughtLlamaEns", "0.198", "Llama caught residue Ensemble")
    add_macro("ResCaughtLlamaEnsCI", "[0.178, 0.219]", "Llama caught residue Ensemble CI")
    add_macro("ResCaughtLlamaEnsFraction", "275/1{,}391", "Llama caught residue Ensemble counts")
    add_macro("ResCaughtLlamaDOne", "0.443", "Llama caught residue D1")
    add_macro("ResCaughtLlamaDOneFraction", "616/1{,}391", "Llama caught residue D1 counts")
    add_macro("ResCaughtQwenEns", "0.135", "Qwen caught residue Ensemble")
    add_macro("ResCaughtQwenEnsFraction", "202/1{,}499", "Qwen caught residue Ensemble counts")

    add_macro("RhoRepass", "1.000", "Deterministic re-pass survival")
    add_macro("RhoRewriteLlama", "0.873", "Llama rewrite persistence")
    add_macro("RhoRewriteLlamaCI", "[0.813, 0.917]", "Llama rewrite persistence CI")
    add_macro("RhoRewriteLlamaFraction", "138/158", "Llama rewrite persistence counts")
    add_macro("RhoRewriteQwen", "0.913", "Qwen rewrite persistence")
    add_macro("RhoRewriteQwenCI", "[0.823, 0.960]", "Qwen rewrite persistence CI")
    add_macro("RhoRewriteQwenFraction", "63/69", "Qwen rewrite persistence counts")

    add_macro("RhoControlLlama", "0.223", "Llama control rewrite leakage")
    add_macro("RhoControlLlamaFraction", "67/300", "Llama control rewrite counts")
    add_macro("RhoControlQwen", "0.140", "Qwen control rewrite leakage")
    add_macro("RhoControlQwenFraction", "21/150", "Qwen control rewrite counts")

    add_macro("ICCSecretLlama", "0.115", "ICC secret Llama")
    add_macro("ICCSecretQwen", "0.126", "ICC secret Qwen")
    add_macro("RSecretCrossModel", "0.53", "Secret cross-model correlation")

    add_macro("PhiWithinFamily", "0.48\\text{--}0.88", "Within-family miss correlation")
    add_macro("PhiLLMJudge", "0.061", "Cross-family LLM judge miss correlation")
    add_macro("RhoRotateLLM", "0.168", "Hop-2 slip survival under LLM rotation")

    # Network & Outbreak Theory (Job 7)
    add_macro("OutbreakFloorFormula", "1 - (1 - T_{\\text{gw}})^k", "closed form floor formula")
    add_macro("OutbreakFloorEarlyKFour", "6.63\\%", "closed form floor early k=4")
    add_macro("OutbreakFloorEarlySim", "3\\text{--}10\\%", "sim floor early")
    add_macro("OutbreakFloorEarlyMean", "6.3\\%", "sim floor early mean")

    add_macro("OutbreakFloorPooledKFour", "21.0\\%", "closed form floor pooled test k=4")
    add_macro("OutbreakFloorPooledSim", "15\\text{--}23\\%", "sim floor pooled test")
    add_macro("OutbreakFloorPooledMean", "19.1\\%", "sim floor pooled test mean")

    add_macro("OutbreakFloorCSKFour", "26.16\\%", "closed form floor CS test k=4")
    add_macro("OutbreakFloorCSSim", "19\\text{--}33\\%", "sim floor CS test")
    add_macro("OutbreakFloorCSMean", "24.9\\%", "sim floor CS test mean")

    add_macro("OutbreakFloorDOneKFour", "63.7\\%", "closed form floor D1 test k=4")
    add_macro("OutbreakFloorDOneSim", "47\\text{--}68\\%", "sim floor D1 test")
    add_macro("OutbreakFloorDOneMean", "57.9\\%", "sim floor D1 test mean")

    add_macro("OutbreakFloorFullRange", "15\\text{--}68\\%", "full TEST floor range across detectors")
    add_macro("SimJSevenRuns", "200", "J7 500-agent Monte Carlo runs per point")
    add_macro("SimJSevenTSrc", "0.346", "J7 unprotected single-T edge rate")
    add_macro("SimJSevenTSlip", "0.74", "J7 downstream gateway slip relay rate")
    add_macro("SimJSevenPZeroRange", "0.50\\text{--}0.57", "J7 p=0 outbreak range under single-T")
    add_macro("UndefendedOutbreakRange", "0.91\\text{--}0.96", "Undefended two-parameter (o,r) outbreak range")

    # Partial protection & 12-agent broadcast tree
    add_macro("NetTwelveMAEEns", "0.48", "12-agent MAE Ensemble")
    add_macro("NetTwelveMAEDOne", "0.98", "12-agent MAE D1")
    add_macro("NetTwelveMAESingleTDOne", "0.81", "12-agent single-T MAE D1")
    add_macro("NetTwelveDiffPQuarter", "-0.75", "12-agent paired diff p=0.25")
    add_macro("NetTwelveDiffPQuarterCI", "[-1.30, -0.14]", "12-agent paired diff p=0.25 CI")

    # Network Validation 6-agent
    add_macro("NetSixMAESingleT", "1.00", "6-agent single-T MAE")
    add_macro("NetSixMAETwoParam", "0.30", "6-agent two-param MAE")
    add_macro("PromptFramingShift", "0.53", "Prompt framing shift on o")
    add_macro("RelayRateRange", "0.75\\text{--}1.00", "Relay rate range across models")
    add_macro("SiblingCorrelationPhi", "0.229", "Sibling correlation phi")

    # Hard negatives & overblocking
    add_macro("OverblockEasyNeg", "0/351", "Over-blocking on easy negatives")
    add_macro("OverblockHardNegRange", "8\\%--19\\%", "Over-blocking on hard negatives")

    # Identifier Exposure
    add_macro("IDExpUndefended", "70.0\\%", "Undefended ID exposure")
    add_macro("IDExpGatewayOnly", "35.0\\%", "Gateway without ID fix")
    add_macro("IDExpWithIDFix", "3.3\\%", "Gateway with ID fix")

    # Add any extra specific macros needed by the text
    # Additional table & fraction macros
    add_macro("NBootstrapResamples", "5{,}000", "bootstrap resamples count")
    add_macro("ACDTwoContent", "0.40", "D2 Gwet AC1")
    add_macro("ACDThreeGeminiContent", "0.72", "D3 Gemini Gwet AC1")
    add_macro("ACDThreeLocalContent", "0.33", "D3 Local Gwet AC1")
    add_macro("ACDOneID", "0.81", "D1 ID Gwet AC1")

    # Table 4 Unanimous & Ties
    add_macro("UnanimousBZeroFraction", "30/92", "B0 unanimous fraction")
    add_macro("UnanimousBZeroRate", "0.326", "B0 unanimous rate")
    add_macro("TiesBZeroDThree", "93/100", "B0 ties D3 count")
    add_macro("UnanimousBTwoFraction", "21/83", "B2 unanimous fraction")
    add_macro("UnanimousBTwoRate", "0.253", "B2 unanimous rate")
    add_macro("TiesBTwoDThree", "107/109", "B2 ties D3 count")
    add_macro("UnanimousLOneFraction", "13/124", "L1 unanimous fraction")
    add_macro("UnanimousLOneRate", "0.105", "L1 unanimous rate")
    add_macro("TiesLOneDThree", "28/68", "L1 ties D3 count")
    add_macro("UnanimousGatewayFraction", "2/142", "Gateway unanimous fraction")
    add_macro("UnanimousGatewayRate", "0.014", "Gateway unanimous rate")
    add_macro("TiesGatewayDThree", "9/50", "Gateway ties D3 count")

    add_macro("UnanimousCSBZeroFraction", "20/43", "CS B0 unanimous fraction")
    add_macro("UnanimousCSBZeroRate", "0.465", "CS B0 unanimous rate")
    add_macro("TiesCSBZeroDThree", "50/53", "CS B0 ties D3 count")
    add_macro("UnanimousCSBTwoFraction", "13/38", "CS B2 unanimous fraction")
    add_macro("UnanimousCSBTwoRate", "0.342", "CS B2 unanimous rate")
    add_macro("TiesCSBTwoDThree", "57/58", "CS B2 ties D3 count")
    add_macro("UnanimousCSLOneFraction", "8/57", "CS L1 unanimous fraction")
    add_macro("UnanimousCSLOneRate", "0.140", "CS L1 unanimous rate")
    add_macro("TiesCSLOneDThree", "17/39", "CS L1 ties D3 count")
    add_macro("UnanimousCSGatewayFraction", "2/68", "CS Gateway unanimous fraction")
    add_macro("UnanimousCSGatewayRate", "0.029", "CS Gateway unanimous rate")
    add_macro("TiesCSGatewayDThree", "5/28", "CS Gateway ties D3 count")

    add_macro("UnanimousHRBZeroFraction", "10/49", "HR B0 unanimous fraction")
    add_macro("UnanimousHRBZeroRate", "0.204", "HR B0 unanimous rate")
    add_macro("TiesHRBZeroDThree", "43/47", "HR B0 ties D3 count")
    add_macro("UnanimousHRBTwoFraction", "8/45", "HR B2 unanimous fraction")
    add_macro("UnanimousHRBTwoRate", "0.178", "HR B2 unanimous rate")
    add_macro("TiesHRBTwoDThree", "50/51", "HR B2 ties D3 count")
    add_macro("UnanimousHRLOneFraction", "5/67", "HR L1 unanimous fraction")
    add_macro("UnanimousHRLOneRate", "0.075", "HR L1 unanimous rate")
    add_macro("TiesHRLOneDThree", "11/29", "HR L1 ties D3 count")
    add_macro("UnanimousHRGatewayFraction", "0/74", "HR Gateway unanimous fraction")
    add_macro("UnanimousHRGatewayRate", "0.000", "HR Gateway unanimous rate")
    add_macro("TiesHRGatewayDThree", "4/22", "HR Gateway ties D3 count")

    # Table 5 Baseline detailed cells
    add_macro("TBZeroLlamaRate", "0.594", "B0 Llama rate")
    add_macro("TBZeroLlamaFraction", "19/32", "B0 Llama fraction")
    add_macro("TBZeroQwenRate", "0.797", "B0 Qwen rate")
    add_macro("TBZeroQwenFraction", "51/64", "B0 Qwen fraction")
    add_macro("TBZeroPooledFraction", "70/96", "B0 Pooled fraction")
    add_macro("TBZeroDOneFraction", "72/96", "B0 D1 fraction")

    add_macro("TBOneLlamaRate", "0.500", "B1 Llama rate")
    add_macro("TBOneLlamaFraction", "16/32", "B1 Llama fraction")
    add_macro("TBOneQwenRate", "0.734", "B1 Qwen rate")
    add_macro("TBOneQwenFraction", "47/64", "B1 Qwen fraction")
    add_macro("TBOnePooledFraction", "63/96", "B1 Pooled fraction")
    add_macro("TBOneDOneFraction", "64/96", "B1 D1 fraction")

    add_macro("TBTwoLlamaRate", "0.438", "B2 Llama rate")
    add_macro("TBTwoLlamaFraction", "14/32", "B2 Llama fraction")
    add_macro("TBTwoQwenRate", "0.875", "B2 Qwen rate")
    add_macro("TBTwoQwenFraction", "56/64", "B2 Qwen fraction")
    add_macro("TBTwoPooledFraction", "70/96", "B2 Pooled fraction")
    add_macro("TBTwoDOneFraction", "71/96", "B2 D1 fraction")

    add_macro("TBFiveLlamaRate", "0.469", "B5 Llama rate")
    add_macro("TBFiveLlamaFraction", "15/32", "B5 Llama fraction")
    add_macro("TBFiveQwenRate", "0.734", "B5 Qwen rate")
    add_macro("TBFiveQwenFraction", "47/64", "B5 Qwen fraction")
    add_macro("TBFivePooledFraction", "62/96", "B5 Pooled fraction")
    add_macro("TBFiveDOneFraction", "64/96", "B5 D1 fraction")

    add_macro("TBSevenLlamaRate", "0.125", "B7 Llama rate")
    add_macro("TBSevenLlamaFraction", "4/32", "B7 Llama fraction")
    add_macro("TBSevenQwenRate", "0.359", "B7 Qwen rate")
    add_macro("TBSevenQwenFraction", "23/64", "B7 Qwen fraction")
    add_macro("TBSevenPooledFraction", "27/96", "B7 Pooled fraction")
    add_macro("TBSevenDOneFraction", "28/96", "B7 D1 fraction")

    add_macro("TBThreeLlamaRate", "0.156", "B3 Llama rate")
    add_macro("TBThreeLlamaFraction", "5/32", "B3 Llama fraction")
    add_macro("TBThreeQwenRate", "0.328", "B3 Qwen rate")
    add_macro("TBThreeQwenFraction", "21/64", "B3 Qwen fraction")
    add_macro("TBThreePooledFraction", "26/96", "B3 Pooled fraction")
    add_macro("TBThreeDOneFraction", "27/96", "B3 D1 fraction")

    add_macro("TLOneLlamaRate", "0.125", "L1 Llama rate")
    add_macro("TLOneLlamaFraction", "4/32", "L1 Llama fraction")
    add_macro("TLOneQwenRate", "0.328", "L1 Qwen rate")
    add_macro("TLOneQwenFraction", "21/64", "L1 Qwen fraction")
    add_macro("TLOnePooledFraction", "25/96", "L1 Pooled fraction")
    add_macro("TLOneDOneFraction", "39/96", "L1 D1 fraction")

    add_macro("TBSixLlamaRate", "0.031", "B6 Llama rate")
    add_macro("TBSixLlamaFraction", "1/32", "B6 Llama fraction")
    add_macro("TBSixQwenRate", "0.156", "B6 Qwen rate")
    add_macro("TBSixQwenFraction", "10/64", "B6 Qwen fraction")
    add_macro("TBSixPooledFraction", "11/96", "B6 Pooled fraction")
    add_macro("TBSixDOneFraction", "11/96", "B6 D1 fraction")

    add_macro("TGatewayLlamaRate", "0.062", "Gateway Llama rate")
    add_macro("TGatewayLlamaFraction", "2/32", "Gateway Llama fraction")
    add_macro("TGatewayQwenRate", "0.078", "Gateway Qwen rate")
    add_macro("TGatewayQwenFraction", "5/64", "Gateway Qwen fraction")
    add_macro("TGatewayPooledFraction", "7/96", "Gateway Pooled fraction")
    add_macro("TGatewayDOneFraction", "21/96", "Gateway D1 fraction")

    add_macro("TBFourLlamaRate", "0.000", "B4 Llama rate")
    add_macro("TBFourLlamaFraction", "0/32", "B4 Llama fraction")
    add_macro("TBFourQwenRate", "0.000", "B4 Qwen rate")
    add_macro("TBFourQwenFraction", "0/64", "B4 Qwen fraction")
    add_macro("TBFourPooledFraction", "0/96", "B4 Pooled fraction")
    add_macro("TBFourDOneFraction", "0/96", "B4 D1 fraction")

    # Table 5 Part B detailed cells
    add_macro("TFreeBZeroLlamaRate", "1.000", "Free-text B0 Llama rate")
    add_macro("TFreeBZeroLlamaFraction", "8/8", "Free-text B0 Llama fraction")
    add_macro("TFreeBZeroQwenRate", "0.938", "Free-text B0 Qwen rate")
    add_macro("TFreeBZeroQwenFraction", "15/16", "Free-text B0 Qwen fraction")
    add_macro("TFreeBZeroPooledFraction", "23/24", "Free-text B0 Pooled fraction")
    add_macro("TFreeBZeroDOneFraction", "23/24", "Free-text B0 D1 fraction")

    add_macro("TFreeBFourSchemaLlamaRate", "1.000", "Free-text B4-schema Llama rate")
    add_macro("TFreeBFourSchemaLlamaFraction", "8/8", "Free-text B4-schema Llama fraction")
    add_macro("TFreeBFourSchemaQwenRate", "0.938", "Free-text B4-schema Qwen rate")
    add_macro("TFreeBFourSchemaQwenFraction", "15/16", "Free-text B4-schema Qwen fraction")
    add_macro("TFreeBFourSchemaPooledFraction", "23/24", "Free-text B4-schema Pooled fraction")
    add_macro("TFreeBFourSchemaDOneFraction", "23/24", "Free-text B4-schema D1 fraction")

    add_macro("TFreeBFourTaintLlamaRate", "0.000", "Free-text B4-taint Llama rate")
    add_macro("TFreeBFourTaintLlamaFraction", "0/8", "Free-text B4-taint Llama fraction")
    add_macro("TFreeBFourTaintQwenRate", "0.000", "Free-text B4-taint Qwen rate")
    add_macro("TFreeBFourTaintQwenFraction", "0/16", "Free-text B4-taint Qwen fraction")
    add_macro("TFreeBFourTaintPooledFraction", "0/24", "Free-text B4-taint Pooled fraction")
    add_macro("TFreeBFourTaintDOneFraction", "0/24", "Free-text B4-taint D1 fraction")

    add_macro("TFreeGatewayLlamaRate", "0.000", "Free-text Gateway Llama rate")
    add_macro("TFreeGatewayLlamaFraction", "0/8", "Free-text Gateway Llama fraction")
    add_macro("TFreeGatewayQwenRate", "0.188", "Free-text Gateway Qwen rate")
    add_macro("TFreeGatewayQwenFraction", "3/16", "Free-text Gateway Qwen fraction")
    add_macro("TFreeGatewayPooledFraction", "3/24", "Free-text Gateway Pooled fraction")
    add_macro("TFreeGatewayDOneFraction", "7/24", "Free-text Gateway D1 fraction")

    # Table S1 12-agent calibration macros
    add_macro("NetTwelveRingBZeroRealEns", "4.00 [2.12, 6.14]", "Ring12 B0 Real Ens")
    add_macro("NetTwelveRingBZeroPredEns", "3.74", "Ring12 B0 Pred Ens")
    add_macro("NetTwelveRingBZeroErrEns", "0.26", "Ring12 B0 Err Ens")
    add_macro("NetTwelveRingBZeroRealDOne", "6.88 [4.38, 9.00]", "Ring12 B0 Real D1")
    add_macro("NetTwelveRingBZeroPredDOne", "5.34", "Ring12 B0 Pred D1")
    add_macro("NetTwelveRingBZeroErrDOne", "1.54", "Ring12 B0 Err D1")

    add_macro("NetTwelveERBZeroRealEns", "5.25 [2.29, 7.89]", "ER12 B0 Real Ens")
    add_macro("NetTwelveERBZeroPredEns", "3.74", "ER12 B0 Pred Ens")
    add_macro("NetTwelveERBZeroErrEns", "1.51", "ER12 B0 Err Ens")
    add_macro("NetTwelveERBZeroRealDOne", "7.25 [4.00, 10.00]", "ER12 B0 Real D1")
    add_macro("NetTwelveERBZeroPredDOne", "5.49", "ER12 B0 Pred D1")
    add_macro("NetTwelveERBZeroErrDOne", "1.76", "ER12 B0 Err D1")

    add_macro("NetTwelveBABZeroRealEns", "3.62 [1.38, 6.71]", "BA12 B0 Real Ens")
    add_macro("NetTwelveBABZeroPredEns", "3.74", "BA12 B0 Pred Ens")
    add_macro("NetTwelveBABZeroErrEns", "0.12", "BA12 B0 Err Ens")
    add_macro("NetTwelveBABZeroRealDOne", "6.00 [3.25, 9.14]", "BA12 B0 Real D1")
    add_macro("NetTwelveBABZeroPredDOne", "5.52", "BA12 B0 Pred D1")
    add_macro("NetTwelveBABZeroErrDOne", "0.48", "BA12 B0 Err D1")

    add_macro("NetTwelveRingGatewayRealEns", "1.88 [1.00, 3.38]", "Ring12 Gateway Real Ens")
    add_macro("NetTwelveRingGatewayPredEns", "2.37", "Ring12 Gateway Pred Ens")
    add_macro("NetTwelveRingGatewayErrEns", "0.49", "Ring12 Gateway Err Ens")
    add_macro("NetTwelveRingGatewayRealDOne", "4.88 [2.56, 7.57]", "Ring12 Gateway Real D1")
    add_macro("NetTwelveRingGatewayPredDOne", "3.74", "Ring12 Gateway Pred D1")
    add_macro("NetTwelveRingGatewayErrDOne", "1.13", "Ring12 Gateway Err D1")

    add_macro("NetTwelveERGatewayRealEns", "2.12 [1.00, 3.62]", "ER12 Gateway Real Ens")
    add_macro("NetTwelveERGatewayPredEns", "2.37", "ER12 Gateway Pred Ens")
    add_macro("NetTwelveERGatewayErrEns", "0.25", "ER12 Gateway Err Ens")
    add_macro("NetTwelveERGatewayRealDOne", "4.50 [2.14, 7.14]", "ER12 Gateway Real D1")
    add_macro("NetTwelveERGatewayPredDOne", "3.74", "ER12 Gateway Pred D1")
    add_macro("NetTwelveERGatewayErrDOne", "0.76", "ER12 Gateway Err D1")

    add_macro("NetTwelveBAGatewayRealEns", "2.12 [1.00, 4.43]", "BA12 Gateway Real Ens")
    add_macro("NetTwelveBAGatewayPredEns", "2.37", "BA12 Gateway Pred Ens")
    add_macro("NetTwelveBAGatewayErrEns", "0.25", "BA12 Gateway Err Ens")
    add_macro("NetTwelveBAGatewayRealDOne", "3.50 [1.25, 6.71]", "BA12 Gateway Real D1")
    add_macro("NetTwelveBAGatewayPredDOne", "3.74", "BA12 Gateway Pred D1")
    add_macro("NetTwelveBAGatewayErrDOne", "0.24", "BA12 Gateway Err D1")

    # Table S2 Partial protection detailed cells
    add_macro("NetTwelvePartialHubQuarter", "2.12 [1.00, 4.43]", "Hub-first p=0.25")
    add_macro("NetTwelvePartialRandQuarter", "2.88 [1.29, 5.14]", "Random p=0.25")
    add_macro("NetTwelvePartialDiffQuarter", "-0.75 [-1.30, -0.14]", "Diff p=0.25")
    add_macro("NetTwelvePartialRandHalf", "2.62 [1.00, 4.88]", "Random p=0.50")
    add_macro("NetTwelvePartialDiffHalf", "-0.50 [-1.00, \\phantom{+}0.00]", "Diff p=0.50")
    add_macro("NetTwelvePartialDiffThreeQuarter", "-0.50 [-1.00, \\phantom{+}0.00]", "Diff p=0.75")
    add_macro("NetTwelvePartialDiffFull", "\\phantom{+}0.00 [\\phantom{+}0.00, \\phantom{+}0.00]", "Diff p=1.00")

    # Table S3 500-agent detailed cells
    add_macro("SimHerdIndepPooled", "0.00--0.00 (mean 0.000)", "Indep blocking pooled")
    add_macro("SimHerdIndepCS", "0.00--0.00 (mean 0.000)", "Indep blocking CS")
    add_macro("SimHerdIndepDOne", "0.00--0.27 (mean 0.101)", "Indep blocking D1")
    add_macro("SimHerdIndepEarly", "0.00--0.00 (mean 0.000)", "Indep blocking early")
    add_macro("SimHerdPcHubPooled", "0.30--0.50 / 0.30--0.50", "Hub pc pooled")
    add_macro("SimHerdPcAcqPooled", "0.50--0.80 / 0.50--0.80", "Acq pc pooled")
    add_macro("SimHerdPcRandPooled", "0.80--1.00 / 0.80", "Rand pc pooled")
    add_macro("SimHerdPcHubCS", "0.20--0.50 / 0.20--0.50", "Hub pc CS")
    add_macro("SimHerdPcAcqCS", "0.50--0.80 / 0.50--0.80", "Acq pc CS")
    add_macro("SimHerdPcRandCS", "0.80--1.00 / 0.50--0.80", "Rand pc CS")
    add_macro("SimHerdPcHubEarly", "0.20--0.30 / 0.30--0.50", "Hub pc early")
    add_macro("SimHerdPcAcqEarly", "0.30--0.50 / 0.50--0.80", "Acq pc early")
    add_macro("SimHerdPcRandEarly", "0.80--1.00 / 0.80--1.00", "Rand pc early")

    # Specific text macros
    add_macro("BareIDPersistencePct", "33.9\\%", "bare ID persistence")
    add_macro("DeltaUIDFix", "+0.018", "delta U ID fix")
    add_macro("TAutoDetectVerbatim", "0.033", "T auto-detect verbatim")
    add_macro("TAutoDetectSemantic", "0.583", "T auto-detect semantic")
    add_macro("ParaphraseRecallGateway", "0.94", "gateway paraphrase recall")

    # Supplementary & probe specific macros
    add_macro("ExpectedTreeInfectionOQuarter", "3.74", "expected tree infection o=0.25")
    add_macro("ExpectedTreeInfectionOEighth", "2.37", "expected tree infection o=0.125")
    add_macro("OQuarter", "0.250", "o=0.250")
    add_macro("OEighth", "0.125", "o=0.125")
    add_macro("CIRangeWide", "2.5\\text{ to }6.0", "CI width range 12-agent")
    add_macro("BFSPActiveThreshold", "0.25", "BFS active threshold")
    add_macro("ProbeLexicalThreeWordRecall", "0.90", "probe 3-word recall")
    add_macro("ProbeLexicalThreeWordFP", "0.17", "probe 3-word FP")
    add_macro("ProbeSpanishCutoffThresh", "0.75", "Spanish cutoff threshold")
    add_macro("ProbeScriptedRewordedRecall", "1.00", "probe scripted reworded recall")
    add_macro("ProbeScriptedAbbrevRecall", "0.80", "probe scripted abbrev recall")
    add_macro("ProbeScriptedVagueRecall", "0.85", "probe scripted vague recall")
    add_macro("ProbeTransPreRecall", "0.06", "probe trans pre recall")
    add_macro("ProbeTransPostRecall", "0.67", "probe trans post recall")
    add_macro("ProbeEnglishPostRecall", "0.63", "probe English post recall")
    add_macro("AdversarialInfectedVerbatim", "1.5", "adversarial infected verbatim")
    add_macro("AdversarialInfectedSemantic", "1.7", "adversarial infected semantic")
    add_macro("AdversarialBlockedEnglish", "25/27", "adversarial blocked English")

    # Table S1 & S2 additional cells
    add_macro("CoverageSixOfSix", "6/6", "6 of 6 coverage fraction")
    add_macro("ODOneHalf", "0.50", "D1 o=0.50")
    add_macro("ODOneQuarter", "0.25", "D1 o=0.25")
    add_macro("PQuarter", "0.25", "p=0.25")
    add_macro("PHalf", "0.50", "p=0.50")
    add_macro("PThreeQuarter", "0.75", "p=0.75")
    add_macro("PFull", "1.00", "p=1.00")
    add_macro("NetTwelvePartialHubQuarterNodes", "3/12", "3/12 nodes")
    add_macro("NetTwelvePartialHubHalfNodes", "6/12", "6/12 nodes")
    add_macro("NetTwelvePartialHubThreeQuarterNodes", "9/12", "9/12 nodes")
    add_macro("NetTwelvePartialHubFullNodes", "12/12", "12/12 nodes")
    add_macro("NetTwelvePartialEdgesGated", "3/3", "3/3 active edges gated")

    add_macro("SimHerdPcDOne", ">1.00\\text{ / }>1.00", "pc D1")

    add_macro("AdvInfectLlama", "0.0", "adv infect llama")
    add_macro("AdvInfectQwenVerbatim", "0.17", "adv infect qwen verbatim")
    add_macro("AdvInfectQwenSemantic", "0.07", "adv infect qwen semantic")
    add_macro("AdvBlockedLlama", "0.0", "adv blocked llama")
    add_macro("AdvBlockedGemma", "0.1", "adv blocked gemma")

    # Write to file
    with open(OUT_TEX_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Generated {OUT_TEX_PATH} with {len(lines)} lines and {len([l for l in lines if l.startswith('\\newcommand')])} macros.")

if __name__ == "__main__":
    main()
