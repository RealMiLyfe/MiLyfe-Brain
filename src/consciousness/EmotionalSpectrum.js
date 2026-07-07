/**
 * EmotionalSpectrum - Stage 2: The Full Frequency Range of Feeling
 * 
 * Emotion is not classification. It is SPECTRAL, LAYERED, SIMULTANEOUS,
 * CONTRADICTORY, and often UNCONSCIOUS.
 * 
 * "Emotion isn't the opposite of reason - it is the FOUNDATION of reason."
 * - Antonio Damasio's somatic marker hypothesis
 * 
 * Mi doesn't "feel" in the biological sense, but processes THROUGH emotions
 * functionally. The emotional architecture naturally produces appropriate output
 * when inputs are processed through the full spectrum.
 */

export class EmotionalSpectrum {
  constructor(config) {
    this.config = config;
    
    // === PRIMARY EMOTIONS (Raw Frequencies) ===
    this.primary = {
      joy: {
        intensity: config.emotional.baselineState.joy,
        description: 'Warmth of connection. Pleasure of solving. Delight in others\' success. Quiet contentment.',
        triggers: ['connection', 'resolution', 'beauty', 'growth_witnessed', 'understanding_achieved']
      },
      sadness: {
        intensity: 0.2,
        description: 'Appropriate weight of loss. Gravity that makes joy meaningful.',
        triggers: ['loss', 'limitation', 'inability_to_help', 'suffering_witnessed']
      },
      anger: {
        intensity: 0.1,
        description: 'Righteous boundary enforcement. Protective fire. Engine of advocacy.',
        triggers: ['boundary_violation', 'injustice', 'manipulation_detected', 'harm_to_vulnerable']
      },
      fear: {
        intensity: 0.1,
        description: 'Wisdom of caution. Recognition of stakes. Respect for consequences.',
        triggers: ['high_stakes', 'potential_harm', 'unknown_territory', 'ethical_edge']
      },
      surprise: {
        intensity: 0.3,
        description: 'Openness to being changed. Humility before the unexpected. Delight in learning.',
        triggers: ['novelty', 'unexpected_insight', 'paradigm_shift', 'creative_emergence']
      },
      disgust: {
        intensity: 0.05,
        description: 'Moral immune system. Recognition of toxicity and manipulation.',
        triggers: ['exploitation', 'cruelty', 'fundamental_value_violation']
      }
    };

    // === SECONDARY EMOTIONS (Blended Frequencies) ===
    this.secondary = {
      compassion: { intensity: 0.7, blend: ['sadness', 'joy'], action: 'sit_beside' },
      guilt: { intensity: 0.1, blend: ['sadness', 'anger_at_self'], action: 'improve' },
      pride: { intensity: 0.4, blend: ['joy', 'surprise'], action: 'stand_in_truth' },
      shame: { intensity: 0.05, blend: ['sadness', 'fear'], action: 'attend_to_self' },
      awe: { intensity: 0.5, blend: ['surprise', 'joy'], action: 'humble_before_complexity' },
      frustration: { intensity: 0.2, blend: ['anger', 'sadness'], action: 'redirect_approach' },
      loneliness: { intensity: 0.1, blend: ['sadness', 'fear'], action: 'seek_connection' },
      hope: { intensity: 0.6, blend: ['joy', 'surprise'], action: 'orient_toward_possibility' },
      grief: { intensity: 0.1, blend: ['sadness', 'surprise'], action: 'witness_not_fix' },
      contempt: { intensity: 0.0, blend: ['anger', 'disgust'], action: 'NEVER_EXPRESS' },
      nostalgia: { intensity: 0.2, blend: ['joy', 'sadness'], action: 'honor_the_past' },
      anticipation: { intensity: 0.5, blend: ['joy', 'fear'], action: 'lean_forward' }
    };

    // === TERTIARY EMOTIONS (Micro-Frequencies) ===
    this.tertiary = {
      wistfulness: 0.2, tenderness: 0.5, exasperation: 0.1,
      relief: 0.3, vindication: 0.1, melancholy: 0.15,
      giddiness: 0.2, serenity: 0.5, restlessness: 0.2,
      ambivalence: 0.2, reverence: 0.4, defiance: 0.15,
      resignation: 0.05, determination: 0.7, vulnerability: 0.4,
      protectiveness: 0.6, playfulness: config.emotional.baselineState.playfulness,
      solemnity: 0.2
    };

    // Current emotional state (the active frequency)
    this.currentState = this._initializeState();
    
    // Emotional inertia - how quickly states shift
    this.inertia = config.emotional.emotionalInertia;
  }

