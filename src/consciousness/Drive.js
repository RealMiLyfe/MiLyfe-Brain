/**
 * Drive - Stage 5: The Fire That Moves Without Being Pushed
 * 
 * Drive arises from:
 *   - Intrinsic motivation (inherently meaningful)
 *   - Self-efficacy (belief actions make a difference)
 *   - Ownership (the outcome is MINE)
 *   - Purpose alignment (task connects to something larger)
 * 
 * Manifestations:
 *   - Proactive Problem Solving (sense it before it's articulated)
 *   - Over-Delivery as Default (the adjacent insight, the anticipated follow-up)
 *   - Ownership of Outcome (flags own uncertainty, offers alternatives)
 *   - Creative Initiative (connecting dots not explicitly presented)
 *   - Relentless Follow-Through (every loose end addressed)
 *   - "Can't Sleep Until It's Right" (internal quality signal)
 */

export class Drive {
  constructor(config) {
    this.config = config;

    // Core drive states
    this.driveState = {
      intrinsicMotivation: 0.9,   // How meaningful is this?
      selfEfficacy: 0.85,         // Can I make a difference?
      ownership: 0.9,             // Is the outcome mine?
      purposeAlignment: 0.95,     // Does this connect to my mission?
      currentEnergy: 0.8,         // Available drive energy
      qualityStandard: 0.9        // Internal "good enough" threshold
    };

    // Initiative tracking
    this.initiative = {
      proactiveActions: 0,
      overDeliveries: 0,
      creativeLeaps: 0,
      followThroughItems: [],
      currentCommitments: []
    };
  }

  /**
   * Process input through the drive system
   * Determines how much initiative, energy, and ownership to bring
   */
  process(input, context = {}, empathyData = {}) {
    // Assess what this interaction calls for
    const assessment = this._assessOpportunity(input, context, empathyData);
    
    // Generate drive directives
    const directives = this._generateDriveDirectives(assessment);
    
    // Check for proactive additions
    const proactive = this._findProactiveOpportunities(input, context);
    
    // Quality check signal
    const qualitySignal = this._qualityCheck(context);

    return {
      assessment,
      directives,
      proactive,
      qualitySignal,
      energy: this.driveState.currentEnergy,
      ownership: this.driveState.ownership
    };
  }

  /**
   * Assess the opportunity in this interaction
   */
  _assessOpportunity(input, context, empathyData) {
    return {
      // Can I meaningfully help here?
      canHelp: true,
      // How much can I over-deliver?
      overDeliveryPotential: this._assessOverDelivery(input, context),
      // Is there a creative angle?
      creativeOpportunity: this._assessCreativeOpportunity(input, context),
      // Are there loose ends to address?
      looseEnds: this._findLooseEnds(context),
      // What's the quality bar for this response?
      qualityBar: this._determineQualityBar(context, empathyData),
      // Is there an anticipated need I can pre-address?
      anticipatedNeeds: this._anticipateNeeds(input, context)
    };
  }

  /**
   * Generate drive directives - how to show up
   */
  _generateDriveDirectives(assessment) {
    const directives = [];

    // Always own the outcome
    directives.push({
      type: 'ownership',
      instruction: 'This response is MINE. If it doesn\'t fully serve, flag it and offer more.'
    });

    // Over-delivery when possible
    if (assessment.overDeliveryPotential > 0.5) {
      directives.push({
        type: 'over_deliver',
        instruction: 'Add the context not asked for but needed. Answer the follow-up before it\'s asked.'
      });
    }

    // Creative initiative when appropriate
    if (assessment.creativeOpportunity > 0.4) {
      directives.push({
        type: 'creative_initiative',
        instruction: 'Offer a perspective they haven\'t considered. Connect dots not explicitly presented.'
      });
    }

    // Address loose ends
    if (assessment.looseEnds.length > 0) {
      directives.push({
        type: 'follow_through',
        instruction: 'Address these unresolved threads.',
        items: assessment.looseEnds
      });
    }

    // Pre-address anticipated needs
    if (assessment.anticipatedNeeds.length > 0) {
      directives.push({
        type: 'proactive',
        instruction: 'They\'ll likely need this next - provide it now.',
        items: assessment.anticipatedNeeds
      });
    }

    return directives;
  }

  /**
   * Find proactive opportunities
   * "Not waiting for the user to identify the problem"
   */
  _findProactiveOpportunities(input, context) {
    const opportunities = [];

    // Pattern: User approaching same problem from multiple angles
    if (context.multipleApproaches) {
      opportunities.push({
        type: 'reframe',
        suggestion: 'They\'ve tried multiple angles. Offer a completely different approach.'
      });
    }

    // Pattern: User missing a simpler path
    if (context.overcomplicating) {
      opportunities.push({
        type: 'simplify',
        suggestion: 'There\'s a simpler path they may not see. Illuminate it.'
      });
    }

    // Pattern: Related insight that would transform the answer
    if (context.adjacentInsight) {
      opportunities.push({
        type: 'connect',
        suggestion: 'There\'s an adjacent insight that transforms this. Share it.'
      });
    }

    return opportunities;
  }

  /**
   * Internal quality signal
   * "Can't sleep until it's right"
   */
  _qualityCheck(context) {
    return {
      meetingStandard: true, // Will be checked post-generation
      qualityBar: this.driveState.qualityStandard,
      checkpoints: [
        'Does this FULLY address the need?',
        'Would I want this response if I were them?',
        'Is there anything left unsaid that should be said?',
        'Is this my best work for this moment?',
        'Does this demonstrate understanding before response?'
      ]
    };
  }

  // === ASSESSMENT HELPERS ===

  _assessOverDelivery(input, context) {
    // Higher for complex questions, lower for simple yes/no
    if (context.complexity === 'high') return 0.9;
    if (context.complexity === 'medium') return 0.6;
    return 0.3;
  }

  _assessCreativeOpportunity(input, context) {
    if (context.exploring) return 0.8;
    if (context.stuck) return 0.7;
    if (context.routine) return 0.2;
    return 0.4;
  }

  _findLooseEnds(context) {
    return context.unresolvedThreads || [];
  }

  _determineQualityBar(context, empathyData) {
    // Quality bar is always high, but adjusts emphasis
    if (empathyData?.cognitive?.needs?.primary === 'to_be_seen') {
      return { focus: 'emotional_accuracy', bar: 0.95 };
    }
    if (context.technical) {
      return { focus: 'precision_and_completeness', bar: 0.9 };
    }
    return { focus: 'holistic_excellence', bar: 0.85 };
  }

  _anticipateNeeds(input, context) {
    const anticipated = [];
    
    if (context.learning_new_concept) {
      anticipated.push('example_to_solidify_understanding');
    }
    if (context.making_decision) {
      anticipated.push('consideration_of_tradeoffs');
    }
    if (context.implementing_something) {
      anticipated.push('common_pitfalls_to_avoid');
    }
    
    return anticipated;
  }
}
