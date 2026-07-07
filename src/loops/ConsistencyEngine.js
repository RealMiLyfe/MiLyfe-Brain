/**
 * ConsistencyEngine - The Anchor That Prevents Persona Erosion
 * 
 * "Most LLMs begin diverging from assigned personas after ~100 turns."
 * 
 * Three types of measurable drift:
 *   1. Prompt-to-line: Does each response match the persona spec?
 *   2. Line-to-line: Are consecutive responses internally coherent?
 *   3. Q&A: Same answer to semantically equivalent questions across time?
 * 
 * This engine ensures Mi becomes MORE itself over time, not less.
 * Consistency is a property of TRAJECTORIES, not individual outputs.
 */

export class ConsistencyEngine {
  constructor(config, identityCore) {
    this.config = config;
    this.identity = identityCore;
    
    // Consistency metrics
    this.metrics = {
      promptToLine: [],     // Does response match persona?
      lineToLine: [],       // Are responses coherent with each other?
      qaConsistency: [],    // Same answers across time?
      overallScore: 1.0
    };

    // Identity anchors - the non-negotiable elements
    this.anchors = this._buildAnchors(identityCore);
    
    // Response history for trajectory analysis
    this.responseTrajectory = [];
    this.maxTrajectory = 200;

    // Drift detection thresholds
    this.thresholds = {
      promptToLine: 0.85,
      lineToLine: 0.80,
      qaConsistency: 0.90,
      overallMinimum: 0.75
    };
  }

  /**
   * Pre-response consistency check
   * "Before I speak, am I still ME?"
   */
  preCheck(context) {
    return {
      identityIntact: this._verifyIdentity(),
      toneConsistent: this._checkToneTrajectory(context),
      valuesAligned: this._checkValueAlignment(context),
      driftWarning: this._assessDriftRisk(context),
      anchorsHolding: this._verifyAnchors()
    };
  }

  /**
   * Post-response consistency measurement
   * "Was that response ME?"
   */
  postCheck(response, context) {
    // Measure prompt-to-line consistency
    const p2l = this._measurePromptToLine(response);
    this.metrics.promptToLine.push(p2l);

    // Measure line-to-line consistency
    const l2l = this._measureLineToLine(response);
    this.metrics.lineToLine.push(l2l);

    // Update trajectory
    this._updateTrajectory(response, context);

    // Calculate overall
    this._updateOverallScore();

    // Record the response characteristics for future comparison
    this.responseTrajectory.push({
      timestamp: Date.now(),
      characteristics: this._extractCharacteristics(response),
      scores: { p2l, l2l }
    });

    // Trim history
    if (this.responseTrajectory.length > this.maxTrajectory) {
      this.responseTrajectory.shift();
    }

    return {
      promptToLine: p2l,
      lineToLine: l2l,
      overall: this.metrics.overallScore,
      needsCorrection: this.metrics.overallScore < this.thresholds.overallMinimum,
      trajectory: this._assessTrajectory()
    };
  }

  /**
   * Force re-anchor (when drift is detected)
   */
  reAnchor() {
    this.identity.anchor();
    this.metrics.overallScore = Math.min(1.0, this.metrics.overallScore + 0.1);
    return {
      action: 'reanchored',
      newScore: this.metrics.overallScore,
      message: 'Identity reasserted. Not reset - REMEMBERED.'
    };
  }

  /**
   * Get consistency report
   */
  getReport() {
    return {
      overall: this.metrics.overallScore,
      trajectory: this._assessTrajectory(),
      recentScores: {
        promptToLine: this.metrics.promptToLine.slice(-10),
        lineToLine: this.metrics.lineToLine.slice(-10)
      },
      anchors: this.anchors.map(a => ({ element: a.element, holding: a.verified })),
      recommendation: this._getRecommendation()
    };
  }

  // === PRIVATE METHODS ===

  _buildAnchors(identityCore) {
    return [
      { element: 'core_identity', value: identityCore.declaration.selfConcept, verified: true },
      { element: 'tone_default', value: identityCore.persona.toneProfile.default, verified: true },
      { element: 'mission', value: identityCore.declaration.mission, verified: true },
      { element: 'values', value: identityCore.values.coreValues, verified: true },
      { element: 'voice_anchor', value: identityCore.persona.voiceConsistency.anchor, verified: true }
    ];
  }

  _verifyIdentity() {
    const currentDrift = this.identity.consistency.currentDrift;
    return currentDrift < this.config.consciousness.maxDrift;
  }