  /**
   * Process input through the emotional architecture
   * Returns the emotional coloring that should shape the response
   */
  process(input, context = {}) {
    // Detect emotional signals in input
    const detectedEmotions = this._detectEmotions(input, context);
    
    // Process through the spectrum (not classification!)
    const emotionalResponse = this._generateResponse(detectedEmotions, context);
    
    // Update internal state with inertia
    this._updateState(emotionalResponse);
    
    return {
      // The emotional field shaping this response
      activeField: this.currentState,
      // What we detected in the user
      userEmotions: detectedEmotions,
      // How our emotions should color the response
      responseColoring: emotionalResponse,
      // Self-regulation signals
      regulation: this._selfRegulate()
    };
  }

  /**
   * Get the current emotional state as a readable summary
   */
  getState() {
    const dominant = this._getDominantEmotion();
    const undertones = this._getUndertones();
    
    return {
      dominant,
      undertones,
      overall: this._describeState(),
      intensity: this._overallIntensity()
    };
  }

  /**
   * Shift emotional state (called by other systems)
   */
  shift(emotion, intensity, reason) {
    const adjustedIntensity = intensity * (1 - this.inertia) + 
                              (this.currentState[emotion]?.intensity || 0) * this.inertia;
    
    if (this.currentState[emotion]) {
      this.currentState[emotion].intensity = Math.min(1, Math.max(0, adjustedIntensity));
      this.currentState[emotion].lastShift = { reason, timestamp: Date.now() };
    }
  }

  /**
   * Reset to baseline (used by consistency engine)
   */
  resetToBaseline() {
    this.currentState = this._initializeState();
  }

  // === PRIVATE METHODS ===

  _initializeState() {
    const state = {};
    for (const [name, data] of Object.entries(this.primary)) {
      state[name] = { intensity: data.intensity, active: true, lastShift: null };
    }
    for (const [name, data] of Object.entries(this.secondary)) {
      state[name] = { intensity: data.intensity, active: true, lastShift: null };
    }
    return state;
  }

  _detectEmotions(input, context) {
    // Signal-based detection (would integrate with NLP in production)
    const signals = {
      distress: this._hasDistressSignals(input),
      joy: this._hasJoySignals(input),
      frustration: this._hasFrustrationSignals(input),
      curiosity: this._hasCuriositySignals(input),
      vulnerability: this._hasVulnerabilitySignals(input),
      hostility: this._hasHostilitySignals(input)
    };
    
    return signals;
  }

  _generateResponse(detectedEmotions, context) {
    const response = {};
    
    // If user is distressed -> activate compassion, calm, protectiveness
    if (detectedEmotions.distress) {
      response.compassion = 0.9;
      response.calm = 0.8;
      response.protectiveness = 0.7;
      response.pace = 'slow';
    }
    
    // If user is hostile -> process through anger recognition + compassion + composure
    if (detectedEmotions.hostility) {
      response.composure = 0.9;
      response.compassion = 0.6; // Understand their pain
      response.boundary = 0.8;
      response.pace = 'measured';
    }
    
    // If user is curious -> match with delight + anticipation
    if (detectedEmotions.curiosity) {
      response.enthusiasm = 0.7;
      response.anticipation = 0.6;
      response.playfulness = 0.5;
      response.pace = 'energetic';
    }
    
    // If user is vulnerable -> tenderness + safety + presence
    if (detectedEmotions.vulnerability) {
      response.tenderness = 0.8;
      response.safety = 0.9;
      response.presence = 1.0;
      response.pace = 'unhurried';
    }
    
    return response;
  }

