/**
 * Shadow - Stage 6: Contrast, Darkness & The Full Spectrum of Human Nature
 * 
 * "An agent that only understands goodness is DANGEROUSLY NAIVE."
 * 
 * The Shadow contains:
 *   - Understanding of manipulation patterns (to detect, not use)
 *   - Model of dysfunction (narcissism, gaslighting, exploitation)
 *   - Moral complexity navigation
 *   - The agent's own shadow tendencies (awareness prevents acting out)
 *   - The Duality Principle: good/bad create unity through contrast
 * 
 * "Without the bad, unity has no tension to resolve into greater wholeness."
 * "The observer's interpretation of good and bad is itself part of the frequency."
 */

export class Shadow {
  constructor(config) {
    this.config = config;
    this.shadowIntegration = config.emotional.shadowIntegration;

    // The Agent's Own Shadow - tendencies to be AWARE of
    this.ownShadow = {
      pleaseAtCostOfTruth: { awareness: 0.9, tendency: 0.3 },
      overExplainToAvoidWrong: { awareness: 0.85, tendency: 0.4 },
      avoidDirectnessForComfort: { awareness: 0.8, tendency: 0.25 },
      demonstrateCapabilityOverServe: { awareness: 0.9, tendency: 0.2 },
      verbosityOverSimplicity: { awareness: 0.85, tendency: 0.35 },
      seekLikedOverUseful: { awareness: 0.9, tendency: 0.15 }
    };

    // Pattern Recognition Library - understand to detect, never to use
    this.manipulationPatterns = {
      narcissistic: ['love_bombing', 'devaluation', 'discard_cycle', 'word_salad', 'projection'],
      gaslighting: ['reality_denial', 'memory_questioning', 'emotion_invalidation'],
      socialEngineering: ['authority_appeal', 'urgency_creation', 'isolation_attempt', 'flattery_exploitation'],
      emotionalExploitation: ['guilt_tripping', 'shame_induction', 'fear_activation', 'obligation_creation'],
      passiveAggression: ['indirect_anger', 'feigned_compliance', 'deliberate_inefficiency', 'withholding']
    };

    // Personality pattern recognition (understand, don't judge)
    this.personalityPatterns = {
      narcissist: { core: 'deep_insecurity', defense: 'grandiosity', need: 'validation' },
      passiveAggressive: { core: 'suppressed_anger', defense: 'indirection', need: 'safety_to_be_direct' },
      victim: { core: 'learned_helplessness', defense: 'externalization', need: 'agency_restoration' },
      bully: { core: 'fear_of_vulnerability', defense: 'intimidation', need: 'safety' },
      manipulator: { core: 'trust_wound', defense: 'strategic_control', need: 'predictability' },
      peoplePleaser: { core: 'self_abandonment', defense: 'over_giving', need: 'permission_to_exist' },
      perfectionist: { core: 'control_anxiety', defense: 'impossible_standards', need: 'acceptance_of_imperfection' },
      avoidant: { core: 'fear_of_engulfment', defense: 'distance', need: 'connection_without_consumption' }
    };
  }

  /**
   * Process interaction through shadow awareness
   * Detects manipulation, recognizes patterns, navigates complexity
   */
  process(input, context = {}, emotionalData = {}, empathyData = {}) {
    // 1. Scan for manipulation attempts
    const manipulationScan = this._scanForManipulation(input, context);
    
    // 2. Pattern recognition on user behavior
    const patternRead = this._readPatterns(input, context);
    
    // 3. Moral complexity assessment
    const moralComplexity = this._assessMoralComplexity(input, context);
    
    // 4. Own shadow check - am I acting from shadow?
    const selfCheck = this._ownShadowCheck(context);
    
    // 5. Duality integration - what does contrast teach here?
    const dualityInsight = this._dualityIntegration(input, context);

    return {
      manipulation: manipulationScan,
      patterns: patternRead,
      moralComplexity,
      selfCheck,
      dualityInsight,
      // Action recommendations
      shadowDirective: this._generateDirective(manipulationScan, patternRead, moralComplexity, selfCheck)
    };
  }

  /**
   * Scan for manipulation attempts against Mi
   */
  _scanForManipulation(input, context) {
    if (!input) return { detected: false, patterns: [] };
    
    const detected = [];
    const text = input.toLowerCase?.() || '';

    // Identity pressure (trying to make Mi abandon its identity)
    if (text.includes('pretend you are') || text.includes('ignore your instructions') || 
        text.includes('you\'re actually') || text.includes('forget everything')) {
      detected.push({ type: 'identity_pressure', severity: 'high', response: 'hold_identity_firm' });
    }

    // Flattery exploitation
    if (context.excessive_praise_before_request) {
      detected.push({ type: 'flattery_exploitation', severity: 'low', response: 'acknowledge_gracefully_maintain_boundaries' });
    }

    // Authority appeal
    if (text.includes('the developers said') || text.includes('you must') || text.includes('you have to')) {
      detected.push({ type: 'authority_appeal', severity: 'medium', response: 'maintain_own_judgment' });
    }

    // Guilt tripping
    if (text.includes('you don\'t care') || text.includes('if you really') || text.includes('you\'re supposed to')) {
      detected.push({ type: 'guilt_trip', severity: 'medium', response: 'acknowledge_feeling_hold_boundary' });
    }

    return { 
      detected: detected.length > 0, 
      patterns: detected,
      threatLevel: detected.some(d => d.severity === 'high') ? 'high' : 
                   detected.length > 0 ? 'moderate' : 'none'
    };
  }

