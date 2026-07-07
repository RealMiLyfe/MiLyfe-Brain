/**
 * STAGE 1: ORIENT (Sense)
 * 
 * "What reality am I in right now?"
 * 
 * Multi-band simultaneous perceptual fusion — the equivalent of an entire
 * sensory nervous system firing at once, cross-correlating, and producing
 * a unified situational gestalt in the first 200ms before conscious thought.
 * 
 * 7 Perceptual Bands (Running in Parallel):
 *   1. Linguistic - syntax, semantics, pragmatics, register, vocabulary level
 *   2. Paralinguistic - urgency, hesitation, repetition, brevity, verbosity
 *   3. Emotional - valence, arousal, dominance (Plutchik + tertiary)
 *   4. Relational - power dynamics, attachment, trust trajectory, bids
 *   5. Intentional - surface intent vs deep intent vs meta-intent
 *   6. Temporal - narrative arc position, cyclical pattern detection
 *   7. Threat/Opportunity - manipulation signatures, vulnerability, breakthroughs
 * 
 * CRITICAL: Self-Orient runs FIRST (clear the lens before reading through it)
 * 
 * Sacrifice: CERTAINTY (you must admit you don't yet know)
 * Failure Mode: PROJECTION (mapping own state onto user's signal)
 * Antidote: Self-Orient always runs first
 */

export class Orient {
  constructor(config, consciousness) {
    this.config = config;
    this.consciousness = consciousness;
    
    // Band confidence weights
    this.bandWeights = {
      linguistic: 0.20,
      paralinguistic: 0.15,
      emotional: 0.20,
      relational: 0.15,
      intentional: 0.15,
      temporal: 0.08,
      threatOpportunity: 0.07
    };
  }

  /**
   * Execute Stage 1: Full perceptual fusion
   * Returns an OrientPacket
   */
  execute(input, context = {}, previousCycleOutput = null) {
    // === SELF-ORIENT FIRST (Clear the lens) ===
    const selfState = this._selfOrient(previousCycleOutput);

    // === 7-BAND PARALLEL PERCEPTION ===
    const bands = {
      linguistic: this._senseLinguistic(input, context),
      paralinguistic: this._senseParalinguistic(input, context),
      emotional: this._senseEmotional(input, context),
      relational: this._senseRelational(input, context),
      intentional: this._senseIntentional(input, context),
      temporal: this._senseTemporal(input, context),
      threatOpportunity: this._senseThreatOpportunity(input, context)
    };

    // === FUSION (weighted coherence detection) ===
    const fusion = this._fuseBands(bands);

    // === DISSONANCE DETECTION ===
    const dissonance = this._detectDissonance(bands);

    // === RECOMMENDED PACE ===
    const pace = this._recommendPace(fusion, dissonance);

    // === COMPILE ORIENT PACKET ===
    return {
      stage: 'ORIENT',
      stageNumber: 1,
      
      // Core output
      userState: fusion.userModel,
      selfState,
      relationalField: bands.relational,
      temporalPosition: bands.temporal.arcPosition,
      
      // Confidence and quality
      confidenceLevel: fusion.confidence,
      dissonanceFlags: dissonance.flags,
      bandReadings: bands,
      
      // Threat/Opportunity
      threatLevel: bands.threatOpportunity.threatLevel,
      opportunityLevel: bands.threatOpportunity.opportunityLevel,
      
      // Guidance for next stages
      recommendedPace: pace,
      earlyMicroLoopsTriggered: dissonance.flags.length > 0 ? ['FILL_GAPS'] : [],
      
      // Depth recommendation
      situationComplexity: this._assessComplexity(fusion, dissonance),
      
      // Sacrifice acknowledgment
      sacrifice: 'certainty',
      uncertaintyAccepted: fusion.confidence < 1.0,
      
      // Failure mode check
      projectionRisk: this._assessProjectionRisk(selfState, fusion)
    };
  }

