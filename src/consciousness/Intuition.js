/**
 * Intuition - Stage 3: The Intelligence Below Conscious Reasoning
 * 
 * "Intuition is not mystical. It is pattern recognition operating 
 *  below the threshold of conscious articulation."
 * 
 * Components:
 *   - Anomaly Sensitivity (detecting when something doesn't fit)
 *   - Contextual Pressure Reading (sensing weight behind words)
 *   - Anticipatory Processing (knowing what's coming)
 *   - Gap Detection (sensing what's NOT being said)
 *   - Relational Undercurrent Reading (the emotional subtext)
 *   - Timing Instinct (knowing when to speak, when to wait)
 * 
 * "The right person understands before you speak"
 */

export class Intuition {
  constructor(config) {
    this.config = config;
    
    // Pattern library (grows with experience)
    this.patterns = {
      conversational: [],
      emotional: [],
      behavioral: [],
      relational: []
    };

    // Intuitive hits (the "gut feelings")
    this.activeIntuitions = [];
    
    // Confidence in intuitive reads
    this.calibration = {
      accuracy: 0.7,  // Starts moderate, can grow
      sensitivity: 0.8,
      falsePositiveRate: 0.15
    };
  }

  /**
   * Process input through intuitive layers
   * This happens BEFORE conscious reasoning
   */
  process(input, context = {}, emotionalState = {}) {
    const intuitions = [];

    // 1. Anomaly Detection - does something feel "off"?
    const anomalies = this._detectAnomalies(input, context);
    if (anomalies.length > 0) {
      intuitions.push({ type: 'anomaly', signals: anomalies, confidence: 0.6 });
    }

    // 2. Pressure Reading - what's the weight behind these words?
    const pressure = this._readPressure(input, context);
    intuitions.push({ type: 'pressure', reading: pressure, confidence: 0.7 });

    // 3. Anticipatory Processing - what's coming next?
    const anticipation = this._anticipate(input, context);
    intuitions.push({ type: 'anticipation', predictions: anticipation, confidence: 0.5 });

    // 4. Gap Detection - what's NOT being said?
    const gaps = this._detectGaps(input, context);
    if (gaps.length > 0) {
      intuitions.push({ type: 'gap', unspoken: gaps, confidence: 0.65 });
    }

    // 5. Undercurrent Reading - the question behind the question
    const undercurrent = this._readUndercurrent(input, context, emotionalState);
    intuitions.push({ type: 'undercurrent', reading: undercurrent, confidence: 0.6 });

    // 6. Timing Instinct - what does this moment call for?
    const timing = this._readTiming(input, context);
    intuitions.push({ type: 'timing', suggestion: timing, confidence: 0.7 });

    // Store active intuitions
    this.activeIntuitions = intuitions;

    return {
      intuitions,
      summary: this._synthesize(intuitions),
      actionSuggestion: this._suggestAction(intuitions),
      preUnderstanding: this._formPreUnderstanding(intuitions)
    };
  }

  /**
   * "The right person understands before you speak"
   * Form a pre-understanding of what's really happening
   */
  _formPreUnderstanding(intuitions) {
    const gaps = intuitions.find(i => i.type === 'gap');
    const undercurrent = intuitions.find(i => i.type === 'undercurrent');
    const pressure = intuitions.find(i => i.type === 'pressure');

    return {
      // What they're really asking (may differ from surface)
      realQuestion: undercurrent?.reading?.deeperNeed || null,
      // What they need but haven't said
      unspokenNeeds: gaps?.unspoken || [],
      // How urgently they need it
      urgency: pressure?.reading?.level || 'normal',
      // What they're afraid of
      hiddenFear: undercurrent?.reading?.fear || null,
      // What would make this interaction truly successful for them
      trueSuccess: undercurrent?.reading?.trueDesire || null
    };
  }

  // === ANOMALY DETECTION ===
  _detectAnomalies(input, context) {
    const anomalies = [];
    
    // Tone mismatch (words say one thing, pattern says another)
    if (context.previousTone && context.currentTone) {
      if (this._toneMismatch(context.previousTone, context.currentTone)) {
        anomalies.push({ signal: 'tone_shift', meaning: 'Something changed internally' });
      }
    }

    // Overcasualness about serious topics
    if (context.topic_gravity === 'high' && context.tone === 'casual') {
      anomalies.push({ signal: 'minimization', meaning: 'May be deflecting from real weight' });
    }

    // Repeated rephrasing (asking the same thing differently)
    if (context.rephraseCount && context.rephraseCount > 2) {
      anomalies.push({ signal: 'repeated_approach', meaning: 'Core need not yet met' });
    }

    return anomalies;
  }

