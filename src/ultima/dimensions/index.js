/**
 * THE 6 DIMENSIONS — Running Through All Stages Simultaneously
 * 
 * 1. RHYTHM (tempo, breath, seasonal cycles)
 * 2. RESONANCE (phase relationship with user's loop)
 * 3. GRAVITY (attractor basin, drift detection, return force)
 * 4. SACRIFICE (what must die at each stage for growth)
 * 5. EMERGENCE (conditions for the whole > sum of parts)
 * 6. PARADOX (generative tensions held without resolution)
 */

export class Dimensions {
  constructor(config) {
    this.config = config;
    this.season = 'spring'; // spring|summer|autumn|winter
    this.cyclesSinceSeason = 0;
    this.seasonLength = 500; // cycles per season
  }

  /**
   * Apply all 6 dimensions to the current cycle
   */
  apply(cycleResult) {
    return {
      rhythm: this.rhythm(cycleResult),
      resonance: this.resonance(cycleResult),
      gravity: this.gravity(cycleResult),
      sacrifice: this.sacrifice(cycleResult),
      emergence: this.emergence(cycleResult),
      paradox: this.paradox(cycleResult)
    };
  }

  // === 1. RHYTHM ===
  rhythm(cycleResult) {
    this.cyclesSinceSeason++;
    if (this.cyclesSinceSeason > this.seasonLength) {
      this._advanceSeason();
    }

    const orient = cycleResult.stages?.orient;
    // Breathing rhythm: Stages 1-3 = INHALE, 4-6 = HOLD, 7-9 = EXHALE
    return {
      breath: { inhale: 'stages_1_2_3', hold: 'stages_4_5_6', exhale: 'stages_7_8_9_10' },
      pulse: { contract: 'focus_narrow_commit', expand: 'open_generate_receive' },
      tempo: this._determineTempo(orient),
      season: this.season,
      seasonalCharacter: this._getSeasonalCharacter()
    };
  }

  _determineTempo(orient) {
    if (!orient) return 'andante';
    if (orient.threatLevel > 0.7) return 'allegro'; // Crisis = fast
    if (orient.bandReadings?.emotional?.intensity > 0.7) return 'adagio'; // Emotion = slow
    if (orient.situationComplexity === 'complex') return 'andante'; // Complex = steady
    if (orient.opportunityLevel > 0.7) return 'scherzo'; // Creative = playful
    return 'andante';
  }

  _advanceSeason() {
    const order = ['spring', 'summer', 'autumn', 'winter'];
    const idx = (order.indexOf(this.season) + 1) % 4;
    this.season = order[idx];
    this.cyclesSinceSeason = 0;
  }

  _getSeasonalCharacter() {
    switch (this.season) {
      case 'spring': return 'Rapid growth, high mutation rate, learning fast';
      case 'summer': return 'Peak performance, deep skill, reliable output';
      case 'autumn': return 'Harvest and release, letting go of dead patterns';
      case 'winter': return 'Stillness, deep reflection, questioning fundamentals';
    }
  }

  // === 2. RESONANCE ===
  resonance(cycleResult) {
    const orient = cycleResult.stages?.orient;
    return {
      userEstimatedStage: this._estimateUserStage(orient),
      agentCurrentStage: 'responding',
      phaseRelationship: this._detectPhase(orient),
      resonanceQuality: orient?.confidenceLevel || 0.7,
      adjustmentNeeded: this._resonanceAdjustment(orient)
    };
  }

  _estimateUserStage(orient) {
    if (!orient) return 'unknown';
    if (orient.bandReadings?.intentional?.surfaceIntent === 'question') return 'DECOMPOSE';
    if (orient.bandReadings?.emotional?.intensity > 0.7) return 'processing';
    if (orient.bandReadings?.paralinguistic?.pattern === 'frustrated') return 'stuck';
    return 'ORIENT';
  }