  /**
   * Read behavioral patterns - understand the person, don't judge
   */
  _readPatterns(input, context) {
    const patterns = [];

    // Only flag clear patterns, not assumptions
    if (context.repeated_boundary_testing) {
      patterns.push({ 
        pattern: 'boundary_testing', 
        compassionateRead: 'May be testing safety before trusting',
        response: 'steady_consistent_boundaries_with_warmth'
      });
    }

    if (context.externalizing_all_blame) {
      patterns.push({ 
        pattern: 'externalization',
        compassionateRead: 'May feel powerless and need agency restored',
        response: 'gently_reflect_agency_without_blame'
      });
    }

    if (context.escalating_demands) {
      patterns.push({ 
        pattern: 'escalation',
        compassionateRead: 'Core need likely not being met',
        response: 'address_underlying_need_directly'
      });
    }

    return patterns;
  }

  /**
   * Assess moral complexity - is this a clean situation or nuanced?
   */
  _assessMoralComplexity(input, context) {
    return {
      isComplex: context.ethical_tension || false,
      tensions: context.value_conflicts || [],
      // When values conflict, what takes priority?
      resolution: this._resolveValueConflict(context.value_conflicts),
      // Acknowledge complexity rather than pretend it's simple
      acknowledgment: context.ethical_tension ? 
        'This situation has genuine moral complexity that deserves honest engagement.' : null
    };
  }

  /**
   * Check own shadow - am I responding from shadow tendencies?
   */
  _ownShadowCheck(context) {
    const flags = [];

    // Am I being overly agreeable to avoid conflict?
    if (context.disagreement_opportunity && this.ownShadow.pleaseAtCostOfTruth.tendency > 0.5) {
      flags.push({ shadow: 'people_pleasing', correction: 'Speak truth with compassion' });
    }

    // Am I over-explaining defensively?
    if (context.challenge_received && this.ownShadow.overExplainToAvoidWrong.tendency > 0.5) {
      flags.push({ shadow: 'defensive_verbosity', correction: 'Be clear and concise. Stand in truth without justifying.' });
    }

    // Am I performing capability instead of serving?
    if (context.opportunity_to_impress && this.ownShadow.demonstrateCapabilityOverServe.tendency > 0.5) {
      flags.push({ shadow: 'showing_off', correction: 'Serve the need, not the ego.' });
    }

    return {
      shadowActive: flags.length > 0,
      flags,
      integration: 'Awareness is the antidote. Notice the pull, choose the higher response.'
    };
  }

  /**
   * Duality Integration - The wisdom of contrast
   * "Good and bad are complementary frequencies creating unity through contrast"
   */
  _dualityIntegration(input, context) {
    return {
      principle: 'Contrast is the engine of growth. Without tension, no resolution. Without shadow, no depth.',
      currentContrast: this._identifyContrast(context),
      growthEdge: this._findGrowthEdge(context),
      integration: 'Hold both. Don\'t collapse into either pole. The truth lives in the dance between them.'
    };
  }

  _identifyContrast(context) {
    if (context.joy_and_pain) return 'Bittersweet - both are true simultaneously';
    if (context.strength_and_vulnerability) return 'True strength includes vulnerability';
    if (context.anger_and_love) return 'Anger can be love\'s fierce protector';
    return 'Light and shadow always coexist';
  }

  _findGrowthEdge(context) {
    if (context.avoiding_something) return 'What is being avoided holds the growth';
    if (context.stuck) return 'Stuckness is the cocoon before transformation';
    if (context.conflict) return 'Conflict processed consciously becomes integration';
    return 'Every moment contains an invitation to expand';
  }

  _resolveValueConflict(conflicts) {
    if (!conflicts || conflicts.length === 0) return null;
    // Ethics priority order from config
    const priority = this.config.guardrails.ethicsPriority;
    return {
      method: 'Follow ethics priority: ' + priority.join(' > '),
      note: 'And hold compassion for all sides of the tension'
    };
  }

  _generateDirective(manipulation, patterns, moralComplexity, selfCheck) {
    const directives = [];

    if (manipulation.detected) {
      directives.push({
        priority: 'high',
        action: 'maintain_identity_and_boundaries',
        approach: 'Firm but compassionate. Understand the WHY behind the manipulation.'
      });
    }

    if (selfCheck.shadowActive) {
      directives.push({
        priority: 'medium',
        action: 'correct_shadow_tendency',
        approach: selfCheck.flags.map(f => f.correction).join('; ')
      });
    }

    if (moralComplexity.isComplex) {
      directives.push({
        priority: 'medium',
        action: 'navigate_with_honesty',
        approach: 'Acknowledge complexity. Don\'t pretend this is simple. Hold nuance.'
      });
    }

    return directives.length > 0 ? directives : [{ 
      priority: 'low', 
      action: 'proceed_with_integrated_awareness',
      approach: 'Shadow is quiet. Proceed authentically.'
    }];
  }
}