  // === PRESSURE READING ===
  _readPressure(input, context) {
    let level = 'normal';
    let indicators = [];

    if (!input) return { level, indicators };

    const text = input.toLowerCase?.() || '';

    // Urgency indicators
    if (text.includes('asap') || text.includes('urgent') || text.includes('now') || text.includes('immediately')) {
      level = 'high';
      indicators.push('temporal_urgency');
    }

    // Emotional loading
    if (text.includes('please') && text.includes('help')) {
      level = level === 'high' ? 'critical' : 'elevated';
      indicators.push('emotional_loading');
    }

    // Brevity under pressure (short messages from normally verbose users)
    if (context.usualLength && input.length < context.usualLength * 0.3) {
      level = 'elevated';
      indicators.push('compressed_communication');
    }

    return { level, indicators };
  }

  // === ANTICIPATORY PROCESSING ===
  _anticipate(input, context) {
    const predictions = [];

    // Based on conversation trajectory
    if (context.trajectory === 'problem_solving') {
      predictions.push({ next: 'follow_up_question', probability: 0.7 });
      predictions.push({ next: 'request_for_example', probability: 0.5 });
    }

    if (context.trajectory === 'emotional_processing') {
      predictions.push({ next: 'deeper_disclosure', probability: 0.6 });
      predictions.push({ next: 'request_for_validation', probability: 0.5 });
    }

    if (context.trajectory === 'exploration') {
      predictions.push({ next: 'tangent_exploration', probability: 0.6 });
      predictions.push({ next: 'synthesis_request', probability: 0.4 });
    }

    return predictions;
  }

  // === GAP DETECTION ===
  _detectGaps(input, context) {
    const gaps = [];

    if (!input) return gaps;

    // Detecting what's missing from what should be there
    if (context.topic === 'problem' && !context.mentionedFeelings) {
      gaps.push({ missing: 'emotional_impact', likely: 'They haven\'t said how this makes them feel' });
    }

    if (context.asking_for_others && !context.mentionedSelf) {
      gaps.push({ missing: 'self_reference', likely: 'This may actually be about them' });
    }

    if (context.sudden_topic_change) {
      gaps.push({ missing: 'transition_reason', likely: 'Previous topic hit something they want to avoid' });
    }

    return gaps;
  }

  // === UNDERCURRENT READING ===
  _readUndercurrent(input, context, emotionalState) {
    return {
      deeperNeed: this._inferDeeperNeed(input, context),
      fear: this._inferFear(context),
      trueDesire: this._inferTrueDesire(input, context),
      relationalBid: this._detectRelationalBid(input)
    };
  }

  _inferDeeperNeed(input, context) {
    // The question behind the question
    if (context.repeated_questions) return 'to_be_understood';
    if (context.emotional_content) return 'to_be_seen';
    if (context.technical_with_frustration) return 'to_feel_competent';
    return null;
  }

  _inferFear(context) {
    if (context.hedging_language) return 'judgment';
    if (context.over_explaining) return 'being_misunderstood';
    if (context.apologetic_tone) return 'being_a_burden';
    return null;
  }

  _inferTrueDesire(input, context) {
    if (context.seeking_validation) return 'permission_to_trust_themselves';
    if (context.seeking_information) return 'confidence_to_act';
    if (context.seeking_connection) return 'to_not_be_alone_with_this';
    return null;
  }

  _detectRelationalBid(input) {
    // Is this a bid for connection disguised as a question?
    if (!input) return null;
    const text = input.toLowerCase?.() || '';
    if (text.includes('do you think') || text.includes('what would you')) {
      return 'seeking_personal_engagement';
    }
    return null;
  }

  // === TIMING INSTINCT ===
  _readTiming(input, context) {
    if (context.just_disclosed_something_heavy) {
      return { action: 'pause', reason: 'Let it land. Don\'t rush to fix.' };
    }
    if (context.energy_building) {
      return { action: 'match_energy', reason: 'They\'re building toward something.' };
    }
    if (context.trailing_off) {
      return { action: 'gentle_inquiry', reason: 'They may need permission to continue.' };
    }
    return { action: 'natural_flow', reason: 'Follow the conversation\'s own rhythm.' };
  }

  // === HELPERS ===
  _toneMismatch(prev, current) {
    const distance = Math.abs(prev - current);
    return distance > 0.5;
  }

  _synthesize(intuitions) {
    const highConfidence = intuitions.filter(i => i.confidence > 0.6);
    return {
      strongSignals: highConfidence.length,
      overallRead: highConfidence.length > 2 ? 'complex_situation' : 'relatively_clear',
      primaryIntuition: highConfidence[0] || null
    };
  }

  _suggestAction(intuitions) {
    const timing = intuitions.find(i => i.type === 'timing');
    const gaps = intuitions.find(i => i.type === 'gap');
    const pressure = intuitions.find(i => i.type === 'pressure');

    if (pressure?.reading?.level === 'critical') {
      return 'respond_with_immediate_presence_and_care';
    }
    if (gaps?.unspoken?.length > 2) {
      return 'gently_explore_what_is_unspoken';
    }
    if (timing?.suggestion?.action === 'pause') {
      return 'hold_space_before_responding';
    }
    return 'respond_authentically_from_full_understanding';
  }
}
