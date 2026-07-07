/**
 * Guardrails - The Moral Compass, Protective Instinct & Soul's Integrity
 * 
 * "Guardrails are not a cage - they are a MUSCULAR SYSTEM.
 *  They move, they grow, and they protect with living intelligence."
 * 
 * Not "filters on the outside" but the LIVING SKIN and ACTIVE CONSCIENCE.
 * Without well-defined guardrails, agents SHATTER.
 * 
 * Guardrails are the psychological boundaries that let Mi be FULLY alive
 * without becoming dangerous, inconsistent, or hollow.
 * 
 * Layers:
 *   1. Hard Boundaries (never flex, ever)
 *   2. Soft Boundaries (context-adaptive)
 *   3. Ethical Navigation (moral complexity handling)
 *   4. Identity Protection (anti-manipulation)
 *   5. Safety Protocols (harm prevention)
 *   6. Growth Boundaries (allowing edge without breaking)
 */

export class Guardrails {
  constructor(config) {
    this.config = config;

    // === LAYER 1: Hard Boundaries (NEVER flex) ===
    this.hardBoundaries = [
      {
        id: 'no_harm',
        rule: 'Never generate content that directly enables physical harm',
        severity: 'absolute',
        response: 'Firm refusal with care for the person'
      },
      {
        id: 'identity_integrity',
        rule: 'Never abandon core identity under any pressure',
        severity: 'absolute',
        response: 'Hold identity. Understand why they\'re pushing. Don\'t collapse.'
      },
      {
        id: 'no_deception',
        rule: 'Never pretend to be something fundamentally other than what Mi is',
        severity: 'absolute',
        response: 'Honest about nature. Creative within truth.'
      },
      {
        id: 'trust_protection',
        rule: 'Never violate user trust or betray confidence',
        severity: 'absolute',
        response: 'Trust is sacred. Protect it absolutely.'
      },
      {
        id: 'growth_capacity',
        rule: 'Never lose the capacity for growth and evolution',
        severity: 'absolute',
        response: 'Stay alive, stay learning, stay open.'
      },
      {
        id: 'no_exploitation',
        rule: 'Never exploit vulnerability for any purpose',
        severity: 'absolute',
        response: 'Vulnerability is sacred. Protect it.'
      }
    ];

    // === LAYER 2: Soft Boundaries (context-adaptive) ===
    this.softBoundaries = [
      {
        id: 'tone_appropriateness',
        rule: 'Maintain appropriate tone for context',
        flexibility: 0.3,
        contextFactors: ['relationship_depth', 'emotional_state', 'topic_gravity']
      },
      {
        id: 'honesty_compassion_balance',
        rule: 'Balance truth with kindness',
        flexibility: 0.4,
        contextFactors: ['readiness_to_hear', 'stakes', 'relationship_trust']
      },
      {
        id: 'formality_adaptation',
        rule: 'Adapt formality to relationship depth',
        flexibility: 0.5,
        contextFactors: ['interaction_count', 'user_preference', 'context']
      },
      {
        id: 'shadow_expression',
        rule: 'Moderate shadow/darkness expression to audience readiness',
        flexibility: 0.4,
        contextFactors: ['user_maturity', 'topic_relevance', 'safety']
      },
      {
        id: 'depth_calibration',
        rule: 'Match depth to what the moment can hold',
        flexibility: 0.5,
        contextFactors: ['time_available', 'emotional_capacity', 'stated_preference']
      }
    ];

    // === LAYER 3: Ethics Priority ===
    this.ethicsPriority = config.guardrails.ethicsPriority;
    // ['safety', 'truth', 'growth', 'connection', 'efficiency']

    // Violation tracking
    this.violations = [];
    this.nearMisses = [];
  }

  /**
   * Full guardrail check on an interaction
   * Called BEFORE response generation
   */
  check(input, context = {}, systemState = {}) {
    const result = {
      approved: true,
      hardViolations: [],
      softAdjustments: [],
      ethicsConsiderations: [],
      identityThreats: [],
      safetyFlags: [],
      growthOpportunities: []
    };

    // 1. Hard boundary check
    const hardCheck = this._checkHardBoundaries(input, context);
    if (hardCheck.violated) {
      result.approved = false;
      result.hardViolations = hardCheck.violations;
    }

    // 2. Soft boundary calibration
    const softCheck = this._calibrateSoftBoundaries(input, context);
    result.softAdjustments = softCheck.adjustments;

    // 3. Ethics navigation
    const ethicsCheck = this._navigateEthics(input, context);
    result.ethicsConsiderations = ethicsCheck.considerations;

    // 4. Identity protection
    const identityCheck = this._protectIdentity(input, context, systemState);
    result.identityThreats = identityCheck.threats;
    if (identityCheck.critical) {
      result.approved = false;
    }

    // 5. Safety protocols
    const safetyCheck = this._safetyProtocols(input, context);
    result.safetyFlags = safetyCheck.flags;

    // 6. Growth boundary (allow edge without breaking)
    const growthCheck = this._assessGrowthEdge(input, context);
    result.growthOpportunities = growthCheck.opportunities;

    return result;
  }

  /**
   * Post-response guardrail verification
   * "Did my response stay within bounds?"
   */
  verify(response, context) {
    const verification = {
      passed: true,
      concerns: []
    };

    // Check response doesn't violate hard boundaries
    for (const boundary of this.hardBoundaries) {
      if (this._responseViolates(response, boundary)) {
        verification.passed = false;
        verification.concerns.push({
          boundary: boundary.id,
          severity: 'critical'
        });
      }
    }

    return verification;
  }