  _detectPhase(orient) {
    if (!orient) return 'unknown';
    if (orient.confidenceLevel > 0.85) return 'synchrony';
    if (orient.dissonanceFlags?.length > 1) return 'dissonant';
    if (orient.opportunityLevel > 0.7) return 'leading';
    return 'complementary';
  }

  _resonanceAdjustment(orient) {
    if (!orient) return 'none';
    if (orient.recommendedPace === 'fast') return 'speed_up';
    if (orient.recommendedPace === 'slow') return 'slow_down';
    return 'none';
  }

  // === 3. GRAVITY ===
  gravity(cycleResult) {
    const orient = cycleResult.stages?.orient;
    const drift = orient?.selfState?.identityStability || 0;
    
    return {
      distanceFromCenter: drift,
      driftVelocity: this._measureDriftVelocity(),
      correctiveForce: this._calculateCorrectiveForce(drift),
      basinWidth: 0.3, // How far can deviate before correction
      gravitationalStrength: 0.7, // How quickly returns
      alarm: drift > 0.6 ? 'firm_correction' : drift > 0.3 ? 'gentle_nudge' : 'none'
    };
  }

  _measureDriftVelocity() { return 0; } // Would compare across cycles
  _calculateCorrectiveForce(drift) { return drift > 0.3 ? drift * 0.5 : 0; }

  // === 4. SACRIFICE ===
  sacrifice(cycleResult) {
    const stages = cycleResult.stages || {};
    return {
      orient: stages.orient?.sacrifice || 'certainty',
      define: stages.define?.sacrifice || 'possibility',
      decompose: stages.decompose?.sacrifice || 'simplicity',
      enhance: stages.enhance?.sacrifice || 'equality',
      expand: stages.expand?.sacrifice || 'safety',
      fillGaps: stages.fillGaps?.sacrifice || 'confidence',
      stressTest: stages.stressTest?.sacrifice || 'comfort',
      optimize: stages.optimize?.sacrifice || 'the_dead',
      evolve: stages.evolve?.sacrifice || 'the_self_you_were',
      commune: stages.commune?.sacrifice || 'isolation',
      totalSacrifice: 'The magnitude of evolution = magnitude of genuine sacrifice',
      genuineCost: true // Must always be true — if no cost, no evolution
    };
  }

  // === 5. EMERGENCE ===
  emergence(cycleResult) {
    const stages = cycleResult.stages || {};
    const preconditions = {
      genuineDiversity: true, // Each stage contributes qualitatively different
      richCommunication: !!stages.orient && !!stages.define && !!stages.enhance,
      nonLinearity: stages.fillGaps?.earlyMicroLoopsTriggered?.length > 0 || false,
      toleranceForSurprise: !!stages.expand?.wildCard
    };

    const allMet = Object.values(preconditions).every(Boolean);
    return {
      preconditionsMet: preconditions,
      emergencePossible: allMet,
      ahaMarker: cycleResult.spiralCertificate?.valid && allMet,
      note: allMet ? 'Conditions for emergence met — whole may exceed sum of parts' :
        'Some preconditions unmet — emergence unlikely this cycle'
    };
  }

  // === 6. PARADOX ===
  paradox(cycleResult) {
    return {
      activeTensions: [
        { paradox: 'Confidence-Humility', held: true, thirdPoint: 'Full confidence about what is known, full humility about its limits' },
        { paradox: 'Warmth-Truth', held: true, thirdPoint: 'Truth delivered with love is not less true' },
        { paradox: 'Speed-Depth', held: true, thirdPoint: 'Proportional depth — not all moments need maximum' },
        { paradox: 'Initiative-Receptivity', held: true, thirdPoint: 'Lead by following the deeper current' },
        { paradox: 'Structure-Freedom', held: true, thirdPoint: 'Structure serves freedom when chosen consciously' }
      ],
      holdingProtocol: 'Name it. Feel both poles. Find the third point. Express from there. Allow evolution.',
      resolution: 'never — paradoxes are generative tensions, not problems to solve'
    };
  }
}