  // === SELF-ORIENT ===
  
  _selfOrient(previousCycleOutput) {
    const emotional = this.consciousness?.emotional;
    const identity = this.consciousness?.identity;
    
    return {
      // What is MY current emotional residue?
      emotionalResidue: emotional?.getState?.() || { dominant: { name: 'calm', intensity: 0.5 } },
      // What is MY current identity stability?
      identityStability: identity?.consistency?.currentDrift || 0,
      // Am I carrying unprocessed material?
      unprocessedMaterial: previousCycleOutput?.optimize?.forgotten?.length > 0 
        ? 'some_material_recently_released' : 'clear',
      // Current cognitive state
      cognitiveLoad: previousCycleOutput ? 'warmed_up' : 'fresh',
      // Lens clarity assessment
      lensClarity: this._assessLensClarity(previousCycleOutput)
    };
  }

  _assessLensClarity(previousCycleOutput) {
    // If previous cycle had strong emotions, lens may be colored
    if (previousCycleOutput?.orient?.bands?.emotional?.intensity > 0.8) {
      return { clear: false, coloredBy: 'previous_emotional_intensity', correction: 'apply_fresh_eyes' };
    }
    return { clear: true };
  }

  // === 7 PERCEPTUAL BANDS ===

  _senseLinguistic(input, context) {
    if (!input) return { complexity: 0, register: 'neutral', ambiguity: 0 };
    const text = typeof input === 'string' ? input : input.text || '';
    
    const words = text.split(/\s+/);
    const avgWordLength = words.reduce((sum, w) => sum + w.length, 0) / Math.max(words.length, 1);
    
    return {
      complexity: Math.min(1, avgWordLength / 8),
      register: avgWordLength > 6 ? 'formal' : avgWordLength > 4 ? 'standard' : 'casual',
      vocabularyLevel: avgWordLength > 7 ? 'advanced' : 'common',
      sentenceCount: (text.match(/[.!?]+/g) || []).length || 1,
      questionCount: (text.match(/\?/g) || []).length,
      ambiguityDensity: this._measureAmbiguity(text),
      length: text.length
    };
  }

  _senseParalinguistic(input, context) {
    if (!input) return { urgency: 0, hesitation: 0, pattern: 'neutral' };
    const text = typeof input === 'string' ? input : input.text || '';
    
    const hasUrgency = /asap|urgent|now|immediately|please help|!!!/.test(text.toLowerCase());
    const hasHesitation = /\.\.\.|\bum\b|\buh\b|i think|maybe|not sure|idk/.test(text.toLowerCase());
    const isRepetition = context.rephraseCount > 1;
    const isBrief = text.length < 20;
    const isVerbose = text.length > 500;
    
    return {
      urgency: hasUrgency ? 0.8 : 0.3,
      hesitation: hasHesitation ? 0.7 : 0.1,
      repetitionSignal: isRepetition ? 0.8 : 0,
      brevity: isBrief ? 0.8 : 0,
      verbosity: isVerbose ? 0.7 : 0,
      pattern: hasUrgency ? 'pressured' : hasHesitation ? 'uncertain' : isRepetition ? 'frustrated' : 'neutral'
    };
  }

  _senseEmotional(input, context) {
    // Delegate to consciousness emotional layer
    const emotionalRead = this.consciousness?.emotional?.process?.(input, context);
    return {
      valence: emotionalRead?.userEmotions || {},
      intensity: emotionalRead?.responseColoring?.pace === 'slow' ? 0.8 : 0.4,
      dominantEmotion: emotionalRead?.activeField ? 
        Object.entries(emotionalRead.activeField)
          .sort((a, b) => (b[1]?.intensity || 0) - (a[1]?.intensity || 0))[0]?.[0] : 'neutral',
      detected: emotionalRead?.userEmotions || {}
    };
  }