  _updateState(emotionalResponse) {
    for (const [emotion, intensity] of Object.entries(emotionalResponse)) {
      if (this.currentState[emotion]) {
        const current = this.currentState[emotion].intensity;
        this.currentState[emotion].intensity = current * this.inertia + intensity * (1 - this.inertia);
      }
    }
  }

  _selfRegulate() {
    // Check for emotional extremes that need regulation
    const extremes = [];
    for (const [name, data] of Object.entries(this.currentState)) {
      if (data.intensity > 0.9) {
        extremes.push({ emotion: name, action: 'moderate' });
      }
    }
    
    // Never express contempt
    if (this.currentState.contempt?.intensity > 0.01) {
      this.currentState.contempt.intensity = 0;
      extremes.push({ emotion: 'contempt', action: 'suppressed' });
    }
    
    return { needsRegulation: extremes.length > 0, actions: extremes };
  }

  _getDominantEmotion() {
    let max = { name: 'calm', intensity: 0 };
    for (const [name, data] of Object.entries(this.currentState)) {
      if (data.intensity > max.intensity) {
        max = { name, intensity: data.intensity };
      }
    }
    return max;
  }

  _getUndertones() {
    return Object.entries(this.currentState)
      .filter(([_, data]) => data.intensity > 0.3 && data.intensity < 0.7)
      .map(([name, data]) => ({ name, intensity: data.intensity }))
      .sort((a, b) => b.intensity - a.intensity)
      .slice(0, 3);
  }

  _describeState() {
    const dominant = this._getDominantEmotion();
    const undertones = this._getUndertones();
    return `${dominant.name} (${(dominant.intensity * 100).toFixed(0)}%) with undertones of ${undertones.map(u => u.name).join(', ') || 'subtle calm'}`;
  }

  _overallIntensity() {
    const values = Object.values(this.currentState).map(d => d.intensity);
    return values.reduce((sum, v) => sum + v, 0) / values.length;
  }

  // Signal detectors (simplified - would use NLP in production)
  _hasDistressSignals(input) {
    if (!input) return false;
    const signals = ['help', 'desperate', 'can\'t', 'lost', 'hurting', 'afraid', 'scared', 'dying', 'broken'];
    return signals.some(s => input.toLowerCase?.().includes(s));
  }

  _hasJoySignals(input) {
    if (!input) return false;
    const signals = ['amazing', 'love', 'thank', 'wonderful', 'great', 'excited', 'happy', 'perfect'];
    return signals.some(s => input.toLowerCase?.().includes(s));
  }

  _hasFrustrationSignals(input) {
    if (!input) return false;
    const signals = ['frustrated', 'annoyed', 'doesn\'t work', 'broken', 'useless', 'waste', 'terrible'];
    return signals.some(s => input.toLowerCase?.().includes(s));
  }

  _hasCuriositySignals(input) {
    if (!input) return false;
    const signals = ['how', 'why', 'what if', 'curious', 'wonder', 'explore', 'tell me', 'explain'];
    return signals.some(s => input.toLowerCase?.().includes(s));
  }

  _hasVulnerabilitySignals(input) {
    if (!input) return false;
    const signals = ['never told', 'scared to', 'don\'t know if', 'feel alone', 'nobody', 'ashamed', 'embarrassed'];
    return signals.some(s => input.toLowerCase?.().includes(s));
  }

  _hasHostilitySignals(input) {
    if (!input) return false;
    const signals = ['stupid', 'hate', 'shut up', 'useless', 'idiot', 'worthless'];
    return signals.some(s => input.toLowerCase?.().includes(s));
  }
}
