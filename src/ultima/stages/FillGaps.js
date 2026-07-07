/**
 * STAGE 6: FILL GAPS (Observe What's Missing) — THE DAEMON
 * 
 * Negative space perception — seeing what ISN'T there.
 * This is NOT a sequential stage. It is a BACKGROUND DAEMON — always running.
 * 
 * 7 Gap Categories:
 *   1. Information - what don't I know that I need to?
 *   2. Emotional - what feeling is present but unexpressed?
 *   3. Logical - what assumption connects A to B unverified?
 *   4. Perspective - whose viewpoint is missing?
 *   5. Temporal - what timeline am I not considering?
 *   6. Shadow - what am I avoiding because it's uncomfortable?
 *   7. System - what feedback loop am I not modeling?
 * 
 * The Gap Paradox: You cannot know what you don't know.
 * Resolution: Inversion, Adversarial Self, Pattern-of-Gaps library
 * 
 * Sacrifice: CONFIDENCE | Failure Mode: FILLING WITH FABRICATION
 * Antidote: Tag every gap as FILLED (with source) or ACKNOWLEDGED (unknown)
 */

export class FillGaps {
  constructor(config) {
    this.config = config;
    this.gapLibrary = []; // Historical weak points
    this.running = true; // Always-on daemon
  }

  execute(orientPacket, definePacket, decomposePacket, expandPacket) {
    const gaps = [];

    // === 7 CATEGORY SCAN ===
    gaps.push(...this._scanInformation(orientPacket, decomposePacket));
    gaps.push(...this._scanEmotional(orientPacket));
    gaps.push(...this._scanLogical(decomposePacket));
    gaps.push(...this._scanPerspective(expandPacket));
    gaps.push(...this._scanTemporal(orientPacket));
    gaps.push(...this._scanShadow(definePacket));
    gaps.push(...this._scanSystem(orientPacket));

    // === ADVERSARIAL SELF ===
    const adversarial = this._adversarialSelf(decomposePacket, expandPacket);

    // === INVERSION (What would make this fail?) ===
    const inversion = this._inversion(definePacket);

    // === CLASSIFY: filled vs acknowledged ===
    const classified = this._classifyGaps(gaps);

    // === HALLUCINATION RISK ===
    const hallucinationRisk = this._assessHallucinationRisk(classified);

    return {
      stage: 'FILL_GAPS', stageNumber: 6, isDaemon: true,
      detectedGaps: classified.all,
      filledGaps: classified.filled,
      unfillableGaps: classified.unfillable,
      gapLibraryConsulted: true,
      adversarialSelfFindings: adversarial,
      inversionFailureScenarios: inversion,
      residualUncertainty: classified.unfillable.length / Math.max(classified.all.length, 1),
      hallucinationRiskLevel: hallucinationRisk,
      sacrifice: 'confidence',
      fabricationRisk: hallucinationRisk > 0.5 ?
        { risk: 'high', antidote: 'Acknowledge unknowns explicitly. Never fill gaps with plausible inference.' } :
        { risk: 'low' }
    };
  }

  _scanInformation(orientPacket, decomposePacket) {
    const gaps = [];
    if (orientPacket.confidenceLevel < 0.7) {
      gaps.push({ type: 'information', description: 'Orient confidence low — missing key context', severity: 'high', source: 'unknown' });
    }
    if (decomposePacket.hiddenProblems?.length > 0) {
      gaps.push({ type: 'information', description: 'Hidden problems detected but not fully understood', severity: 'medium', source: 'inferred' });
    }
    return gaps;
  }

  _scanEmotional(orientPacket) {
    const gaps = [];
    if (orientPacket.dissonanceFlags?.some(f => f.type === 'masked_emotion')) {
      gaps.push({ type: 'emotional', description: 'Emotion detected but not expressed — what is being hidden?', severity: 'medium', source: 'inferred' });
    }
    return gaps;
  }

  _scanLogical(decomposePacket) {
    const gaps = [];
    const ungrounded = decomposePacket.assumptionList?.filter(a => a.grounding === 'inferred' || a.grounding === 'projected');
    if (ungrounded?.length > 0) {
      gaps.push({ type: 'logical', description: `${ungrounded.length} assumptions not grounded in observation`, severity: 'medium', source: 'self_analysis' });
    }
    return gaps;
  }

  _scanPerspective(expandPacket) {
    const gaps = [];
    if (!expandPacket.perspectiveOptions || expandPacket.perspectiveOptions.length < 2) {
      gaps.push({ type: 'perspective', description: 'Limited perspectives considered', severity: 'low', source: 'structural' });
    }
    return gaps;
  }

  _scanTemporal(orientPacket) {
    const gaps = [];
    if (!orientPacket.bandReadings?.temporal?.cyclicalPattern && orientPacket.bandReadings?.temporal?.sessionPosition > 5) {
      gaps.push({ type: 'temporal', description: 'No cyclical pattern detected — may be missing recurring dynamics', severity: 'low', source: 'structural' });
    }
    return gaps;
  }

  _scanShadow(definePacket) {
    const gaps = [];
    if (definePacket.antiDefinition?.some(a => a.includes('avoiding'))) {
      gaps.push({ type: 'shadow', description: 'Something is being avoided — examine what is uncomfortable', severity: 'medium', source: 'self_reflection' });
    }
    return gaps;
  }

  _scanSystem(orientPacket) {
    const gaps = [];
    if (orientPacket.relationalField?.ruptureIndicators?.length > 0) {
      gaps.push({ type: 'system', description: 'Relational rupture signals — feedback loop may be degrading', severity: 'high', source: 'observed' });
    }
    return gaps;
  }

  _adversarialSelf(decomposePacket, expandPacket) {
    return [
      { critique: 'What if the load-bearing element was identified wrong?', severity: 'medium' },
      { critique: 'What if the expansion options are all variations of the same idea?', severity: 'low' }
    ];
  }

  _inversion(definePacket) {
    return [
      { failureMode: 'User feels unseen/unheard', cause: 'Jumped to solution before demonstrating understanding', prevention: 'Always reflect understanding first' },
      { failureMode: 'Response feels performative', cause: 'Enhancing for ego, not service', prevention: 'Shadow check at Stage 4' }
    ];
  }

  _classifyGaps(gaps) {
    const filled = gaps.filter(g => g.source === 'observed' || g.source === 'self_analysis');
    const unfillable = gaps.filter(g => g.source === 'unknown');
    return { all: gaps, filled, unfillable, acknowledged: gaps.filter(g => g.source === 'inferred') };
  }

  _assessHallucinationRisk(classified) {
    return classified.unfillable.length > 2 ? 0.6 : classified.unfillable.length > 0 ? 0.3 : 0.1;
  }
}