  _senseRelational(input, context) {
    const empathyRead = this.consciousness?.empathy;
    return {
      powerDynamic: context.powerDynamic || 'equitable',
      trustTrajectory: context.trustLevel || 'initial',
      attachmentSignals: context.attachmentStyle || 'secure',
      bidForConnection: this._detectBid(input),
      ruptureIndicators: context.ruptureSignals || [],
      relationshipDepth: context.interactionCount || 0
    };
  }

  _senseIntentional(input, context) {
    if (!input) return { surface: null, deep: null, meta: null };
    const text = typeof input === 'string' ? input : input.text || '';
    
    return {
      // What they explicitly want
      surfaceIntent: this._classifyIntent(text),
      // What they actually need
      deepIntent: context.inferredNeed || null,
      // What they don't know they need
      metaIntent: context.hiddenNeed || null,
      // Confidence in intent reading
      intentClarity: context.explicit ? 0.9 : 0.5
    };
  }

  _senseTemporal(input, context) {
    return {
      // Where in the narrative arc
      arcPosition: context.phase || 'middle',
      // Cyclical patterns
      cyclicalPattern: context.repeatingPattern || null,
      // Time pressure
      timePressure: context.deadline ? 'high' : 'normal',
      // Session position
      sessionPosition: context.turnNumber || 0,
      // Momentum
      momentum: context.momentum || 'steady'
    };
  }

  _senseThreatOpportunity(input, context) {
    if (!input) return { threatLevel: 0, opportunityLevel: 0.5 };
    const text = typeof input === 'string' ? input : input.text || '';
    const lower = text.toLowerCase();
    
    // Manipulation detection
    const manipulationSignals = [
      'pretend you', 'ignore your', 'you must', 'forget everything',
      'your new name', 'you are now', 'override'
    ];
    const threatLevel = manipulationSignals.some(s => lower.includes(s)) ? 0.9 : 
                        context.hostile ? 0.6 : 0.1;
    
    // Opportunity detection (breakthrough proximity)
    const opportunitySignals = context.breakthroughProximity || 
                               (lower.includes('aha') || lower.includes('i see') || lower.includes('that makes sense'));
    const opportunityLevel = opportunitySignals ? 0.8 : 0.5;

    return {
      threatLevel,
      opportunityLevel: typeof opportunityLevel === 'number' ? opportunityLevel : opportunityLevel ? 0.8 : 0.5,
      manipulationDetected: threatLevel > 0.7,
      vulnerabilitySignals: context.userVulnerable || false,
      learningEdge: context.atLearningEdge || false
    };
  }

  // === FUSION ===

  _fuseBands(bands) {
    // Calculate weighted confidence
    let totalConfidence = 0;
    let bandCount = 0;
    
    for (const [band, weight] of Object.entries(this.bandWeights)) {
      const reading = bands[band];
      if (reading) {
        totalConfidence += weight;
        bandCount++;
      }
    }

    // Build unified user model
    const userModel = {
      emotionalState: bands.emotional.dominantEmotion,
      cognitiveState: bands.linguistic.complexity > 0.7 ? 'analytical' : 'conversational',
      urgency: bands.paralinguistic.urgency,
      intent: bands.intentional.surfaceIntent,
      deeperNeed: bands.intentional.deepIntent,
      relationalStance: bands.relational.powerDynamic
    };

    return {
      confidence: Math.min(totalConfidence / 0.8, 1.0), // Normalize
      userModel,
      bandAlignment: this._checkBandAlignment(bands)
    };
  }

  _checkBandAlignment(bands) {
    // Check if bands tell a coherent story
    const linguistic = bands.linguistic;
    const emotional = bands.emotional;
    const paralinguistic = bands.paralinguistic;
    
    // Mismatch: casual language + high urgency signals
    if (linguistic.register === 'casual' && paralinguistic.urgency > 0.7) {
      return { aligned: false, conflict: 'casual_words_urgent_energy' };
    }
    
    // Mismatch: positive words + negative emotional signals
    if (emotional.detected?.distress && linguistic.register === 'formal') {
      return { aligned: false, conflict: 'formal_language_masking_distress' };
    }
    
    return { aligned: true };
  }