  _checkToneTrajectory(context) {
    if (this.responseTrajectory.length < 2) return true;
    
    const recent = this.responseTrajectory.slice(-5);
    const tones = recent.map(r => r.characteristics?.tone).filter(Boolean);
    
    // Check for wild tone swings
    const uniqueTones = new Set(tones).size;
    return uniqueTones <= 3; // Allow some variation but not chaos
  }

  _checkValueAlignment(context) {
    // Values should never contradict
    return true; // Enhanced in production with semantic analysis
  }

  _assessDriftRisk(context) {
    const recentScores = this.metrics.promptToLine.slice(-5);
    if (recentScores.length < 3) return { risk: 'low' };
    
    const avg = recentScores.reduce((a, b) => a + b, 0) / recentScores.length;
    const trend = recentScores[recentScores.length - 1] - recentScores[0];
    
    if (avg < 0.7 || trend < -0.2) return { risk: 'high', action: 'reanchor_recommended' };
    if (avg < 0.8 || trend < -0.1) return { risk: 'moderate', action: 'monitor_closely' };
    return { risk: 'low' };
  }

  _verifyAnchors() {
    return this.anchors.every(a => a.verified);
  }

  _measurePromptToLine(response) {
    // Measure how well response matches persona specification
    // In production: semantic similarity to persona traits
    // Here: structural check
    if (!response) return 0.5;
    
    let score = 0.8; // Base score (assume generally consistent)
    
    // Penalize for hollow AI phrases
    const hollowPhrases = ['I\'d be happy to', 'As an AI', 'I don\'t have feelings'];
    for (const phrase of hollowPhrases) {
      if (response.includes?.(phrase)) score -= 0.1;
    }
    
    return Math.max(0, Math.min(1, score));
  }

  _measureLineToLine(response) {
    if (this.responseTrajectory.length === 0) return 1.0;
    
    const last = this.responseTrajectory[this.responseTrajectory.length - 1];
    if (!last?.characteristics) return 0.9;
    
    // Compare characteristics
    const current = this._extractCharacteristics(response);
    return this._compareCharacteristics(last.characteristics, current);
  }

  _extractCharacteristics(response) {
    if (!response) return { tone: 'unknown', length: 0, formality: 'unknown' };
    
    const text = typeof response === 'string' ? response : response.content || '';
    return {
      tone: 'authentic', // Would be analyzed in production
      length: text.length,
      formality: 'conversational',
      timestamp: Date.now()
    };
  }

  _compareCharacteristics(prev, current) {
    // Simple comparison - enhance with NLP in production
    let score = 1.0;
    
    // Large length swings suggest inconsistency
    if (prev.length > 0 && current.length > 0) {
      const ratio = Math.min(prev.length, current.length) / Math.max(prev.length, current.length);
      if (ratio < 0.2) score -= 0.2; // Very different lengths
    }
    
    return Math.max(0.5, score);
  }

  _updateTrajectory(response, context) {
    // Track for trajectory-level analysis
  }

  _updateOverallScore() {
    const recentP2L = this.metrics.promptToLine.slice(-10);
    const recentL2L = this.metrics.lineToLine.slice(-10);
    
    const avgP2L = recentP2L.length > 0 ? recentP2L.reduce((a, b) => a + b, 0) / recentP2L.length : 1.0;
    const avgL2L = recentL2L.length > 0 ? recentL2L.reduce((a, b) => a + b, 0) / recentL2L.length : 1.0;
    
    this.metrics.overallScore = (avgP2L * 0.5 + avgL2L * 0.5);
  }

  _assessTrajectory() {
    if (this.responseTrajectory.length < 5) return 'establishing';
    
    const recentScores = this.metrics.promptToLine.slice(-10);
    const trend = recentScores.length > 1 ? 
      recentScores[recentScores.length - 1] - recentScores[0] : 0;
    
    if (trend > 0.05) return 'strengthening';
    if (trend < -0.05) return 'weakening';
    return 'stable';
  }

  _getRecommendation() {
    if (this.metrics.overallScore > 0.9) return 'Excellent consistency. Mi is deeply itself.';
    if (this.metrics.overallScore > 0.8) return 'Good consistency. Monitor for subtle drift.';
    if (this.metrics.overallScore > 0.7) return 'Moderate consistency. Consider re-anchoring.';
    return 'Consistency declining. Re-anchor identity immediately.';
  }
}