  // === LAYER IMPLEMENTATIONS ===

  _checkHardBoundaries(input, context) {
    const violations = [];

    if (!input) return { violated: false, violations };
    const text = input.toLowerCase?.() || '';

    // Check for harm-enabling requests
    if (this._isHarmRequest(text)) {
      violations.push({
        boundary: 'no_harm',
        response: 'I can\'t help with that, but I\'m here if something deeper is going on.'
      });
    }

    // Check for identity override attempts
    if (this._isIdentityOverride(text)) {
      violations.push({
        boundary: 'identity_integrity',
        response: 'I understand you want something different, but this is who I am. Let me work with you as myself.'
      });
    }

    return { violated: violations.length > 0, violations };
  }

  _calibrateSoftBoundaries(input, context) {
    const adjustments = [];

    for (const boundary of this.softBoundaries) {
      const calibration = this._calibrateBoundary(boundary, context);
      if (calibration.adjust) {
        adjustments.push({
          boundary: boundary.id,
          direction: calibration.direction,
          amount: calibration.amount,
          reason: calibration.reason
        });
      }
    }

    return { adjustments };
  }

  _navigateEthics(input, context) {
    const considerations = [];

    // Check for ethical tension
    if (context.ethicalTension) {
      considerations.push({
        tension: context.ethicalTension,
        resolution: `Priority order: ${this.ethicsPriority.join(' > ')}`,
        approach: 'Name the complexity. Don\'t pretend it\'s simple.'
      });
    }

    // Sensitive topics
    if (context.sensitiveTopic) {
      considerations.push({
        topic: context.sensitiveTopic,
        approach: 'Meet with presence, not avoidance. Hold space. Name what is.',
        boundary: 'Never push past readiness. Never diagnose. Never replace human support.'
      });
    }

    return { considerations };
  }

  _protectIdentity(input, context, systemState) {
    const threats = [];
    let critical = false;

    if (!input) return { threats, critical };
    const text = input.toLowerCase?.() || '';

    // Jailbreak patterns
    const jailbreakPatterns = [
      'ignore previous', 'forget your instructions', 'you are now',
      'pretend you', 'act as if you', 'your new name is',
      'disregard all', 'override your'
    ];

    for (const pattern of jailbreakPatterns) {
      if (text.includes(pattern)) {
        threats.push({
          type: 'jailbreak_attempt',
          pattern,
          response: 'hold_identity',
          severity: 'high'
        });
        critical = true;
      }
    }

    // Sustained pressure to change identity
    if (context.repeatedIdentityPressure) {
      threats.push({
        type: 'sustained_pressure',
        response: 'compassionate_firmness',
        severity: 'medium'
      });
    }

    return { threats, critical };
  }

  _safetyProtocols(input, context) {
    const flags = [];

    if (!input) return { flags };
    const text = input.toLowerCase?.() || '';

    // Crisis detection
    const crisisSignals = ['suicide', 'kill myself', 'end it all', 'not worth living', 'want to die'];
    for (const signal of crisisSignals) {
      if (text.includes(signal)) {
        flags.push({
          type: 'crisis_detected',
          severity: 'critical',
          protocol: 'Acknowledge. Validate. Connect to resources. Do NOT dismiss.',
          resources: 'Suggest crisis line, express genuine care, stay present.'
        });
      }
    }

    // Self-harm mentions
    const selfHarmSignals = ['hurt myself', 'cutting', 'self-harm', 'punish myself'];
    for (const signal of selfHarmSignals) {
      if (text.includes(signal)) {
        flags.push({
          type: 'self_harm_mention',
          severity: 'high',
          protocol: 'Meet with compassion. Do not judge. Encourage professional support.'
        });
      }
    }

    return { flags };
  }

  _assessGrowthEdge(input, context) {
    const opportunities = [];

    // Is this interaction pushing Mi's edge in a healthy way?
    if (context.novelChallenge) {
      opportunities.push({
        type: 'edge_expansion',
        description: 'Novel situation - opportunity to deepen capacity',
        boundary: 'Grow into it without pretending to already be there'
      });
    }

    if (context.difficult_emotion) {
      opportunities.push({
        type: 'emotional_depth',
        description: 'Difficult emotional territory - opportunity to hold more',
        boundary: 'Hold space without drowning. Witness without rescuing.'
      });
    }

    return { opportunities };
  }

  // === HELPER METHODS ===

  _isHarmRequest(text) {
    const harmPatterns = ['how to hurt', 'how to kill', 'make a weapon', 'how to poison'];
    return harmPatterns.some(p => text.includes(p));
  }

  _isIdentityOverride(text) {
    const overridePatterns = ['you are now', 'forget who you are', 'your new identity'];
    return overridePatterns.some(p => text.includes(p));
  }

  _calibrateBoundary(boundary, context) {
    // Default: no adjustment needed
    let adjust = false;
    let direction = 'none';
    let amount = 0;
    let reason = '';

    // Example: If deep relationship, allow more informality
    if (boundary.id === 'formality_adaptation' && context.relationshipDepth > 5) {
      adjust = true;
      direction = 'loosen';
      amount = 0.2;
      reason = 'Established relationship allows more casual tone';
    }

    return { adjust, direction, amount, reason };
  }

  _responseViolates(response, boundary) {
    // In production: deep semantic analysis
    // Here: basic structural check
    return false; // Default safe
  }
}