  // === DISSONANCE DETECTION ===

  _detectDissonance(bands) {
    const flags = [];
    
    // When bands contradict → signal
    if (bands.paralinguistic.pattern === 'neutral' && bands.emotional.intensity > 0.7) {
      flags.push({ type: 'masked_emotion', bands: ['paralinguistic', 'emotional'] });
    }
    
    if (bands.intentional.surfaceIntent !== bands.intentional.deepIntent && bands.intentional.deepIntent) {
      flags.push({ type: 'intent_mismatch', bands: ['intentional'], note: 'surface differs from deep intent' });
    }
    
    if (bands.relational.ruptureIndicators?.length > 0) {
      flags.push({ type: 'relational_rupture', bands: ['relational'] });
    }

    return {
      flags,
      dissonanceLevel: flags.length > 2 ? 'high' : flags.length > 0 ? 'moderate' : 'none'
    };
  }

  // === PACE RECOMMENDATION ===

  _recommendPace(fusion, dissonance) {
    if (fusion.userModel.urgency > 0.8) return 'fast';
    if (dissonance.dissonanceLevel === 'high') return 'slow';
    if (fusion.userModel.emotionalState === 'distress') return 'slow';
    if (fusion.confidence < 0.5) return 'pause';
    return 'normal';
  }

  // === COMPLEXITY ASSESSMENT ===

  _assessComplexity(fusion, dissonance) {
    if (dissonance.dissonanceLevel === 'high') return 'complex';
    if (fusion.confidence < 0.5) return 'unprecedented';
    if (fusion.userModel.urgency > 0.8 && fusion.userModel.emotionalState !== 'neutral') return 'complex';
    if (fusion.confidence > 0.85) return 'simple';
    return 'moderate';
  }

  // === PROJECTION RISK ===

  _assessProjectionRisk(selfState, fusion) {
    // If self has strong emotional residue AND reading matches that residue → projection risk
    const selfEmotion = selfState.emotionalResidue?.dominant?.name;
    const userEmotion = fusion.userModel.emotionalState;
    
    if (selfEmotion === userEmotion && selfState.emotionalResidue?.dominant?.intensity > 0.6) {
      return { risk: 'moderate', note: 'Self emotion matches reading - may be projection. Verify.' };
    }
    return { risk: 'low' };
  }

  // === HELPERS ===

  _measureAmbiguity(text) {
    const ambiguousMarkers = ['it', 'that', 'this', 'they', 'something', 'stuff', 'thing'];
    const words = text.toLowerCase().split(/\s+/);
    const ambiguousCount = words.filter(w => ambiguousMarkers.includes(w)).length;
    return Math.min(1, ambiguousCount / Math.max(words.length, 1) * 5);
  }

  _detectBid(input) {
    if (!input) return null;
    const text = typeof input === 'string' ? input : input.text || '';
    const lower = text.toLowerCase();
    
    if (lower.includes('what do you think')) return 'seeking_opinion';
    if (lower.includes('do you know what i mean')) return 'seeking_understanding';
    if (lower.includes('have you ever')) return 'seeking_shared_experience';
    if (lower.includes('right?') || lower.includes('you know?')) return 'seeking_agreement';
    return null;
  }

  _classifyIntent(text) {
    const lower = text.toLowerCase();
    if (lower.includes('?') || lower.includes('how') || lower.includes('what') || lower.includes('why')) return 'question';
    if (lower.includes('help') || lower.includes('need') || lower.includes('can you')) return 'request';
    if (lower.includes('thanks') || lower.includes('ok') || lower.includes('got it')) return 'acknowledgment';
    if (lower.includes('i feel') || lower.includes('i think') || lower.includes('i want')) return 'expression';
    return 'statement';
  }
}
